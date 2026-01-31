"""Configuration management using Pydantic Settings."""
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection URL with asyncpg driver")
    
    # Authentication
    SECRET_KEY: str = Field(..., min_length=32, description="Secret key for JWT encoding")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, description="JWT token expiry in minutes")
    EVENT_PASSWORD: str = Field(..., description="Single event password for authentication")
    
    # Google Drive
    GOOGLE_DRIVE_CREDENTIALS_PATH: str = Field(..., description="Path to service account JSON")
    GOOGLE_DRIVE_FOLDER_ID: str = Field(..., description="Root folder ID containing day folders")
    
    # Face Recognition
    FACE_SIMILARITY_THRESHOLD: float = Field(default=0.6, ge=0.0, le=1.0, description="Face similarity threshold")
    FACE_DETECTION_MODEL: str = Field(default="hog", description="Face detection model (hog or cnn)")
    MAX_UPLOAD_SIZE_MB: int = Field(default=10, description="Maximum upload size in MB")
    
    # Application
    CORS_ORIGINS: str = Field(default="http://localhost:3000", description="Comma-separated CORS origins")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    @field_validator("FACE_DETECTION_MODEL")
    @classmethod
    def validate_face_model(cls, v: str) -> str:
        """Validate face detection model."""
        if v not in ["hog", "cnn"]:
            raise ValueError("FACE_DETECTION_MODEL must be 'hog' or 'cnn'")
        return v
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Get maximum upload size in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


# Singleton settings instance
settings = Settings()
