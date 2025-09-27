from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
import uuid
from datetime import datetime
from .test_case import TestCase

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

class StepResult(BaseModel):
    step_id: str
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    screenshot_path: Optional[str] = None
    dom_snapshot_path: Optional[str] = None
    console_logs: List[str] = []
    network_logs: List[Dict[str, Any]] = []
    error_message: Optional[str] = None
    actual_result: Optional[str] = None

class ExecutionResult(BaseModel):
    execution_id: str = ""
    test_case: TestCase
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    step_results: List[StepResult] = []
    final_verdict: Optional[str] = None
    agent_id: str = ""
    retry_count: int = 0
    artifacts_dir: Optional[str] = None
    
    def __init__(self, **data):
        if not data.get('execution_id'):
            data['execution_id'] = f"EX_{str(uuid.uuid4())[:8]}"
        super().__init__(**data)