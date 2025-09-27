from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
import uuid
from datetime import datetime

class TestType(str, Enum):
    FUNCTIONAL = "functional"
    USABILITY = "usability" 
    PERFORMANCE = "performance"
    BOUNDARY = "boundary"
    ERROR_HANDLING = "error_handling"

class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TestStep(BaseModel):
    step_id: str = ""
    action: str
    target: str
    expected_result: str
    wait_time: float = 1.0
    screenshot: bool = True

    def __init__(self, **data):
        if not data.get('step_id'):
            data['step_id'] = str(uuid.uuid4())[:8]
        super().__init__(**data)

class TestCase(BaseModel):
    test_id: str = ""
    title: str
    description: str
    test_type: TestType
    priority: Priority
    steps: List[TestStep]
    expected_outcome: str
    preconditions: List[str] = []
    tags: List[str] = []
    estimated_duration: float = 30.0  # seconds
    created_at: Optional[datetime] = None
    
    def __init__(self, **data):
        if not data.get('test_id'):
            data['test_id'] = f"TC_{str(uuid.uuid4())[:8]}"
        if not data.get('created_at'):
            data['created_at'] = datetime.now()
        super().__init__(**data)