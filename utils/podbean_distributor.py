import os
import json
import time
import requests
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

from utils.logger import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

class PodbeanDistributor:
    """
    Handles the distribution of podcast episodes to Podbean.
    Uses OAuth2 authentication and Podbean's API to upload and publish episodes.
    """
    
    def __init__(self):
        # Load credentials from environment
        self.client_id = os.getenv("PODBEAN_CLIENT_ID")
        self.client_secret = os.getenv("PODBEAN_CLIENT_SECRET")
        self.base_url = "https://api.podbean.com/v1"
        self.auth_url = "https://api.podbean.com/v1/oauth/token"
        
        # Initialize token variables
        self.access_token = None
        self.token_expiry = None
        
        # Session for making requests
        self.session = requests.Session()
        
        # Check if we're in mock mode (no real API calls)
        self.use_mock = not bool(self.client_id and self.client_secret)
        if self.use_mock:
            logger.warning("Podbean API credentials not found. Running in mock mode.")
    
    def authenticate(self) -> bool:
        """
        Handle OAuth2 authentication with Podbean API.
        Returns True if authentication was successful, False otherwise.
        """
        # If in mock mode, return fake success
        if self.use_mock:
            logger.info("Mock authentication successful")
            self.access_token = "mock_token"
            self.token_expiry = datetime.now() + timedelta(hours=1)
            return True
            
        # If we already have a valid token, use it
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            logger.debug("Using existing access token")
            return True
            
        # Otherwise, get a new token
        try:
            logger.info("Authenticating with Podbean API")
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = requests.post(self.auth_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            
            # Update session headers
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })
            
            logger.info("Podbean authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def upload_episode(self, audio_file_path: str, title: str) -> Optional[str]:
        """
        Upload audio file to Podbean.
        Returns the file key if successful, None otherwise.
        """
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return None
            
        # Ensure we have a valid token
        if not self.authenticate():
            return None
            
        if self.use_mock:
            logger.info(f"Mock uploading file: {audio_file_path}")
            return "mock_file_key_12345"
            
        try:
            logger.info(f"Uploading episode: {title}")
            
            # First, request authorization to upload
            authorize_url = f"{self.base_url}/files/uploadAuthorize"
            file_size = os.path.getsize(audio_file_path)
            file_name = os.path.basename(audio_file_path)
            
            auth_data = {
                "filename": file_name,
                "filesize": file_size,
                "content_type": "audio/mp3"  # Assuming MP3 format
            }
            
            response = self.session.get(authorize_url, params=auth_data)
            response.raise_for_status()
            upload_info = response.json()
            
            # Now use the presigned URL to upload the file
            presigned_url = upload_info.get("presigned_url")
            if not presigned_url:
                logger.error("Failed to get presigned URL for upload")
                return None
                
            with open(audio_file_path, "rb") as file:
                upload_response = requests.put(
                    presigned_url,
                    data=file,
                    headers={"Content-Type": "audio/mp3"}
                )
                upload_response.raise_for_status()
            
            # Return the file key for publishing
            file_key = upload_info.get("file_key")
            logger.info(f"Upload successful. File key: {file_key}")
            return file_key
            
        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def publish_episode(self, file_key: str, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Publish the uploaded episode with metadata.
        Returns the episode ID if successful, None otherwise.
        """
        if not file_key:
            logger.error("No file key provided for publishing")
            return None
            
        # Ensure we have a valid token
        if not self.authenticate():
            return None
            
        if self.use_mock:
            logger.info(f"Mock publishing episode: {metadata.get('title', 'Untitled')}")
            return "mock_episode_id_67890"
            
        try:
            logger.info(f"Publishing episode: {metadata.get('title', 'Untitled')}")
            
            # Prepare publish data
            publish_url = f"{self.base_url}/episodes"
            
            # Required metadata fields
            publish_data = {
                "title": metadata.get("title", ""),
                "content": metadata.get("description", ""),
                "status": "publish",
                "type": "public",
                "media_key": file_key
            }
            
            # Optional metadata fields
            if metadata.get("tags"):
                publish_data["tags"] = metadata.get("tags")
                
            if metadata.get("category"):
                publish_data["category"] = metadata.get("category")
                
            if metadata.get("season"):
                publish_data["season"] = metadata.get("season")
                
            if metadata.get("episode_number"):
                publish_data["episode"] = metadata.get("episode_number")
            
            # Make the publish request
            response = self.session.post(publish_url, data=publish_data)
            response.raise_for_status()
            
            publish_info = response.json()
            episode_id = publish_info.get("episode", {}).get("id")
            
            logger.info(f"Episode published successfully. Episode ID: {episode_id}")
            return episode_id
            
        except Exception as e:
            logger.error(f"Publishing error: {str(e)}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_episode_status(self, episode_id: str) -> Dict[str, Any]:
        """
        Get the status of a published episode.
        Returns episode details if successful, empty dict otherwise.
        """
        if not episode_id:
            logger.error("No episode ID provided")
            return {}
            
        # Ensure we have a valid token
        if not self.authenticate():
            return {}
            
        if self.use_mock:
            logger.info(f"Mock getting status for episode ID: {episode_id}")
            return {
                "id": episode_id,
                "title": "Mock Episode Title",
                "status": "published",
                "published_at": datetime.now().isoformat(),
                "url": f"https://example.podbean.com/e/mock-episode-{episode_id}/"
            }
            
        try:
            logger.info(f"Getting status for episode ID: {episode_id}")
            
            # Get episode details
            episode_url = f"{self.base_url}/episodes/{episode_id}"
            response = self.session.get(episode_url)
            response.raise_for_status()
            
            episode_info = response.json()
            logger.info(f"Successfully retrieved episode status")
            return episode_info
            
        except Exception as e:
            logger.error(f"Error getting episode status: {str(e)}")
            return {}
    
    def distribute_podcast(self, audio_file_path: str, metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Complete distribution workflow: upload and publish an episode.
        Returns a tuple of (success, episode_url).
        """
        try:
            # Step 1: Upload the audio file
            file_key = self.upload_episode(audio_file_path, metadata.get("title", "Untitled"))
            if not file_key:
                return False, None
                
            # Step 2: Publish the episode
            episode_id = self.publish_episode(file_key, metadata)
            if not episode_id:
                return False, None
                
            # Step 3: Get the published episode URL
            episode_info = self.get_episode_status(episode_id)
            episode_url = episode_info.get("episode", {}).get("permalink_url")
            
            if not episode_url and self.use_mock:
                episode_url = f"https://example.podbean.com/e/mock-episode-{episode_id}/"
                
            logger.info(f"Distribution complete. Episode URL: {episode_url}")
            return True, episode_url
            
        except Exception as e:
            logger.error(f"Distribution error: {str(e)}")
            return False, None