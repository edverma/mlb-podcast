#!/usr/bin/env python3
"""
Test script to verify Podbean distribution functionality.
This script tests the complete distribution workflow for a single team.
"""

import os
import sys
import datetime
import argparse

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.processor import PodcastProcessor
from utils.podbean_distributor import PodbeanDistributor
from config.config import MLB_TEAMS
from utils.logger import get_logger

logger = get_logger(__name__)

def test_podbean_distribution(team_code, date_str=None, mock=False):
    """Test Podbean distribution for a single team."""
    if team_code not in MLB_TEAMS:
        print(f"❌ Invalid team code: {team_code}")
        print("Valid team codes:")
        for code, name in MLB_TEAMS.items():
            print(f"  {code}: {name}")
        return False
    
    # Parse date
    date = None
    if date_str:
        try:
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"❌ Invalid date format: {date_str}. Use YYYY-MM-DD.")
            return False
    else:
        # Default to yesterday
        date = datetime.date.today() - datetime.timedelta(days=1)
    
    date_str = date.strftime("%Y-%m-%d")
    
    print(f"=== Testing Podbean Distribution for {MLB_TEAMS[team_code]} on {date_str} ===")
    
    if mock:
        print("Running in mock mode (skipping audio generation)")
        
        # Create a mock audio file
        audio_dir = os.path.join("audio", team_code)
        os.makedirs(audio_dir, exist_ok=True)
        mock_audio_path = os.path.join(audio_dir, f"{date_str}_mock.mp3")
        
        # Create an empty MP3 file or copy a sample file if available
        sample_path = os.path.join("tests", "sample_audio.mp3")
        if os.path.exists(sample_path):
            import shutil
            shutil.copy(sample_path, mock_audio_path)
            print(f"Copied sample audio to {mock_audio_path}")
        else:
            # Create a minimal MP3 file
            with open(mock_audio_path, "wb") as f:
                # This is a minimal valid MP3 header
                f.write(b"\xFF\xFB\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
            print(f"Created mock audio file at {mock_audio_path}")
            
        # Create a mock script file
        script_dir = os.path.join("scripts", team_code)
        os.makedirs(script_dir, exist_ok=True)
        mock_script_path = os.path.join(script_dir, f"{date_str}.txt")
        
        with open(mock_script_path, "w") as f:
            f.write(f"# {MLB_TEAMS[team_code]} Daily Update - {date_str}\n\n")
            f.write("This is a mock podcast script for testing Podbean distribution.\n")
        print(f"Created mock script at {mock_script_path}")
        
        # Now test just the distribution part using the mock files
        try:
            # Create distributor
            distributor = PodbeanDistributor()
            
            # Prepare metadata
            metadata = {
                "title": f"{MLB_TEAMS[team_code]} Daily Update - {date_str} (Test)",
                "description": f"Test podcast for {MLB_TEAMS[team_code]} on {date_str}",
                "tags": ["MLB", "baseball", "sports", team_code, MLB_TEAMS[team_code], "test"],
                "category": "Sports & Recreation"
            }
            
            # Distribute podcast
            print(f"Distributing mock podcast for {MLB_TEAMS[team_code]} to Podbean...")
            distribution_success, podbean_url = distributor.distribute_podcast(mock_audio_path, metadata)
            
            if distribution_success and podbean_url:
                print(f"✅ Successfully distributed to Podbean")
                print(f"  Podbean URL: {podbean_url}")
                return True
            else:
                print(f"❌ Distribution failed")
                return False
        except Exception as e:
            print(f"❌ Error during distribution: {str(e)}")
            return False
    else:
        # Normal workflow - create and distribute a real podcast
        # Create processor and process team
        processor = PodcastProcessor()
        print(f"Processing {MLB_TEAMS[team_code]}...")
        result = processor.process_team(team_code, date, distribute=True)
        
        # Check results
        if result.success:
            print(f"✅ Successfully generated podcast for {result.team_name}")
            print(f"  Audio file: {result.audio_file}")
            
            if result.distribution_success:
                print(f"✅ Successfully distributed to Podbean")
                print(f"  Podbean URL: {result.podbean_url}")
                return True
            else:
                print(f"❌ Distribution failed")
                return False
        else:
            print(f"❌ Failed to generate podcast: {result.error}")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Podbean distribution")
    parser.add_argument("team", help="Team code to test (e.g., NYY, BOS)")
    parser.add_argument("--date", help="Date to process (YYYY-MM-DD)")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (skip audio generation)")
    
    args = parser.parse_args()
    
    success = test_podbean_distribution(args.team.upper(), args.date, args.mock)
    
    sys.exit(0 if success else 1) 