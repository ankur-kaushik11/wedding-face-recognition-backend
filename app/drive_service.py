"""Google Drive service for fetching wedding photos."""
import io
from typing import List, Dict, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """Service for interacting with Google Drive API."""
    
    def __init__(self):
        """Initialize Google Drive service with service account."""
        self.credentials = None
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive API service."""
        try:
            # Load service account credentials
            self.credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_DRIVE_CREDENTIALS_PATH,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            
            # Build service
            self.service = build('drive', 'v3', credentials=self.credentials)
            logger.info("Google Drive service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            raise
    
    def list_day_folders(self) -> List[Dict[str, str]]:
        """
        List all day folders in the root wedding photos folder.
        
        Returns:
            List of folder dictionaries with 'id' and 'name'
        """
        try:
            query = f"'{settings.GOOGLE_DRIVE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                orderBy="name"
            ).execute()
            
            folders = results.get('files', [])
            logger.info(f"Found {len(folders)} day folders")
            return folders
            
        except Exception as e:
            logger.error(f"Error listing day folders: {e}")
            raise
    
    def list_photos_in_folder(self, folder_id: str) -> List[Dict[str, str]]:
        """
        List all photo files in a specific folder.
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            List of photo dictionaries with 'id', 'name', and 'webViewLink'
        """
        try:
            query = f"'{folder_id}' in parents and (mimeType='image/jpeg' or mimeType='image/png' or mimeType='image/jpg') and trashed=false"
            
            photos = []
            page_token = None
            
            while True:
                results = self.service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, webViewLink, webContentLink)",
                    pageSize=1000,
                    pageToken=page_token
                ).execute()
                
                files = results.get('files', [])
                photos.extend(files)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Found {len(photos)} photos in folder {folder_id}")
            return photos
            
        except Exception as e:
            logger.error(f"Error listing photos in folder {folder_id}: {e}")
            raise
    
    def get_photo_bytes(self, file_id: str, size: str = 'thumbnail') -> bytes:
        """
        Download photo bytes from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            size: Size variant ('thumbnail' for preview, 'full' for original)
            
        Returns:
            Image bytes
        """
        try:
            if size == 'thumbnail':
                # Get thumbnail/preview (faster, smaller)
                request = self.service.files().get_media(fileId=file_id)
                # Note: For thumbnails, we could use thumbnailLink, but get_media works well
            else:
                # Get full resolution
                request = self.service.files().get_media(fileId=file_id)
            
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_buffer.seek(0)
            image_bytes = file_buffer.read()
            
            logger.debug(f"Downloaded {len(image_bytes)} bytes for file {file_id}")
            return image_bytes
            
        except Exception as e:
            logger.error(f"Error downloading photo {file_id}: {e}")
            raise
    
    def get_shareable_link(self, file_id: str) -> str:
        """
        Get shareable/viewable link for a photo.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Shareable web view link
        """
        try:
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            
            return file_metadata.get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view")
            
        except Exception as e:
            logger.error(f"Error getting shareable link for {file_id}: {e}")
            return f"https://drive.google.com/file/d/{file_id}/view"
    
    def get_photo_download_link(self, file_id: str) -> str:
        """
        Get direct download link for a photo.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Download link
        """
        return f"https://drive.google.com/uc?export=download&id={file_id}"


# Singleton instance
drive_service = GoogleDriveService()
