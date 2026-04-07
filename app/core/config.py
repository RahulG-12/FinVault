from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./finvault.db"
    SECRET_KEY: str = "finvault-super-secret-key-change-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "financial_docs"

    # Embedding model
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # Chunking
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64

    # Reranking top results
    TOP_K_VECTOR: int = 20
    TOP_K_RERANK: int = 5

    class Config:
        env_file = ".env"

settings = Settings()
