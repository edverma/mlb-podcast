#!/usr/bin/env python3
"""
API endpoint scanner for Podbean.
This script systematically tests various potential Podbean API endpoints
to find the correct ones for file upload functionality.
"""

import os
import sys
import json
import base64
import requests
import time
from dotenv import load_dotenv

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

class PodbeanAPIScanner:
    """
    Scanner to systematically test Podbean API endpoints.
    """
    
    BASE_URL = "https://api.podbean.com/v1"
    
    def __init__(self):
        """Initialize the scanner."""
        self.client_id = os.getenv("PODBEAN_CLIENT_ID")
        self.client_secret = os.getenv("PODBEAN_CLIENT_SECRET")
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Podbean credentials not found. Please set PODBEAN_CLIENT_ID and PODBEAN_CLIENT_SECRET in .env file.")
        
        self.access_token = None
        
        # Create a test file if needed
        self.test_file_path = "tests/sample_audio.mp3"
        if not os.path.exists(self.test_file_path):
            self._create_test_file()
    
    def _create_test_file(self, size_kb=100):
        """Create a sample test file."""
        try:
            from tests.create_sample_audio import create_sample_audio
            create_sample_audio(size_kb=size_kb)
        except ImportError:
            # Create a minimal MP3 file
            os.makedirs(os.path.dirname(self.test_file_path), exist_ok=True)
            with open(self.test_file_path, "wb") as f:
                # MP3 header + random data
                f.write(b"\xFF\xFB\x90\x44\x00" * 20000)
        
        print(f"Created test file: {self.test_file_path} ({os.path.getsize(self.test_file_path)} bytes)")
    
    def authenticate(self):
        """Authenticate with Podbean API."""
        print("\n===== Authenticating with Podbean API =====")
        
        # Create Basic Auth header
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        
        # Set up the request headers and data
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials"
        }
        
        url = f"{self.BASE_URL}/oauth/token"
        
        try:
            response = requests.post(url, headers=headers, data=data)
            print(f"Authentication response status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)
                
                print(f"✅ Authentication successful!")
                print(f"Access token: {self.access_token[:10]}...{self.access_token[-10:]}")
                print(f"Token expires in: {expires_in} seconds")
                return True
            else:
                print(f"❌ Authentication failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {str(e)}")
            return False
    
    def _test_endpoint(self, endpoint, method="GET", data=None, params=None, files=None):
        """Test a specific API endpoint."""
        if not self.access_token:
            print("Access token not available. Authenticate first.")
            return False
        
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                if files:
                    response = requests.post(url, headers=headers, data=data, files=files)
                else:
                    headers["Content-Type"] = "application/json" if isinstance(data, dict) else "application/x-www-form-urlencoded"
                    response = requests.post(url, headers=headers, data=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, data=data)
            else:
                print(f"Unsupported method: {method}")
                return False
            
            print(f"{method} {url}: {response.status_code}")
            
            # Check if we get anything other than a 404
            if response.status_code != 404:
                print(f"Response headers: {json.dumps(dict(response.headers), indent=2)}")
                print(f"Response content: {response.text[:500]}...")
                return True, response
            
            return False, response
        except Exception as e:
            print(f"Error testing {method} {url}: {str(e)}")
            return False, None
    
    def scan_upload_endpoints(self):
        """Scan various potential file upload endpoints."""
        print("\n===== Scanning for File Upload Endpoints =====")
        
        if not self.authenticate():
            print("Authentication failed. Cannot proceed with scanning.")
            return
        
        # File metadata
        file_name = os.path.basename(self.test_file_path)
        file_size = os.path.getsize(self.test_file_path)
        
        # Preparation for multipart form upload
        with open(self.test_file_path, "rb") as f:
            file_content = f.read()
        
        # List of endpoint patterns to try
        endpoint_templates = [
            # Basic variations
            "files/uploadAuthorization",
            "files/upload_authorization",
            "files/upload",
            "media/uploadAuthorization",
            "medias/uploadAuthorization",
            "mediafiles/uploadAuthorization",
            "media_files/uploadAuthorization",
            
            # Podcast-specific endpoints
            "podcast/files/upload",
            "podcasts/files/upload",
            "episodes/upload",
            
            # Case variations
            "Files/upload",
            "Media/upload",
            
            # Other common patterns
            "file/upload",
            "audio/upload",
            "audios/upload",
            "audiofiles/upload",
            "audio_files/upload",
            "api/upload",
            "upload/authorization",
            "upload/authorize",
            "upload/request",
            "upload/init",
            "upload/media",
            "upload/audio",
            "upload/file",
            "media/upload",
            "media/file/upload",
            "podcast/media/upload",
            "episode/media/upload",
            "episode/audio/upload",
            "v1/files/upload",  # Explicit v1 in path
            "files/upload/authorization"
        ]
        
        # Common parameter names to try
        param_templates = [
            # Standard
            {"filename": file_name, "filesize": file_size, "content_type": "audio/mpeg"},
            
            # Variations
            {"file_name": file_name, "file_size": file_size, "content_type": "audio/mpeg"},
            {"name": file_name, "size": file_size, "type": "audio/mpeg"},
            {"fileName": file_name, "fileSize": file_size, "contentType": "audio/mpeg"},
            {"file": file_name, "size": file_size, "type": "audio/mpeg"},
            
            # Other possibilities
            {"filename": file_name, "size": file_size, "mime_type": "audio/mpeg"},
            {"file": file_name, "length": file_size, "content_type": "audio/mpeg"},
            {"filename": file_name, "bytes": file_size, "content_type": "audio/mpeg"},
            {"path": file_name, "filesize": file_size, "content_type": "audio/mpeg"}
        ]
        
        # Track successful endpoints
        successful_endpoints = []
        
        # Test GET + parameters
        print("\n--- Testing GET requests with query parameters ---")
        for endpoint in endpoint_templates:
            for params in param_templates:
                success, response = self._test_endpoint(endpoint, method="GET", params=params)
                if success:
                    print(f"✅ Found potential endpoint: GET {endpoint} with params {params}")
                    print(f"Response: {response.text[:200]}...")
                    successful_endpoints.append({
                        "method": "GET",
                        "endpoint": endpoint,
                        "params": params,
                        "status_code": response.status_code,
                        "response_sample": response.text[:100]
                    })
                time.sleep(0.1)  # Add a small delay to prevent rate limiting
        
        # Test POST + form data
        print("\n--- Testing POST requests with form data ---")
        for endpoint in endpoint_templates:
            for params in param_templates:
                success, response = self._test_endpoint(endpoint, method="POST", data=params)
                if success:
                    print(f"✅ Found potential endpoint: POST {endpoint} with data {params}")
                    print(f"Response: {response.text[:200]}...")
                    successful_endpoints.append({
                        "method": "POST",
                        "endpoint": endpoint,
                        "data": params,
                        "status_code": response.status_code,
                        "response_sample": response.text[:100]
                    })
                time.sleep(0.1)  # Add a small delay to prevent rate limiting
        
        # Test POST + JSON data
        print("\n--- Testing POST requests with JSON data ---")
        for endpoint in endpoint_templates:
            for params in param_templates:
                success, response = self._test_endpoint(endpoint, method="POST", data=json.dumps(params))
                if success:
                    print(f"✅ Found potential endpoint: POST {endpoint} with JSON {params}")
                    print(f"Response: {response.text[:200]}...")
                    successful_endpoints.append({
                        "method": "POST",
                        "endpoint": endpoint,
                        "json": params,
                        "status_code": response.status_code,
                        "response_sample": response.text[:100]
                    })
                time.sleep(0.1)  # Add a small delay to prevent rate limiting
        
        # Test Direct file upload
        print("\n--- Testing direct file uploads ---")
        for endpoint in endpoint_templates:
            files = {"file": (file_name, file_content, "audio/mpeg")}
            success, response = self._test_endpoint(endpoint, method="POST", files=files)
            if success:
                print(f"✅ Found potential endpoint: POST {endpoint} with direct file upload")
                print(f"Response: {response.text[:200]}...")
                successful_endpoints.append({
                    "method": "POST",
                    "endpoint": endpoint,
                    "files": True,
                    "status_code": response.status_code,
                    "response_sample": response.text[:100]
                })
            time.sleep(0.1)  # Add a small delay to prevent rate limiting
        
        # Test Direct file upload + parameters
        print("\n--- Testing direct file uploads with parameters ---")
        for endpoint in endpoint_templates:
            for params in param_templates:
                files = {"file": (file_name, file_content, "audio/mpeg")}
                success, response = self._test_endpoint(endpoint, method="POST", data=params, files=files)
                if success:
                    print(f"✅ Found potential endpoint: POST {endpoint} with direct file upload + params {params}")
                    print(f"Response: {response.text[:200]}...")
                    successful_endpoints.append({
                        "method": "POST",
                        "endpoint": endpoint,
                        "data": params,
                        "files": True,
                        "status_code": response.status_code,
                        "response_sample": response.text[:100]
                    })
                time.sleep(0.2)  # Slightly longer delay for combined requests
        
        # Test two endpoints that might be using a newer versioning scheme
        v2_endpoints = [
            "v2/files/upload",
            "v2/media/upload",
            "v2/assets/upload"
        ]
        
        print("\n--- Testing potential v2 API endpoints ---")
        for endpoint in v2_endpoints:
            full_url = f"https://api.podbean.com/{endpoint}"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            for params in param_templates[:2]:  # Just try a couple parameter variations
                try:
                    response = requests.get(full_url, headers=headers, params=params)
                    print(f"GET {full_url}: {response.status_code}")
                    
                    if response.status_code != 404:
                        print(f"Response headers: {json.dumps(dict(response.headers), indent=2)}")
                        print(f"Response content: {response.text[:500]}...")
                        successful_endpoints.append({
                            "method": "GET",
                            "full_url": full_url,
                            "params": params,
                            "status_code": response.status_code,
                            "response_sample": response.text[:100]
                        })
                except Exception as e:
                    print(f"Error testing GET {full_url}: {str(e)}")
        
        # Check direct API entry points (without /v1/)
        base_endpoints = [
            "uploadAuthorization",
            "upload_authorization",
            "upload",
            "uploadfile",
            "upload_file"
        ]
        
        print("\n--- Testing direct API endpoints (without /v1/) ---")
        for endpoint in base_endpoints:
            full_url = f"https://api.podbean.com/{endpoint}"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            try:
                response = requests.get(full_url, headers=headers, params=param_templates[0])
                print(f"GET {full_url}: {response.status_code}")
                
                if response.status_code != 404:
                    print(f"Response headers: {json.dumps(dict(response.headers), indent=2)}")
                    print(f"Response content: {response.text[:500]}...")
                    successful_endpoints.append({
                        "method": "GET",
                        "full_url": full_url,
                        "params": param_templates[0],
                        "status_code": response.status_code,
                        "response_sample": response.text[:100]
                    })
            except Exception as e:
                print(f"Error testing GET {full_url}: {str(e)}")
        
        # Summary of results
        print("\n===== Scan Summary =====")
        if successful_endpoints:
            print(f"Found {len(successful_endpoints)} potential endpoints that returned non-404 responses:")
            for i, endpoint_info in enumerate(successful_endpoints, 1):
                print(f"\n{i}. {endpoint_info.get('method')} {endpoint_info.get('endpoint', endpoint_info.get('full_url', 'unknown'))}")
                print(f"   Status: {endpoint_info.get('status_code')}")
                print(f"   Sample response: {endpoint_info.get('response_sample')}")
                
                if 'params' in endpoint_info:
                    print(f"   Parameters: {endpoint_info.get('params')}")
                if 'data' in endpoint_info:
                    print(f"   Form data: {endpoint_info.get('data')}")
                if 'json' in endpoint_info:
                    print(f"   JSON: {endpoint_info.get('json')}")
                if endpoint_info.get('files'):
                    print(f"   Files: Yes (direct file upload)")
        else:
            print("No successful endpoints found. All tested endpoints returned 404 errors.")
        
        # Save results to file
        results_file = "scan_results.json"
        with open(results_file, "w") as f:
            json.dump({
                "timestamp": time.time(),
                "successful_endpoints": successful_endpoints
            }, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")
        return successful_endpoints

def main():
    scanner = PodbeanAPIScanner()
    scanner.scan_upload_endpoints()

if __name__ == "__main__":
    main() 