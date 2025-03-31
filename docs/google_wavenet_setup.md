# Setting Up Google Wavenet with SSML for Text-to-Speech

This guide explains how to set up Google Cloud Text-to-Speech with Wavenet voices and SSML for the MLB Podcast Generator.

## Setting up Google Cloud

1. **Create a Google Cloud account**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create an account or sign in with your Google account

2. **Create a new project**:
   - In the Cloud Console, click on the project dropdown at the top
   - Click "New Project"
   - Name the project (e.g., "MLB Podcast Generator")
   - Click "Create"

3. **Enable the Text-to-Speech API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Text-to-Speech"
   - Click on "Cloud Text-to-Speech API"
   - Click "Enable"

4. **Create an API key**:
   - Navigate to "APIs & Services" > "Credentials"
   - Click "Create Credentials" at the top
   - Select "API key"
   - Your API key will be created and displayed
   - Copy this key to use in your configuration
   - Optional but recommended: Click "Restrict Key" to limit its use to only the Text-to-Speech API

5. **Create a Service Account** (recommended for authentication):
   - Navigate to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Enter a name (e.g., "mlb-podcast-tts")
   - Add a description (e.g., "Service account for MLB Podcast TTS")
   - Click "Create and Continue"
   - For the role, add these roles:
     - "Cloud Text-to-Speech Admin"
     - "Storage Admin" (needed for GCS bucket access)
   - Click "Continue" and then "Done"
   - After creation, click on the service account in the list
   - Go to the "Keys" tab and click "Add Key" > "Create new key"
   - Select "JSON" as the key type and click "Create"
   - The key file will be downloaded automatically - save it securely
   - Add the path to this file in your `.env` configuration
   
   **Important Notes on Service Account Authentication**:
   - Service Account authentication is preferred over API key authentication for security
   - Service Accounts provide better access controls and auditing
   - The service account key file contains credentials and should be kept secure
   - Never commit the service account key file to version control
   - You can use both service account and API key in your configuration, but service account will be preferred
   - For local development, place the key file outside of your project directory to avoid accidentally committing it
   
6. **Enable the Cloud Storage API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Cloud Storage"
   - Click on "Google Cloud Storage JSON API"
   - Click "Enable"

