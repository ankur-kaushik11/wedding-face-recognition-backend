"""Admin routes for administrative operations."""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database import get_db
from app.dependencies import require_admin
from app.models import User, Photo, ActivityLog, ActionEnum
from app.schemas import (
    StatsResponse,
    ActivityLogResponse,
    PhotosSummaryResponse,
    PhotosByDay,
    ReindexRequest,
    ReindexResponse
)
from app.face_engine import face_engine
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get administrative statistics.
    
    Returns:
        Statistics including total photos, users, scans, and photos by day
    """
    try:
        # Total photos (distinct by drive_file_id)
        result = await db.execute(
            select(func.count(func.distinct(Photo.drive_file_id)))
        )
        total_photos = result.scalar() or 0
        
        # Total users
        result = await db.execute(select(func.count(User.id)))
        total_users = result.scalar() or 0
        
        # Total face scans
        result = await db.execute(
            select(func.count(ActivityLog.id)).where(ActivityLog.action == ActionEnum.face_scan)
        )
        total_scans = result.scalar() or 0
        
        # Photos by day
        result = await db.execute(
            select(Photo.day_name, func.count(func.distinct(Photo.drive_file_id)))
            .group_by(Photo.day_name)
        )
        photos_by_day_rows = result.all()
        photos_by_day = {row[0]: row[1] for row in photos_by_day_rows}
        
        # Last index time
        result = await db.execute(
            select(func.max(Photo.indexed_at))
        )
        last_index_time = result.scalar()
        
        return StatsResponse(
            total_photos=total_photos,
            total_users=total_users,
            total_scans=total_scans,
            photos_by_day=photos_by_day,
            last_index_time=last_index_time
        )
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")


@router.get("/activity", response_model=List[ActivityLogResponse])
async def get_activity(
    limit: int = 100,
    user_id: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get activity logs with optional filtering.
    
    Args:
        limit: Maximum number of records to return (default: 100)
        user_id: Optional user ID to filter by
        
    Returns:
        List of activity logs with user information
    """
    try:
        query = select(ActivityLog, User).join(User, ActivityLog.user_id == User.id)
        
        if user_id:
            import uuid
            try:
                user_uuid = uuid.UUID(user_id)
                query = query.where(ActivityLog.user_id == user_uuid)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid user_id format")
        
        query = query.order_by(desc(ActivityLog.timestamp)).limit(limit)
        
        result = await db.execute(query)
        rows = result.all()
        
        # Build response with user role
        activity_logs = []
        for activity_log, user in rows:
            log_response = ActivityLogResponse(
                id=activity_log.id,
                user_id=activity_log.user_id,
                action=activity_log.action.value,
                photo_count=activity_log.photo_count,
                timestamp=activity_log.timestamp,
                user_role=user.role.value
            )
            activity_logs.append(log_response)
        
        return activity_logs
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting activity logs: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving activity logs: {str(e)}")


@router.get("/photos-summary", response_model=PhotosSummaryResponse)
async def get_photos_summary(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary of indexed photos grouped by day.
    
    Returns:
        Summary of photos by day with counts
    """
    try:
        # Get photos by day
        result = await db.execute(
            select(Photo.day_name, func.count(func.distinct(Photo.drive_file_id)))
            .group_by(Photo.day_name)
            .order_by(Photo.day_name)
        )
        rows = result.all()
        
        photos_by_day = [
            PhotosByDay(day_name=row[0], count=row[1])
            for row in rows
        ]
        
        total_photos = sum(item.count for item in photos_by_day)
        
        return PhotosSummaryResponse(
            photos_by_day=photos_by_day,
            total_photos=total_photos
        )
        
    except Exception as e:
        logger.error(f"Error getting photos summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving photos summary: {str(e)}")


@router.post("/reindex", response_model=ReindexResponse)
async def reindex_photos(
    request: ReindexRequest = ReindexRequest(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Reindex photos from Google Drive.
    
    Args:
        request: Reindex request with force flag
        
    Returns:
        Indexing results and statistics
    """
    try:
        logger.info(f"Starting reindex with force={request.force}")
        
        # Run indexing
        stats = await face_engine.index_all_photos(db, force=request.force)
        
        # Get total indexed photos
        result = await db.execute(
            select(func.count(func.distinct(Photo.drive_file_id)))
        )
        total_photos_indexed = result.scalar() or 0
        
        message = f"Indexing complete. Processed {stats['total_photos_processed']} photos."
        if stats['errors']:
            message += f" {len(stats['errors'])} errors occurred."
        
        return ReindexResponse(
            message=message,
            total_photos_indexed=total_photos_indexed,
            new_photos_indexed=stats['new_photos_indexed'],
            photos_by_day=stats['photos_by_day'],
            indexing_time_seconds=stats['indexing_time_seconds']
        )
        
    except Exception as e:
        logger.error(f"Error during reindexing: {e}")
        raise HTTPException(status_code=500, detail=f"Error during reindexing: {str(e)}")
