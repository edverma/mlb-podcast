# MLB Podcast Generator - Developer Guide

## Commands
- Run locally: `python main.py --team <TEAM_CODE> --date <YYYY-MM-DD>`
- Test with defaults: `python test.py` (uses NYY and yesterday's date)
- Run for all teams: `python main.py --all`
- Run as scheduled service: `python main.py --schedule`

## Code Style Guidelines
- **Imports**: Group imports as stdlib, third-party, and local
- **Typing**: Use type hints for all function parameters and return values
- **Error Handling**: Use try/except with specific exceptions and proper logging
- **Logging**: Use the logger from utils.logger with appropriate log levels
- **API Clients**: Implement mock mode for testing without valid API keys
- **Formatting**: Use consistent 4-space indentation
- **Naming**: Use snake_case for variables/functions, PascalCase for classes
- **Documentation**: Include docstrings for all functions and classes

## Environment
- Use `.env` file for API keys (not in git)
- All API clients should handle missing keys gracefully with mock mode