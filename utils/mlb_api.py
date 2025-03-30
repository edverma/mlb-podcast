import os
import json
import datetime
from typing import Dict, List, Any, Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from config.config import MLB_API_BASE_URL, MLB_API_KEY, DATA_DIR, MLB_TEAMS
from utils.logger import get_logger

logger = get_logger(__name__)

class MLBDataFetcher:
    def __init__(self):
        self.base_url = MLB_API_BASE_URL
        self.api_key = MLB_API_KEY
        self.use_mock = False
        self.session = requests.Session()
        
        # Only set headers if we have a valid API key
        if self.api_key and not self.use_mock:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the MLB API with retries."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching from MLB API: {e}")
            raise

    def get_schedule(self, date: Optional[datetime.date] = None) -> Dict[str, Any]:
        """Get MLB schedule for a specific date."""
        date_str = date.strftime("%Y-%m-%d") if date else datetime.date.today().strftime("%Y-%m-%d")
        return self._make_request("schedule", {"date": date_str, "sportId": 1})

    def get_game_boxscore(self, game_id: str) -> Dict[str, Any]:
        """Get detailed boxscore for a specific game."""
        return self._make_request(f"game/{game_id}/boxscore")

    def get_team_stats(self, team_id: str) -> Dict[str, Any]:
        """Get team stats."""
        return self._make_request(f"teams/{team_id}/stats")

    def get_standings(self) -> Dict[str, Any]:
        """Get current league standings."""
        return self._make_request("standings", {"leagueId": "103,104"})

    def get_team_roster(self, team_id: str) -> Dict[str, Any]:
        """Get team roster."""
        return self._make_request(f"teams/{team_id}/roster")

    def process_team_daily_data(self, team_code: str, date: Optional[datetime.date] = None) -> Dict[str, Any]:
        """
        Process daily data for a specific team.
        Returns a structured format with game results, standings, and roster information.
        """
        date = date or datetime.date.today() - datetime.timedelta(days=1)  # Default to yesterday
        date_str = date.strftime("%Y-%m-%d")
        team_name = MLB_TEAMS.get(team_code)
        
        logger.info(f"Processing data for {team_name} on {date_str}")
        
        # If we're using mock mode, return demo data
        if self.use_mock:
            logger.info(f"Using mock MLB data for {team_name} (demo mode)")
            
            # Get the existing data if available
            team_dir = os.path.join(DATA_DIR, team_code)
            file_path = os.path.join(team_dir, f"{date_str}.json")
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r") as f:
                        return json.load(f)
                except:
                    pass  # If file exists but can't be read, generate new mock data
            
            # Generate mock data
            team_data = {
                "team_code": team_code,
                "team_name": team_name,
                "date": date_str,
                "games": [
                    {
                        "game_id": 12345,
                        "status": "Final",
                        "home_team": team_name,
                        "away_team": "Visiting Team",
                        "home_score": 8,
                        "away_score": 3,
                        "venue": "Home Stadium",
                        "start_time": f"{date_str}T19:05:00Z",
                        "home_hits": 12,
                        "away_hits": 6,
                        "notable_performances": [
                            {
                                "name": "Star Player 1",
                                "team": team_name,
                                "hr": 2,
                                "rbi": 4,
                                "hits": 3
                            },
                            {
                                "name": "Star Player 2",
                                "team": team_name,
                                "hr": 1,
                                "rbi": 2,
                                "hits": 2
                            }
                        ]
                    }
                ],
                "standings": {
                    "wins": 5,
                    "losses": 2,
                    "division_rank": "1",
                    "games_back": 0,
                    "streak": "W3"
                }
            }
            
            # Save to file
            os.makedirs(os.path.join(DATA_DIR, team_code), exist_ok=True)
            with open(file_path, "w") as f:
                json.dump(team_data, f, indent=2)
                
            return team_data
        
        # Use the real API
        schedule_data = self.get_schedule(date)
        team_data = {
            "team_code": team_code,
            "team_name": team_name,
            "date": date_str,
            "games": [],
            "standings": {},
        }
        
        # Process games for this team
        for date_data in schedule_data.get("dates", []):
            for game in date_data.get("games", []):
                away_team = game.get("teams", {}).get("away", {}).get("team", {})
                home_team = game.get("teams", {}).get("home", {}).get("team", {})
                
                if (away_team.get("name") == team_name or home_team.get("name") == team_name):
                    # This game involves our team
                    game_id = game.get("gamePk")
                    game_status = game.get("status", {}).get("abstractGameState")
                    
                    game_info = {
                        "game_id": game_id,
                        "status": game_status,
                        "home_team": home_team.get("name"),
                        "away_team": away_team.get("name"),
                        "home_score": game.get("teams", {}).get("home", {}).get("score", 0),
                        "away_score": game.get("teams", {}).get("away", {}).get("score", 0),
                        "venue": game.get("venue", {}).get("name", ""),
                        "start_time": game.get("gameDate", "")
                    }
                    
                    # Add detailed boxscore data if game is finished
                    if game_status == "Final":
                        try:
                            boxscore = self.get_game_boxscore(game_id)
                            
                            # Extract key stats like home runs, RBIs, pitching stats
                            home_hr = 0
                            away_hr = 0
                            home_hits = boxscore.get("teams", {}).get("home", {}).get("teamStats", {}).get("batting", {}).get("hits", 0)
                            away_hits = boxscore.get("teams", {}).get("away", {}).get("teamStats", {}).get("batting", {}).get("hits", 0)
                            
                            # Add notable performances
                            notable_performances = []
                            
                            for side in ["home", "away"]:
                                players = boxscore.get("teams", {}).get(side, {}).get("players", {})
                                for player_id, player_data in players.items():
                                    # Check for notable batting performances
                                    batting_stats = player_data.get("stats", {}).get("batting", {})
                                    if batting_stats.get("homeRuns", 0) > 0 or batting_stats.get("rbi", 0) > 2:
                                        notable_performances.append({
                                            "name": player_data.get("person", {}).get("fullName", ""),
                                            "team": boxscore.get("teams", {}).get(side, {}).get("team", {}).get("name", ""),
                                            "hr": batting_stats.get("homeRuns", 0),
                                            "rbi": batting_stats.get("rbi", 0),
                                            "hits": batting_stats.get("hits", 0)
                                        })
                            
                            game_info["home_hits"] = home_hits
                            game_info["away_hits"] = away_hits
                            game_info["notable_performances"] = notable_performances
                            
                        except Exception as e:
                            logger.error(f"Error fetching boxscore for game {game_id}: {e}")
                    
                    team_data["games"].append(game_info)
        
        # Get standings data
        try:
            standings = self.get_standings()
            for division in standings.get("records", []):
                for team_record in division.get("teamRecords", []):
                    if team_record.get("team", {}).get("name") == team_name:
                        team_data["standings"] = {
                            "wins": team_record.get("wins", 0),
                            "losses": team_record.get("losses", 0),
                            "division_rank": team_record.get("divisionRank", ""),
                            "games_back": team_record.get("gamesBack", 0),
                            "streak": team_record.get("streak", {}).get("streakCode", "")
                        }
        except Exception as e:
            logger.error(f"Error fetching standings data: {e}")
            
        # Save the data
        team_dir = os.path.join(DATA_DIR, team_code)
        os.makedirs(team_dir, exist_ok=True)
        
        file_path = os.path.join(team_dir, f"{date_str}.json")
        with open(file_path, "w") as f:
            json.dump(team_data, f, indent=2)
            
        logger.info(f"Saved data for {team_name} to {file_path}")
        return team_data