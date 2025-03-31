import os
import json
import datetime
import time
import base64
import uuid
from typing import Dict, Any, Optional, List, Tuple
from google.cloud import texttospeech, storage
from google.cloud.storage import Blob
from google.oauth2 import service_account
import google.auth
import google.auth.transport.requests
import google.oauth2.id_token
from tenacity import retry, stop_after_attempt, wait_exponential
import requests

from config.config import (
    GOOGLE_CLOUD_API_KEY, GOOGLE_WAVENET_VOICE, GOOGLE_WAVENET_LANGUAGE_CODE,
    SCRIPTS_DIR, AUDIO_DIR, MLB_TEAMS
)

# Try to import optional Long Audio API settings, with fallbacks
try:
    from config.config import GOOGLE_CLOUD_PROJECT_ID
except ImportError:
    GOOGLE_CLOUD_PROJECT_ID = None

try:
    from config.config import GOOGLE_CLOUD_LOCATION
except ImportError:
    GOOGLE_CLOUD_LOCATION = "us-central1"
    
try:
    from config.config import GOOGLE_CLOUD_BUCKET
except ImportError:
    GOOGLE_CLOUD_BUCKET = None
    
try:
    from config.config import GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE
except ImportError:
    GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE = None
from utils.logger import get_logger

logger = get_logger(__name__)

