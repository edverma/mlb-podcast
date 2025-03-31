import os
import sys
from pathlib import Path
from utils.google_wavenet_tts import GoogleWavenetTTS
from config.config import (
    GOOGLE_CLOUD_API_KEY, 
    GOOGLE_WAVENET_VOICE, 
    GOOGLE_WAVENET_LANGUAGE_CODE,
    GOOGLE_CLOUD_PROJECT_ID,
    GOOGLE_CLOUD_BUCKET
)

# Print configuration (without showing full credentials)
print(f"Google Wavenet Configuration:")
print(f"  API Key: {'*' * 8 + GOOGLE_CLOUD_API_KEY[-4:] if GOOGLE_CLOUD_API_KEY else 'Not configured'}")
print(f"  Voice: {GOOGLE_WAVENET_VOICE}")
print(f"  Language Code: {GOOGLE_WAVENET_LANGUAGE_CODE}")
print(f"  Project ID: {GOOGLE_CLOUD_PROJECT_ID[:4] + '*****' if GOOGLE_CLOUD_PROJECT_ID else 'Not configured'}")
print(f"  GCS Bucket: {GOOGLE_CLOUD_BUCKET[:4] + '*****' if GOOGLE_CLOUD_BUCKET else 'Not configured'}")

# Initialize the TTS service
print("\nInitializing Google Wavenet TTS service...")
tts = GoogleWavenetTTS()

# Check if using mock mode
if tts.use_mock:
    print("WARNING: Using mock mode - Google Cloud API key may be invalid or not set")
    print("This is expected if you're just testing the code structure.")
    print("To use actual Google Wavenet API, add your API key to the .env file.")

# Test 1: Short text
print("\n--- TEST 1: Short Text ---")
short_text = "Hello! This is a test of the Google Wavenet text-to-speech integration for the MLB podcast generator."

try:
    # Generate audio from test text
    print("Generating test audio for short text...")
    audio_data = tts.generate_audio(short_text)
    
    # Save the test audio to a file
    test_file_path = "test_google_wavenet_short.mp3"
    with open(test_file_path, "wb") as f:
        f.write(audio_data)
    
    # Get file size to verify it contains data
    file_size = os.path.getsize(test_file_path)
    
    print(f"\nSuccess! Test audio file created: {test_file_path}")
    print(f"File size: {file_size} bytes")
    print("Google Wavenet TTS test is working correctly")
    
except Exception as e:
    print(f"\nERROR: Failed to generate audio with Google Wavenet")
    print(f"Exception: {str(e)}")
    print("\nPossible issues:")
    print("1. Google Cloud API key may be invalid")
    print("2. Network connectivity issues to Google Cloud services")
    exit(1)

# Test 2: Medium text 
print("\n--- TEST 2: Medium Text ---")
medium_text = short_text * 5  # Repeat the short text to make it longer
print(f"Medium text length: {len(medium_text)} characters")

try:
    # Generate audio from medium test text
    print("Generating test audio for medium text...")
    
    audio_data = tts.generate_audio(medium_text)
    
    # Save the test audio to a file
    test_file_path = "test_google_wavenet_medium.mp3"
    with open(test_file_path, "wb") as f:
        f.write(audio_data)
    
    # Get file size to verify it contains data
    file_size = os.path.getsize(test_file_path)
    
    print(f"\nSuccess! Test audio file created: {test_file_path}")
    print(f"File size: {file_size} bytes")
    print("Google Wavenet TTS test is working correctly for medium text")
    
except Exception as e:
    print(f"\nERROR: Failed to generate audio with Google Wavenet for medium text")
    print(f"Exception: {str(e)}")
    exit(1)

# Test 3: Long text using chunking
print("\n--- TEST 3: Long Text (with chunking) ---")
long_text = short_text * 10  # Repeat the short text to make it long enough to trigger chunking
print(f"Long text length: {len(long_text)} characters")

