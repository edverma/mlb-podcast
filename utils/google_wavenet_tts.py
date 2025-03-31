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
            logger.info("No service account credentials file found. Using API key authentication.")
        
        # Set up clients with service account credentials if available
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
            except Exception as e:
                logger.error(f"Error initializing Google Cloud clients: {e}")
                self.have_service_account = False
        
        # Check if we're using demo/invalid API key
        self.use_mock = not self.api_key
        
        # Check if long audio API is available
        self.long_audio_available = bool(
            self.api_key and self.project_id and self.cloud_bucket and 
            (self.have_service_account or self.api_key)
        )
        
        if not self.long_audio_available:
            missing = []
            if not self.api_key:
                missing.append("GOOGLE_CLOUD_API_KEY")
            if not self.project_id:
                missing.append("GOOGLE_CLOUD_PROJECT_ID")
            if not self.cloud_bucket:
                missing.append("GOOGLE_CLOUD_BUCKET")
            if not self.have_service_account and not self.service_account_file:
                missing.append("GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE")
                
            logger.warning("Long Audio API is not available - SSML will use chunking fallback")
            logger.warning(f"Missing configuration: {', '.join(missing)}")
            logger.warning("Set these variables in .env to enable Long Audio API")
        
        # Character limits
        self.max_char_limit = 5000  # Standard TTS API limit is 5000 bytes
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _tts_request(self, text: str, voice_name: Optional[str] = None, is_ssml: bool = False) -> bytes:
        """Make a TTS request to Google Wavenet API using API Key authentication.
        
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
                import base64
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
            
        except Exception as e:
            logger.error(f"Error in Google Wavenet TTS request: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _long_audio_synthesis(self, text: str, voice_name: Optional[str] = None, is_ssml: bool = False) -> bytes:
        """Use Google's Long Audio API for synthesizing longer content.
        
        This method handles longer texts by using Google Cloud's long audio synthesis,
        which requires a GCS bucket for storing the results.
        """
        if self.use_mock:
            logger.info("Using mock audio data (demo mode)")
            return b"MOCK_AUDIO_DATA"
            
        # Generate a unique ID for this synthesis request
        synthesis_id = str(uuid.uuid4())
        output_gcs_uri = f"gs://{self.cloud_bucket}/audio-{synthesis_id}.mp3"
        
        # Prepare the request
        url = f"{self.long_audio_api_base_url}/projects/{self.project_id}/locations/{self.location}/operations"
        
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
        
        logger.info(f"Starting long audio synthesis for content of length {len(text)} bytes")
        
        try:
            # Get authentication headers
            headers = self._get_auth_headers()
            
            # Build URL for Long Audio API
            api_path = f"projects/{self.project_id}/locations/{self.location}:synthesizeLongAudio"
            api_url = self._build_api_url(self.long_audio_api_base_url, api_path)
            
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
                    
                    if self.have_service_account:
                        # Use the storage client with service account auth
                        try:
                            bucket = self.storage_client.bucket(self.cloud_bucket)
                            blob = bucket.blob(f"audio-{synthesis_id}.mp3")
                            
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
                            logger.info("Successfully downloaded and cleaned up GCS storage file")
                        except Exception as e:
                            logger.error(f"Error accessing GCS with service account: {e}")
                            raise
                    else:
                        # Fall back to REST API with API key
                        download_url = f"https://storage.googleapis.com/storage/v1/b/{self.cloud_bucket}/o/audio-{synthesis_id}.mp3?alt=media"
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
                        delete_url = f"https://storage.googleapis.com/storage/v1/b/{self.cloud_bucket}/o/audio-{synthesis_id}.mp3"
                        delete_url = self._build_api_url(delete_url)
                        try:
                            requests.delete(delete_url, headers=headers)
                            logger.info("Successfully cleaned up GCS storage file")
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
        
        Returns OAuth headers when service account is available, otherwise empty dict.
        For API key auth, the key is added to the URL rather than header.
        """
        if self.use_mock:
            return {}
            
        try:
            if self.have_service_account:
                # Create auth request
                auth_req = google.auth.transport.requests.Request()
                # Refresh credentials token
                self.credentials.refresh(auth_req)
                # Return the proper authorization header
                return {
                    "Authorization": f"Bearer {self.credentials.token}",
                    "Content-Type": "application/json"
                }
            else:
                # Just return content-type header, API key will be in URL
                return {"Content-Type": "application/json"}
        except Exception as e:
            logger.error(f"Error getting auth headers: {e}")
            raise
            
    def _build_api_url(self, base_url: str, endpoint: str = "") -> str:
        """Build API URL with proper authentication.
        
        Adds API key as query parameter when service account isn't available.
        
        Args:
            base_url: The base URL for the API
            endpoint: Optional additional endpoint path
            
        Returns:
            The full URL with appropriate authentication
        """
        url = f"{base_url}/{endpoint}" if endpoint else base_url
        
        # Add API key to URL if not using service account auth
        if not self.have_service_account and self.api_key:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}key={self.api_key}"
            
        return url
            
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
        
        # For SSML, try to use Long Audio API to avoid splitting XML
        if is_ssml:
            if self.long_audio_available:
                logger.info("Processing SSML content using Long Audio API")
                try:
                    return self._long_audio_synthesis(text, voice_name, is_ssml=True)
                except Exception as e:
                    logger.error(f"Error processing SSML with Long Audio API: {e}")
                    logger.info("Falling back to standard API with SSML")
            
            # If Long Audio API isn't available or fails, try standard API directly
            # This will work only for short SSML (under 5000 bytes)
            logger.info("Processing SSML content using standard API")
            if len(text) <= self.max_char_limit:
                try:
                    return self._tts_request(text, voice_name, is_ssml=True)
                except Exception as e:
                    logger.error(f"Error processing SSML with standard API: {e}")
                    raise
            else:
                logger.warning(f"SSML content is too long ({len(text)} bytes) for standard API")
                logger.warning("Attempting basic SSML chunking (may affect speech quality)")
                
                try:
                    # Basic SSML chunking - this is not perfect but should work for many cases
                    chunks = self._chunk_ssml(text)
                    logger.info(f"Split SSML into {len(chunks)} chunks")
                    
                    audio_chunks = []
                    for i, chunk in enumerate(chunks):
                        logger.info(f"Processing SSML chunk {i+1}/{len(chunks)}")
                        chunk_audio = self._tts_request(chunk, voice_name, is_ssml=True)
                        audio_chunks.append(chunk_audio)
                    
                    # Combine audio chunks
                    return b''.join(audio_chunks)
                    
                except Exception as e:
                    logger.error(f"Error processing chunked SSML: {e}")
                    logger.error("To process long SSML properly, configure Long Audio API settings in .env")
                    logger.error("For details, see docs/google_wavenet_setup.md")
                    raise Exception("Could not process long SSML")
        
        # For regular text, use Long Audio API if text is very long (>50K bytes) and available
        if len(text) > 50000 and self.long_audio_available:
            logger.info(f"Text is very long ({len(text)} bytes), using Long Audio API")
            try:
                return self._long_audio_synthesis(text, voice_name, is_ssml=False)
            except Exception as e:
                logger.error(f"Error processing long text with Long Audio API: {e}")
                # Fall back to chunking if Long Audio API fails
                logger.info("Falling back to chunking method")
        
        # For regular text using chunking approach
        logger.info("Processing text using chunking approach")
        # Split text by sentences to avoid cutting words
        sentences = text.replace('\n', ' ').split('.')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Add the period back except for the last empty sentence if the text ends with a period
            if sentence:
                sentence = sentence + '.'
            
            # If adding this sentence would exceed the limit, add the current chunk to chunks
            # and start a new chunk
            if len(current_chunk) + len(sentence) > self.max_char_limit:
                chunks.append(current_chunk)
                current_chunk = sentence
            else:
                current_chunk += sentence
                
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk)
        
        # Process each chunk
        audio_chunks = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
            try:
                audio_data = self._tts_request(chunk, voice_name, is_ssml=False)
                audio_chunks.append(audio_data)
            except Exception as e:
                logger.error(f"Error processing chunk {i+1}: {e}")
                raise
        
        # Combine the audio chunks (this is a simple concatenation and may have small gaps)
        # For more advanced audio concatenation, consider using a library like pydub
        return b''.join(audio_chunks)
    
    def generate_audio(self, script_text: str, voice_name: Optional[str] = None, is_ssml: bool = False) -> bytes:
        """Generate audio from script text, handling any length limitations.
        
        Args:
            script_text: The text or SSML content to convert to speech
            voice_name: Optional voice name to use instead of the default
            is_ssml: If True, the script_text is treated as SSML content
        """
        try:
            # Check if this is SSML content
            if is_ssml:
                logger.info("Processing SSML content for audio generation")
                return self._process_long_text(script_text, voice_name, is_ssml=True)
            
            # For regular text, process based on length
            if len(script_text) <= self.max_char_limit:
                logger.info(f"Text length ({len(script_text)} chars) within limit, processing directly")
                return self._tts_request(script_text, voice_name, is_ssml=False)
            
            # For longer text, break it into chunks and process each chunk
            else:
                logger.info(f"Text length ({len(script_text)} chars) exceeds limit, processing in chunks")
                return self._process_long_text(script_text, voice_name, is_ssml=False)
        
        except Exception as e:
            logger.error(f"Failed to generate audio: {e}")
            raise
    
    def get_script_text(self, team_code: str, date: Optional[datetime.date] = None) -> tuple[str, bool]:
        """Get the script text for a team.
        
        Returns:
            A tuple containing (script_text, is_ssml_format)
        """
        date = date or datetime.date.today()
        date_str = date.strftime("%Y-%m-%d")
        
        # First try to find an SSML file
        ssml_file_path = os.path.join(SCRIPTS_DIR, team_code, f"{date_str}.ssml")
        
        try:
            with open(ssml_file_path, "r") as f:
                script_text = f.read()
            logger.info(f"Found SSML script: {ssml_file_path}")
            return script_text, True
        except FileNotFoundError:
            # Fall back to text file
            text_file_path = os.path.join(SCRIPTS_DIR, team_code, f"{date_str}.txt")
            try:
                with open(text_file_path, "r") as f:
                    script_text = f.read()
                logger.info(f"Found text script: {text_file_path}")
                return script_text, False
            except FileNotFoundError:
                logger.error(f"No script file found: Tried {ssml_file_path} and {text_file_path}")
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