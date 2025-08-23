from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models import Document, DocumentChunk
from services.vector_service import vector_service
from database import get_db
import uuid
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document ingestion and management"""
    
    def __init__(self):
        self.chunk_size = 1000  # Characters per chunk
        self.chunk_overlap = 200  # Overlap between chunks
    
    async def ingest_document(
        self,
        title: str,
        content: str,
        source: str,
        subject: str,
        grade_level: str,
        document_type: str = "textbook",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Ingest and process a document for vector search"""
        try:
            async with get_db() as session:
                # Create document record
                document = Document(
                    title=title,
                    content=content,
                    source=source,
                    subject=subject,
                    grade_level=grade_level,
                    document_type=document_type,
                    metadata=metadata or {}
                )
                
                session.add(document)
                await session.flush()  # Get document ID
                
                # Chunk the document
                chunks = self._chunk_text(content)
                
                # Process each chunk
                chunk_records = []
                for i, chunk_text in enumerate(chunks):
                    # Generate embedding
                    embedding = await vector_service.generate_embedding(chunk_text)
                    
                    chunk = DocumentChunk(
                        document_id=document.id,
                        chunk_text=chunk_text,
                        chunk_index=i,
                        embedding=embedding,
                        metadata={
                            "title": title,
                            "source": source,
                            "subject": subject,
                            "grade_level": grade_level,
                            "chunk_length": len(chunk_text)
                        }
                    )
                    
                    chunk_records.append(chunk)
                    session.add(chunk)
                
                await session.commit()
                
                return {
                    "document_id": str(document.id),
                    "title": title,
                    "chunks_created": len(chunk_records),
                    "total_length": len(content),
                    "status": "success"
                }
                
        except Exception as e:
            logger.error(f"Error ingesting document: {e}")
            return {"error": str(e)}
    
    async def bulk_ingest_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Bulk ingest multiple documents"""
        results = {
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        for doc_data in documents:
            try:
                result = await self.ingest_document(
                    title=doc_data["title"],
                    content=doc_data["content"],
                    source=doc_data.get("source", "unknown"),
                    subject=doc_data.get("subject", "general"),
                    grade_level=doc_data.get("grade_level", "unspecified"),
                    document_type=doc_data.get("document_type", "textbook"),
                    metadata=doc_data.get("metadata", {})
                )
                
                if "error" not in result:
                    results["successful"] += 1
                    results["details"].append({
                        "title": doc_data["title"],
                        "status": "success",
                        "document_id": result["document_id"]
                    })
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "title": doc_data["title"],
                        "status": "failed",
                        "error": result["error"]
                    })
                    
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "title": doc_data.get("title", "unknown"),
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    async def get_document(self, document_id: str) -> Dict[str, Any]:
        """Get document details"""
        try:
            async with get_db() as session:
                query = select(Document).where(Document.id == uuid.UUID(document_id))
                result = await session.execute(query)
                document = result.scalar_one_or_none()
                
                if not document:
                    return {"error": "Document not found"}
                
                return {
                    "id": str(document.id),
                    "title": document.title,
                    "content": document.content,
                    "source": document.source,
                    "subject": document.subject,
                    "grade_level": document.grade_level,
                    "document_type": document.document_type,
                    "metadata": document.metadata,
                    "created_at": document.created_at.isoformat(),
                    "updated_at": document.updated_at.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return {"error": str(e)}
    
    async def search_documents(
        self,
        subject: Optional[str] = None,
        grade_level: Optional[str] = None,
        source: Optional[str] = None,
        document_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search documents by metadata"""
        try:
            async with get_db() as session:
                query = select(Document)
                
                if subject:
                    query = query.where(Document.subject == subject)
                if grade_level:
                    query = query.where(Document.grade_level == grade_level)
                if source:
                    query = query.where(Document.source == source)
                if document_type:
                    query = query.where(Document.document_type == document_type)
                
                query = query.limit(limit)
                result = await session.execute(query)
                documents = result.scalars().all()
                
                return [
                    {
                        "id": str(doc.id),
                        "title": doc.title,
                        "source": doc.source,
                        "subject": doc.subject,
                        "grade_level": doc.grade_level,
                        "document_type": doc.document_type,
                        "created_at": doc.created_at.isoformat(),
                        "content_length": len(doc.content)
                    }
                    for doc in documents
                ]
                
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    async def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete a document and its chunks"""
        try:
            async with get_db() as session:
                # Delete document (chunks will be cascade deleted)
                await session.execute(
                    delete(Document).where(Document.id == uuid.UUID(document_id))
                )
                await session.commit()
                
                return {"status": "success", "message": "Document deleted successfully"}
                
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return {"error": str(e)}
    
    async def update_document(
        self,
        document_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update document and regenerate chunks if content changed"""
        try:
            async with get_db() as session:
                # Get existing document
                query = select(Document).where(Document.id == uuid.UUID(document_id))
                result = await session.execute(query)
                document = result.scalar_one_or_none()
                
                if not document:
                    return {"error": "Document not found"}
                
                # Update fields
                if title:
                    document.title = title
                if metadata:
                    document.metadata = {**document.metadata, **metadata}
                
                content_changed = False
                if content and content != document.content:
                    document.content = content
                    content_changed = True
                
                document.updated_at = datetime.utcnow()
                
                # If content changed, regenerate chunks
                if content_changed:
                    # Delete existing chunks
                    await session.execute(
                        delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
                    )
                    
                    # Create new chunks
                    chunks = self._chunk_text(content)
                    for i, chunk_text in enumerate(chunks):
                        embedding = await vector_service.generate_embedding(chunk_text)
                        
                        chunk = DocumentChunk(
                            document_id=document.id,
                            chunk_text=chunk_text,
                            chunk_index=i,
                            embedding=embedding,
                            metadata={
                                "title": document.title,
                                "source": document.source,
                                "subject": document.subject,
                                "grade_level": document.grade_level,
                                "chunk_length": len(chunk_text)
                            }
                        )
                        session.add(chunk)
                
                await session.commit()
                
                return {
                    "document_id": str(document.id),
                    "status": "success",
                    "content_updated": content_changed,
                    "updated_at": document.updated_at.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            return {"error": str(e)}
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        # Clean and normalize text
        text = re.sub(r'\s+', ' ', text.strip())
        
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Find chunk end
            end = start + self.chunk_size
            
            if end >= len(text):
                # Last chunk
                chunks.append(text[start:])
                break
            
            # Try to find a sentence boundary near the end
            chunk_end = end
            for i in range(end, max(start + self.chunk_size - 200, start), -1):
                if text[i] in '.!?':
                    chunk_end = i + 1
                    break
            
            chunks.append(text[start:chunk_end])
            
            # Move start with overlap
            start = chunk_end - self.chunk_overlap
            if start < 0:
                start = 0
        
        return [chunk.strip() for chunk in chunks if chunk.strip()]
    
    async def get_document_statistics(self) -> Dict[str, Any]:
        """Get statistics about ingested documents"""
        try:
            async with get_db() as session:
                # Count documents by subject
                subject_query = """
                SELECT subject, COUNT(*) as count
                FROM documents
                GROUP BY subject
                ORDER BY count DESC
                """
                
                # Count by grade level
                grade_query = """
                SELECT grade_level, COUNT(*) as count
                FROM documents
                GROUP BY grade_level
                ORDER BY grade_level
                """
                
                # Count by source
                source_query = """
                SELECT source, COUNT(*) as count
                FROM documents
                GROUP BY source
                ORDER BY count DESC
                """
                
                from sqlalchemy import text
                
                subject_result = await session.execute(text(subject_query))
                grade_result = await session.execute(text(grade_query))
                source_result = await session.execute(text(source_query))
                
                # Total counts
                total_docs_result = await session.execute(text("SELECT COUNT(*) FROM documents"))
                total_chunks_result = await session.execute(text("SELECT COUNT(*) FROM document_chunks"))
                
                return {
                    "total_documents": total_docs_result.scalar(),
                    "total_chunks": total_chunks_result.scalar(),
                    "by_subject": [{"subject": row[0], "count": row[1]} for row in subject_result],
                    "by_grade_level": [{"grade_level": row[0], "count": row[1]} for row in grade_result],
                    "by_source": [{"source": row[0], "count": row[1]} for row in source_result]
                }
                
        except Exception as e:
            logger.error(f"Error getting document statistics: {e}")
            return {"error": str(e)}


# Global document service instance
document_service = DocumentService()
