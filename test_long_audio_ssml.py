"""
Test script to verify Google Cloud Text-to-Speech Long Audio API with SSML.
"""

import os
import sys
from utils.google_wavenet_tts import GoogleWavenetTTS
from config.config import (
    GOOGLE_CLOUD_API_KEY,
    GOOGLE_WAVENET_VOICE,
    GOOGLE_WAVENET_LANGUAGE_CODE,
    GOOGLE_CLOUD_PROJECT_ID,
    GOOGLE_CLOUD_BUCKET,
    GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE
)

# Print configuration (without showing full credentials)
print(f"Google Wavenet Long Audio API Test Configuration:")
print(f"  API Key: {'*' * 8 + GOOGLE_CLOUD_API_KEY[-4:] if GOOGLE_CLOUD_API_KEY else 'Not configured'}")
print(f"  Voice: {GOOGLE_WAVENET_VOICE}")
print(f"  Language Code: {GOOGLE_WAVENET_LANGUAGE_CODE}")
print(f"  Project ID: {GOOGLE_CLOUD_PROJECT_ID[:4] + '*****' if GOOGLE_CLOUD_PROJECT_ID else 'Not configured'}")
print(f"  GCS Bucket: {GOOGLE_CLOUD_BUCKET[:4] + '*****' if GOOGLE_CLOUD_BUCKET else 'Not configured'}")
print(f"  Service Account: {'Configured' if GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE and os.path.exists(GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE) else 'Not configured or not found'}")

# Create a simple SSML test file for the Long Audio API
# Using extremely simple SSML to maximize chances of success
def create_test_ssml():
    """Create the simplest possible SSML that should work with Long Audio API."""
    ssml = """<speak>
Hello, this is a test of the Google Cloud Text to Speech Long Audio API with SSML.
<break time="1s"/>
This test uses service account authentication to access the Long Audio API.
<break time="1s"/>
If you can hear this message, it means the Long Audio API is working correctly with SSML.
</speak>"""
    return ssml

# Initialize TTS engine
print("\nInitializing Google Wavenet TTS service...")
tts = GoogleWavenetTTS()

# Check authentication status
print("\nAuthentication Status:")
if tts.have_service_account:
    print("✅ Using service account authentication (preferred)")
    print(f"  - Service account file: {GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE}")
    if tts.storage_client:
        print("✅ Storage client initialized successfully")
    else:
        print("❌ Storage client failed to initialize")
    if tts.tts_client:
        print("✅ Text-to-Speech client initialized successfully")
    else:
        print("❌ Text-to-Speech client failed to initialize")
elif tts.api_key:
    print("⚠️ Using API key authentication (fallback)")
    print("  - For better security and reliability, consider setting up service account authentication")
else:
    print("❌ No valid authentication method configured")
    print("This test cannot run without authentication. Exiting.")
    sys.exit(1)

# Check if Long Audio API is available
if not tts.long_audio_available:
    print("❌ Long Audio API is not available. This test requires:")
    print("  - Valid authentication (service account or API key)")
    print("  - Google Cloud project ID")
    print("  - Google Cloud Storage bucket")
    sys.exit(1)

# Create test SSML
print("\nCreating simple test SSML...")
ssml_text = create_test_ssml()
print(f"Created SSML content ({len(ssml_text)} characters)")

# Process through Long Audio API
print("\nSending to Long Audio API...")
print("This may take a minute or two to complete.")

try:
    # Specially prepare the SSML for Long Audio API
    prepared_ssml = tts._prepare_ssml_for_google(ssml_text, for_long_audio_api=True)
    
    # Send to Long Audio API
    audio_data = tts._long_audio_synthesis(prepared_ssml, is_ssml=True)
    
    # Save the test audio to a file
    test_file_path = "test_long_audio_ssml.mp3"
    with open(test_file_path, "wb") as f:
        f.write(audio_data)
    
    # Get file size to verify it contains data
    file_size = os.path.getsize(test_file_path)
    
    print(f"\nSuccess! Test audio file created: {test_file_path}")
    print(f"File size: {file_size} bytes")
    print("Google Wavenet Long Audio API with SSML is working correctly!")
    
except Exception as e:
    print(f"\nERROR: Failed to generate audio with Long Audio API")
    print(f"Exception: {str(e)}")
    sys.exit(1)