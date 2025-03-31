#!/usr/bin/env python3
import os
import sys
import argparse
import datetime

from config.config import MLB_TEAMS
from utils.logger import get_logger
from utils.processor import PodcastProcessor
from utils.scheduler import PodcastScheduler

logger = get_logger(__name__)

# Function removed as it's now defined in main()

def validate_team(team_code):
    """Validate the team code."""
    if team_code not in MLB_TEAMS:
        logger.error(f"Invalid team code: {team_code}")
        print(f"Error: Invalid team code '{team_code}'")
        print("Valid team codes:")
        for code, name in MLB_TEAMS.items():
            print(f"  {code}: {name}")
        sys.exit(1)
    return team_code

def validate_date(date_str):
    """Validate and parse the date string."""
    if not date_str:
        return datetime.date.today() - datetime.timedelta(days=1)  # Default to yesterday
    
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.error(f"Invalid date format: {date_str}")
        print(f"Error: Invalid date format '{date_str}'. Use YYYY-MM-DD.")
        sys.exit(1)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MLB Daily Podcast Generator")
    
    parser.add_argument("--team", type=str, help="Team code to process (e.g., NYY, BOS)")
    parser.add_argument("--date", type=str, help="Date to process (YYYY-MM-DD)")
    parser.add_argument("--all", action="store_true", help="Process all teams")
    parser.add_argument("--schedule", action="store_true", help="Run as a scheduled service")
    parser.add_argument("--no-distribute", action="store_true", help="Skip Podbean distribution")
    
    args = parser.parse_args()
    
    # Create necessary directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("scripts", exist_ok=True)
    os.makedirs("audio", exist_ok=True)
    
    processor = PodcastProcessor()
    
    # Determine whether to distribute
    distribute = not args.no_distribute
    
    if args.schedule:
        # Run as a scheduled service
        logger.info("Starting scheduled service...")
        scheduler = PodcastScheduler()
        scheduler.start()
    elif args.all:
        # Process all teams
        date = validate_date(args.date)
        logger.info(f"Processing all teams for {date.strftime('%Y-%m-%d')}...")
        
        # Add distribute parameter
        results = processor.process_all_teams(date=date, distribute=distribute)
        
        # Print summary
        success_count = sum(1 for result in results if result.success)
        distribution_count = sum(1 for result in results if result.distribution_success)
        
        print(f"\nProcessed {len(results)} teams:")
        print(f"  {success_count} successfully generated")
        
        if distribute:
            print(f"  {distribution_count} successfully distributed to Podbean")
            
            # Print distributed URLs
            if distribution_count > 0:
                print("\nDistributed podcasts:")
                for result in results:
                    if result.distribution_success and result.podbean_url:
                        print(f"  {result.team_name}: {result.podbean_url}")
        else:
            print("  Distribution to Podbean skipped (--no-distribute flag set)")
    elif args.team:
        # Process a single team
        team_code = validate_team(args.team.upper())
        date = validate_date(args.date)
        
        logger.info(f"Processing {MLB_TEAMS[team_code]} for {date.strftime('%Y-%m-%d')}...")
        
        # Add distribute parameter
        result = processor.process_team(team_code, date, distribute=distribute)
        
        # Print result
        if result.success:
            print(f"\nSuccessfully processed {result.team_name}:")
            print(f"  Data file: {result.data_file}")
            print(f"  News file: {result.news_file}")
            print(f"  Script file: {result.script_file}")
            print(f"  Audio file: {result.audio_file}")
            
            if distribute:
                if result.distribution_success:
                    print(f"  Podbean URL: {result.podbean_url}")
                elif result.audio_file:
                    print(f"  Podbean distribution: Failed")
            else:
                print(f"  Podbean distribution: Skipped (--no-distribute flag set)")
        else:
            print(f"\nFailed to process {result.team_name}: {result.error}")
    else:
        # No arguments provided, show help
        parser.print_help()

if __name__ == "__main__":
    main()