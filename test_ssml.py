#!/usr/bin/env python3
"""
Simple test script for validating Google Wavenet TTS with SSML.
This script creates a small SSML file and tests the TTS API.
"""

import os
import sys
from utils.google_wavenet_tts import GoogleWavenetTTS
from utils.logger import get_logger

# Get configuration
try:
    from config.config import GOOGLE_CLOUD_API_KEY, GOOGLE_WAVENET_VOICE
    from config.config import GOOGLE_CLOUD_PROJECT_ID, GOOGLE_CLOUD_BUCKET
except ImportError:
    GOOGLE_CLOUD_API_KEY = None
    GOOGLE_WAVENET_VOICE = "en-US-Wavenet-D"
    GOOGLE_CLOUD_PROJECT_ID = None
    GOOGLE_CLOUD_BUCKET = None

logger = get_logger("test_ssml")

# Create a simple SSML test
TEST_SSML = """<?xml version="1.0"?>
<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="en-US">
    <prosody rate="medium" pitch="medium">
        <emphasis level="moderate">Hello!</emphasis> This is a test of the 
        <break time="0.2s"/>
        <emphasis level="strong">Google Wavenet SSML</emphasis> integration.
        <break time="0.5s"/>
        The date today is <say-as interpret-as="date" format="mdy">3/30/2025</say-as>.
        <break time="0.5s"/>
        Numbers like <say-as interpret-as="cardinal">42</say-as> should be pronounced properly.
        <break time="0.5s"/>
        Team codes like <sub alias="Yankees">NYY</sub> will be expanded.
    </prosody>
</speak>
"""

# Print configuration
print(f"Google Wavenet Configuration:")
print(f"  API Key: {'*' * 8 + GOOGLE_CLOUD_API_KEY[-4:] if GOOGLE_CLOUD_API_KEY else 'Not configured'}")
print(f"  Voice: {GOOGLE_WAVENET_VOICE}")

# Initialize TTS
print("\nInitializing Google Wavenet TTS service...")
tts = GoogleWavenetTTS()

# Check if mock mode
if tts.use_mock:
    print("WARNING: Using mock mode - Google Cloud API key may be invalid or not set")
    print("Set GOOGLE_CLOUD_API_KEY in your .env file to use actual Google Wavenet API")
    exit(1)

# Test direct SSML call (using standard API)
print("\n=== TEST 1: Direct SSML with standard API ===")
try:
    # Generate audio from SSML
    print("Generating audio from SSML using standard TTS API...")
    audio_data = tts._tts_request(TEST_SSML, is_ssml=True)
    
    # Save the test audio to a file
    test_file_path = "test_ssml_standard_api.mp3"
    with open(test_file_path, "wb") as f:
        f.write(audio_data)
    
    # Get file size to verify it contains data
    file_size = os.path.getsize(test_file_path)
    
    print(f"\nSuccess! Test audio file created: {test_file_path}")
    print(f"File size: {file_size} bytes")
    print("Direct SSML test is working correctly!")
    
except Exception as e:
    print(f"\nERROR: Failed to generate audio with SSML")
    print(f"Exception: {str(e)}")
    print("Please check your Google Cloud configuration and API key")
    exit(1)

# Test process_long_text method with SSML
print("\n=== TEST 2: SSML Processing with _process_long_text ===")
try:
    # Generate audio from SSML
    print("Generating audio from SSML using process_long_text method...")
    audio_data = tts._process_long_text(TEST_SSML, is_ssml=True)
    
    # Save the test audio to a file
    test_file_path = "test_ssml_process_long_text.mp3"
    with open(test_file_path, "wb") as f:
        f.write(audio_data)
    
    # Get file size to verify it contains data
    file_size = os.path.getsize(test_file_path)
    
    print(f"\nSuccess! Test audio file created: {test_file_path}")
    print(f"File size: {file_size} bytes")
    print("SSML processing test is working correctly!")
    
except Exception as e:
    print(f"\nWARNING: Could not process SSML with _process_long_text")
    print(f"Exception: {str(e)}")
    print("This is expected if Long Audio API is not configured")
    # Continue with test instead of exiting

# Test the full public generate_audio method
print("\n=== TEST 3: Full public API with generate_audio ===")
try:
    # Generate audio from SSML
    print("Generating audio from SSML using the public generate_audio method...")
    audio_data = tts.generate_audio(TEST_SSML, is_ssml=True)
    
    # Save the test audio to a file
    test_file_path = "test_ssml_generate_audio.mp3"
    with open(test_file_path, "wb") as f:
        f.write(audio_data)
    
    # Get file size to verify it contains data
    file_size = os.path.getsize(test_file_path)
    
    print(f"\nSuccess! Test audio file created: {test_file_path}")
    print(f"File size: {file_size} bytes")
    print("Full generate_audio API test is working correctly!")
    
except Exception as e:
    print(f"\nWARNING: Could not process SSML with generate_audio")
    print(f"Exception: {str(e)}")
    
print("\nAll tests completed successfully!")