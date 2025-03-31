# MLB Daily Podcast Generator

An automated system that generates daily MLB team podcasts using AI. This application fetches MLB statistics, news, generates scripts with OpenAI GPT, and converts them to audio with Amazon Polly TTS.

## Features

- Fetches daily MLB game results, statistics, and standings
- Retrieves latest news articles for each team
- Generates natural-sounding podcast scripts using Anthropic Claude 3 Sonnet
- Creates audio files with Amazon Polly text-to-speech
- Supports all 30 MLB teams
- Fully automated with daily scheduling
- Distributes podcasts to major platforms via Podbean

## Requirements

- Python 3.8+
- API Keys:
  - MLB Stats API (optional for basic usage)
  - Perplexity API
  - Anthropic API
  - AWS Access Key and Secret (for Amazon Polly)
  - Podbean Client ID & Secret

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/mlb-podcast.git
   cd mlb-podcast
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create an `.env` file by copying the example:
   ```
   cp .env.example .env
   ```

4. Edit the `.env` file and add your API keys:
   ```
   MLB_API_KEY=your_mlb_api_key
   PERPLEXITY_API_KEY=your_perplexity_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   AWS_ACCESS_KEY_ID=your_aws_access_key_id
   AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
   AWS_REGION=us-east-1
   POLLY_VOICE_ID=Joanna
   PODBEAN_CLIENT_ID=your_podbean_client_id
   PODBEAN_CLIENT_SECRET=your_podbean_client_secret
   ```

5. Configure your Podbean account (see [Podbean Setup Guide](docs/podbean_setup.md))

## Usage

### Process a Single Team

```
python main.py --team NYY
```

This will generate a podcast for the New York Yankees with yesterday's data and distribute it to Podbean.

### Specify a Date

```
python main.py --team BOS --date 2023-07-15
```

This will generate a podcast for the Boston Red Sox using data from July 15, 2023.

### Process All Teams

```
python main.py --all
```

This will generate podcasts for all 30 MLB teams using yesterday's data and distribute them to Podbean.

### Skip Podbean Distribution

If you want to generate podcasts without distributing them to Podbean:

```
python main.py --team NYY --no-distribute
```

or

```
python main.py --all --no-distribute
```

### Run as a Scheduled Service

```
python main.py --schedule
```

This will start the application as a service that automatically generates podcasts for all teams every day at 6 AM.

### Test Podbean Integration

```
python tests/test_podbean_auth.py
```

This tests your Podbean API configuration to ensure authentication is working correctly.

```
python tests/test_podbean_distribution.py NYY
```

This tests the full Podbean distribution workflow for the New York Yankees.

## Project Structure

- `config/` - Configuration settings
- `data/` - JSON data files for teams and news
- `scripts/` - Generated podcast scripts
- `audio/` - Generated MP3 audio files
- `utils/` - Utility modules for each part of the process
- `logs/` - Application logs
- `docs/` - Documentation for setup and usage
- `tests/` - Test scripts for verifying functionality

## Podcast Distribution

This project uses Podbean for podcast distribution. To set up Podbean integration:

1. Create a Podbean account and select an appropriate plan
2. Register an OAuth2 application to get a client ID and secret
3. Configure your podcast settings (artwork, categories, etc.)
4. Add your Podbean credentials to the `.env` file

For detailed setup instructions, see [Podbean Setup Guide](docs/podbean_setup.md).
For implementation details, see [Podbean Integration](docs/podbean_integration.md).

## Extensions and Next Steps

1. **Distribution to Podcast Platforms**:
   - ✅ Add integration with Podbean to automatically upload and publish episodes
   - Generate RSS feeds for additional podcast distribution channels

2. **Additional Features**:
   - Add player interviews or commentary by using AI voices
   - Include weekly round-ups or special event coverage
   - Add support for minor league teams

3. **Customization Options**:
   - Allow customization of script templates
   - Provide different voice options for each team
   - Adjust podcast length based on amount of content

## License

MIT License

# Update to implement Google Wavenet TTS with SSML

## Google Wavenet TTS with SSML Integration

The MLB Podcast Generator now uses Google Wavenet TTS with SSML (Speech Synthesis Markup Language) for enhanced speech quality and control.

### Key Changes:

1. Generate SSML content instead of plain text scripts
2. Added support for enhanced speech features via SSML:
   - Emphasis on important words and phrases
   - Controlled pauses and breaks
   - Proper pronunciation of numbers, dates, and abbreviations
   - Voice modulation for emotion and emphasis
3. Implemented Google Cloud's Long Audio API for processing SSML content of any length
4. Updated configuration and testing tools

### Setup Instructions:

1. Set up a Google Cloud account and create a project
2. Enable the Text-to-Speech API for your project
3. Create a service account and download the JSON key file
4. Create a Google Cloud Storage bucket for the Long Audio API
5. Add your Google Cloud settings to the `.env` file:
   ```
   GOOGLE_CLOUD_API_KEY=your_api_key_here
   GOOGLE_WAVENET_VOICE=en-US-Wavenet-D
   GOOGLE_WAVENET_LANGUAGE_CODE=en-US
   GOOGLE_CLOUD_PROJECT_ID=your_project_id
   GOOGLE_CLOUD_LOCATION=us-central1
   GOOGLE_CLOUD_BUCKET=your-gcs-bucket-name
   ```
6. Run the test script to verify your integration:
   ```
   python test_google_wavenet.py
   ```

For detailed information, see the [Google Wavenet setup documentation](docs/google_wavenet_setup.md).

### SSML Features Used

The generated SSML includes these features to enhance audio quality:
- `<break>` tags for pauses between sentences and sections
- `<emphasis>` tags for highlighting important information
- `<prosody>` tags to adjust rate, pitch, and volume for emotional impact
- `<say-as>` tags for proper pronunciation of numbers, dates, and scores
- `<sub>` tags to expand abbreviations like team codes (NYY → Yankees)

All SSML content is validated and properly formatted according to the W3C SSML specification.
