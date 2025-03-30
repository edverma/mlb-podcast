import time
import datetime
import schedule

from config.config import UPDATE_TIME
from utils.processor import PodcastProcessor
from utils.logger import get_logger

logger = get_logger(__name__)

class PodcastScheduler:
    """Scheduler for daily podcast generation."""
    
    def __init__(self):
        self.processor = PodcastProcessor()
        
    def daily_job(self):
        """Process all teams for daily update."""
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        
        logger.info(f"Running daily job for date: {yesterday.strftime('%Y-%m-%d')}")
        
        try:
            # Process yesterday's data for all teams
            results = self.processor.process_all_teams(date=yesterday)
            
            # Log results
            success_count = sum(1 for result in results if result.success)
            failure_count = len(results) - success_count
            
            logger.info(f"Daily job completed: {success_count} successes, {failure_count} failures")
            
            # Log failures in detail
            if failure_count > 0:
                for result in results:
                    if not result.success:
                        logger.error(f"Failed to process {result.team_name}: {result.error}")
                        
        except Exception as e:
            logger.error(f"Error in daily job: {str(e)}")
    
    def run_once(self, date=None):
        """Run the processor once for a specific date or yesterday."""
        if date is None:
            date = datetime.date.today() - datetime.timedelta(days=1)
            
        logger.info(f"Running one-time processing for date: {date.strftime('%Y-%m-%d')}")
        self.processor.process_all_teams(date=date)
    
    def start(self):
        """Start the scheduler."""
        logger.info(f"Starting scheduler, will run daily at {UPDATE_TIME}")
        
        # Schedule the job to run daily
        schedule.every().day.at(UPDATE_TIME).do(self.daily_job)
        
        # Run the job immediately
        logger.info("Running initial job...")
        self.daily_job()
        
        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute