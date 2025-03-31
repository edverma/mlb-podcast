import os
import json
import datetime
import re
from typing import Dict, List, Any, Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from config.config import PERPLEXITY_API_BASE_URL, PERPLEXITY_API_KEY, DATA_DIR, NEWS_ARTICLES_COUNT, MLB_TEAMS
from utils.logger import get_logger

logger = get_logger(__name__)

class PerplexityNewsFetcher:
    def __init__(self):
        self.base_url = PERPLEXITY_API_BASE_URL
        self.api_key = PERPLEXITY_API_KEY
        self.session = requests.Session()
        
        # Check if we're using a demo key
        self.use_mock = not self.api_key or self.api_key == "sample_perplexity_api_key"
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _make_request(self, query: str) -> Dict[str, Any]:
        """Make a request to the Perplexity API with retries."""
        # If using mock mode, we're not making actual API calls
        if self.use_mock:
            # Return empty response for mock
            return {"answer": "", "web_search": []}
            
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar-reasoning-pro",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a sports news reporter specializing in Major League Baseball."
                },
                {
                    "role": "user",
                    "content": f"Generate a summary of today's sports opinion pieces about the {query}. Make sure the news sources you use are only from today, {datetime.date.today().strftime('%B %d %Y')}."
                }
            ],
        }
        
        try:
            response = self.session.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching from Perplexity API: {e}")
            raise

    def get_team_news(self, team_name: str, days: int = 1) -> List[Dict[str, Any]]:
        """Get news for a specific team over the last few days."""
        # If we're in mock mode, return sample news data
        if self.use_mock:
            logger.info(f"Using mock news data for {team_name} (demo mode)")
            return [
                {
                    "title": f"{team_name} Star Shines in Latest Win",
                    "source": "Sports Daily",
                    "description": f"The {team_name} continued their strong performance with another impressive win.",
                    "url": "https://example.com/news/1",
                    "published_at": datetime.datetime.now().isoformat()
                },
                {
                    "title": f"Trade Rumors Surround {team_name} Ahead of Deadline",
                    "source": "Baseball Insider",
                    "description": f"Sources close to the team suggest the {team_name} are looking to strengthen their bullpen.",
                    "url": "https://example.com/news/2",
                    "published_at": datetime.datetime.now().isoformat()
                },
                {
                    "title": f"Injury Update: Key {team_name} Player Returning Soon",
                    "source": "MLB Network",
                    "description": "The team expects their star player to return from the IL next week.",
                    "url": "https://example.com/news/3",
                    "published_at": datetime.datetime.now().isoformat()
                },
                {
                    "title": f"Fan Favorite Hosts Charity Event in {team_name} Community",
                    "source": "Local News",
                    "description": "The annual fundraiser broke previous records for donations.",
                    "url": "https://example.com/news/4",
                    "published_at": datetime.datetime.now().isoformat()
                },
                {
                    "title": f"Analysis: What's Behind {team_name}'s Recent Success?",
                    "source": "Baseball Analytics",
                    "description": "An in-depth look at the statistics behind the team's performance.",
                    "url": "https://example.com/news/5",
                    "published_at": datetime.datetime.now().isoformat()
                }
            ]
        
        # Create search query for the team
        search_query = f"{team_name} MLB baseball recent news"
        
        try:
            response = self._make_request(search_query)
            
            # Extract content from response
            raw_content = ""
            choices = response.get("choices", [])
            
            if choices and len(choices) > 0:
                # Extract content from message
                content = choices[0].get("message", {}).get("content", "")
                
                # Remove the <think> section if present
                if "<think>" in content and "</think>" in content:
                    # Extract content outside of <think> tags
                    pattern = r"<think>.*?</think>"
                    # Remove the thinking section, preserving content outside of it
                    raw_content = re.sub(pattern, "", content, flags=re.DOTALL).strip()
                else:
                    # If no think tags, use the whole content
                    raw_content = content
            
            return raw_content
        except Exception as e:
            logger.error(f"Error fetching news for {team_name}: {e}")
            return []

    def fetch_and_save_team_news(self, team_code: str, date: Optional[datetime.date] = None) -> List[Dict[str, Any]]:
        """Fetch and save news for a specific team."""
        date = date or datetime.date.today()
        date_str = date.strftime("%Y-%m-%d")
        team_name = MLB_TEAMS.get(team_code)
        
        logger.info(f"Fetching news for {team_name} on {date_str}")
        
        # Get news articles
        articles = self.get_team_news(team_name)
        
        # Save to file
        team_dir = os.path.join(DATA_DIR, team_code)
        os.makedirs(team_dir, exist_ok=True)
        
        news_file_path = os.path.join(team_dir, f"{date_str}_news.txt")
        with open(news_file_path, "w") as f:
            json.dump(articles, f, indent=2)
            
        logger.info(f"Saved {len(articles)} news articles for {team_name} to {news_file_path}")
        return articles