from typing import List, Dict, Any
import json
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models.test_case import TestCase, TestType, Priority
from config import settings

class RankerAgent(BaseAgent):
    def __init__(self):
        super().__init__("RankerAgent")
        self.setup_system_prompt()

    def setup_system_prompt(self):
        system_prompt = f"""
You are an expert test case ranking and selection agent for web game testing.

Your task is to analyze {settings.num_candidate_tests} candidate test cases and select the top {settings.num_selected_tests} most valuable ones.

RANKING CRITERIA (in order of importance):
1. CRITICAL FUNCTIONALITY - Tests that validate core game mechanics
2. HIGH IMPACT BUGS - Tests likely to catch serious issues that affect user experience
3. COVERAGE - Tests that cover different areas (UI, logic, performance, error handling)
4. RISK MITIGATION - Tests for known problem areas in web games
5. EXECUTION EFFICIENCY - Reasonable execution time vs value

SCORING WEIGHTS:
- Priority High = 10 points, Medium = 6 points, Low = 3 points
- Test Type Functional = +5 points, Error Handling = +4 points, Performance = +3 points, Usability = +2 points, Boundary = +1 point
- Coverage Bonus = +2 points if test covers unique functionality
- Efficiency Penalty = -1 point per 30 seconds over 60 seconds duration

SELECTION STRATEGY:
- Must include at least 2 functional tests
- Must include at least 1 error handling test
- Should cover different test types
- Prioritize tests that can catch critical bugs early

Return a JSON object with:
{{
  "selected_test_ids": ["TC_001", "TC_002", ...],
  "ranking_rationale": "Explanation of selection criteria and decisions",
  "coverage_analysis": {{"functional": 3, "usability": 2, "performance": 1, "boundary": 2, "error_handling": 2}},
  "estimated_total_duration": 300.0,
  "risk_coverage": ["core_gameplay", "user_input", "error_scenarios", "performance"]
}}
"""
        self.add_system_message(system_prompt)

    def execute(self, test_cases: List[TestCase]) -> Dict[str, Any]:
        """Rank and select the top test cases"""
        self.logger.info(f"Ranking {len(test_cases)} test cases")

        if not test_cases:
            return self._empty_selection()

        if self.llm:
            try:
                return self._llm_ranking(test_cases)
            except Exception as e:
                self.logger.warning(f"LLM ranking failed: {e}, falling back to smart ranking")
                return self._smart_ranking(test_cases)
        else:
            return self._smart_ranking(test_cases)

    def _llm_ranking(self, test_cases: List[TestCase]) -> Dict[str, Any]:
        """Use LLM for intelligent ranking and selection"""
        # Prepare test cases data for LLM
        test_data = []
        for i, tc in enumerate(test_cases):
            test_data.append({
                "id": f"TC_{i+1:03d}",
                "title": tc.title,
                "description": tc.description,
                "test_type": tc.test_type.value,
                "priority": tc.priority.value,
                "steps_count": len(tc.steps),
                "estimated_duration": tc.estimated_duration,
                "tags": tc.tags
            })

        # Create user message with test data
        user_message = f"""
Analyze these {len(test_cases)} test cases and select the top {settings.num_selected_tests} most valuable ones.

TEST CASES:
{json.dumps(test_data, indent=2)}

Return a JSON object with your ranking and selection analysis.
"""

        # Call LLM
        messages = [
            {"role": "system", "content": self.conversation_history[0]["content"]},
            {"role": "user", "content": user_message}
        ]

        response = self.llm.invoke(messages)
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Parse JSON response
        try:
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
            else:
                result = json.loads(response_text)

            # Extract selected test IDs and map back to test cases
            selected_ids = result.get("selected_test_ids", [])
            selected_tests = []
            for test_id in selected_ids:
                if test_id.startswith("TC_"):
                    index = int(test_id[3:]) - 1
                    if 0 <= index < len(test_cases):
                        selected_tests.append(test_cases[index])

            # If LLM didn't select enough, fall back to smart ranking
            if len(selected_tests) < settings.num_selected_tests:
                self.logger.warning(f"LLM selected only {len(selected_tests)} tests, using smart ranking to fill")
                smart_result = self._smart_ranking(test_cases)
                selected_tests = smart_result["selected_tests"][:settings.num_selected_tests]

            # Generate analysis
            coverage_analysis = self._analyze_coverage(selected_tests)
            total_duration = sum(tc.estimated_duration for tc in selected_tests)
            risk_areas = self._identify_risk_coverage(selected_tests)

            return {
                "selected_test_ids": [tc.test_id for tc in selected_tests],
                "selected_tests": selected_tests,
                "ranking_rationale": result.get("ranking_rationale", "LLM-based selection"),
                "coverage_analysis": coverage_analysis,
                "estimated_total_duration": total_duration,
                "risk_coverage": risk_areas,
                "selection_stats": {
                    "total_candidates": len(test_cases),
                    "selected": len(selected_tests),
                    "method": "llm"
                }
            }

        except Exception as e:
            self.logger.error(f"Failed to parse LLM ranking response: {e}")
            raise

    def _smart_ranking(self, test_cases: List[TestCase]) -> Dict[str, Any]:
        """Implement intelligent ranking based on defined criteria"""
        scored_tests = []

        for test_case in test_cases:
            score = self._calculate_test_score(test_case)
            scored_tests.append((score, test_case))

        # Sort by score descending
        scored_tests.sort(key=lambda x: x[0], reverse=True)

        # Apply selection constraints
        selected_tests = self._apply_selection_constraints(scored_tests)

        # Generate analysis
        coverage_analysis = self._analyze_coverage(selected_tests)
        total_duration = sum(tc.estimated_duration for tc in selected_tests)
        risk_areas = self._identify_risk_coverage(selected_tests)

        return {
            "selected_test_ids": [tc.test_id for tc in selected_tests],
            "selected_tests": selected_tests,
            "ranking_rationale": self._generate_rationale(selected_tests, coverage_analysis),
            "coverage_analysis": coverage_analysis,
            "estimated_total_duration": total_duration,
            "risk_coverage": risk_areas,
            "selection_stats": {
                "total_candidates": len(test_cases),
                "selected": len(selected_tests),
                "avg_score": sum(score for score, _ in scored_tests[:len(selected_tests)]) / len(selected_tests)
            }
        }

    def _calculate_test_score(self, test_case: TestCase) -> float:
        """Calculate numerical score for a test case"""
        score = 0.0

        # Priority scoring
        priority_scores = {
            Priority.HIGH: 10,
            Priority.MEDIUM: 6,
            Priority.LOW: 3
        }
        score += priority_scores.get(test_case.priority, 0)

        # Test type scoring
        type_scores = {
            TestType.FUNCTIONAL: 5,
            TestType.ERROR_HANDLING: 4,
            TestType.PERFORMANCE: 3,
            TestType.USABILITY: 2,
            TestType.BOUNDARY: 1
        }
        score += type_scores.get(test_case.test_type, 0)

        # Step complexity bonus (more comprehensive tests)
        if len(test_case.steps) >= 3:
            score += 2
        elif len(test_case.steps) >= 5:
            score += 3

        # Duration efficiency penalty
        if test_case.estimated_duration > 60:
            penalty = (test_case.estimated_duration - 60) // 30
            score -= penalty

        # Tag-based bonuses
        valuable_tags = ["core", "critical", "regression", "smoke", "integration"]
        tag_bonus = len([tag for tag in test_case.tags if tag.lower() in valuable_tags])
        score += tag_bonus

        return max(score, 0.0)  # Ensure non-negative

    def _apply_selection_constraints(self, scored_tests: List[tuple]) -> List[TestCase]:
        """Apply selection constraints to ensure good coverage"""
        selected = []
        functional_count = 0
        error_handling_count = 0
        type_counts = {test_type: 0 for test_type in TestType}

        # Sort by score and select with constraints
        for score, test_case in scored_tests:
            if len(selected) >= settings.num_selected_tests:
                break

            # Check constraints
            should_select = True

            # Must have functional tests
            if test_case.test_type == TestType.FUNCTIONAL:
                functional_count += 1
            elif test_case.test_type == TestType.ERROR_HANDLING:
                error_handling_count += 1

            # Avoid too many of same type
            if type_counts[test_case.test_type] >= 4:  # Max 4 per type
                should_select = False

            if should_select:
                selected.append(test_case)
                type_counts[test_case.test_type] += 1

        # Ensure minimum requirements are met
        if functional_count < 2:
            # Try to swap in more functional tests
            selected = self._ensure_functional_tests(scored_tests, selected)

        return selected[:settings.num_selected_tests]

    def _ensure_functional_tests(self, scored_tests: List[tuple], current_selection: List[TestCase]) -> List[TestCase]:
        """Ensure we have enough functional tests"""
        functional_tests = [(score, tc) for score, tc in scored_tests
                           if tc.test_type == TestType.FUNCTIONAL and tc not in current_selection]

        if functional_tests:
            # Replace lowest scoring non-functional test
            non_functional = [(i, tc) for i, tc in enumerate(current_selection)
                            if tc.test_type != TestType.FUNCTIONAL]

            if non_functional:
                # Replace the last non-functional test
                replace_idx = non_functional[-1][0]
                current_selection[replace_idx] = functional_tests[0][1]

        return current_selection

    def _analyze_coverage(self, selected_tests: List[TestCase]) -> Dict[str, int]:
        """Analyze test type coverage"""
        coverage = {test_type.value: 0 for test_type in TestType}

        for test_case in selected_tests:
            coverage[test_case.test_type.value] += 1

        return coverage

    def _identify_risk_coverage(self, selected_tests: List[TestCase]) -> List[str]:
        """Identify what risk areas are covered"""
        risk_areas = set()

        for test_case in selected_tests:
            if test_case.test_type == TestType.FUNCTIONAL:
                risk_areas.add("core_gameplay")
            elif test_case.test_type == TestType.ERROR_HANDLING:
                risk_areas.add("error_scenarios")
            elif test_case.test_type == TestType.PERFORMANCE:
                risk_areas.add("performance")
            elif test_case.test_type == TestType.USABILITY:
                risk_areas.add("user_experience")

            # Check specific test content for additional risks
            title_lower = test_case.title.lower()
            if "input" in title_lower or "number" in title_lower:
                risk_areas.add("user_input")
            if "load" in title_lower or "performance" in title_lower:
                risk_areas.add("performance")
            if "boundary" in title_lower or "edge" in title_lower:
                risk_areas.add("edge_cases")

        return list(risk_areas)

    def _generate_rationale(self, selected_tests: List[TestCase], coverage: Dict[str, int]) -> str:
        """Generate human-readable rationale for selection"""
        total_tests = len(selected_tests)
        high_priority = len([tc for tc in selected_tests if tc.priority == Priority.HIGH])
        functional_tests = coverage.get("functional", 0)

        rationale = f"Selected {total_tests} tests based on comprehensive ranking criteria. "
        rationale += f"Prioritized {high_priority} high-priority tests and {functional_tests} functional tests "
        rationale += f"to ensure core functionality coverage. "
        rationale += f"Coverage includes: {', '.join([f'{k}({v})' for k, v in coverage.items() if v > 0])}. "
        rationale += "Selection balanced execution time with critical risk coverage."

        return rationale

    def _empty_selection(self) -> Dict[str, Any]:
        """Return empty selection result"""
        return {
            "selected_test_ids": [],
            "selected_tests": [],
            "ranking_rationale": "No test cases provided for ranking",
            "coverage_analysis": {},
            "estimated_total_duration": 0.0,
            "risk_coverage": [],
            "selection_stats": {"total_candidates": 0, "selected": 0, "avg_score": 0}
        }
