"""Database models using SQLAlchemy."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, Enum, ForeignKey, Index, ARRAY, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.database import Base


class RoleEnum(str, enum.Enum):
    """User role enumeration."""
    admin = "admin"
    user = "user"


class ActionEnum(str, enum.Enum):
    """Activity action enumeration."""
    login = "login"
    face_scan = "face_scan"
    download = "download"


class User(Base):
    """User model for both admin and regular users."""
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationship
    activity_logs: Mapped[list["ActivityLog"]] = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("ix_users_role", "role"),
        Index("ix_users_created_at", "created_at"),
    )


class Photo(Base):
    """Photo model for indexed wedding photos."""
    __tablename__ = "photos"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_file_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    drive_url: Mapped[str] = mapped_column(String, nullable=False)
    day_name: Mapped[str] = mapped_column(String, nullable=False)
    face_embedding: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("ix_photos_day_name", "day_name"),
        Index("ix_photos_indexed_at", "indexed_at"),
    )


class ActivityLog(Base):
    """Activity log model for tracking user actions."""
    __tablename__ = "activity_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[ActionEnum] = mapped_column(Enum(ActionEnum), nullable=False)
    photo_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="activity_logs")
    
    # Indexes
    __table_args__ = (
        Index("ix_activity_logs_user_id", "user_id"),
        Index("ix_activity_logs_action", "action"),
        Index("ix_activity_logs_timestamp", "timestamp"),
    )
