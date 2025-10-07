from typing import List, Dict, Any
import json
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models.test_case import TestCase, TestStep, TestType, Priority
from config import settings
from utils.rag_utils import rag_system

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

        if self.llm:
            try:
                return self._generate_with_llm(game_context)
            except Exception as e:
                self.logger.warning(f"LLM generation failed: {e}, falling back to mock")
                return self._generate_mock_tests()
        else:
            return self._generate_mock_tests()

    def _generate_with_llm(self, game_context: Dict[str, Any] = None) -> List[TestCase]:
        """Generate test cases using LLM with RAG augmentation"""
        # Retrieve relevant patterns from RAG
        query = f"test cases for {settings.target_game_url} math puzzle game"
        relevant_patterns = rag_system.retrieve_relevant_patterns(query, k=3)

        # Augment system prompt with retrieved patterns
        augmented_prompt = self.conversation_history[0]["content"]  # Base system prompt

        if relevant_patterns:
            augmented_prompt += "\n\nLEARNED PATTERNS FROM SUCCESSFUL TESTS:\n"
            for i, pattern in enumerate(relevant_patterns, 1):
                augmented_prompt += f"\nPattern {i} (Quality: {pattern['metadata'].get('quality_score', 0)}):\n"
                augmented_prompt += pattern["content"][:500] + "...\n"  # Truncate for brevity

        # Create user message
        user_message = f"Generate {settings.num_candidate_tests} test cases for the math puzzle game at {settings.target_game_url}. Focus on comprehensive coverage including functional, usability, performance, boundary, and error handling tests."

        # Call LLM
        messages = [
            {"role": "system", "content": augmented_prompt},
            {"role": "user", "content": user_message}
        ]

        response = self.llm.invoke(messages)
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Parse JSON response
        try:
            # Extract JSON from response (might be wrapped in markdown)
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                test_data = json.loads(json_str)
            else:
                test_data = json.loads(response_text)

            # Convert to TestCase objects
            test_cases = []
            for test_dict in test_data:
                steps = []
                for step_data in test_dict.get("steps", []):
                    step = TestStep(
                        action=step_data.get("action", "navigate"),
                        target=step_data.get("target", ""),
                        expected_result=step_data.get("expected_result", ""),
                        wait_time=step_data.get("wait_time", 2.0),
                        screenshot=step_data.get("screenshot", True)
                    )
                    steps.append(step)

                test_case = TestCase(
                    title=test_dict.get("title", "Generated Test"),
                    description=test_dict.get("description", ""),
                    test_type=TestType(test_dict.get("test_type", "functional").upper()),
                    priority=Priority(test_dict.get("priority", "medium").upper()),
                    steps=steps,
                    expected_outcome=test_dict.get("expected_outcome", ""),
                    preconditions=test_dict.get("preconditions", []),
                    tags=test_dict.get("tags", ["generated"]),
                    estimated_duration=test_dict.get("estimated_duration", 30.0)
                )
                test_cases.append(test_case)

            self.logger.info(f"Generated {len(test_cases)} test cases with LLM")
            return test_cases

        except Exception as e:
            self.logger.error(f"Failed to parse LLM response: {e}")
            raise

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
