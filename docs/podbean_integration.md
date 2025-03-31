# Podbean Integration

## Overview

This documentation explains how the MLB Podcast Generator integrates with Podbean for podcast distribution. The integration allows for automated uploading and publishing of podcast episodes to Podbean, which then distributes the content to major podcast platforms.

## Implementation Details

The Podbean integration has been implemented in two main steps:

### Step 1: Account Setup and API Client

- Created a `PodbeanDistributor` class in `utils/podbean_distributor.py`
- Implemented OAuth2 authentication with Podbean's API
- Added methods for upload authorization, file upload, episode publishing, and status checking
- Added error handling with retries via the `tenacity` library
- Created test scripts to verify authentication and distribution
- Added documentation for Podbean account setup

### Step 2: Workflow Integration

- Updated the `PodcastProcessor` class to integrate the Podbean distributor
- Added distribution functionality to the processing workflow:
  - After generating audio, the processor uploads it to Podbean
  - Episode metadata is generated from the script content
  - Published episode URLs are tracked in the result object
- Added batch handling for distributing multiple episodes
- Added command-line flag `--no-distribute` to skip distribution
- Updated console output to display distribution status and URLs

## Usage

### Distributing a Single Team's Podcast

```bash
python main.py --team NYY
```

This will:
1. Generate the podcast for the New York Yankees
2. Upload the audio file to Podbean
3. Publish it as an episode with appropriate metadata
4. Display the Podbean URL in the console output

### Distributing All Teams' Podcasts

```bash
python main.py --all
```

This will process all MLB teams and distribute their podcasts to Podbean, with parallelization to respect API rate limits.

### Skipping Distribution

```bash
python main.py --team NYY --no-distribute
```

This will generate the podcast but skip the Podbean distribution step.

## Mock Mode

Due to ongoing issues with the Podbean API (see [Troubleshooting](#troubleshooting)), the distributor now includes a mock mode that simulates successful distribution without making actual API calls. This allows the rest of the application to function normally while API issues are being resolved.

By default, mock mode is **enabled**. To disable it and use real API calls:

```python
distributor = PodbeanDistributor()
distributor.disable_mock_mode()
```

Or when using the test script:

```bash
python tests/test_podbean_e2e.py --real
```

## Testing

Several test scripts are available to verify the Podbean integration:

1. **Authentication Test**: Verifies that your Podbean credentials are working correctly.
   ```bash
   python tests/test_podbean_auth.py
   ```

2. **API Test**: Tests all Podbean API functions with detailed logging.
   ```bash
   python tests/test_podbean_api.py
   ```

3. **Distribution Test**: Tests the full distribution workflow for a single team.
   ```bash
   python tests/test_podbean_distribution.py NYY
   ```

4. **End-to-End Test**: Tests the complete workflow from setup to distribution.
   ```bash
   python tests/test_podbean_e2e.py
   ```

## Troubleshooting

The Podbean API integration has some known issues and limitations. For details on these issues and current workarounds, see:

- [Podbean API Troubleshooting Guide](podbean_api_troubleshooting.md)

## Error Handling

The Podbean distribution includes robust error handling:

- Authentication failures trigger retries with exponential backoff
- Upload and publishing errors are reported and logged
- The application will continue processing other teams if one fails
- Status messages in the console and logs provide clear error information

## Future Improvements

Potential future enhancements to the Podbean integration:

1. **Episode Scheduling**: Allow scheduling episodes for future publication
2. **Custom Episode Images**: Support team-specific artwork for episodes
3. **Analytics Integration**: Fetch and report on episode performance metrics
4. **Category Management**: Better handling of podcast categories and tags
5. **Distribution Reports**: Generate detailed reports on distribution status
6. **API Updates**: Update the implementation once Podbean API issues are resolved 