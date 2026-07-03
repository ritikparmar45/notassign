import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API Configuration
    PROJECT_NAME: str = "Notification Service"
    API_V1_STR: str = "/api/v1"
    API_KEY: str = Field(default="dev-api-key-12345", description="Simple API Key for authorization")
    MOCK_MODE: bool = Field(default=False, description="Whether to run the application in-memory with mocked DB and Redis")
    
    # MongoDB Configuration
    MONGODB_URL: str = Field(default="mongodb://mongodb:27017", description="MongoDB connection URL")
    DATABASE_NAME: str = Field(default="notification_service", description="MongoDB database name")
    
    # Redis Configuration
    REDIS_URL: str = Field(default="redis://redis:6379/0", description="Redis connection URL")
    
    # Rate Limiting Configuration
    RATE_LIMIT_LIMIT: int = Field(default=100, description="Max notifications per user")
    RATE_LIMIT_WINDOW: int = Field(default=3600, description="Window size in seconds (1 hour)")
    
    # Provider Settings
    PROVIDER_FAIL_RATE: float = Field(default=0.20, description="Probability of simulated provider failure (0.0 to 1.0)")
    
    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_FAILURES_THRESHOLD: int = Field(default=3, description="Consecutive failures before tripping breaker")
    CIRCUIT_BREAKER_RECOVERY_TIME: int = Field(default=30, description="Time in seconds before trying to reset the breaker")
    
    # Celery Configuration
    CELERY_BROKER_URL: str = Field(default="redis://redis:6379/0", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://redis:6379/0", description="Celery result backend URL")
    
    # Webhooks
    WEBHOOK_TIMEOUT: float = Field(default=5.0, description="Timeout for webhook requests in seconds")
    WEBHOOK_MAX_RETRIES: int = Field(default=3, description="Max retries for webhook dispatching")

settings = Settings()
