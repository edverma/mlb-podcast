#!/usr/bin/env python3
"""
Focused test for Podbean file upload authorization endpoint
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger
from utils.podbean_distributor import PodbeanDistributor

# Set up logging
logger = get_logger(__name__)

# Load environment variables
load_dotenv()

def test_direct_upload_auth():
    """
    Test the upload authorization endpoint directly 
    using the exact parameters from the API documentation.
    """
    # First authenticate to get a token
    distributor = PodbeanDistributor(debug_mode=True)
    distributor.authenticate()
    
    if not distributor.access_token:
        print("❌ Failed to get access token")
        return False
    
    print(f"✅ Got access token: {distributor.access_token[:10]}...")
    
    # Set up the exact URL from documentation
    url = "https://api.podbean.com/v1/files/uploadAuthorize"
    
    # Set up exact parameters from documentation
    params = {
        'access_token': distributor.access_token,
        'filename': 'test.mp3',
        'filesize': 100000,
        'content_type': 'audio/mpeg'
    }
    
    # Add a User-Agent header as mentioned in the documentation
    headers = {
        'User-Agent': 'MLB-Podcast/1.0'
    }
    
    print(f"Sending request to: {url}")
    print(f"Parameters: {params}")
    
    # Make the GET request exactly as shown in documentation
    response = requests.get(url, params=params, headers=headers)
    
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    
    try:
        print(f"Response body: {response.text}")
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ SUCCESS! Got presigned URL: {data.get('presigned_url')[:50]}...")
            print(f"File key: {data.get('file_key')}")
            return True
        else:
            print(f"❌ Failed with status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error parsing response: {str(e)}")
        return False

if __name__ == "__main__":
    print("===== Testing Podbean Upload Authorization =====")
    success = test_direct_upload_auth()
    
    if success:
        print("\n✅ Upload authorization test PASSED!")
    else:
        print("\n❌ Upload authorization test FAILED!")
        sys.exit(1) 