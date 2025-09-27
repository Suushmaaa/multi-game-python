from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import uuid
from datetime import datetime
from .execution_result import ExecutionResult

class ValidationResult(BaseModel):
    is_valid: bool
    confidence_score: float  # 0.0 to 1.0
    validation_notes: List[str] = []
    cross_agent_agreement: bool = False
    repeat_consistency: bool = False

class TestReport(BaseModel):
    report_id: str = ""
    generation_time: Optional[datetime] = None
    execution_results: List[ExecutionResult]
    validation_results: Dict[str, ValidationResult] = {}
    summary_stats: Dict[str, Any] = {}
    reproducibility_stats: Dict[str, float] = {}
    triage_notes: List[str] = []
    artifacts_summary: Dict[str, List[str]] = {}
    
    def __init__(self, **data):
        if not data.get('report_id'):
            data['report_id'] = f"RPT_{str(uuid.uuid4())[:8]}"
        if not data.get('generation_time'):
            data['generation_time'] = datetime.now()
        super().__init__(**data)