import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
MLB_API_KEY = os.getenv("MLB_API_KEY", "")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# Removed Unreal Speech API key
# Added Google Cloud API key
GOOGLE_CLOUD_API_KEY = os.getenv("GOOGLE_CLOUD_API_KEY", "")

# MLB API Settings
MLB_API_BASE_URL = "https://statsapi.mlb.com/api/v1"

# Perplexity API Settings
PERPLEXITY_API_BASE_URL = "https://api.perplexity.ai"
NEWS_ARTICLES_COUNT = 5

# Anthropic API Settings
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "")

# Google Wavenet Settings
GOOGLE_WAVENET_VOICE = os.getenv("GOOGLE_WAVENET_VOICE", "en-US-Chirp3-HD-Orus")
GOOGLE_WAVENET_LANGUAGE_CODE = os.getenv("GOOGLE_WAVENET_LANGUAGE_CODE", "en-US")
GOOGLE_CLOUD_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT_ID", "")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "")
GOOGLE_CLOUD_BUCKET = os.getenv("GOOGLE_CLOUD_BUCKET", "")
GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE", "")

# Podcast Settings
PODCAST_LENGTH_MINUTES = 5
UPDATE_TIME = "06:00"  # 6 AM

# Storage Settings
DATA_DIR = "data"
SCRIPTS_DIR = "scripts"
AUDIO_DIR = "audio"

# Teams Configuration
MLB_TEAMS = {
    "ARI": "Arizona Diamondbacks",
    "ATL": "Atlanta Braves",
    "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox",
    "CHC": "Chicago Cubs",
    "CWS": "Chicago White Sox",
    "CIN": "Cincinnati Reds",
    "CLE": "Cleveland Guardians",
    "COL": "Colorado Rockies",
    "DET": "Detroit Tigers",
    "HOU": "Houston Astros",
    "KC": "Kansas City Royals",
    "LAA": "Los Angeles Angels",
    "LAD": "Los Angeles Dodgers",
    "MIA": "Miami Marlins",
    "MIL": "Milwaukee Brewers",
    "MIN": "Minnesota Twins",
    "NYM": "New York Mets",
    "NYY": "New York Yankees",
    "OAK": "Oakland Athletics",
    "PHI": "Philadelphia Phillies",
    "PIT": "Pittsburgh Pirates",
    "SD": "San Diego Padres",
    "SF": "San Francisco Giants",
    "SEA": "Seattle Mariners",
    "STL": "St. Louis Cardinals",
    "TB": "Tampa Bay Rays",
    "TEX": "Texas Rangers",
    "TOR": "Toronto Blue Jays",
    "WSH": "Washington Nationals"
}