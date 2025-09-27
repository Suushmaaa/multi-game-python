# Fix Import Errors in Multi-Agent Game Tester

## Problem
ModuleNotFoundError: No module named 'agents' when running agent files. This is due to absolute imports in subpackages that should be relative.

## Files to Fix
- [x] backend/agents/executor_agent.py
- [x] backend/agents/analyzer_agent.py
- [x] backend/agents/planner_agent.py
- [x] backend/agents/ranker_agent.py
- [x] backend/agents/orchestrator_agent.py
- [x] backend/main.py (fixed imports to be relative)

## Changes Needed
For each agent file, change imports:
- `from agents.base_agent import BaseAgent` → `from .base_agent import BaseAgent`
- `from models.*` → `from ..models.*`
- `from config import settings` → `from ..config import settings`
- `from agents.executor_agent import ExecutorAgent` → `from .executor_agent import ExecutorAgent` (in orchestrator_agent.py)

## Testing
After fixes, test by running the main.py to ensure no import errors.

## Status
✅ All import errors fixed! The application is now running successfully on http://localhost:8000
✅ Fixed session reset issue - can now regenerate tests even after previous runs

## Usage
- **API**: http://localhost:8000
- **Web UI**: http://localhost:8000/ui
- **Health Check**: http://localhost:8000/health

**Important**: Do NOT open the HTML files directly from the file system. Use the web UI at http://localhost:8000/ui to avoid CORS issues.

## Recent Fixes
- Modified `/generate-tests` endpoint to automatically reset session if not idle, allowing test regeneration
- Fixed Python syntax errors in main.py
