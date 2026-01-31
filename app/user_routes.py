"""User routes for face scanning and photo retrieval."""
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import require_user, limiter
from app.models import User, Photo, ActivityLog, ActionEnum
from app.schemas import (
    ScanFaceResponse,
    PhotoResponse,
    DownloadLogRequest,
    DownloadLogResponse
)
from app.face_engine import face_engine
from app.utils import validate_image_file
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["user"])


async def log_activity(db: AsyncSession, user_id, action: ActionEnum, photo_count: Optional[int] = None):
    """
    Helper function to log user activity.
    
    Args:
        db: Database session
        user_id: User ID
        action: Action type
        photo_count: Optional photo count for scan/download actions
    """
    activity_log = ActivityLog(
        user_id=user_id,
        action=action,
        photo_count=photo_count
    )
    db.add(activity_log)
    await db.commit()


@router.post("/scan-face", response_model=ScanFaceResponse)
@limiter.limit("5/minute")
async def scan_face(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Scan uploaded face image and find matching photos.
    
    Args:
        request: FastAPI request (for rate limiting)
        file: Uploaded image file
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Matched photos grouped by day
    """
    try:
        # Validate image file
        image_bytes = await validate_image_file(file)
        
        # Match face
        matched_photos = await face_engine.match_face(db, image_bytes)
        
        # Group by day
        grouped_by_day: Dict[str, List[PhotoResponse]] = {}
        for photo in matched_photos:
            photo_response = PhotoResponse.model_validate(photo)
            
            if photo.day_name not in grouped_by_day:
                grouped_by_day[photo.day_name] = []
            
            grouped_by_day[photo.day_name].append(photo_response)
        
        # Remove duplicate photos by drive_file_id
        unique_photos = {}
        for photo in matched_photos:
            if photo.drive_file_id not in unique_photos:
                unique_photos[photo.drive_file_id] = photo
        
        matched_photos_response = [
            PhotoResponse.model_validate(photo) 
            for photo in unique_photos.values()
        ]
        
        # Log activity
        await log_activity(db, current_user.id, ActionEnum.face_scan, len(matched_photos_response))
        
        return ScanFaceResponse(
            matched_photos=matched_photos_response,
            total_matches=len(matched_photos_response),
            grouped_by_day=grouped_by_day
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning face: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing face scan: {str(e)}")


@router.get("/photos", response_model=List[PhotoResponse])
async def get_photos(
    day: Optional[str] = None,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get photos, optionally filtered by day.
    
    Args:
        day: Optional day name to filter by
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of photos
    """
    try:
        query = select(Photo)
        
        if day:
            query = query.where(Photo.day_name == day)
        
        result = await db.execute(query)
        photos = result.scalars().all()
        
        # Remove duplicates by drive_file_id
        unique_photos = {}
        for photo in photos:
            if photo.drive_file_id not in unique_photos:
                unique_photos[photo.drive_file_id] = photo
        
        return [PhotoResponse.model_validate(photo) for photo in unique_photos.values()]
        
    except Exception as e:
        logger.error(f"Error getting photos: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving photos: {str(e)}")


@router.post("/download-log", response_model=DownloadLogResponse)
async def log_download(
    request: DownloadLogRequest,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Log photo download activity.
    
    Args:
        request: Download log request with photo IDs
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success response
    """
    try:
        # Log download activity
        await log_activity(db, current_user.id, ActionEnum.download, len(request.photo_ids))
        
        return DownloadLogResponse(logged=True)
        
    except Exception as e:
        logger.error(f"Error logging download: {e}")
        raise HTTPException(status_code=500, detail=f"Error logging download: {str(e)}")
