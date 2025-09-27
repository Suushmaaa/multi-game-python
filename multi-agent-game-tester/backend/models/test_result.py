from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running" 
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

class ExecutionArtifact:
    def __init__(self, type: str, filename: str, content: str, timestamp: datetime):
        self.type = type
        self.filename = filename
        self.content = content
        self.timestamp = timestamp

class TestResult:
    def __init__(self, test_id: str, title: str, status: TestStatus,
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None,
                 duration: Optional[float] = None,
                 executor_id: Optional[str] = None,
                 error_message: Optional[str] = None,
                 artifacts: Optional[List[ExecutionArtifact]] = None):
        self.test_id = test_id
        self.title = title
        self.status = status
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration
        self.executor_id = executor_id
        self.error_message = error_message
        self.artifacts = artifacts or []

class ValidationResult:
    def __init__(self, test_id: str, is_valid: bool, confidence_score: float, 
                 validation_notes: List[str], recommended_action: str):
        self.test_id = test_id
        self.is_valid = is_valid
        self.confidence_score = confidence_score
        self.validation_notes = validation_notes
        self.recommended_action = recommended_action

class AnalysisReport:
    def __init__(self, analysis_timestamp: datetime, analyzer_id: str,
                 total_tests_analyzed: int, reliability_score: float,
                 coverage_score: float, quality_score: float, 
                 overall_confidence: float, validation_results: List[ValidationResult],
                 detailed_analysis: Dict[str, Any], triage_recommendations: List[Dict[str, Any]],
                 actionable_insights: List[str]):
        self.analysis_timestamp = analysis_timestamp
        self.analyzer_id = analyzer_id
        self.total_tests_analyzed = total_tests_analyzed
        self.reliability_score = reliability_score
        self.coverage_score = coverage_score
        self.quality_score = quality_score
        self.overall_confidence = overall_confidence
        self.validation_results = validation_results
        self.detailed_analysis = detailed_analysis
        self.triage_recommendations = triage_recommendations
        self.actionable_insights = actionable_insights