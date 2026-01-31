"""Utility functions for the application."""
import io
from typing import Tuple
from PIL import Image
from fastapi import HTTPException, UploadFile
from app.config import settings
import logging

logger = logging.getLogger(__name__)


async def validate_image_file(file: UploadFile) -> bytes:
    """
    Validate uploaded image file.
    
    Args:
        file: Uploaded file
        
    Returns:
        Image bytes
        
    Raises:
        HTTPException: If validation fails
    """
    # Check content type
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only JPEG and PNG images are allowed. Got: {file.content_type}"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB}MB"
        )
    
    # Validate image can be opened
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()
    except Exception as e:
        logger.error(f"Invalid image file: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid image file. Cannot open or verify image."
        )
    
    return content


def validate_image_bytes(image_bytes: bytes) -> Tuple[bool, str]:
    """
    Validate image bytes can be processed.
    
    Args:
        image_bytes: Image bytes to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.verify()
        return True, ""
    except Exception as e:
        return False, str(e)


def bytes_to_pil_image(image_bytes: bytes) -> Image.Image:
    """
    Convert image bytes to PIL Image.
    
    Args:
        image_bytes: Image bytes
        
    Returns:
        PIL Image object
    """
    return Image.open(io.BytesIO(image_bytes))


def format_error_response(error: Exception) -> dict:
    """
    Format error response.
    
    Args:
        error: Exception object
        
    Returns:
        Error response dictionary
    """
    return {
        "error": type(error).__name__,
        "detail": str(error)
    }
