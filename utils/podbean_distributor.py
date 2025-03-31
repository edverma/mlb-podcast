import os
import json
import time
import requests
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv
import base64

from utils.logger import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

class PodbeanDistributor:
    """
    Handles the distribution of podcast episodes to Podbean.
    Uses OAuth2 authentication and Podbean's API to upload and publish episodes.
    """
    
    # Podbean API endpoints
    BASE_URL = "https://api.podbean.com/v1"
    AUTH_URL = f"{BASE_URL}/oauth/token"
    
    # Upload authorization endpoint (verified working)
    UPLOAD_AUTH_URL = f"{BASE_URL}/files/uploadAuthorize"
    
    # Episode publishing endpoint
    EPISODE_URL = f"{BASE_URL}/episodes"
    
    def __init__(self, debug_mode=True):
        """Initialize the Podbean distributor."""
        self.logger = get_logger(__name__)
        self.client_id = os.getenv("PODBEAN_CLIENT_ID")
        self.client_secret = os.getenv("PODBEAN_CLIENT_SECRET")
        self.debug_mode = debug_mode
        
        if not self.client_id or not self.client_secret:
            self.logger.error("Podbean credentials not found in .env file")
            raise ValueError("Podbean credentials not found. Please set PODBEAN_CLIENT_ID and PODBEAN_CLIENT_SECRET in .env file.")
        
        self.logger.info("Podbean distributor initialized")
        self.access_token = None
        self.token_expires_at = 0
        
        # Mock mode is disabled by default now that we have the correct API endpoint
        # Set use_mock=True during testing or when needed
        self.use_mock = False
        logger.info("Using live Podbean API endpoints")
    
    def authenticate(self) -> bool:
        """
        Handle OAuth2 authentication with Podbean API.
        Returns True if authentication was successful, False otherwise.
        """
        if self.use_mock:
            logger.info("Mock authentication successful")
            self.access_token = "mock_token"
            self.token_expires_at = time.time() + 3600 - 60
            return True
            
        # If we already have a valid token, use it
        if self.access_token and time.time() < self.token_expires_at:
            logger.debug("Using existing access token")
            return True
        
        try:
            logger.info("Authenticating with Podbean API")
            
            # Create Basic Auth header (Base64 encoded client_id:client_secret)
            auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            
            # Set up the request headers and data
            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "grant_type": "client_credentials"
            }
            
            # Make the authentication request
            response = requests.post(self.AUTH_URL, headers=headers, data=data)
            
            if self.debug_mode:
                logger.debug(f"Auth response status: {response.status_code}")
                logger.debug(f"Auth response body: {response.text}")
            
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
            self.token_expires_at = time.time() + expires_in - 60
            
            logger.info("Podbean authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            return False
    
    def _get_upload_authorization(self, params, file_path):
        """
        Get upload authorization from Podbean API using the verified endpoint.
        """
        if self.use_mock:
            logger.info(f"Mock file upload for {file_path}")
            return {
                "presigned_url": "https://mock-s3-upload.podbean.com/upload",
                "file_key": f"mock_file_key_{int(time.time())}"
            }
            
        # Make sure access_token is included in params as required by the API
        if "access_token" not in params and self.access_token:
            params["access_token"] = self.access_token
        
        # Add User-Agent header as mentioned in the documentation
        headers = {"User-Agent": "MLB-Podcast/1.0"}
        
        try:
            logger.info(f"Requesting upload authorization from: {self.UPLOAD_AUTH_URL}")
            
            # Make the request as specified in the documentation (GET with query params)
            response = requests.get(self.UPLOAD_AUTH_URL, params=params, headers=headers)
            
            if self.debug_mode:
                logger.debug(f"Upload auth response status: {response.status_code}")
                logger.debug(f"Upload auth response body: {response.text[:1000] if response.text else 'Empty response'}")
            
            # Check for successful response
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Upload authorization failed with status code {response.status_code}")
                logger.error(f"Response: {response.text}")
                raise Exception(f"Upload authorization failed: {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting upload authorization: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def upload_episode(self, audio_file_path: str, title: str) -> Optional[str]:
        """
        Upload audio file to Podbean.
        Returns the file key if successful, None otherwise.
        """
        if self.use_mock:
            logger.info(f"Mock uploading file: {audio_file_path}")
            return f"mock_file_key_{int(time.time())}"
        
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
            
        # Ensure we have a valid token
        if not self.authenticate():
            return None
            
        try:
            logger.info(f"Uploading episode: {title}")
            
            # Prepare the file upload parameters
            file_size = os.path.getsize(audio_file_path)
            file_name = os.path.basename(audio_file_path)
            
            # For testing with small files, set a minimum size
            # Podbean may reject files that are too small
            if file_size < 10000 and "test" in title.lower():
                logger.warning(f"File size is very small ({file_size} bytes). Artificially increasing size for Podbean API.")
                file_size = 10000  # Set a minimum size for testing
            
            # Prepare upload parameters (as specified in the documentation)
            upload_params = {
                "access_token": self.access_token,
                "filename": file_name,
                "filesize": file_size,
                "content_type": "audio/mpeg"  # Assuming MP3 format
            }
            
            # Get upload authorization
            logger.info(f"Requesting upload authorization from Podbean API")
            upload_info = self._get_upload_authorization(upload_params, audio_file_path)
            
            # Get the presigned URL and file key
            presigned_url = upload_info.get("presigned_url")
            file_key = upload_info.get("file_key")
            
            if not presigned_url or not file_key:
                logger.error(f"Missing presigned_url or file_key in response: {upload_info}")
                return None
            
            # Upload the file to S3 using the presigned URL
            logger.info(f"Uploading file to S3 using presigned URL")
            with open(audio_file_path, "rb") as file:
                upload_response = requests.put(
                    presigned_url,
                    data=file,
                    headers={"Content-Type": "audio/mpeg"}
                )
                
                if self.debug_mode:
                    logger.debug(f"S3 upload response status: {upload_response.status_code}")
                    if upload_response.text:
                        logger.debug(f"S3 upload response body: {upload_response.text[:1000]}")
                
                upload_response.raise_for_status()
            
            logger.info(f"Upload successful. File key: {file_key}")
            return file_key
            
        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def publish_episode(self, file_key: str, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Publish the uploaded episode with metadata.
        Returns the episode ID if successful, None otherwise.
        """
        if self.use_mock:
            logger.info(f"Mock publishing episode: {metadata.get('title', 'Untitled')}")
            return f"mock_episode_id_{int(time.time())}"
        
        if not file_key:
            logger.error("No file key provided for publishing")
            return None
            
        # Ensure we have a valid token
        if not self.authenticate():
            return None
            
        try:
            logger.info(f"Publishing episode: {metadata.get('title', 'Untitled')}")
            
            # Prepare publish data (per documentation, DO NOT include Authorization header)
            # Only include access_token in form data
            
            # Required metadata fields
            publish_data = {
                "access_token": self.access_token,
                "title": metadata.get("title", ""),
                "content": metadata.get("description", ""),
                "status": "publish",
                "type": "public",
                "media_key": file_key
            }
            
            # Optional metadata fields
            if metadata.get("tags"):
                # Convert tags list to comma-separated string
                publish_data["tag"] = ",".join(metadata.get("tags"))
                
            if metadata.get("category"):
                publish_data["category"] = metadata.get("category")
                
            if metadata.get("season"):
                publish_data["season_number"] = metadata.get("season")
                
            if metadata.get("episode_number"):
                publish_data["episode_number"] = metadata.get("episode_number")
                
            if metadata.get("explicit"):
                publish_data["content_explicit"] = "explicit" if metadata.get("explicit") else "clean"
                
            if metadata.get("logo_key"):
                publish_data["logo_key"] = metadata.get("logo_key")
                
            if metadata.get("transcripts_key"):
                publish_data["transcripts_key"] = metadata.get("transcripts_key")
                
            if metadata.get("apple_episode_type"):
                publish_data["apple_episode_type"] = metadata.get("apple_episode_type", "full")
                
            if metadata.get("publish_timestamp"):
                publish_data["publish_timestamp"] = metadata.get("publish_timestamp")
            
            # Make the publish request
            logger.info(f"Sending publish request to Podbean API")
            if self.debug_mode:
                logger.debug(f"Publish data: {publish_data}")
            
            # Use form data with no headers as per documentation
            response = requests.post(
                self.EPISODE_URL,
                data=publish_data
            )
            
            if self.debug_mode:
                logger.debug(f"Publish response status: {response.status_code}")
                logger.debug(f"Publish response body: {response.text[:1000]}")
            
            response.raise_for_status()
            
            publish_info = response.json()
            episode_id = publish_info.get("episode", {}).get("id")
            
            logger.info(f"Episode published successfully. Episode ID: {episode_id}")
            return episode_id
            
        except Exception as e:
            logger.error(f"Publishing error: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_episode_status(self, episode_id: str) -> Dict[str, Any]:
        """
        Get the status of a published episode.
        Returns episode details if successful, empty dict otherwise.
        """
        if self.use_mock:
            logger.info(f"Mock getting status for episode ID: {episode_id}")
            return {
                "episode": {
                    "id": episode_id,
                    "title": "Mock Episode Title",
                    "status": "published",
                    "published_at": datetime.now().isoformat(),
                    "permalink_url": f"https://example.podbean.com/e/mock-episode-{episode_id}/"
                }
            }
        
        if not episode_id:
            logger.error("No episode ID provided")
            return {}
            
        # Ensure we have a valid token
        if not self.authenticate():
            return {}
            
        try:
            logger.info(f"Getting status for episode ID: {episode_id}")
            
            # Get episode details using access_token as query parameter
            params = {"access_token": self.access_token}
            response = requests.get(
                f"{self.EPISODE_URL}/{episode_id}",
                params=params
            )
            
            if self.debug_mode:
                logger.debug(f"Episode status response status: {response.status_code}")
                logger.debug(f"Episode status response body: {response.text[:1000]}")
            
            response.raise_for_status()
            
            episode_info = response.json()
            logger.info(f"Successfully retrieved episode status")
            return episode_info
            
        except Exception as e:
            logger.error(f"Error getting episode status: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise
    
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
    
    def enable_mock_mode(self):
        """Enable mock mode for testing without actual API calls"""
        self.use_mock = True
        logger.info("Mock mode enabled - no actual API calls will be made")
        return True
        
    def disable_mock_mode(self):
        """Disable mock mode to make actual API calls"""
        self.use_mock = False
        logger.info("Mock mode disabled - actual API calls will be made")
        return True