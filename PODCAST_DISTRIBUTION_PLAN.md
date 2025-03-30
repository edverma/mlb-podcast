# MLB Podcast Distribution Plan

## Core Steps

### 1. Set up Podbean Account
- Create Podbean account and select appropriate plan
- Register OAuth2 application to obtain client_id and client_secret
- Store credentials in project .env file
- Configure show settings through Podbean dashboard:
  - Upload podcast artwork (1400x1400px JPG/PNG)
  - Set show title, description, categories, language
  - Configure explicit content rating

### 2. Create Distribution Module
- Create `utils/podbean_distributor.py` file
- Implement PodbeanDistributor class with methods:
  - `__init__`: Load credentials, set up logging, initialize session
  - `authenticate`: Handle OAuth2 authentication flow
  - `upload_episode`: Upload audio file to Podbean
  - `publish_episode`: Set metadata and publish episode
  - `get_status`: Check episode status
- Add error handling with retries for API failures
- Update requirements.txt to include requests library

### 3. Integrate with Existing Workflow
- Modify `main.py` to call distributor after audio generation
- Pass required metadata (team name, date, episode title)
- Implement batch handling for --all flag:
  - Create upload queue for multiple episodes
  - Add parallel processing with rate limiting
- Add status tracking and error reporting

### 4. Test and Deploy
- Test with single team upload
- Verify episode appears on Podbean dashboard
- Check episode distribution to major platforms
- Test batch uploads with multiple teams
- Document deployment steps