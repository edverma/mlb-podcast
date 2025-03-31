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
from utils.google_wavenet_tts import GoogleWavenetTTS
from utils.podbean_distributor import PodbeanDistributor

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
    podbean_url: Optional[str] = None
    distribution_success: bool = False
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
        self.tts = GoogleWavenetTTS()
        self.distributor = PodbeanDistributor()
    
    def process_team(self, team_code: str, date: Optional[datetime.date] = None, distribute: bool = True) -> TeamPodcastResult:
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
                
                # Step 5: Distribute to Podbean
                if result.success and result.audio_file and distribute:
                    logger.info(f"Distributing podcast for {team_name} to Podbean")
                    
                    # Load script content for episode description
                    script_content = ""
                    if os.path.exists(result.script_file):
                        with open(result.script_file, 'r') as f:
                            script_content = f.read()
                    
                    # Prepare metadata for Podbean
                    metadata = {
                        "title": f"{team_name} Daily Update - {date_str}",
                        "description": script_content[:1000] if script_content else f"Daily update for {team_name}",
                        "tags": ["MLB", "baseball", "sports", team_code, team_name],
                        "category": "Sports & Recreation"
                    }
                    
                    # Distribute the podcast
                    distribution_success, podbean_url = self.distributor.distribute_podcast(
                        result.audio_file, metadata
                    )
                    
                    if distribution_success and podbean_url:
                        result.podbean_url = podbean_url
                        result.distribution_success = True
                        logger.info(f"Successfully distributed {team_name} podcast to Podbean: {podbean_url}")
                    else:
                        logger.error(f"Failed to distribute {team_name} podcast to Podbean")
                elif result.success and not distribute:
                    logger.info(f"Skipping Podbean distribution for {team_name} (--no-distribute flag set)")
                
            else:
                result.error = "Failed to generate audio file"
                
        except Exception as e:
            logger.error(f"Error processing {team_name}: {str(e)}")
            result.error = str(e)
            result.success = False
            
        return result
    
    def process_all_teams(self, date: Optional[datetime.date] = None, max_workers: int = 5, distribute: bool = True) -> List[TeamPodcastResult]:
        """Process podcasts for all MLB teams using parallel processing."""
        date = date or datetime.date.today()
        logger.info(f"Starting batch processing for all teams on {date.strftime('%Y-%m-%d')}")
        
        results = []
        
        # Process teams in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_team = {
                executor.submit(self.process_team, team_code, date, distribute): team_code 
                for team_code in MLB_TEAMS.keys()
            }
            
            for future in concurrent.futures.as_completed(future_to_team):
                team_code = future_to_team[future]
                try:
                    result = future.result()
                    results.append(result)
                    status = "Success"
                    if not result.success:
                        status = "Failed"
                    elif not result.distribution_success and distribute:
                        status = "Generated but not distributed"
                    elif not distribute:
                        status = "Generated (distribution skipped)"
                    logger.info(f"Completed processing for {MLB_TEAMS.get(team_code)}: {status}")
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
        distributed_count = sum(1 for result in results if result.distribution_success)
        
        if distribute:
            logger.info(f"Batch processing complete: {success_count}/{len(MLB_TEAMS)} teams generated, {distributed_count}/{len(MLB_TEAMS)} distributed")
        else:
            logger.info(f"Batch processing complete: {success_count}/{len(MLB_TEAMS)} teams generated (distribution skipped)")
        
        return results