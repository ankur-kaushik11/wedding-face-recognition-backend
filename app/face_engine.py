"""Face recognition engine for indexing and matching faces."""
import io
import time
import numpy as np
from typing import List, Dict, Tuple, Optional
from PIL import Image
import face_recognition
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import Photo
from app.drive_service import drive_service
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class FaceRecognitionEngine:
    """Engine for face detection, encoding, and matching."""
    
    def __init__(self):
        """Initialize face recognition engine."""
        self.similarity_threshold = settings.FACE_SIMILARITY_THRESHOLD
        self.detection_model = settings.FACE_DETECTION_MODEL
    
    def detect_and_encode(self, image_bytes: bytes) -> List[np.ndarray]:
        """
        Detect faces and generate embeddings from image bytes.
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            List of face embeddings (128-dimensional vectors)
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes))
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to numpy array
            image_array = np.array(image)
            
            # Detect face locations
            face_locations = face_recognition.face_locations(
                image_array,
                model=self.detection_model
            )
            
            if not face_locations:
                logger.debug("No faces detected in image")
                return []
            
            # Generate face encodings
            face_encodings = face_recognition.face_encodings(
                image_array,
                face_locations
            )
            
            logger.debug(f"Detected {len(face_encodings)} face(s) in image")
            return face_encodings
            
        except Exception as e:
            logger.error(f"Error detecting and encoding faces: {e}")
            return []
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two face embeddings.
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            
        Returns:
            Similarity score (0 to 1, higher is more similar)
        """
        # Compute cosine similarity
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # Convert from [-1, 1] to [0, 1]
        similarity = (similarity + 1) / 2
        
        return float(similarity)
    
    async def index_all_photos(self, db: AsyncSession, force: bool = False) -> Dict[str, any]:
        """
        Index all photos from Google Drive.
        
        Args:
            db: Database session
            force: If True, reindex all photos; if False, only index new ones
            
        Returns:
            Indexing statistics dictionary
        """
        start_time = time.time()
        stats = {
            "total_photos_processed": 0,
            "new_photos_indexed": 0,
            "faces_detected": 0,
            "photos_by_day": {},
            "errors": []
        }
        
        try:
            # Get all day folders
            day_folders = drive_service.list_day_folders()
            logger.info(f"Found {len(day_folders)} day folders to process")
            
            for folder in day_folders:
                folder_id = folder['id']
                day_name = folder['name']
                
                logger.info(f"Processing folder: {day_name}")
                
                # Get all photos in folder
                photos = drive_service.list_photos_in_folder(folder_id)
                stats["total_photos_processed"] += len(photos)
                stats["photos_by_day"][day_name] = 0
                
                for photo in photos:
                    photo_id = photo['id']
                    photo_name = photo.get('name', 'Unknown')
                    photo_url = photo.get('webViewLink', drive_service.get_shareable_link(photo_id))
                    
                    # Check if already indexed
                    if not force:
                        result = await db.execute(
                            select(Photo).where(Photo.drive_file_id == photo_id)
                        )
                        existing = result.scalar_one_or_none()
                        if existing:
                            logger.debug(f"Photo {photo_id} already indexed, skipping")
                            continue
                    else:
                        # Delete existing entries if force reindex
                        result = await db.execute(
                            select(Photo).where(Photo.drive_file_id == photo_id)
                        )
                        existing_photos = result.scalars().all()
                        for existing_photo in existing_photos:
                            await db.delete(existing_photo)
                    
                    try:
                        # Download photo (thumbnail for faster processing)
                        image_bytes = drive_service.get_photo_bytes(photo_id, size='thumbnail')
                        
                        # Detect and encode faces
                        face_encodings = self.detect_and_encode(image_bytes)
                        
                        if not face_encodings:
                            logger.debug(f"No faces detected in {photo_name}, skipping")
                            continue
                        
                        # Store each face as a separate photo record
                        for encoding in face_encodings:
                            photo_record = Photo(
                                drive_file_id=photo_id,
                                drive_url=photo_url,
                                day_name=day_name,
                                face_embedding=encoding.tolist()
                            )
                            db.add(photo_record)
                            stats["faces_detected"] += 1
                        
                        stats["new_photos_indexed"] += 1
                        stats["photos_by_day"][day_name] += 1
                        
                        # Commit in batches
                        if stats["new_photos_indexed"] % 50 == 0:
                            await db.commit()
                            logger.info(f"Indexed {stats['new_photos_indexed']} photos so far...")
                        
                    except Exception as e:
                        error_msg = f"Error processing photo {photo_name}: {str(e)}"
                        logger.error(error_msg)
                        stats["errors"].append(error_msg)
                        continue
            
            # Final commit
            await db.commit()
            
            elapsed_time = time.time() - start_time
            stats["indexing_time_seconds"] = round(elapsed_time, 2)
            
            logger.info(f"Indexing complete: {stats['new_photos_indexed']} photos indexed in {elapsed_time:.2f}s")
            return stats
            
        except Exception as e:
            logger.error(f"Error during indexing: {e}")
            await db.rollback()
            raise
    
    async def match_face(self, db: AsyncSession, image_bytes: bytes) -> List[Photo]:
        """
        Match a face in the uploaded image against indexed photos.
        
        Args:
            db: Database session
            image_bytes: Uploaded selfie image bytes
            
        Returns:
            List of matched Photo objects
        """
        try:
            # Detect and encode face in uploaded image
            face_encodings = self.detect_and_encode(image_bytes)
            
            if not face_encodings:
                logger.warning("No face detected in uploaded image")
                return []
            
            # Use the first detected face
            query_embedding = face_encodings[0]
            
            # Get all indexed photos
            result = await db.execute(select(Photo))
            all_photos = result.scalars().all()
            
            if not all_photos:
                logger.warning("No indexed photos found in database")
                return []
            
            # Compare with all stored embeddings
            matches = []
            for photo in all_photos:
                stored_embedding = np.array(photo.face_embedding)
                similarity = self.compute_similarity(query_embedding, stored_embedding)
                
                if similarity >= self.similarity_threshold:
                    matches.append((photo, similarity))
            
            # Sort by similarity (highest first)
            matches.sort(key=lambda x: x[1], reverse=True)
            
            # Return only photo objects (without similarity scores)
            matched_photos = [photo for photo, _ in matches]
            
            logger.info(f"Found {len(matched_photos)} matching photos")
            return matched_photos
            
        except Exception as e:
            logger.error(f"Error matching face: {e}")
            raise


# Singleton instance
face_engine = FaceRecognitionEngine()
