import os
import json
import datetime
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import elevenlabs
from elevenlabs import Voice, VoiceSettings

from config.config import ELEVENLABS_API_KEY, ELEVENLABS_API_BASE_URL, ELEVENLABS_VOICE_ID
from config.config import SCRIPTS_DIR, AUDIO_DIR, MLB_TEAMS
from utils.logger import get_logger

logger = get_logger(__name__)

class ElevenLabsTTS:
    def __init__(self):
        self.api_key = ELEVENLABS_API_KEY
        self.voice_id = ELEVENLABS_VOICE_ID
        
        # Check if we're using a demo key
        self.use_mock = not self.api_key or self.api_key == "sample_elevenlabs_api_key"
        
        # We'll use the API key in each request rather than setting it globally
            
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _tts_request(self, text: str, voice_id: Optional[str] = None) -> bytes:
        """Make a TTS request to ElevenLabs using their SDK."""
        # For testing/demo purposes, don't make actual API calls
        if self.use_mock:
            # Return dummy audio data for mock response
            return b"MOCK_AUDIO_DATA"
            
        # Use a default voice ID if none is provided or config value is invalid
        voice_id = voice_id or "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
        
        try:
            # Configure voice settings
            voice_settings = VoiceSettings(
                stability=0.0,
                similarity_boost=0.0,
                style=1.0,
                use_speaker_boost=False,
                speed=1.0
            )
            
            # Create voice object
            voice = Voice(voice_id=voice_id, settings=voice_settings)
            
            # Initialize client with API key
            client = elevenlabs.client.ElevenLabs(api_key=self.api_key)
            
            # Generate audio using the client - returns a generator
            audio_stream = client.generate(
                text=text,
                voice=voice,
                model="eleven_monolingual_v1"
            )
            
            # Collect all chunks from the generator
            audio_chunks = []
            for chunk in audio_stream:
                audio_chunks.append(chunk)
                
            # Combine all chunks into one audio byte string
            audio_data = b''.join(audio_chunks)
            
            return audio_data
        except Exception as e:
            logger.error(f"Error in TTS request: {e}")
            raise
    
    def generate_audio(self, script_text: str, voice_id: Optional[str] = None) -> bytes:
        """Generate audio from script text."""
        try:
            return self._tts_request(script_text, voice_id)
        except Exception as e:
            logger.error(f"Failed to generate audio: {e}")
            raise
    
    def get_script_text(self, team_code: str, date: Optional[datetime.date] = None) -> str:
        """Get the script text for a team."""
        date = date or datetime.date.today()
        date_str = date.strftime("%Y-%m-%d")
        
        script_file_path = os.path.join(SCRIPTS_DIR, team_code, f"{date_str}.txt")
        
        try:
            with open(script_file_path, "r") as f:
                script_text = f.read()
            return script_text
        except FileNotFoundError:
            logger.error(f"Script file not found: {script_file_path}")
            return ""
    
    def generate_and_save_audio(self, team_code: str, date: Optional[datetime.date] = None) -> str:
        """Generate and save audio for a team's script."""
        date = date or datetime.date.today()
        date_str = date.strftime("%Y-%m-%d")
        team_name = MLB_TEAMS.get(team_code)
        
        # Get script text
        script_text = self.get_script_text(team_code, date)
        if not script_text:
            logger.error(f"No script found for {team_name} on {date_str}")
            return ""
        
        logger.info(f"Generating audio for {team_name} on {date_str}")
        
        # For demo/testing purposes
        if self.use_mock:
            logger.info(f"Using mock audio for {team_name} (demo mode)")
            
            # Create a placeholder audio file with the script content
            team_audio_dir = os.path.join(AUDIO_DIR, team_code)
            os.makedirs(team_audio_dir, exist_ok=True)
            
            # Save as .mp3 for consistency with real implementation
            audio_file_path = os.path.join(team_audio_dir, f"{date_str}.mp3")
            with open(audio_file_path, "wb") as f:
                f.write(b"MOCK_AUDIO_DATA")
                
            logger.info(f"Created mock audio file at {audio_file_path}")
            return audio_file_path
        
        try:
            # Generate audio with real API
            audio_data = self.generate_audio(script_text)
            
            # Save to file
            team_audio_dir = os.path.join(AUDIO_DIR, team_code)
            os.makedirs(team_audio_dir, exist_ok=True)
            
            audio_file_path = os.path.join(team_audio_dir, f"{date_str}.mp3")
            with open(audio_file_path, "wb") as f:
                f.write(audio_data)
                
            logger.info(f"Saved audio for {team_name} to {audio_file_path}")
            return audio_file_path
            
        except Exception as e:
            logger.error(f"Error generating audio for {team_name}: {e}")
            return ""