7. **Create a Cloud Storage bucket** (for Long Audio API):
   - Navigate to "Cloud Storage" > "Buckets"
   - Click "Create Bucket"
   - Give it a unique name
   - Choose a region (preferably the same as where you'll run the Text-to-Speech API)
   - Choose a storage class (Standard is fine)
   - Click "Create"

## Configuring Your Environment

1. **Edit your `.env` file**:
   - Add your Google Cloud configuration:
   ```
   # Google Cloud API key
   GOOGLE_CLOUD_API_KEY=your_google_cloud_api_key_here
   
   # Voice settings
   GOOGLE_WAVENET_VOICE=en-US-Wavenet-D
   GOOGLE_WAVENET_LANGUAGE_CODE=en-US
   
   # Long Audio API settings (required for SSML processing)
   GOOGLE_CLOUD_PROJECT_ID=your_project_id_here
   GOOGLE_CLOUD_LOCATION=us-central1
   GOOGLE_CLOUD_BUCKET=your_bucket_name_here
   GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE=path/to/your-service-account-key.json
   ```

2. **Install the required packages**:
   - Make sure you have the Google Cloud Python packages installed:
   ```
   pip install google-cloud-texttospeech google-cloud-storage
   ```

3. **Test the setup**:
   - Run the test script:
   ```
   python test_google_wavenet.py
   ```
   - If successful, you should see all tests pass with audio files generated

## Available Voice Options

Google Wavenet offers high-quality neural voices for many languages. For English, some popular options include:

### US English Voices:
- `en-US-Wavenet-A` (Female)
- `en-US-Wavenet-B` (Male)
- `en-US-Wavenet-C` (Female)
- `en-US-Wavenet-D` (Male)
- `en-US-Wavenet-E` (Female)
- `en-US-Wavenet-F` (Female)
- `en-US-Wavenet-G` (Female)
- `en-US-Wavenet-H` (Female)
- `en-US-Wavenet-I` (Male)
- `en-US-Wavenet-J` (Male)

### British English Voices:
- `en-GB-Wavenet-A` (Female)
- `en-GB-Wavenet-B` (Male)
- `en-GB-Wavenet-C` (Female)
- `en-GB-Wavenet-D` (Male)
- `en-GB-Wavenet-F` (Female)

### Australian English Voices:
- `en-AU-Wavenet-A` (Female)
- `en-AU-Wavenet-B` (Male)
- `en-AU-Wavenet-C` (Female)
- `en-AU-Wavenet-D` (Male)

To use a different language, change both the voice and the language code. For example:
```
GOOGLE_WAVENET_VOICE=es-US-Wavenet-B
GOOGLE_WAVENET_LANGUAGE_CODE=es-US
```

For a complete list of available voices, you can use the Google Cloud Console or run a script that calls the `list_voices()` method of the Text-to-Speech client.

## How It Works

The implementation handles different text formats and lengths:

1. **Standard Text Processing (≤ 5,000 characters)**:
   - Processes plain text in a single API call
   - Fast and efficient for typical podcast segments

2. **Chunked Text Processing (> 5,000 characters)**:
   - Automatically breaks plain text into chunks at sentence boundaries
   - Processes each chunk separately and combines the audio
   - Seamlessly handles very long scripts

3. **SSML Processing with Long Audio API**:
   - Uses Google Cloud's Long Audio API for SSML content
   - Handles the complex structure of SSML without needing to split it
   - Creates higher quality audio with precise control over speech characteristics
   - Stores temporary files in your Google Cloud Storage bucket during processing

## SSML Features

Speech Synthesis Markup Language (SSML) allows granular control over how text is spoken:

1. **Structure**:
   ```xml
   <?xml version="1.0"?>
   <speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis">
       <!-- Content here -->
   </speak>
   ```

2. **Pauses and Breaks**:
   ```xml
   <break time="0.5s"/>  <!-- Half-second pause -->
   <break time="1s"/>    <!-- One-second pause -->
   <break strength="medium"/>  <!-- Medium pause -->
   ```

3. **Emphasis**:
   ```xml
   <emphasis level="strong">Very important</emphasis>
   <emphasis level="moderate">Somewhat important</emphasis>
   <emphasis level="reduced">Less important</emphasis>
   ```

4. **Prosody (Rate, Pitch, Volume)**:
   ```xml
   <prosody rate="slow" pitch="low">Slow with low pitch</prosody>
   <prosody rate="fast" pitch="high">Fast with high pitch</prosody>
   <prosody volume="loud">Louder speech</prosody>
   ```

5. **Special Types**:
   ```xml
   <say-as interpret-as="cardinal">42</say-as>  <!-- Numbers -->
   <say-as interpret-as="date" format="mdy">12/25/2025</say-as>  <!-- Dates -->
   <say-as interpret-as="time">3:30pm</say-as>  <!-- Times -->
   ```

6. **Substitute/Alias**:
   ```xml
   <sub alias="Yankees">NYY</sub>  <!-- Replaces NYY with Yankees -->
   ```

## Authentication Methods

The application supports two authentication methods for Google Cloud services:

### 1. Service Account Authentication (Recommended)

Service account authentication uses a JSON key file to authenticate with Google Cloud services. This is the recommended method for enhanced security, especially for production environments.

**Setup**:
- Create a service account with appropriate roles (Text-to-Speech Admin, Storage Admin)
- Download the service account key file (JSON format)
- Add the path to this file in your `.env` configuration:
  ```
  GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE=/path/to/your-service-account-key.json
  ```

**Benefits**:
- More secure than API keys
- Fine-grained access control
- Full access to all Text-to-Speech features including Long Audio API
- Better auditing and logging
- Token-based authentication that refreshes automatically

**How it works**:
- When the application starts, it loads the service account credentials from the provided file
- It uses the Google Cloud client libraries directly when possible
- For REST API calls, it obtains and refreshes OAuth tokens automatically
- Handles authentication for both Text-to-Speech and Storage services

### 2. API Key Authentication (Fallback)

API key authentication uses a simple key string for authentication. This is easier to set up but less secure and has more limitations.

**Setup**:
- Create an API key in the Google Cloud Console
- Add it to your `.env` configuration:
  ```
  GOOGLE_CLOUD_API_KEY=your_api_key_here
  ```

**Limitations**:
- Less secure (keys can be leaked more easily)
- Limited access control options
- May have more restrictive quotas
- Manual key rotation required

The application will automatically use service account authentication if available, and fall back to API key authentication if no service account is configured.

## Troubleshooting

If you encounter issues:

1. **Authentication issues**:
   - For service account authentication:
     - Ensure the service account file path is correct and the file exists
     - Check that the service account has the required roles
     - Verify the service account is in the same project as the APIs you're using
   - For API key authentication:
     - Ensure your API key is valid and hasn't expired
     - Check that the Text-to-Speech API is enabled for your project
     - Verify that you've restricted the API key appropriately (if applicable)

2. **Long Audio API issues**:
   - Verify that your Google Cloud project ID is correct in your `.env` file
   - Check that the Cloud Storage bucket exists and is correctly configured
   - Ensure your service account or API key has permission to access the Long Audio API and Storage

3. **SSML validation errors**:
   - Check that your SSML is valid XML with properly closed tags
   - Ensure you're using supported SSML features and attributes
   - Look for special characters that might need to be escaped

4. **Quota limits**:
   - Be aware that Google Cloud has usage quotas
   - The Long Audio API may have different quotas than the standard API
   - For production use, you may need to request higher quotas

5. **Character limits**:
   - The standard API has a 5,000 character limit per request
   - The Long Audio API is designed for longer content

6. **Audio format limitations**:
   - The standard API supports MP3 output format
   - The Long Audio API currently only supports LINEAR16 (WAV) format
   - The implementation handles format conversion internally

7. **Billing concerns**:
   - Google Cloud Text-to-Speech is a paid service after the free tier
   - Long Audio API usage may incur additional costs
   - Set up budget alerts in Google Cloud Console to avoid unexpected charges 