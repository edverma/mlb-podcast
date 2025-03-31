# Podbean API Integration

This document explains the implementation of the Podbean API integration for the MLB Podcast distributor.

## Overview

The integration uses Podbean's API to:
1. Authenticate using OAuth2
2. Upload audio files
3. Publish podcast episodes
4. Retrieve episode status and URLs

## Key Implementation Details

### Authentication
- Uses OAuth2 client credentials flow
- Endpoint: `https://api.podbean.com/v1/oauth/token`
- Method: POST with Basic Auth header (base64 encoded client_id:client_secret)
- Returns access token valid for 1 hour

### File Upload
- Two-step process:
  1. Get upload authorization (presigned S3 URL)
  2. Upload file to S3 using the presigned URL
- Upload Authorization Endpoint: `https://api.podbean.com/v1/files/uploadAuthorize`
- Method: GET with query parameters (not in Authorization header)
- Required parameters:
  - `access_token` (in query params, not header)
  - `filename`
  - `filesize`
  - `content_type` (e.g., "audio/mpeg")
- Returns:
  - `presigned_url` - URL to upload the file to S3
  - `expire_at` - Expiration time for the URL
  - `file_key` - Key to use when publishing the episode

### Episode Publishing
- Endpoint: `https://api.podbean.com/v1/episodes`
- Method: POST with form data (not JSON)
- Required parameters:
  - `access_token` (in form data, not header)
  - `title` - Episode title
  - `content` - Episode description
  - `status` - "publish" to make it live
  - `type` - "public" for public episodes
  - `media_key` - File key from the upload step
- Optional parameters:
  - `tag` - Comma-separated tags
  - `category` - Episode category
  - `season_number` - Season number
  - `episode_number` - Episode number
  - `content_explicit` - "clean" or "explicit"
  - `logo_key` - Cover image file key
  - `transcripts_key` - SRT transcript file key
  - `apple_episode_type` - "full", "trailer", etc.
  - `publish_timestamp` - For scheduled publishing

### Episode Status
- Endpoint: `https://api.podbean.com/v1/episodes/{episode_id}`
- Method: GET with query parameters
- Required parameters:
  - `access_token` (in query params, not header)
- Returns episode details including permalink URL

## Important API Notes

1. **Authentication Method**: Podbean requires the access token to be passed in the request parameters/form data rather than in the Authorization header for most endpoints.

2. **Upload Endpoint**: The correct upload endpoint is `/files/uploadAuthorize` (not `/files/uploadAuthorization`).

3. **API Errors**: The API returns a 401 error if you try to use both an Authorization header and the access_token parameter.

4. **Parameter Format**: Use form data for POST requests, not JSON.

## Usage Example

```python
from utils.podbean_distributor import PodbeanDistributor

# Initialize the distributor
distributor = PodbeanDistributor()

# Distribute a podcast
metadata = {
    "title": "MLB Game Recap - Yankees vs Red Sox",
    "description": "A recap of the Yankees vs Red Sox game from April 1, 2023",
    "tags": ["mlb", "baseball", "yankees", "red sox"],
    "season": 2023,
    "episode_number": 42,
    "explicit": False
}

success, episode_url = distributor.distribute_podcast("audio_file.mp3", metadata)

if success:
    print(f"Podcast published successfully at {episode_url}")
else:
    print("Failed to publish podcast")
```

## Testing

Use the test scripts to verify API functionality:

1. `tests/test_upload_authorization.py` - Tests the upload authorization endpoint
2. `tests/test_podbean_api.py` - Tests the complete distribution workflow 