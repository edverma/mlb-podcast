#!/usr/bin/env python3
"""
Test script to verify Podbean API authentication.
This script tests that your Podbean client credentials are correctly configured
and that the authentication workflow is working.
"""

import os
import sys

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.podbean_distributor import PodbeanDistributor

def test_podbean_auth():
    """Test Podbean authentication."""
    try:
        print("Initializing Podbean distributor...")
        distributor = PodbeanDistributor()
        
        print("Authenticating with Podbean API...")
        token = distributor.authenticate()
        
        if token:
            print("✅ Authentication successful!")
            print(f"Token expires at: {distributor.token_expires_at}")
            return True
        else:
            print("❌ Authentication failed: No token received")
            return False
    except Exception as e:
        print(f"❌ Authentication failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== Podbean Authentication Test ===")
    success = test_podbean_auth()
    print("==================================")
    
    if success:
        print("Your Podbean configuration is working correctly.")
        print("You can now use the PodBean distributor to upload and publish episodes.")
    else:
        print("Please check your credentials in the .env file.")
        print("See docs/podbean_setup.md for setup instructions.")
    
    sys.exit(0 if success else 1) 