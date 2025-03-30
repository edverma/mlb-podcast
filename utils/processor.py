import os
import datetime
from typing import List, Dict, Any, Optional
import concurrent.futures
from pydantic import BaseModel

from config.config import MLB_TEAMS
from utils.logger import get_logger
from utils.mlb_api import MLBDataFetcher
from utils.perplexity_api import PerplexityNewsFetcher
from utils.anthropic_generator import ScriptGenerator
from utils.elevenlabs_tts import ElevenLabsTTS

logger = get_logger(__name__)

class TeamPodcastResult(BaseModel):
    """Model for team podcast processing result."""
    team_code: str
    team_name: str
    date: str
    data_file: Optional[str] = None
    news_file: Optional[str] = None
    script_file: Optional[str] = None
    audio_file: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    
    # Pydantic v2 compatible config
    model_config = {
        "arbitrary_types_allowed": True
    }

class PodcastProcessor:
    """Main processor for generating team podcasts."""
    
    def __init__(self):
        self.mlb_data = MLBDataFetcher()
        self.perplexity_api = PerplexityNewsFetcher()
        self.script_generator = ScriptGenerator()
        self.tts = ElevenLabsTTS()
    
    def process_team(self, team_code: str, date: Optional[datetime.date] = None) -> TeamPodcastResult:
        """Process a single team's podcast."""
        date = date or datetime.date.today()
        date_str = date.strftime("%Y-%m-%d")
        team_name = MLB_TEAMS.get(team_code)
        
        logger.info(f"Starting podcast processing for {team_name} on {date_str}")
        
        result = TeamPodcastResult(
            team_code=team_code,
            team_name=team_name,
            date=date_str
        )
        
        try:
            # Step 1: Fetch MLB Data
            team_data = self.mlb_data.process_team_daily_data(team_code, date)
            result.data_file = os.path.join("data", team_code, f"{date_str}.json")
            
            # Step 2: Fetch News Data
            news_file_path = os.path.join("data", team_code, f"{date_str}_news.txt")
            result.news_file = news_file_path
            
            if os.path.exists(news_file_path):
                logger.info(f"News file for {team_name} on {date_str} already exists. Using existing file.")
                # Load existing news data if needed
                with open(news_file_path, 'r') as f:
                    news_data = f.read()
            else:
                logger.info(f"Fetching news data for {team_name} on {date_str}")
                news_data = self.perplexity_api.fetch_and_save_team_news(team_code, date)
            
            # Step 3: Generate Script
            script = self.script_generator.generate_and_save_script(team_code, date)
            result.script_file = os.path.join("scripts", team_code, f"{date_str}.txt")
            
            # Step 4: Generate Audio
            audio_file = self.tts.generate_and_save_audio(team_code, date)
            if audio_file:
                result.audio_file = audio_file
                result.success = True
            else:
                result.error = "Failed to generate audio file"
                
        except Exception as e:
            logger.error(f"Error processing {team_name}: {str(e)}")
            result.error = str(e)
            result.success = False
            
        return result
    
    def process_all_teams(self, date: Optional[datetime.date] = None, max_workers: int = 5) -> List[TeamPodcastResult]:
        """Process podcasts for all MLB teams using parallel processing."""
        date = date or datetime.date.today()
        logger.info(f"Starting batch processing for all teams on {date.strftime('%Y-%m-%d')}")
        
        results = []
        
        # Process teams in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_team = {
                executor.submit(self.process_team, team_code, date): team_code 
                for team_code in MLB_TEAMS.keys()
            }
            
            for future in concurrent.futures.as_completed(future_to_team):
                team_code = future_to_team[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Completed processing for {MLB_TEAMS.get(team_code)}: {'Success' if result.success else 'Failed'}")
                except Exception as e:
                    logger.error(f"Error in thread for {MLB_TEAMS.get(team_code)}: {str(e)}")
                    results.append(TeamPodcastResult(
                        team_code=team_code,
                        team_name=MLB_TEAMS.get(team_code),
                        date=date.strftime("%Y-%m-%d"),
                        success=False,
                        error=str(e)
                    ))
        
        # Log summary
        success_count = sum(1 for result in results if result.success)
        logger.info(f"Batch processing complete: {success_count}/{len(MLB_TEAMS)} teams successful")
        
        return results