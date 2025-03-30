# MLB Daily Podcast Generator

An automated system that generates daily MLB team podcasts using AI. This application fetches MLB statistics, news, generates scripts with OpenAI GPT, and converts them to audio with ElevenLabs TTS.

## Features

- Fetches daily MLB game results, statistics, and standings
- Retrieves latest news articles for each team
- Generates natural-sounding podcast scripts using Anthropic Claude 3 Sonnet
- Creates audio files with ElevenLabs text-to-speech
- Supports all 30 MLB teams
- Fully automated with daily scheduling

## Requirements

- Python 3.8+
- API Keys:
  - MLB Stats API (optional for basic usage)
  - Perplexity API
  - Anthropic API
  - ElevenLabs API

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
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ELEVENLABS_VOICE_ID=your_elevenlabs_voice_id
   ```

## Usage

### Process a Single Team

```
python main.py --team NYY
```

This will generate a podcast for the New York Yankees with yesterday's data.

### Specify a Date

```
python main.py --team BOS --date 2023-07-15
```

This will generate a podcast for the Boston Red Sox using data from July 15, 2023.

### Process All Teams

```
python main.py --all
```

This will generate podcasts for all 30 MLB teams using yesterday's data.

### Run as a Scheduled Service

```
python main.py --schedule
```

This will start the application as a service that automatically generates podcasts for all teams every day at 6 AM.

## Project Structure

- `config/` - Configuration settings
- `data/` - JSON data files for teams and news
- `scripts/` - Generated podcast scripts
- `audio/` - Generated MP3 audio files
- `utils/` - Utility modules for each part of the process
- `logs/` - Application logs

## Extensions and Next Steps

1. **Distribution to Podcast Platforms**:
   - Add integration with Anchor to automatically upload audio files
   - Generate RSS feeds for podcast distribution

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