class GoogleWavenetTTS:
    def __init__(self):
        self.api_key = GOOGLE_CLOUD_API_KEY
        self.voice_name = GOOGLE_WAVENET_VOICE
        self.language_code = GOOGLE_WAVENET_LANGUAGE_CODE
        self.project_id = GOOGLE_CLOUD_PROJECT_ID
        self.location = GOOGLE_CLOUD_LOCATION or "us-central1"  # Default location
        self.cloud_bucket = GOOGLE_CLOUD_BUCKET
        self.service_account_file = GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE
        
        # Base URLs for Google Text-to-Speech APIs
        self.api_url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        self.long_audio_api_base_url = f"https://{self.location}-texttospeech.googleapis.com/v1beta1"
        
        # Load service account credentials if available
        self.credentials = None
        self.have_service_account = False
        if self.service_account_file and os.path.exists(self.service_account_file):
            try:
                self.credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_file,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                self.have_service_account = True
                logger.info(f"Loaded service account credentials from {self.service_account_file}")
            except Exception as e:
                logger.error(f"Failed to load service account credentials: {e}")
                self.have_service_account = False
        else:
            logger.info("No service account credentials file found. Will attempt to use API key authentication.")
        
        # Set up Storage client with service account credentials if available
        self.storage_client = None
        if self.have_service_account:
            try:
                # Initialize Storage client with credentials
                self.storage_client = storage.Client(
                    project=self.project_id,
                    credentials=self.credentials
                )
                # Test bucket access
                if self.cloud_bucket:
                    try:
                        bucket = self.storage_client.bucket(self.cloud_bucket)
                        # Test if bucket exists and is accessible
                        bucket.exists()
                        logger.info(f"Successfully authenticated to GCS bucket {self.cloud_bucket}")
                    except Exception as e:
                        logger.warning(f"Could not access GCS bucket {self.cloud_bucket}: {e}")
                        self.storage_client = None
                else:
                    logger.warning("GCS bucket name not specified in configuration")
            except Exception as e:
                logger.error(f"Error initializing Google Cloud Storage client: {e}")
                self.storage_client = None
                self.have_service_account = False
        
        # Create Text-to-Speech client if we have service account credentials
        self.tts_client = None
        if self.have_service_account:
            try:
                self.tts_client = texttospeech.TextToSpeechClient(credentials=self.credentials)
                logger.info("Successfully initialized Text-to-Speech client with service account")
            except Exception as e:
                logger.error(f"Error initializing Text-to-Speech client: {e}")
                self.tts_client = None
        
        # Check if we're using demo/invalid keys (no service account and no API key)
        self.use_mock = not (self.have_service_account or self.api_key)
        if self.use_mock:
            logger.warning("No valid authentication method found. Using mock mode.")
        
        # Check if long audio API is available - requires project ID, bucket, and auth
        self.long_audio_available = bool(
            self.project_id and self.cloud_bucket and (self.have_service_account or self.api_key)
        )
        
        if not self.long_audio_available:
            missing = []
            if not self.project_id:
                missing.append("GOOGLE_CLOUD_PROJECT_ID")
            if not self.cloud_bucket:
                missing.append("GOOGLE_CLOUD_BUCKET")
            if not self.have_service_account and not self.api_key:
                missing.append("GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE or GOOGLE_CLOUD_API_KEY")
                
            logger.warning("Long Audio API is not available - SSML will use chunking fallback")
            if missing:
                logger.warning(f"Missing configuration: {', '.join(missing)}")
                logger.warning("Set these variables in .env to enable Long Audio API")
        
        # Character limits
        self.max_char_limit = 5000  # Standard TTS API limit is 5000 bytes
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _tts_request(self, text: str, voice_name: Optional[str] = None, is_ssml: bool = False) -> bytes:
        """Make a TTS request to Google Wavenet API.
        
        Attempts to use service account authentication with the client library first,
        then falls back to API key authentication if service account is not available.
        
        Args:
            text: The text or SSML content to convert to speech
            voice_name: Optional voice name to use instead of the default
            is_ssml: If True, the text input is treated as SSML content
        """
        # For testing/demo purposes, don't make actual API calls
        if self.use_mock:
            # Return dummy audio data for mock response
            logger.info("Using mock audio data (demo mode)")
            return b"MOCK_AUDIO_DATA"
        
        # Use a default voice name if none is provided
        voice_name = voice_name or self.voice_name
        
        try:
            # Try using the client library with service account first
            if self.have_service_account and self.tts_client:
                logger.debug("Using Text-to-Speech client library with service account auth")
                
                # Prepare the input
                synthesis_input = texttospeech.SynthesisInput(
                    ssml=text if is_ssml else None,
                    text=None if is_ssml else text
                )
                
                # Build the voice request
                voice = texttospeech.VoiceSelectionParams(
                    language_code=self.language_code,
                    name=voice_name
                )
                
                # Select the audio encoding
                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                    speaking_rate=1.0,
                    pitch=0.0,
                    sample_rate_hertz=24000
                )
                
                # Perform the synthesis request
                try:
                    response = self.tts_client.synthesize_speech(
                        input=synthesis_input,
                        voice=voice,
                        audio_config=audio_config
                    )
                    # Return the audio content
                    return response.audio_content
                except Exception as e:
                    logger.warning(f"Service account TTS request failed: {e}. Trying API key method.")
            
            # Fall back to API key method if service account is not available or fails
            if self.api_key:
                logger.debug("Using REST API with API key auth")
                
                # Prepare request payload
                payload = {
                    "input": {
                        # Use ssml or text based on the is_ssml parameter
                        "ssml" if is_ssml else "text": text
                    },
                    "voice": {
                        "languageCode": self.language_code,
                        "name": voice_name
                    },
                    "audioConfig": {
                        "audioEncoding": "MP3",
                        "speakingRate": 1.0,
                        "pitch": 0.0,
                        "sampleRateHertz": 24000
                    }
                }
                
                # Get headers and build URL with authentication
                headers = self._get_auth_headers()
                url = self._build_api_url(self.api_url)
                
                # Make API request
                response = requests.post(url, json=payload, headers=headers)
                
                # Check for successful response
                if response.status_code == 200:
                    # The response contains a base64-encoded audio content
                    audio_content = response.json().get("audioContent")
                    if audio_content:
                        return base64.b64decode(audio_content)
                    else:
                        logger.error("No audio content in response")
                        raise Exception("No audio content in response")
                else:
                    error_message = response.text
                    logger.error(f"Google TTS API error: {error_message}")
                    raise Exception(f"Google TTS API error: {response.status_code} - {error_message}")
            else:
                raise Exception("No valid authentication method available for TTS request")
            
        except Exception as e:
            logger.error(f"Error in Google Wavenet TTS request: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _long_audio_synthesis(self, text: str, voice_name: Optional[str] = None, is_ssml: bool = False) -> bytes:
        """Use Google's Long Audio API for synthesizing longer content.
        
        This method handles longer texts by using Google Cloud's long audio synthesis,
        which requires a GCS bucket for storing the results. It prioritizes using service
        account authentication when available.
        
        Note: Google's Long Audio API has strict SSML validation rules. It requires a
        simple <speak>...</speak> format without XML declarations or namespace attributes.
        """
        if self.use_mock:
            logger.info("Using mock audio data (demo mode)")
            return b"MOCK_AUDIO_DATA"
            
        # Generate a unique ID for this synthesis request
        synthesis_id = str(uuid.uuid4())
        output_gcs_uri = f"gs://{self.cloud_bucket}/audio-{synthesis_id}.mp3"
        blob_name = f"audio-{synthesis_id}.mp3"
        
        logger.info(f"Starting long audio synthesis for content of length {len(text)} bytes")
        
        try:
            # Start synthesis operation - different approaches based on authentication method
            operation_name = None
            
            # Method 1: Try using client library with service account if available
            if self.have_service_account and self.tts_client and self.storage_client:
                logger.info("Using client library with service account for Long Audio API")
                try:
                    # Note: The Beta API client might not be available in standard packages
                    # We'll use REST API with service account authentication instead
                    # which will be more reliable across environments
                    
                    # Create the operation using OAuth-authenticated REST API
                    # Build the request payload
                    payload = {
                        "parent": f"projects/{self.project_id}/locations/{self.location}",
                        "input": {
                            "ssml" if is_ssml else "text": text
                        },
                        "voice": {
                            "languageCode": self.language_code,
                            "name": voice_name or self.voice_name
                        },
                        "audioConfig": {
                            "audioEncoding": "LINEAR16",  # Long Audio API only supports LINEAR16 currently
                            "speakingRate": 1.0,
                            "pitch": 0.0,
                            "sampleRateHertz": 24000
                        },
                        "outputGcsUri": output_gcs_uri
                    }
                    
                    # Get authentication headers with service account token
                    headers = self._get_auth_headers()
                    
                    # Build URL for Long Audio API
                    api_path = f"projects/{self.project_id}/locations/{self.location}:synthesizeLongAudio"
                    api_url = self._build_api_url(self.long_audio_api_base_url, api_path)
                    
                    # Start the long-running operation
                    logger.info(f"Making Long Audio API request with service account auth")
                    response = requests.post(api_url, json=payload, headers=headers)
                    
                    # Check for successful response
                    if response.status_code != 200:
                        error_message = response.text
                        logger.error(f"Long Audio API error: {error_message}")
                        raise Exception(f"Long Audio API error: {response.status_code} - {error_message}")
                    
                    # Get the operation name from the response
                    operation_name = response.json().get("name")
                    if not operation_name:
                        logger.error("No operation name in response")
                        raise Exception("No operation name in response")
                    
                    logger.info(f"Long audio synthesis operation started (service account): {operation_name}")
                    
                    # Poll for operation completion
                    complete = False
                    retry_count = 0
                    max_retries = 60  # 30 minutes with 30-second polling
                    
                    while not complete and retry_count < max_retries:
                        # Wait 30 seconds between polls
                        time.sleep(30)
                        
                        # Check operation status - use service account token
                        operation_url = self._build_api_url(self.long_audio_api_base_url, operation_name)
                        status_response = requests.get(operation_url, headers=headers)
                        
                        if status_response.status_code != 200:
                            logger.error(f"Error checking operation status: {status_response.text}")
                            retry_count += 1
                            continue
                            
                        operation_status = status_response.json()
                        
                        # Check if operation is done
                        if operation_status.get("done", False):
                            complete = True
                            logger.info(f"Long audio synthesis complete after {retry_count * 30} seconds")
                            
                            # Check for errors
                            if "error" in operation_status:
                                error_details = operation_status["error"]
                                logger.error(f"Long audio synthesis failed: {error_details}")
                                raise Exception(f"Long audio synthesis failed: {error_details}")
                            
                            # Now download the resulting file using Storage client
                            logger.info("Using Storage client to download result file")
                            bucket = self.storage_client.bucket(self.cloud_bucket)
                            blob = bucket.blob(blob_name)
                            
                            # Create a temporary file for downloading
                            temp_file = f"/tmp/audio-{synthesis_id}.mp3"
                            blob.download_to_filename(temp_file)
                            
                            # Read the file content
                            with open(temp_file, "rb") as f:
                                audio_data = f.read()
                            
                            # Clean up temporary file
                            os.remove(temp_file)
                            
                            # Delete the blob from bucket
                            blob.delete()
                            logger.info("Successfully downloaded and cleaned up GCS storage file")
                            
                            return audio_data
                        else:
                            logger.info(f"Long audio synthesis in progress... (poll {retry_count+1})")
                            retry_count += 1
                    
                    if not complete:
                        logger.error("Long audio synthesis timed out")
                        raise Exception("Long audio synthesis timed out after 30 minutes")
                    
                except Exception as e:
                    logger.warning(f"Failed to use service account for Long Audio API: {e}")
                    logger.warning("Falling back to API key approach")
            
            # Method 2: Use REST API if client library fails or is unavailable
            # Build the request payload for REST API
            # Note: SSML preprocessing is now done in _process_long_text before calling this method
            payload = {
                "parent": f"projects/{self.project_id}/locations/{self.location}",
                "input": {
                    "ssml" if is_ssml else "text": text
                },
                "voice": {
                    "languageCode": self.language_code,
                    "name": voice_name or self.voice_name
                },
                "audioConfig": {
                    "audioEncoding": "LINEAR16",  # Long Audio API only supports LINEAR16 currently
                    "speakingRate": 1.0,
                    "pitch": 0.0,
                    "sampleRateHertz": 24000
                },
                "outputGcsUri": output_gcs_uri
            }
            
            # Get authentication headers
            headers = self._get_auth_headers()
            
            # Build URL for Long Audio API
            api_path = f"projects/{self.project_id}/locations/{self.location}:synthesizeLongAudio"
            api_url = self._build_api_url(self.long_audio_api_base_url, api_path)
            
            logger.info("Using REST API for Long Audio synthesis")
            
            # Start the long-running operation
            response = requests.post(
                api_url,
                json=payload,
                headers=headers
            )
            
            # Check for successful response
            if response.status_code != 200:
                error_message = response.text
                logger.error(f"Long Audio API error: {error_message}")
                raise Exception(f"Long Audio API error: {response.status_code} - {error_message}")
                
            # Get the operation name from the response
            operation_name = response.json().get("name")
            if not operation_name:
                logger.error("No operation name in response")
                raise Exception("No operation name in response")
                
            logger.info(f"Long audio synthesis operation started: {operation_name}")
            
            # Poll for operation completion
            complete = False
            retry_count = 0
            max_retries = 60  # 30 minutes with 30-second polling
            
            while not complete and retry_count < max_retries:
                # Wait 30 seconds between polls
                time.sleep(30)
                
                # Check operation status
                operation_url = self._build_api_url(self.long_audio_api_base_url, operation_name)
                status_response = requests.get(operation_url, headers=headers)
                
                if status_response.status_code != 200:
                    logger.error(f"Error checking operation status: {status_response.text}")
                    retry_count += 1
                    continue
                    
                operation_status = status_response.json()
                
                # Check if operation is done
                if operation_status.get("done", False):
                    complete = True
                    logger.info(f"Long audio synthesis complete after {retry_count * 30} seconds")
                    
                    # Check for errors
                    if "error" in operation_status:
                        error_details = operation_status["error"]
                        logger.error(f"Long audio synthesis failed: {error_details}")
                        raise Exception(f"Long audio synthesis failed: {error_details}")
                        
                    # Download the file from GCS
                    logger.info(f"Downloading audio file from GCS bucket")
                    
                    # Try to use the Storage client with service account if available
                    if self.have_service_account and self.storage_client:
                        try:
                            bucket = self.storage_client.bucket(self.cloud_bucket)
                            blob = bucket.blob(blob_name)
                            
                            # Download to a temporary file
                            temp_file = f"/tmp/audio-{synthesis_id}.mp3"
                            blob.download_to_filename(temp_file)
                            
                            # Read the file
                            with open(temp_file, "rb") as f:
                                audio_data = f.read()
                                
                            # Clean up the temp file
                            os.remove(temp_file)
                            
                            # Delete the blob from bucket
                            blob.delete()
                            logger.info("Successfully downloaded and cleaned up GCS storage file using Storage client")
                            return audio_data
                        except Exception as e:
                            logger.warning(f"Error accessing GCS with service account: {e}")
                            logger.warning("Falling back to REST API for downloading")
                    
                    # Fall back to REST API with API key (or service account token) if client access fails
                    download_url = f"https://storage.googleapis.com/storage/v1/b/{self.cloud_bucket}/o/{blob_name}?alt=media"
                    download_url = self._build_api_url(download_url)
                    
                    # Get fresh headers
                    headers = self._get_auth_headers()
                    download_response = requests.get(download_url, headers=headers, stream=True)
                    
                    # Check download success
                    if download_response.status_code != 200:
                        logger.error(f"Error downloading file from GCS: {download_response.text}")
                        raise Exception(f"Error downloading file: {download_response.status_code}")
                        
                    # Stream directly to memory
                    audio_data = download_response.content
                    
                    # Delete the file from GCS - use API
                    delete_url = f"https://storage.googleapis.com/storage/v1/b/{self.cloud_bucket}/o/{blob_name}"
                    delete_url = self._build_api_url(delete_url)
                    try:
                        requests.delete(delete_url, headers=headers)
                        logger.info("Successfully cleaned up GCS storage file using REST API")
                    except Exception as e:
                        logger.warning(f"Failed to delete GCS file: {e} - This may need manual cleanup")
                    
                    return audio_data
                else:
                    logger.info(f"Long audio synthesis in progress... (poll {retry_count+1})")
                    retry_count += 1
            
            if not complete:
                logger.error("Long audio synthesis timed out")
                raise Exception("Long audio synthesis timed out after 30 minutes")
            
        except Exception as e:
            logger.error(f"Error in long audio synthesis: {e}")
            raise
            
    def _chunk_ssml(self, ssml_text: str) -> List[str]:
        """Split SSML text into smaller chunks while preserving valid SSML structure.
        
        This is a simple implementation that tries to break SSML at major boundaries.
        """
        import re
        
        # Extract header and root element for reuse
        header_match = re.search(r'<\?xml.*?\?>', ssml_text)
        header = header_match.group(0) if header_match else '<?xml version="1.0"?>'
        
        speak_open_match = re.search(r'<speak[^>]*>', ssml_text)
        speak_open = speak_open_match.group(0) if speak_open_match else '<speak>'
        
        # Extract the content from the SSML
        content = re.sub(r'<\?xml.*?\?>', '', ssml_text)
        content = re.sub(r'<speak[^>]*>', '', content)
        content = re.sub(r'</speak>\s*$', '', content)
        
        # Look for good break points
        # 1. First try to split at major sections (breaks)
        break_points = []
        
        # Look for <break> tags with significant time
        for match in re.finditer(r'<break\s+time="([^"]+)"', content):
            time_value = match.group(1)
            # Only consider breaks of 0.5s or more as potential split points
            if 's' in time_value:
                try:
                    seconds = float(time_value.replace('s', ''))
                    if seconds >= 0.5:
                        break_points.append(match.end())
                except ValueError:
                    pass
        
        # 2. Also look for major prosody or paragraph changes
        for pattern in [r'</prosody>\s*<prosody', r'</p>\s*<p', r'<break', r'</emphasis>\s*<emphasis']:
            for match in re.finditer(pattern, content):
                break_points.append(match.end())
        
        # If we found any good break points, use them
        chunks = []
        if break_points:
            break_points.sort()
            
            # Create chunks based on the break points
            start = 0
            for point in break_points:
                # Only create a chunk if it doesn't exceed our size limit
                chunk_content = content[start:point]
                if len(chunk_content) <= self.max_char_limit - 200:  # Leave room for XML overhead
                    if chunk_content.strip():  # Only add non-empty chunks
                        # Add wrapper tags
                        chunk = f"{header}\n{speak_open}\n{chunk_content}\n</speak>"
                        chunks.append(chunk)
                    start = point
        
        # If we didn't get any valid chunks, we need to force chunking
        if not chunks:
            logger.warning("Using simple SSML chunking - speech quality may be affected")
            
            # Try to find a root prosody tag
            root_prosody_match = re.search(r'^\s*<prosody[^>]*>', content)
            root_prosody_end = re.search(r'</prosody>\s*$', content)
            
            root_start = ""
            root_end = ""
            
            # If we found a root prosody, extract it to add to each chunk
            if root_prosody_match and root_prosody_end:
                root_start = root_prosody_match.group(0)
                root_end = "</prosody>"
                # Remove from content to avoid duplication
                content = re.sub(r'^\s*<prosody[^>]*>', '', content)
                content = re.sub(r'</prosody>\s*$', '', content)
            
            # Calculate chunk size, leaving room for XML overhead
            max_content_size = self.max_char_limit - 300  # XML header + speak tags + some padding
            
            # Simple character-based chunking
            for i in range(0, len(content), max_content_size):
                chunk_content = content[i:min(i+max_content_size, len(content))]
                
                # If this isn't the first chunk and starts with a tag, make sure it's a starting tag
                if i > 0 and chunk_content.lstrip().startswith('<'):
                    # Find the first tag
                    tag_match = re.search(r'<[^>]+>', chunk_content)
                    if tag_match and '/' not in tag_match.group(0):
                        # It's an opening tag, which is good
                        pass
                    else:
                        # Try to find the previous complete tag end
                        prev_content = content[max(0, i-100):i]
                        last_tag_end = prev_content.rfind('>')
                        if last_tag_end >= 0:
                            # Adjust the chunk to start after the tag end
                            i -= (len(prev_content) - last_tag_end - 1)
                            chunk_content = content[i:min(i+max_content_size, len(content))]
                
                # If this isn't the last chunk, try to end at a reasonable boundary
                if i + max_content_size < len(content):
                    # Try to find the last full tag
                    last_tag_end = chunk_content.rfind('>')
                    if last_tag_end >= 0 and last_tag_end < len(chunk_content) - 10:
                        # Truncate at the last tag end
                        chunk_content = chunk_content[:last_tag_end+1]
                
                # Make sure any essential tags are properly closed
                # This is a very simple approach that might not handle all cases correctly
                open_tags = re.findall(r'<([a-zA-Z]+)[^>]*>', chunk_content)
                close_tags = re.findall(r'</([a-zA-Z]+)>', chunk_content)
                
                # Count occurrences of each tag
                tag_count = {}
                for tag in open_tags:
                    tag_count[tag] = tag_count.get(tag, 0) + 1
                
                for tag in close_tags:
                    tag_count[tag] = tag_count.get(tag, 0) - 1
                
                # Add missing closing tags
                for tag, count in tag_count.items():
                    if count > 0:  # More opens than closes
                        chunk_content += f"</{tag}>"
                
                # Add wrapper tags
                full_chunk = f"{header}\n{speak_open}\n{root_start}\n{chunk_content}\n{root_end}\n</speak>"
                chunks.append(full_chunk)
            
        # Make sure we have at least one chunk
        if not chunks:
            # Fallback to the original SSML if all else fails
            chunks = [ssml_text]
            
        logger.info(f"Split SSML into {len(chunks)} chunks")
        return chunks
            
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests.
        
        Returns OAuth headers when service account is available, otherwise
        returns content-type headers only since API key will be in URL.
        """
        # In mock mode, no authentication needed
        if self.use_mock:
            return {}
        
        # Basic headers that are always included
        headers = {"Content-Type": "application/json"}
            
        try:
            # Add OAuth token if we have service account credentials
            if self.have_service_account and self.credentials:
                # Make sure token is refreshed
                auth_req = google.auth.transport.requests.Request()
                self.credentials.refresh(auth_req)
                
                # Add authorization header with bearer token
                headers["Authorization"] = f"Bearer {self.credentials.token}"
                logger.debug("Using service account authentication with OAuth token")
            else:
                logger.debug("Using API key authentication (key will be in URL)")
                
            return headers
            
        except Exception as e:
            logger.error(f"Error getting auth headers: {e}")
            # Return basic headers if token refresh fails
            return headers
            
    def _build_api_url(self, base_url: str, endpoint: str = "") -> str:
        """Build API URL with proper authentication.
        
        Adds API key as query parameter when service account isn't available.
        Fixes URL path formatting issues by handling extra slashes properly.
        
        Args:
            base_url: The base URL for the API
            endpoint: Optional additional endpoint path
            
        Returns:
            The full URL with appropriate authentication
        """
        # Handle path joining correctly to avoid double slashes
        if endpoint:
            # Remove any leading slashes from endpoint
            endpoint = endpoint.lstrip('/')
            # Remove any trailing slashes from base_url
            base_url = base_url.rstrip('/')
            url = f"{base_url}/{endpoint}"
        else:
            url = base_url
        
        # Add API key to URL if not using service account auth
        if not self.have_service_account and self.api_key:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}key={self.api_key}"
            
        return url
            
    def _prepare_ssml_for_google(self, ssml_text: str, for_long_audio_api: bool = False) -> str:
        """Process SSML to make it compatible with Google's TTS APIs.
        
        Google's TTS APIs have strict SSML validation rules, especially the Long Audio API.
        This method normalizes SSML to increase compatibility.
        
        Args:
            ssml_text: The SSML content to normalize
            for_long_audio_api: If True, apply stricter formatting required by the Long Audio API
        """
        try:
            import re
            
            # For Long Audio API, create a completely clean, minimal SSML document
            if for_long_audio_api:
                # First, remove any XML declaration if present
                if "<?xml" in ssml_text:
                    ssml_text = re.sub(r'<\?xml.*?\?>\s*', '', ssml_text)
                
                # Check for nested <speak> tags, which is a common issue
                speak_count = len(re.findall(r'<speak[^>]*>', ssml_text))
                
                if speak_count > 1:
                    logger.warning(f"Found {speak_count} <speak> tags in SSML. Fixing nested tags.")
                    # Extract all content between any speak tags
                    all_content = []
                    for match in re.finditer(r'<speak[^>]*>(.*?)</speak>', ssml_text, re.DOTALL):
                        all_content.append(match.group(1).strip())
                    
                    # Combine all content and wrap in a single speak tag
                    core_content = " ".join(all_content)
                    ssml_text = f"<speak>{core_content}</speak>"
                elif speak_count == 1:
                    # Just one speak tag, simplify it by removing attributes
                    ssml_text = re.sub(r'<speak[^>]*>', '<speak>', ssml_text)
                else:
                    # No speak tags, add them
                    ssml_text = f"<speak>{ssml_text}</speak>"
                
                # Make other adjustments for Long Audio API compatibility
                # Fix common formatting issues that cause Long Audio API to reject SSML
                
                # Fix double spaces
                ssml_text = re.sub(r'\s{2,}', ' ', ssml_text)
                
                # Fix rate attributes (ensure proper format)
                # Example: replace rate="95%" with rate="0.95"
                for rate_match in re.finditer(r'rate="(\d+)%"', ssml_text):
                    rate_value = int(rate_match.group(1))
                    # Convert percentage to decimal
                    decimal_rate = rate_value / 100.0
                    # Replace with decimal format
                    ssml_text = ssml_text.replace(rate_match.group(0), f'rate="{decimal_rate}"')
                
                # Fix volume attributes (ensure proper format)
                # Example: replace volume="+10%" with volume="loud"
                ssml_text = re.sub(r'volume="\+\d+%"', 'volume="loud"', ssml_text)
                
                # Fix relative pitch adjustments
                # Example: replace pitch="+5%" with pitch="high"
                ssml_text = re.sub(r'pitch="\+\d+%"', 'pitch="high"', ssml_text)
                ssml_text = re.sub(r'pitch="-\d+%"', 'pitch="low"', ssml_text)
                
                # For Long Audio API, we need to ensure tags are properly balanced
                # For complex tags like prosody, we remove them entirely to avoid imbalance
                if for_long_audio_api:
                    # Remove the <speak> tags temporarily
                    content = re.sub(r'</?speak[^>]*>', '', ssml_text)
                    
                    # First, handle nested tags - remove all prosody tags since Google often rejects them in Long Audio API
                    # This is a simple approach - a more complex approach would be to balance them properly
                    content = re.sub(r'<prosody[^>]*>', '', content)
                    content = re.sub(r'</prosody>', '', content)
                    
                    # Now wrap in speak tags again
                    ssml_text = f"<speak>{content}</speak>"
                
                logger.info("Created simplified SSML format for Long Audio API")
            else:
                # Standard cleanup for regular API
                # Remove XML declaration if present
                if "<?xml" in ssml_text:
                    ssml_text = re.sub(r'<\?xml.*?\?>\s*', '', ssml_text)
                
                # Check if <speak> tag exists and normalize it
                if "<speak" in ssml_text:
                    # Remove any attributes from the speak tag
                    ssml_text = re.sub(r'<speak[^>]*>', '<speak>', ssml_text)
                else:
                    # Wrap in speak tag if not present
                    ssml_text = f"<speak>{ssml_text}</speak>"
                    
                # Remove any extra whitespace between speak tags
                ssml_text = re.sub(r'<speak>\s+', '<speak>', ssml_text)
                ssml_text = re.sub(r'\s+</speak>', '</speak>', ssml_text)
            
            # Final validation check - make sure we only have one pair of speak tags
            if for_long_audio_api:
                open_tags = len(re.findall(r'<speak[^>]*>', ssml_text))
                close_tags = len(re.findall(r'</speak>', ssml_text))
                
                if open_tags != 1 or close_tags != 1:
                    logger.warning(f"After processing, SSML still has {open_tags} opening and {close_tags} closing speak tags. Fixing...")
                    # Extract all content without speak tags
                    content = re.sub(r'</?speak[^>]*>', '', ssml_text)
                    # Wrap in a single pair of speak tags
                    ssml_text = f"<speak>{content}</speak>"
                
                # For Long Audio API, double check that the SSML is valid
                # Look for common issues that would cause the API to reject it
                if "<prosody" in ssml_text and "</prosody>" not in ssml_text:
                    logger.warning("Found unclosed prosody tag. Removing all prosody tags.")
                    # Extract content inside speak tags
                    match = re.search(r'<speak[^>]*>(.*?)</speak>', ssml_text, re.DOTALL)
                    if match:
                        content = match.group(1)
                        # Remove prosody tags
                        content = re.sub(r'<prosody[^>]*>', '', content)
                        content = re.sub(r'</prosody>', '', content)
                        ssml_text = f"<speak>{content}</speak>"
            
            logger.info(f"Normalized SSML for better Google TTS compatibility")
            return ssml_text
        except Exception as e:
            logger.warning(f"Failed to normalize SSML: {e}")
            return ssml_text  # Return original if normalization fails
            
    def _process_long_text(self, text: str, voice_name: Optional[str] = None, is_ssml: bool = False) -> bytes:
        """Process long text by breaking it into smaller chunks or using Long Audio API.
        
        For SSML, we use the Long Audio API since it's challenging to split SSML correctly.
        For regular text, we can either use chunking or the Long Audio API depending on length.
        """
        # For testing/demo purposes, don't make actual API calls
        if self.use_mock:
            # Return dummy audio data for mock response
            logger.info("Using mock audio data (demo mode)")
            return b"MOCK_AUDIO_DATA"
        
        # For regular text, use Long Audio API
        logger.info(f"Using Long Audio API")
        try:
            return self._long_audio_synthesis(text, voice_name, is_ssml=False)
        except Exception as e:
            logger.error(f"Error processing long text with Long Audio API: {e}")
            # Fall back to chunking if Long Audio API fails
            logger.info("Falling back to chunking method")
        
    
    def generate_audio(self, script_text: str, voice_name: Optional[str] = None, is_ssml: bool = False) -> bytes:
        """Generate audio from script text, handling any length limitations.
        
        Args:
            script_text: The text or SSML content to convert to speech
            voice_name: Optional voice name to use instead of the default
            is_ssml: If True, the script_text is treated as SSML content
        """
        try:
            return self._process_long_text(script_text, voice_name, is_ssml=False)
        except Exception as e:
            logger.error(f"Failed to generate audio: {e}")
            raise
    
    def get_script_text(self, team_code: str, date: Optional[datetime.date] = None) -> tuple[str, bool]:
        """Get the script text for a team.
        
        First checks for an optimized SSML file, then regular SSML, then plain text.
        
        Returns:
            A tuple containing (script_text, is_ssml_format)
        """
        date = date or datetime.date.today()
        date_str = date.strftime("%Y-%m-%d")
        
        # Find text file
        text_file_path = os.path.join(SCRIPTS_DIR, team_code, f"{date_str}.txt")
        try:
            with open(text_file_path, "r") as f:
                script_text = f.read()
            logger.info(f"Found text script: {text_file_path}")
            return script_text, False
        except FileNotFoundError:
            logger.error(f"No script file found: Tried {text_file_path}")
            return "", False
    
    def generate_and_save_audio(self, team_code: str, date: Optional[datetime.date] = None) -> str:
        """Generate audio from script and save to file."""
        date = date or datetime.date.today()
        date_str = date.strftime("%Y-%m-%d")
        team_name = MLB_TEAMS.get(team_code, team_code)
        
        # Ensure directories exist
        team_audio_dir = os.path.join(AUDIO_DIR, team_code)
        os.makedirs(team_audio_dir, exist_ok=True)
        
        # Define output file path
        output_file = os.path.join(team_audio_dir, f"{date_str}.mp3")
        
        # Get script text and check if it's SSML
        script_text, is_ssml = self.get_script_text(team_code, date)
        
        if not script_text:
            logger.error(f"No script text found for {team_name} on {date_str}")
            return ""
        
        script_type = "SSML" if is_ssml else "text"
        logger.info(f"Generating audio from {script_type} for {team_name} on {date_str}")
        
        try:
            # Generate audio, specifying if the content is SSML
            audio_data = self.generate_audio(script_text, is_ssml=is_ssml)
            
            # Save to file
            with open(output_file, "wb") as f:
                f.write(audio_data)
            
            logger.info(f"Audio saved to {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to generate or save audio: {e}")
            return ""