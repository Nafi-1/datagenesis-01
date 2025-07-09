
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    supabase_url: str = "your_supabase_url"
    supabase_key: str = "your_supabase_anon_key" 
    supabase_service_role_key: str = "your_supabase_service_role_key"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_password: Optional[str] = None
    
    # AI Services - Fixed to properly read from .env
    gemini_api_key: str = ""
    google_cloud_project_id: Optional[str] = None
    
    # Vector Database
    pinecone_api_key: str = "your_pinecone_api_key"
    pinecone_environment: str = "us-east-1-aws"
    pinecone_index_name: str = "datagenesis-embeddings"
    
    # Security
    secret_key: str = "your-super-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Celery/Background Jobs
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # API Settings
    api_v1_str: str = "/api"
    project_name: str = "DataGenesis AI"
    
    # Generation Settings
    max_concurrent_generations: int = 5
    max_dataset_size_mb: int = 100
    default_cache_ttl: int = 3600  # 1 hour
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Add extra configuration to help with environment loading
        extra = "allow"
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure we get the GEMINI_API_KEY if it's not loaded properly
        if not self.gemini_api_key:
            self.gemini_api_key = os.getenv('GEMINI_API_KEY', '')

settings = Settings()
