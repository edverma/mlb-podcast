import os
import json
import datetime
from typing import Dict, Any, Optional, List
import anthropic

from config.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, SCRIPTS_DIR, MLB_TEAMS, PODCAST_LENGTH_MINUTES
from utils.logger import get_logger

logger = get_logger(__name__)

class ScriptGenerator:
    def __init__(self):
        self.api_key = ANTHROPIC_API_KEY
        
        # Always use a valid model name - use claude-3-sonnet-20240229 as a fallback
        self.model = ANTHROPIC_MODEL
        
        # Check if we're using a demo key
        self.use_mock = not self.api_key or self.api_key == "sample_anthropic_api_key"
        
        # Only create client if we have a valid API key
        if not self.use_mock:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            # Use a dummy API key for initialization (won't actually be used)
            self.client = anthropic.Anthropic(api_key="sk-ant-dummy123")
        
    def load_team_data(self, team_code: str, date: Optional[datetime.date] = None) -> Dict[str, Any]:
        """Load team data from the JSON file."""
        date = date or datetime.date.today()
        date_str = date.strftime("%Y-%m-%d")
        
        # Construct the file path
        file_path = os.path.join("data", team_code, f"{date_str}.json")
        news_file_path = os.path.join("data", team_code, f"{date_str}_news.txt")
        
        # Load team data
        try:
            with open(file_path, "r") as f:
                team_data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Team data file not found: {file_path}")
            team_data = {
                "team_code": team_code,
                "team_name": MLB_TEAMS.get(team_code, "Unknown Team"),
                "date": date_str,
                "games": [],
                "standings": {}
            }
            
        # Load news data
        try:
            with open(news_file_path, "r") as f:
                news_data = json.load(f)
        except FileNotFoundError:
            logger.error(f"News data file not found: {news_file_path}")
            news_data = []
            
        # Add news to team data
        team_data["news"] = news_data
        
        return team_data
    
    def generate_script(self, team_data: Dict[str, Any]) -> str:
        """Generate a podcast script based on team data."""
        team_name = team_data.get("team_name")
        date_str = team_data.get("date")
        games = team_data.get("games", [])
        standings = team_data.get("standings", {})
        news = team_data.get("news", [])
        
        logger.info(f"Generating script for {team_name} on {date_str}")
        
        # Build the prompt
        prompt = self._build_prompt(team_name, date_str, games, standings, news)
        
        # Check if we're using mock mode (for testing/demo purposes)
        if self.use_mock:
            logger.info("Using mock response for testing")
            return self._generate_mock_script(team_name, date_str, games, standings, news)
        
        try:
            message = self.client.messages.create(
                model=self.model,
                system="You are a professional sports podcaster specializing in MLB baseball coverage. Your goal is to create engaging, informative daily update podcasts for baseball fans.",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=15000
            )
            
            script_text = message.content[0].text
            
            return script_text
            
        except Exception as e:
            logger.error(f"Error generating script for {team_name}: {e}")
            # Provide a mock script for testing with any API error
            return self._generate_mock_script(team_name, date_str, games, standings, news)
            
    def _generate_mock_script(self, team_name: str, date_str: str, 
                             games: List[Dict[str, Any]], 
                             standings: Dict[str, Any],
                             news: List[Dict[str, Any]]) -> str:
        """Generate a mock script for testing purposes using SSML."""
        
        # Format date for readable output
        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%B %d, %Y")
        except:
            formatted_date = date_str
        
        # Build a simple mock script with SSML
        script = f"""<speak>
    <prosody rate="medium" pitch="medium">
        <emphasis level="strong">{team_name} Daily Update</emphasis> - <say-as interpret-as="date" format="mdy">{formatted_date}</say-as>
        <break time="1s"/>
        
        Hello, fans! <prosody volume="loud">Welcome</prosody> to the {team_name} Daily Update podcast. I'm your host, and I've got all the latest news and updates for you on this <say-as interpret-as="date" format="mdy">{formatted_date}</say-as>.
        <break time="0.5s"/>
        
        <emphasis level="moderate">Game Recap</emphasis>
        <break time="0.5s"/>
"""
        
        if games:
            for game in games:
                status = game.get("status")
                home_team = game.get("home_team")
                away_team = game.get("away_team")
                home_score = int(game.get("home_score", 0))
                away_score = int(game.get("away_score", 0))
                
                if status == "Final":
                    result = "won" if ((home_team == team_name and home_score > away_score) or 
                                      (away_team == team_name and away_score > home_score)) else "lost"
                    
                    script += f"""
        <p>Yesterday, the {team_name} <emphasis level="moderate">{result}</emphasis> their game """
                    
                    if home_team == team_name:
                        script += f"""against the {away_team}. The final score was <say-as interpret-as="cardinal">{home_score}</say-as> to <say-as interpret-as="cardinal">{away_score}</say-as>.</p>
        <break time="0.3s"/>"""
                    else:
                        script += f"""against the {home_team}. The final score was <say-as interpret-as="cardinal">{away_score}</say-as> to <say-as interpret-as="cardinal">{home_score}</say-as>.</p>
        <break time="0.3s"/>"""
                        
                    # Add notable performances if available
                    notable_performances = game.get("notable_performances", [])
                    if notable_performances:
                        script += """
        <p><prosody pitch="high">Standout performances</prosody> included:</p>
        <break time="0.3s"/>"""
                        for perf in notable_performances:
                            name = perf.get("name", "")
                            hr = perf.get("hr", 0)
                            hits = perf.get("hits", 0)
                            rbi = perf.get("rbi", 0)
                            
                            if name:
                                script += f"""        <p>{name}: """
                                stats = []
                                if hr > 0:
                                    stats.append(f"""<say-as interpret-as="cardinal">{hr}</say-as> home run{'s' if hr > 1 else ''}""")
                                if hits > 0:
                                    stats.append(f"""<say-as interpret-as="cardinal">{hits}</say-as> hit{'s' if hits > 1 else ''}""")
                                if rbi > 0:
                                    stats.append(f"""<say-as interpret-as="cardinal">{rbi}</say-as> RBI{'s' if rbi > 1 else ''}""")
                                
                                script += ", ".join(stats) + "</p>\n"
                else:
                    script += f"""
        <p>The {team_name} {'host' if home_team == team_name else 'visit'} the {home_team if away_team == team_name else away_team} today.</p>
        <break time="0.3s"/>"""
        else:
            script += """
        <p>The team didn't play yesterday. They'll be back in action soon!</p>
        <break time="0.3s"/>"""
        
        # Add standings information if available
        if standings:
            wins = standings.get("wins", 0)
            losses = standings.get("losses", 0)
            division_rank = standings.get("division_rank", "")
            games_back = standings.get("games_back", 0)
            try:
                games_back = float(games_back) if games_back != "-" else 0
            except (ValueError, TypeError):
                games_back = 0
            
            script += """
        <break time="0.7s"/>
        <emphasis level="moderate">Current Standings</emphasis>
        <break time="0.5s"/>"""
            
            script += f"""
        <p>The {team_name} currently have a record of <say-as interpret-as="cardinal">{wins}</say-as> and <say-as interpret-as="cardinal">{losses}</say-as>, """
            
            if division_rank:
                script += f"""putting them in <emphasis level="strong">{division_rank}</emphasis> place in their division.</p>"""
            
            if games_back == 0:
                script += """
        <p><prosody rate="slow" pitch="high">They're leading their division!</prosody></p>"""
            elif games_back > 0:
                script += f"""
        <p>They're <say-as interpret-as="cardinal">{games_back}</say-as> game{'s' if games_back > 1 else ''} behind the division leader.</p>"""
        
        # Add news if available
        if news:
            script += """
        <break time="0.7s"/>
        <emphasis level="moderate">Recent News</emphasis>
        <break time="0.5s"/>"""
            
            for article in news[:2]:
                title = article.get("title", "")
                if title:
                    script += f"""
        <p>{title}</p>
        <break time="0.3s"/>"""
        
        # Add outro
        script += f"""
        <break time="0.7s"/>
        <emphasis level="moderate">Closing Thoughts</emphasis>
        <break time="0.5s"/>
        
        <p>That's all for today's {team_name} update. Thanks for listening, and be sure to check back tomorrow for the latest news and updates.</p>
        
        <prosody rate="slow" pitch="low">This is your host signing off. <prosody volume="loud">Go {team_name}!</prosody></prosody>
    </prosody>
</speak>"""
        
        return script
    
    def _build_prompt(self, team_name: str, date_str: str, games: List[Dict[str, Any]], 
                    standings: Dict[str, Any], news: List[Dict[str, Any]]) -> str:
        """Build a prompt for the script generation."""
        # Format date for readable output
        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%B %d, %Y")
        except:
            formatted_date = date_str
            
        prompt = f"""Generate a {PODCAST_LENGTH_MINUTES}-minute podcast script for the {team_name} for {formatted_date}.

Include a brief intro and outro. The script should sound natural when read aloud and include enthusiasm and personality of a baseball fan and podcaster.

Here is the data to include in the podcast:

"""

        # Add game information
        if games:
            prompt += "GAME RESULTS:\n"
            for game in games:
                status = game.get("status")
                home_team = game.get("home_team")
                away_team = game.get("away_team")
                home_score = game.get("home_score")
                away_score = game.get("away_score")
                
                if status == "Final":
                    prompt += f"- {away_team} ({away_score}) at {home_team} ({home_score}) - Game completed\n"
                    
                    # Add notable performances
                    notable_performances = game.get("notable_performances", [])
                    if notable_performances:
                        prompt += "  Notable performances:\n"
                        for perf in notable_performances:
                            name = perf.get("name")
                            hr = perf.get("hr", 0)
                            hits = perf.get("hits", 0)
                            rbi = perf.get("rbi", 0)
                            
                            stats = []
                            if hr > 0:
                                stats.append(f"{hr} HR")
                            if hits > 0:
                                stats.append(f"{hits} hits")
                            if rbi > 0:
                                stats.append(f"{rbi} RBI")
                                
                            if stats:
                                prompt += f"  - {name}: {', '.join(stats)}\n"
                else:
                    # Game not completed or scheduled for future
                    prompt += f"- {away_team} at {home_team} - {status}\n"
        else:
            prompt += "NO GAMES: The team did not play yesterday.\n"
            
        # Add standings information
        if standings:
            wins = standings.get("wins", 0)
            losses = standings.get("losses", 0)
            division_rank = standings.get("division_rank", "")
            games_back = standings.get("games_back", 0)
            streak = standings.get("streak", "")
            
            prompt += f"\nSTANDINGS:\n"
            prompt += f"- Record: {wins}-{losses}\n"
            prompt += f"- Division Rank: {division_rank}\n"
            prompt += f"- Games Back: {games_back}\n"
            prompt += f"- Current Streak: {streak}\n"
            
        # Add news
        if news:
            prompt += f"\nRECENT NEWS:\n {news}"
        # Add final instructions
        prompt += f"""
INSTRUCTIONS:
1. Start with a brief, catchy intro for the "{team_name} Daily Update" podcast.
2. Cover yesterday's game results with excitement, highlight key plays and players.
3. Mention the current standings and what it means for the team.
4. Discuss the recent news articles and their implications.
5. Add some color commentary and baseball insights throughout.
6. End with a brief outro that encourages listeners to check back tomorrow.
7. The entire script should be readable in approximately {PODCAST_LENGTH_MINUTES} minutes.
8. Use a conversational, enthusiastic tone as if you're speaking directly to baseball fans.
9. Include specific references to players, scores, and stats where relevant.
"""
        
        return prompt
    
    def generate_and_save_script(self, team_code: str, date: Optional[datetime.date] = None) -> str:
        """Generate and save a script for a team as SSML."""
        date = date or datetime.date.today()
        date_str = date.strftime("%Y-%m-%d")
        team_name = MLB_TEAMS.get(team_code)
        
        # Load team data
        team_data = self.load_team_data(team_code, date)
        
        # Generate script
        script = self.generate_script(team_data)
        
        # Save to file
        team_script_dir = os.path.join(SCRIPTS_DIR, team_code)
        os.makedirs(team_script_dir, exist_ok=True)
        
        # Save as XML file
        script_file_path = os.path.join(team_script_dir, f"{date_str}.txt")
        with open(script_file_path, "w") as f:
            f.write(script)
            
        logger.info(f"Saved script for {team_name} to {script_file_path}")
        return script