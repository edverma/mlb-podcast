# Setting Up Unreal Speech for Text-to-Speech

This guide explains how to set up Unreal Speech for text-to-speech (TTS) functionality in the MLB Podcast Generator.

## Getting an API Key

1. **Sign up for Unreal Speech**:
   - Go to [Unreal Speech](https://unrealspeech.com/)
   - Create an account or sign in
   - Navigate to your dashboard

2. **Get your API Key**:
   - In your dashboard, find your API key
   - Copy the key to use in the next step

## Configuring Your Environment

1. **Edit your `.env` file**:
   - Add your Unreal Speech API key:
   ```
   UNREAL_SPEECH_API_KEY=your_api_key_here
   ```
   
   - Optionally, set a voice preference:
   ```
   UNREAL_SPEECH_VOICE_ID=Eleanor
   ```
   
   Available voice options include:
   - Eleanor (default)
   - Melody
   - Javier
   - Amelia 
   - Jasper
   - Lauren
   - Luna
   - Sierra
   - Edward
   - Charlotte
   - And many more (reference the error message from the test script for a complete list)

2. **Test the setup**:
   - Run the test script:
   ```
   python test_unreal_speech.py
   ```
   - If successful, you should see all tests pass with audio files generated

## How It Works

The implementation uses three different Unreal Speech endpoints based on text length:

1. **Short Text (≤ 1,000 characters)**:
   - Uses the `/stream` endpoint
   - Fast, nearly instantaneous response
   - Perfect for short snippets

2. **Medium Text (≤ 3,000 characters)**:
   - Uses the `/speech` endpoint
   - Synchronous processing, typically takes ~1 second per 700 characters
   - Returns MP3 audio data

3. **Long Text (> 3,000 characters)**:
   - Uses the `/synthesisTasks` endpoint
   - Asynchronous processing for very long texts (up to 500,000 characters)
   - Takes ~1 second per 800 characters to process
   - Polls the API until the task completes

## Troubleshooting

If you encounter issues:

1. **Check API Key**:
   - Verify your API key is correctly entered in the `.env` file
   - Make sure your Unreal Speech account is active

2. **Test Connectivity**:
   - Ensure your network can connect to Unreal Speech servers
   - Try running the test script to isolate issues

3. **Check Usage Limits**:
   - Unreal Speech has different usage limits based on your plan
   - Check your dashboard to ensure you haven't exceeded your quota

4. **Voice Selection**:
   - Make sure you're using a valid voice ID
   - If you're unsure which voices are available, check the error message from the test script for a complete list
   - Voice IDs are case sensitive

For more detailed information, refer to the [Unreal Speech API Documentation](https://docs.unrealspeech.com/). 