#!/usr/bin/env python3
"""
Test script to process a single team and generate a podcast.
This is useful for testing the entire workflow without processing all teams.
"""

import os
import datetime
from config.config import MLB_TEAMS
from utils.processor import PodcastProcessor
from utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """Process a test team."""
    # Create necessary directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("scripts", exist_ok=True)
    os.makedirs("audio", exist_ok=True)
    
    # Choose a team to test with - New York Yankees
    team_code = "NYY"
    team_name = MLB_TEAMS.get(team_code)
    
    # Use yesterday's date
    date = datetime.date.today() - datetime.timedelta(days=1)
    date_str = date.strftime("%Y-%m-%d")
    
    print(f"Testing with {team_name} for {date_str}")
    
    # Process the team
    processor = PodcastProcessor()
    result = processor.process_team(team_code, date)
    
    # Print result
    if result.success:
        print(f"\nSuccess! Generated podcast for the {team_name}:")
        print(f"  Data file: {result.data_file}")
        print(f"  News file: {result.news_file}")
        print(f"  Script file: {result.script_file}")
        print(f"  Audio file: {result.audio_file}")
    else:
        print(f"\nFailed to generate podcast for the {team_name}:")
        print(f"  Error: {result.error}")

if __name__ == "__main__":
    main()