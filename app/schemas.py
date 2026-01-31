"""Pydantic v2 schemas for request/response validation."""
from datetime import datetime
from typing import List, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


# Authentication Schemas
class LoginRequest(BaseModel):
    """Login request schema."""
    password: str = Field(..., min_length=1, description="Event password")
    role: str = Field(..., pattern="^(admin|user)$", description="User role (admin or user)")


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    role: str = Field(..., description="User role")


# Photo Schemas
class PhotoResponse(BaseModel):
    """Photo response schema."""
    id: UUID
    drive_file_id: str
    drive_url: str
    day_name: str
    indexed_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MatchedPhotoGroup(BaseModel):
    """Matched photos grouped by day."""
    day_name: str
    photos: List[PhotoResponse]
    count: int


class MatchedPhotosResponse(BaseModel):
    """Response for face matching."""
    matched_photos: List[PhotoResponse]
    total_matches: int
    grouped_by_day: Dict[str, List[PhotoResponse]]


class ScanFaceResponse(BaseModel):
    """Response for face scan."""
    matched_photos: List[PhotoResponse]
    total_matches: int
    grouped_by_day: Dict[str, List[PhotoResponse]]


# Download Log Schema
class DownloadLogRequest(BaseModel):
    """Download log request schema."""
    photo_ids: List[UUID] = Field(..., min_length=1, description="List of photo IDs to log")


class DownloadLogResponse(BaseModel):
    """Download log response schema."""
    logged: bool = Field(default=True)


# Admin Schemas
class PhotosByDay(BaseModel):
    """Photos grouped by day count."""
    day_name: str
    count: int


class StatsResponse(BaseModel):
    """Admin statistics response."""
    total_photos: int
    total_users: int
    total_scans: int
    photos_by_day: Dict[str, int]
    last_index_time: Optional[datetime] = None


class PhotosSummaryResponse(BaseModel):
    """Photos summary response."""
    photos_by_day: List[PhotosByDay]
    total_photos: int


class ActivityLogResponse(BaseModel):
    """Activity log response."""
    id: UUID
    user_id: UUID
    action: str
    photo_count: Optional[int]
    timestamp: datetime
    user_role: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class ReindexRequest(BaseModel):
    """Reindex request schema."""
    force: bool = Field(default=False, description="Force reindex all photos")


class ReindexResponse(BaseModel):
    """Reindex response schema."""
    message: str
    total_photos_indexed: int
    new_photos_indexed: int
    photos_by_day: Dict[str, int]
    indexing_time_seconds: float


# User Info Schema
class UserInfo(BaseModel):
    """User information schema."""
    id: UUID
    role: str
    created_at: datetime
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# Health Check Schema
class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="healthy")
    timestamp: datetime
