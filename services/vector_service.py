import openai
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from models import DocumentChunk, Document
from database import get_db
from config import settings
import logging

logger = logging.getLogger(__name__)

# Configure OpenAI for embeddings
openai.api_key = settings.openai_api_key


class VectorService:
    """Service for vector operations and similarity search"""
    
    def __init__(self):
        self.embedding_model = settings.embedding_model
        self.search_limit = settings.vector_search_limit
        self.similarity_threshold = settings.similarity_threshold
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text"""
        try:
            response = await openai.Embedding.acreate(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    async def search_similar_documents(
        self,
        query: str,
        subject: Optional[str] = None,
        grade_level: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)
            
            # Use provided limit or default
            search_limit = limit or self.search_limit
            
            async with get_db() as session:
                # Build the query
                query_parts = [
                    "SELECT dc.id, dc.chunk_text, dc.chunk_index, dc.metadata,",
                    "d.title, d.source, d.subject, d.grade_level,",
                    "1 - (dc.embedding <=> :query_embedding) as similarity",
                    "FROM document_chunks dc",
                    "JOIN documents d ON dc.document_id = d.id",
                    "WHERE 1 - (dc.embedding <=> :query_embedding) > :threshold"
                ]
                
                params = {
                    "query_embedding": str(query_embedding),
                    "threshold": self.similarity_threshold
                }
                
                # Add optional filters
                if subject:
                    query_parts.append("AND d.subject = :subject")
                    params["subject"] = subject
                
                if grade_level:
                    query_parts.append("AND d.grade_level = :grade_level")
                    params["grade_level"] = grade_level
                
                query_parts.extend([
                    "ORDER BY similarity DESC",
                    "LIMIT :limit"
                ])
                params["limit"] = search_limit
                
                query_sql = " ".join(query_parts)
                
                result = await session.execute(text(query_sql), params)
                rows = result.fetchall()
                
                # Format results
                documents = []
                for row in rows:
                    documents.append({
                        "id": str(row.id),
                        "content": row.chunk_text,
                        "title": row.title,
                        "source": row.source,
                        "subject": row.subject,
                        "grade_level": row.grade_level,
                        "similarity": float(row.similarity),
                        "chunk_index": row.chunk_index,
                        "metadata": row.metadata
                    })
                
                return documents
                
        except Exception as e:
            logger.error(f"Error searching similar documents: {e}")
            return []
    
    async def search_by_topic(
        self,
        topic: str,
        subject: Optional[str] = None,
        grade_level: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search documents by topic with enhanced query"""
        # Enhance the query for better search results
        enhanced_query = f"Educational content about {topic}"
        if subject:
            enhanced_query += f" in {subject}"
        if grade_level:
            enhanced_query += f" for grade {grade_level}"
        
        return await self.search_similar_documents(
            query=enhanced_query,
            subject=subject,
            grade_level=grade_level,
            limit=limit
        )
    
    async def get_document_recommendations(
        self,
        student_profile: Dict[str, Any],
        recent_topics: List[str]
    ) -> List[Dict[str, Any]]:
        """Get personalized document recommendations for a student"""
        try:
            # Build recommendation query based on student profile and recent topics
            preferred_subjects = student_profile.get("preferred_subjects", [])
            grade_level = student_profile.get("grade_level")
            
            all_recommendations = []
            
            # Search for documents related to recent topics
            for topic in recent_topics[-3:]:  # Last 3 topics
                docs = await self.search_by_topic(
                    topic=topic,
                    grade_level=grade_level,
                    limit=3
                )
                all_recommendations.extend(docs)
            
            # Search for documents in preferred subjects
            for subject in preferred_subjects:
                docs = await self.search_similar_documents(
                    query=f"educational content for {subject}",
                    subject=subject,
                    grade_level=grade_level,
                    limit=2
                )
                all_recommendations.extend(docs)
            
            # Remove duplicates and sort by similarity
            seen_ids = set()
            unique_recommendations = []
            for doc in all_recommendations:
                if doc["id"] not in seen_ids:
                    seen_ids.add(doc["id"])
                    unique_recommendations.append(doc)
            
            # Sort by similarity score
            unique_recommendations.sort(key=lambda x: x["similarity"], reverse=True)
            
            return unique_recommendations[:10]  # Return top 10 recommendations
            
        except Exception as e:
            logger.error(f"Error getting document recommendations: {e}")
            return []
    
    async def update_document_embedding(self, chunk_id: str, new_text: str):
        """Update embedding for a document chunk"""
        try:
            new_embedding = await self.generate_embedding(new_text)
            
            async with get_db() as session:
                await session.execute(
                    text("UPDATE document_chunks SET embedding = :embedding WHERE id = :chunk_id"),
                    {"embedding": str(new_embedding), "chunk_id": chunk_id}
                )
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error updating document embedding: {e}")
            raise


# Global vector service instance
vector_service = VectorService()
