from typing import List, Dict, Any
import json
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models.test_case import TestCase, TestStep, TestType, Priority
from config import settings

class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__("PlannerAgent")
        self.setup_system_prompt()
    
    def setup_system_prompt(self):
        system_prompt = f"""
You are an expert test case generator for web-based number/math puzzle games.

TARGET GAME: {settings.target_game_url}
This is a math puzzle game where players solve numerical challenges.

Your task is to generate {settings.num_candidate_tests} diverse, comprehensive test cases.

FOCUS AREAS:
1. Core Game Mechanics - number input, calculations, scoring
2. UI Interactions - buttons, forms, navigation  
3. Edge Cases - invalid inputs, boundary values, large numbers
4. User Experience - loading times, feedback, error handling
5. Game Flow - start, progress, completion, restart

TEST TYPES TO GENERATE:
- functional: Core gameplay features
- usability: User experience and interface
- performance: Loading and response times
- boundary: Edge cases and limits
- error_handling: Invalid inputs and error recovery

For each test case, provide JSON in this exact format:
{{
  "title": "Clear descriptive test name",
  "description": "What this test validates",
  "test_type": "functional",
  "priority": "high",
  "steps": [
    {{
      "action": "navigate",
      "target": "URL or element",
      "expected_result": "what should happen",
      "wait_time": 2.0,
      "screenshot": true
    }}
  ],
  "expected_outcome": "overall success criteria",
  "preconditions": [],
  "tags": ["game", "math"],
  "estimated_duration": 30.0
}}

Return a JSON array with exactly {settings.num_candidate_tests} test cases.
"""
        self.add_system_message(system_prompt)
    
    def execute(self, game_context: Dict[str, Any] = None) -> List[TestCase]:
        """Generate test cases for the target game"""
        self.logger.info(f"Generating {settings.num_candidate_tests} test cases")
        
        # For now, return mock test cases (we'll implement OpenAI integration later)
        return self._generate_mock_tests()
    
    def _generate_mock_tests(self) -> List[TestCase]:
        """Generate mock test cases for development"""
        test_cases = []
        
        test_templates = [
            {
                "title": "Basic Game Load Test",
                "description": "Verify the math puzzle game loads successfully",
                "test_type": TestType.FUNCTIONAL,
                "priority": Priority.HIGH,
                "steps": [
                    {"action": "navigate", "target": settings.target_game_url, "expected_result": "Game page loads without errors"},
                    {"action": "wait", "target": "body", "expected_result": "Page fully rendered"}
                ],
                "expected_outcome": "Game interface is visible and interactive",
                "tags": ["smoke", "critical"]
            },
            {
                "title": "Number Input Validation", 
                "description": "Test basic number input functionality",
                "test_type": TestType.FUNCTIONAL,
                "priority": Priority.HIGH,
                "steps": [
                    {"action": "click", "target": "input[type='number']", "expected_result": "Input field focuses"},
                    {"action": "type", "target": "123", "expected_result": "Number appears in field"}
                ],
                "expected_outcome": "Numbers can be entered correctly",
                "tags": ["input", "core"]
            },
            {
                "title": "Invalid Input Handling",
                "description": "Test error handling for invalid mathematical inputs",
                "test_type": TestType.ERROR_HANDLING,
                "priority": Priority.HIGH,
                "steps": [
                    {"action": "type", "target": "abc", "expected_result": "Error message or input rejection"},
                    {"action": "verify", "target": ".error-message", "expected_result": "Error feedback shown"}
                ],
                "expected_outcome": "Invalid inputs are handled gracefully",
                "tags": ["error", "validation"]
            },
            {
                "title": "Mathematical Calculation Test",
                "description": "Verify correct mathematical calculations in puzzles",
                "test_type": TestType.FUNCTIONAL,
                "priority": Priority.HIGH,
                "steps": [
                    {"action": "input", "target": "2+2", "expected_result": "Expression entered"},
                    {"action": "submit", "target": "form", "expected_result": "Calculation performed"},
                    {"action": "verify", "target": ".result", "expected_result": "Shows result 4"}
                ],
                "expected_outcome": "Mathematical operations work correctly",
                "tags": ["math", "calculation", "core"]
            },
            {
                "title": "Game Performance Test",
                "description": "Verify game loads within acceptable time limits",
                "test_type": TestType.PERFORMANCE,
                "priority": Priority.MEDIUM,
                "steps": [
                    {"action": "navigate", "target": settings.target_game_url, "expected_result": "Page starts loading"},
                    {"action": "measure", "target": "load_time", "expected_result": "Load time < 5 seconds"}
                ],
                "expected_outcome": "Game loads quickly for good user experience",
                "tags": ["performance", "loading"]
            },
            {
                "title": "Large Number Boundary Test",
                "description": "Test game behavior with very large numbers",
                "test_type": TestType.BOUNDARY,
                "priority": Priority.MEDIUM,
                "steps": [
                    {"action": "input", "target": "999999999", "expected_result": "Large number handled"},
                    {"action": "submit", "target": "form", "expected_result": "Calculation processes"}
                ],
                "expected_outcome": "Large numbers are processed correctly",
                "tags": ["boundary", "edge-case"]
            },
            {
                "title": "Empty Input Test",
                "description": "Test behavior when no input is provided",
                "test_type": TestType.ERROR_HANDLING,
                "priority": Priority.MEDIUM,
                "steps": [
                    {"action": "click", "target": "submit", "expected_result": "Error handling triggered"},
                    {"action": "verify", "target": ".error", "expected_result": "Shows empty input error"}
                ],
                "expected_outcome": "Empty inputs are handled properly",
                "tags": ["error", "validation"]
            },
            {
                "title": "UI Responsiveness Test",
                "description": "Test user interface responsiveness and feedback",
                "test_type": TestType.USABILITY,
                "priority": Priority.MEDIUM,
                "steps": [
                    {"action": "click", "target": "button", "expected_result": "Button responds immediately"},
                    {"action": "hover", "target": ".interactive", "expected_result": "Visual feedback shown"}
                ],
                "expected_outcome": "UI provides immediate feedback to user actions",
                "tags": ["ui", "feedback"]
            }
        ]
        
        # Generate test cases based on templates, cycling through them
        template_index = 0
        for i in range(settings.num_candidate_tests):
            template = test_templates[template_index % len(test_templates)]
            template_index += 1
            
            steps = []
            for step_data in template["steps"]:
                step = TestStep(
                    action=step_data["action"],
                    target=step_data["target"], 
                    expected_result=step_data["expected_result"],
                    wait_time=2.0,
                    screenshot=True
                )
                steps.append(step)
            
            # Create unique title by adding variation number
            variation_num = (i // len(test_templates)) + 1
            title = template["title"]
            if variation_num > 1:
                title += f" - Variation {variation_num}"
            
            test_case = TestCase(
                title=title,
                description=template["description"],
                test_type=template["test_type"],
                priority=template["priority"],
                steps=steps,
                expected_outcome=template["expected_outcome"],
                tags=template.get("tags", ["automated"]),
                estimated_duration=30.0 + (len(steps) * 5)  # Base 30s + 5s per step
            )
            test_cases.append(test_case)
        
        self.logger.info(f"Generated {len(test_cases)} mock test cases")
        return test_cases