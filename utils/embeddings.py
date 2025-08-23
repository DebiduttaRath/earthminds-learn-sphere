import openai
import numpy as np
from typing import List, Union
from config import settings
import logging
import asyncio
import time

logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = settings.openai_api_key


class EmbeddingService:
    """Service for generating and managing embeddings"""
    
    def __init__(self):
        self.model = settings.embedding_model
        self.max_retries = 3
        self.retry_delay = 1.0
        self.batch_size = 100  # Process embeddings in batches
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        return await self._generate_embeddings([text])[0]
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not texts:
            return []
        
        embeddings = []
        
        # Process in batches to avoid rate limits
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = await self._generate_embeddings_batch(batch)
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    async def _generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts with retry logic"""
        for attempt in range(self.max_retries):
            try:
                # Clean and validate texts
                cleaned_texts = [self._clean_text(text) for text in texts]
                
                response = await openai.Embedding.acreate(
                    model=self.model,
                    input=cleaned_texts
                )
                
                embeddings = [data.embedding for data in response.data]
                
                logger.info(f"Generated {len(embeddings)} embeddings using {response.usage.total_tokens} tokens")
                
                return embeddings
                
            except openai.error.RateLimitError as e:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Rate limit hit, waiting {wait_time} seconds (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)
                
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to generate embeddings after {self.max_retries} attempts")
                    raise
                    
            except openai.error.OpenAIError as e:
                logger.error(f"OpenAI API error: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                logger.error(f"Unexpected error generating embeddings: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay)
    
    def _clean_text(self, text: str) -> str:
        """Clean and prepare text for embedding"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Truncate if too long (OpenAI has token limits)
        max_length = 8000  # Conservative limit
        if len(text) > max_length:
            text = text[:max_length]
            logger.warning(f"Text truncated to {max_length} characters for embedding")
        
        return text
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def find_most_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 5
    ) -> List[tuple]:
        """Find most similar embeddings from candidates"""
        try:
            similarities = []
            
            for i, candidate in enumerate(candidate_embeddings):
                similarity = self.calculate_similarity(query_embedding, candidate)
                similarities.append((i, similarity))
            
            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Error finding similar embeddings: {e}")
            return []
    
    async def embed_query_for_search(self, query: str, context: str = "") -> List[float]:
        """Generate embedding optimized for search queries"""
        # Enhance query with context for better search results
        enhanced_query = query
        if context:
            enhanced_query = f"{context}: {query}"
        
        return await self.generate_embedding(enhanced_query)
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """Validate embedding format and content"""
        try:
            if not embedding:
                return False
            
            if not isinstance(embedding, list):
                return False
            
            if len(embedding) != 1536:  # OpenAI embedding dimension
                logger.warning(f"Unexpected embedding dimension: {len(embedding)}")
                return False
            
            # Check for valid numbers
            for val in embedding:
                if not isinstance(val, (int, float)) or np.isnan(val) or np.isinf(val):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating embedding: {e}")
            return False
    
    async def get_embedding_stats(self, embeddings: List[List[float]]) -> dict:
        """Get statistics about a collection of embeddings"""
        try:
            if not embeddings:
                return {"count": 0}
            
            embeddings_array = np.array(embeddings)
            
            stats = {
                "count": len(embeddings),
                "dimensions": embeddings_array.shape[1] if len(embeddings_array.shape) > 1 else 0,
                "mean_magnitude": float(np.mean(np.linalg.norm(embeddings_array, axis=1))),
                "std_magnitude": float(np.std(np.linalg.norm(embeddings_array, axis=1))),
                "min_value": float(np.min(embeddings_array)),
                "max_value": float(np.max(embeddings_array)),
                "mean_value": float(np.mean(embeddings_array))
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating embedding stats: {e}")
            return {"count": len(embeddings), "error": str(e)}


# Global embedding service instance
embedding_service = EmbeddingService()
