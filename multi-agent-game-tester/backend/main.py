from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
import json
import asyncio
import uuid
from datetime import datetime
from pydantic import BaseModel
import logging
from pathlib import Path

# Import your agents
from agents.planner_agent import PlannerAgent
from agents.ranker_agent import RankerAgent
# from agents.orchestrator_agent import OrchestratorAgent
# from agents.analyzer_agent import AnalyzerAgent
from models.test_case import TestCase
from config import settings

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

app = FastAPI(title="Multi-Agent Game Tester", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (your frontend) - THIS WAS MISSING
frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

# In-memory storage for demo (use database in production)
execution_sessions = {}
test_reports = {}

class ExecutionRequest(BaseModel):
    game_url: Optional[str] = None
    num_tests: Optional[int] = 20
    select_top: Optional[int] = 10

class ExecutionResponse(BaseModel):
    session_id: str
    status: str
    message: str

@app.get("/")
async def serve_frontend():
    """Serve the main frontend page"""
    return FileResponse(str(frontend_dir / "index.html"))

@app.post("/api/generate-tests", response_model=ExecutionResponse)
async def generate_tests(request: ExecutionRequest):
    """Generate test cases using PlannerAgent"""
    try:
        session_id = str(uuid.uuid4())
        
        # Initialize PlannerAgent
        planner = PlannerAgent()
        
        # Generate test cases
        game_context = {"target_url": request.game_url or settings.target_game_url}
        test_cases = planner.execute(game_context)
        
        # Store session data
        execution_sessions[session_id] = {
            "status": "tests_generated",
            "generated_tests": test_cases,
            "selected_tests": None,
            "execution_results": None,
            "analysis_report": None,
            "created_at": datetime.utcnow(),
            "game_url": request.game_url or settings.target_game_url
        }
        
        logger.info(f"Generated {len(test_cases)} test cases for session {session_id}")
        
        return ExecutionResponse(
            session_id=session_id,
            status="success",
            message=f"Generated {len(test_cases)} test cases"
        )
        
    except Exception as e:
        logger.error(f"Test generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test generation failed: {str(e)}")

@app.post("/api/rank-select/{session_id}", response_model=ExecutionResponse)
async def rank_and_select_tests(session_id: str, num_selected: Optional[int] = 10):
    """Rank and select top test cases using RankerAgent"""
    try:
        if session_id not in execution_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = execution_sessions[session_id]
        
        if session["status"] != "tests_generated":
            raise HTTPException(status_code=400, detail="Invalid session state for ranking")
        
        # Initialize RankerAgent
        ranker = RankerAgent()
        
        # Rank and select tests
        ranking_result = ranker.execute(session["generated_tests"])
        selected_tests = ranking_result["selected_tests"]
        
        # Update session
        session["status"] = "tests_selected"
        session["selected_tests"] = selected_tests
        session["ranking_result"] = ranking_result
        
        logger.info(f"Selected {len(selected_tests)} tests for session {session_id}")
        
        return ExecutionResponse(
            session_id=session_id,
            status="success", 
            message=f"Selected {len(selected_tests)} top-ranked test cases"
        )
        
    except Exception as e:
        logger.error(f"Test ranking failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test ranking failed: {str(e)}")

@app.post("/api/execute-tests/{session_id}", response_model=ExecutionResponse)
async def execute_tests(session_id: str, background_tasks: BackgroundTasks):
    """Execute selected tests - Mock implementation for now"""
    try:
        if session_id not in execution_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = execution_sessions[session_id]
        
        if session["status"] != "tests_selected":
            raise HTTPException(status_code=400, detail="Invalid session state for execution")
        
        # Start mock execution in background
        background_tasks.add_task(execute_tests_mock, session_id)
        
        # Update session status
        session["status"] = "executing"
        
        logger.info(f"Started execution for session {session_id}")
        
        return ExecutionResponse(
            session_id=session_id,
            status="started",
            message=f"Started execution of {len(session['selected_tests'])} test cases"
        )
        
    except Exception as e:
        logger.error(f"Test execution start failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test execution start failed: {str(e)}")

async def execute_tests_mock(session_id: str):
    """Mock test execution for demo purposes"""
    try:
        import time
        session = execution_sessions[session_id]
        selected_tests = session["selected_tests"]
        
        # Simulate execution time
        await asyncio.sleep(10)  # Simulate 10 seconds of execution
        
        # Create mock results
        mock_results = {
            "execution_summary": {
                "total_tests": len(selected_tests),
                "passed": len(selected_tests) - 2,  # Mock some failures
                "failed": 2,
                "success_rate": ((len(selected_tests) - 2) / len(selected_tests)) * 100,
                "total_duration": 45.2,
                "avg_execution_time": 4.5
            },
            "test_results": [
                {
                    "test_id": test.test_id,
                    "title": test.title,
                    "status": "passed" if i < len(selected_tests) - 2 else "failed",
                    "duration": 3.0 + i,
                    "executor_id": f"ExecutorAgent_{(i % 3) + 1}",
                    "error_message": "Mock timeout error" if i >= len(selected_tests) - 2 else None,
                    "artifacts": [
                        {"type": "screenshot", "filename": f"test_{i}_screenshot.png"},
                        {"type": "dom_snapshot", "filename": f"test_{i}_dom.html"},
                        {"type": "console_log", "filename": f"test_{i}_console.json"}
                    ]
                }
                for i, test in enumerate(selected_tests)
            ],
            "artifact_summary": {
                "total_artifacts": len(selected_tests) * 3,
                "artifact_types": {
                    "screenshot": len(selected_tests),
                    "dom_snapshot": len(selected_tests), 
                    "console_log": len(selected_tests)
                }
            }
        }
        
        # Mock analysis
        mock_analysis = {
            "overall_confidence": 0.85,
            "reliability_score": 0.78,
            "coverage_score": 0.92,
            "quality_score": 0.81,
            "actionable_insights": [
                "High success rate indicates stable application",
                "2 timeout errors suggest network optimization needed",
                "All tests captured complete artifact sets"
            ]
        }
        
        # Update session with results
        session["status"] = "completed"
        session["execution_results"] = mock_results
        session["analysis_report"] = mock_analysis
        session["completed_at"] = datetime.utcnow()
        
        # Store final report
        test_reports[session_id] = {
            "session_id": session_id,
            "execution_report": mock_results,
            "analysis_report": mock_analysis,
            "generated_at": datetime.utcnow()
        }
        
        logger.info(f"Mock execution completed for session {session_id}")
        
    except Exception as e:
        logger.error(f"Mock execution failed: {e}")
        session = execution_sessions.get(session_id, {})
        session["status"] = "failed"
        session["error"] = str(e)

@app.get("/api/session-status/{session_id}")
async def get_session_status(session_id: str):
    """Get current session status"""
    if session_id not in execution_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = execution_sessions[session_id]
    
    status_info = {
        "session_id": session_id,
        "status": session["status"],
        "created_at": session["created_at"].isoformat(),
        "game_url": session.get("game_url")
    }
    
    if session["status"] == "tests_generated":
        status_info["generated_count"] = len(session.get("generated_tests", []))
    
    elif session["status"] == "tests_selected":
        status_info["generated_count"] = len(session.get("generated_tests", []))
        status_info["selected_count"] = len(session.get("selected_tests", []))
        status_info["ranking_result"] = session.get("ranking_result", {})
    
    elif session["status"] == "executing":
        status_info["selected_count"] = len(session.get("selected_tests", []))
        status_info["message"] = "Tests are currently executing..."
    
    elif session["status"] == "completed":
        execution_results = session.get("execution_results", {})
        status_info["execution_summary"] = execution_results.get("execution_summary", {})
        status_info["completed_at"] = session.get("completed_at").isoformat()
        
    elif session["status"] == "failed":
        status_info["error"] = session.get("error")
    
    return status_info

@app.get("/api/report/{session_id}")
async def get_test_report(session_id: str):
    """Get comprehensive test report"""
    if session_id not in test_reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = test_reports[session_id]
    
    # Convert to serializable format
    serializable_report = {
        "session_id": session_id,
        "generated_at": report["generated_at"].isoformat(),
        "execution_summary": report["execution_report"]["execution_summary"],
        "test_results": report["execution_report"]["test_results"],
        "artifact_summary": report["execution_report"]["artifact_summary"],
        "analysis": report["analysis_report"]
    }
    
    return serializable_report

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_sessions": len(execution_sessions),
        "stored_reports": len(test_reports)
    }

@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its data"""
    if session_id in execution_sessions:
        del execution_sessions[session_id]
    
    if session_id in test_reports:
        del test_reports[session_id]
    
    return {"message": f"Session {session_id} deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)