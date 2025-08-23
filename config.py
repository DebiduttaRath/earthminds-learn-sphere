import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/tutoring_platform")
    
    # OpenAI API
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Redis (for caching)
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Application
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # AI Settings
    max_tokens: int = int(os.getenv("MAX_TOKENS", "2000"))
    temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
    
    # Vector Search
    vector_search_limit: int = int(os.getenv("VECTOR_SEARCH_LIMIT", "5"))
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
    
    # Quiz Generation
    default_quiz_questions: int = int(os.getenv("DEFAULT_QUIZ_QUESTIONS", "10"))
    quiz_time_limit_minutes: int = int(os.getenv("QUIZ_TIME_LIMIT_MINUTES", "30"))
    
    class Config:
        env_file = ".env"


settings = Settings()
