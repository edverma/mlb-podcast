#!/usr/bin/env python3
"""
Test script for Podbean API.
This will test authentication, file upload, and episode publishing.
"""

import os
import sys
import json
import requests
import time
from dotenv import load_dotenv

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger
from utils.podbean_distributor import PodbeanDistributor

# Set up logging
logger = get_logger(__name__)

# Create test file if it doesn't exist
def create_test_file(filepath="tests/test_audio.mp3", size_kb=100):
    """Create a sample test MP3 file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if not os.path.exists(filepath):
        # Create a minimal MP3 file
        with open(filepath, "wb") as f:
            # MP3 header + random data
            f.write(b"\xFF\xFB\x90\x44\x00" * 20000)
        logger.info(f"Created test file: {filepath} ({os.path.getsize(filepath)} bytes)")
    return filepath

def test_podbean_api():
    """Test the Podbean API functionality."""
    # Initialize distributor
    distributor = PodbeanDistributor(debug_mode=True)
    
    # Test authentication
    print("\n===== Testing Podbean Authentication =====")
    distributor.disable_mock_mode()  # Use real API calls
    success = distributor.authenticate()
    print(f"Authentication successful: {success}")
    
    if not success:
        print("Authentication failed, cannot proceed with tests")
        return
    
    # Create a test file
    test_file = create_test_file()
    
    # Test direct publishing to see if API endpoint works
    print("\n===== Testing Direct Publish Call =====")
    
    # 1. Try to publish with direct API call to verify endpoint
    access_token = distributor.access_token
    headers = {"Authorization": f"Bearer {access_token}"}
    
    publish_data = {
        "access_token": access_token,
        "title": "Test Episode via Direct API Call",
        "content": "This is a test episode created via direct API call",
        "status": "publish",
        "type": "public",
        "media_key": "test_media_key"  # This is invalid but will help check if the endpoint exists
    }
    
    try:
        response = requests.post(
            distributor.EPISODE_URL,
            headers=headers,
            data=publish_data
        )
        
        print(f"Publish API call response status: {response.status_code}")
        print(f"Response content: {response.text[:500]}")
        
        # Even if we get an error about media_key, at least we know the endpoint exists
        if response.status_code != 404:
            print("✅ Publish endpoint exists and is responding (even if with an error about the media_key)")
        else:
            print("❌ Publish endpoint returned 404")
    except Exception as e:
        print(f"Error testing publish endpoint: {str(e)}")
    
    # Test upload endpoints with direct API calls
    print("\n===== Testing Upload Endpoints with Direct API Calls =====")
    
    # Try the upload endpoints directly
    upload_endpoints = [
        "/files/uploadAuthorization",
        "/medias/uploadAuthorization",
        "/mediafiles/uploadAuthorization",
        "/files/upload"
    ]
    
    file_name = os.path.basename(test_file)
    file_size = os.path.getsize(test_file)
    
    upload_params = {
        "access_token": access_token,
        "filename": file_name,
        "filesize": file_size,
        "content_type": "audio/mpeg"
    }
    
    for endpoint in upload_endpoints:
        url = f"{distributor.BASE_URL}{endpoint}"
        try:
            print(f"\nTesting endpoint: {url}")
            # Try GET
            response = requests.get(url, params=upload_params)
            print(f"GET response: {response.status_code}")
            
            if response.status_code != 404:
                print(f"GET response content: {response.text[:500]}")
                print("✅ GET request successful!")
                break
                
            # Try POST form data
            response = requests.post(url, data=upload_params)
            print(f"POST (form) response: {response.status_code}")
            
            if response.status_code != 404:
                print(f"POST response content: {response.text[:500]}")
                print("✅ POST form request successful!")
                break
            
        except Exception as e:
            print(f"Error testing {url}: {str(e)}")
    
    # Now use the distributor to attempt a full workflow
    print("\n===== Testing Full Workflow with Distributor =====")
    
    try:
        # Test with the distributor's methods for a full workflow
        metadata = {
            "title": "Test Podbean Episode",
            "description": "This is a test episode for the Podbean API",
            "tags": ["test", "mlb", "podcast"],
            "season": 1,
            "episode_number": 1,
            "explicit": False
        }
        
        # Attempt to upload and publish
        success, episode_url = distributor.distribute_podcast(test_file, metadata)
        
        print(f"Distribution successful: {success}")
        if success:
            print(f"Episode URL: {episode_url}")
        
    except Exception as e:
        print(f"Error in full workflow test: {str(e)}")

if __name__ == "__main__":
    test_podbean_api() 