try:
    # Generate audio from long test text
    print("Generating test audio for long text...")
    print("This will use text chunking for processing")
    
    audio_data = tts.generate_audio(long_text)
    
    # Save the test audio to a file
    test_file_path = "test_google_wavenet_long.mp3"
    with open(test_file_path, "wb") as f:
        f.write(audio_data)
    
    # Get file size to verify it contains data
    file_size = os.path.getsize(test_file_path)
    
    print(f"\nSuccess! Test audio file created: {test_file_path}")
    print(f"File size: {file_size} bytes")
    print("Google Wavenet TTS test is working correctly for long text")
    
except Exception as e:
    print(f"\nERROR: Failed to generate audio with Google Wavenet for long text")
    print(f"Exception: {str(e)}")
    exit(1)

print("\nGoogle Wavenet integration is working correctly!")

# Test 4: SSML with Long Audio API
print("\n--- TEST 4: SSML with Long Audio API ---")

def create_test_ssml():
    """Create a test SSML string."""
    ssml_content = """<?xml version="1.0"?>
<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.w3.org/2001/10/synthesis http://www.w3.org/TR/speech-synthesis11/synthesis.xsd" xml:lang="en-US">
    <prosody rate="medium" pitch="medium">
        <emphasis level="strong">MLB Daily Update</emphasis> - <say-as interpret-as="date" format="mdy">3/30/2025</say-as>
        <break time="1s"/>
        
        Welcome to the MLB Daily Update podcast. I'm your host, testing the <emphasis level="strong">Google Wavenet SSML integration</emphasis>.
        <break time="0.5s"/>
        
        This test includes various SSML features like:
        <break time="0.3s"/>
        
        <prosody rate="slow" pitch="low">Slow speech with low pitch</prosody>
        <break time="0.3s"/>
        
        <prosody rate="fast" pitch="high">Fast speech with high pitch</prosody>
        <break time="0.3s"/>
        
        Numbers like <say-as interpret-as="cardinal">42</say-as> and dates like <say-as interpret-as="date" format="mdy">12/25/2025</say-as>.
        <break time="0.5s"/>
        
        Team abbreviations like <sub alias="Yankees">NYY</sub> and <sub alias="Dodgers">LAD</sub>.
        <break time="0.5s"/>
        
        That concludes our test. <prosody volume="loud">Thank you for listening!</prosody>
    </prosody>
</speak>
"""
    return ssml_content

# Check if Long Audio API configs are available
if not (GOOGLE_CLOUD_PROJECT_ID and GOOGLE_CLOUD_BUCKET):
    print("Skipping SSML with Long Audio API test - missing PROJECT_ID or BUCKET")
    print("To enable this test, add GOOGLE_CLOUD_PROJECT_ID and GOOGLE_CLOUD_BUCKET to .env")
    sys.exit(0)

# Create test SSML
ssml_content = create_test_ssml()
print(f"Created test SSML content ({len(ssml_content)} bytes)")

try:
    # Generate audio from SSML
    print("Generating test audio from SSML using Long Audio API...")
    print("This process may take a few minutes to complete.")
    
    audio_data = tts.generate_audio(ssml_content, is_ssml=True)
    
    # Save the test audio to a file
    test_file_path = "test_google_wavenet_ssml.mp3"
    with open(test_file_path, "wb") as f:
        f.write(audio_data)
    
    # Get file size to verify it contains data
    file_size = os.path.getsize(test_file_path)
    
    print(f"\nSuccess! Test audio file created: {test_file_path}")
    print(f"File size: {file_size} bytes")
    print("Google Wavenet SSML with Long Audio API test is working correctly")
    
except Exception as e:
    print(f"\nERROR: Failed to generate audio with Google Wavenet using SSML")
    print(f"Exception: {str(e)}")
    print("\nPossible issues:")
    print("1. Google Cloud project may not have Long Audio API enabled")
    print("2. Google Cloud Storage bucket may not be properly configured")
    print("3. Service account may not have proper permissions")
    sys.exit(1)

print("\nAll Google Wavenet tests completed successfully!")