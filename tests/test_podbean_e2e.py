#!/usr/bin/env python3
"""
End-to-end test script for the entire podcast distribution flow.
This script simulates the complete workflow from audio generation to Podbean distribution.
"""

import os
import sys
import argparse
import datetime
import json
import shutil

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.podbean_distributor import PodbeanDistributor
from utils.processor import PodcastProcessor, TeamPodcastResult
from config.config import MLB_TEAMS
from utils.logger import get_logger

logger = get_logger(__name__)

def setup_test_environment(team_code):
    """Set up the test environment for the specified team."""
    team_name = MLB_TEAMS.get(team_code, "Test Team")
    date = datetime.date.today()
    date_str = date.strftime("%Y-%m-%d")
    
    # Ensure necessary directories exist
    os.makedirs(f"data/{team_code}", exist_ok=True)
    os.makedirs(f"scripts/{team_code}", exist_ok=True)
    os.makedirs(f"audio/{team_code}", exist_ok=True)
    
    # Create or copy a sample audio file
    sample_audio_path = "tests/sample_audio.mp3"
    target_audio_path = f"audio/{team_code}/{date_str}.mp3"
    
    if not os.path.exists(sample_audio_path):
        from tests.create_sample_audio import create_sample_audio
        create_sample_audio(size_kb=100)
    
    shutil.copy(sample_audio_path, target_audio_path)
    print(f"Created sample audio at {target_audio_path}")
    
    # Create a sample script
    script_content = f"""# {team_name} Daily Update - {date_str}

Hello and welcome to the {team_name} Daily Update podcast for {date_str}.

This is a test script for demonstration purposes.

Thanks for listening!
"""
    script_path = f"scripts/{team_code}/{date_str}.txt"
    with open(script_path, "w") as f:
        f.write(script_content)
    print(f"Created sample script at {script_path}")
    
    # Create a sample data file
    data = {
        "team": team_code,
        "date": date_str,
        "test": True
    }
    data_path = f"data/{team_code}/{date_str}.json"
    with open(data_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Created sample data at {data_path}")
    
    # Create a test result object
    result = TeamPodcastResult(
        team_code=team_code,
        team_name=team_name,
        date=date_str,
        data_file=data_path,
        script_file=script_path,
        audio_file=target_audio_path,
        success=True
    )
    
    return result

def test_distribution(team_code):
    """Test the distribution of a podcast to Podbean."""
    print(f"\n===== Testing End-to-End Distribution for {MLB_TEAMS.get(team_code, 'Unknown Team')} =====")
    
    # Set up test environment
    result = setup_test_environment(team_code)
    
    # Create a distributor
    distributor = PodbeanDistributor()
    date_str = result.date
    
    # Prepare metadata for Podbean
    metadata = {
        "title": f"{result.team_name} Daily Update - {date_str} (Test)",
        "description": f"Test podcast for {result.team_name} generated on {date_str}",
        "tags": ["MLB", "baseball", "sports", team_code, result.team_name, "test"],
        "category": "Sports & Recreation"
    }
    
    # Distribute the podcast
    print(f"Distributing podcast for {result.team_name} to Podbean...")
    distribution_success, podbean_url = distributor.distribute_podcast(
        result.audio_file, metadata
    )
    
    if distribution_success and podbean_url:
        print(f"✅ Distribution successful!")
        print(f"Podbean URL: {podbean_url}")
        result.podbean_url = podbean_url
        result.distribution_success = True
        return True, result
    else:
        print(f"❌ Distribution failed")
        return False, result

def main():
    parser = argparse.ArgumentParser(description="End-to-end test for podcast distribution")
    parser.add_argument("--team", default="NYY", help="Team code to test (e.g., NYY, BOS)")
    parser.add_argument("--real", action="store_true", help="Use real API calls (not mock mode)")
    
    args = parser.parse_args()
    team_code = args.team.upper()
    
    # Validate team code
    if team_code not in MLB_TEAMS:
        print(f"❌ Invalid team code: {team_code}")
        print("Valid team codes:")
        for code, name in MLB_TEAMS.items()[:10]:  # Show first 10 teams
            print(f"  {code}: {name}")
        print("  ...")
        return False
    
    # Run the test
    distributor = PodbeanDistributor()
    
    if args.real:
        print("⚠️ Using real API calls (disabling mock mode)")
        distributor.disable_mock_mode()
    else:
        print("ℹ️ Using mock mode (no real API calls)")
        distributor.enable_mock_mode()
    
    success, result = test_distribution(team_code)
    
    print("\n===== Test Results =====")
    if success:
        print(f"✅ End-to-end test for {result.team_name} completed successfully")
        print(f"  Audio file: {result.audio_file}")
        print(f"  Podbean URL: {result.podbean_url}")
    else:
        print(f"❌ End-to-end test for {result.team_name} failed")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 