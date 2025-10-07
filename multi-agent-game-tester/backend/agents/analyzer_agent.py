from typing import List, Dict, Any, Optional
import json
import statistics
from datetime import datetime
from .base_agent import BaseAgent
from ..models.test_result import TestResult, TestStatus, ValidationResult, AnalysisReport
from ..config import settings

class AnalyzerAgent(BaseAgent):
    def __init__(self):
        super().__init__("AnalyzerAgent")
        self.setup_system_prompt()
    
    def setup_system_prompt(self):
        system_prompt = """
You are an expert test result analyzer and validator for web game testing.

Your responsibilities:
1. VALIDATE test execution results for accuracy and reliability
2. IDENTIFY patterns, anomalies, and potential false positives/negatives
3. CROSS-REFERENCE results across multiple executions for consistency
4. PROVIDE actionable insights for test improvement and bug triage
5. GENERATE confidence scores for test verdicts

VALIDATION CRITERIA:
- Result consistency across repeat executions
- Artifact completeness (screenshots, DOM, logs)
- Execution time reasonableness
- Error message clarity and actionability
- Cross-agent result correlation

ANALYSIS DIMENSIONS:
- Reliability: How consistent are the results?
- Coverage: What functionality was actually tested?
- Quality: How thorough was the test execution?
- Actionability: How useful are the findings?

Generate comprehensive analysis with confidence scores and triage recommendations.
"""
        self.add_system_message(system_prompt)
    
    def execute(self, execution_report: Dict[str, Any]) -> AnalysisReport:
        """Analyze and validate test execution results"""
        self.logger.info("Starting test result analysis and validation")
        
        test_results = self._parse_test_results(execution_report)
        
        # Perform multiple types of analysis
        reliability_analysis = self._analyze_reliability(test_results)
        coverage_analysis = self._analyze_coverage(test_results, execution_report)
        quality_analysis = self._analyze_quality(test_results)
        performance_analysis = self._analyze_performance(execution_report)
        
        # Generate validation results
        validation_results = self._validate_results(test_results)
        
        # Compile comprehensive report
        analysis_report = AnalysisReport(
            analysis_timestamp=datetime.utcnow(),
            analyzer_id=self.agent_id,
            total_tests_analyzed=len(test_results),
            reliability_score=reliability_analysis["score"],
            coverage_score=coverage_analysis["score"], 
            quality_score=quality_analysis["score"],
            overall_confidence=self._calculate_overall_confidence(
                reliability_analysis, coverage_analysis, quality_analysis
            ),
            validation_results=validation_results,
            detailed_analysis={
                "reliability": reliability_analysis,
                "coverage": coverage_analysis,
                "quality": quality_analysis,
                "performance": performance_analysis
            },
            triage_recommendations=self._generate_triage_recommendations(
                test_results, validation_results
            ),
            actionable_insights=self._generate_actionable_insights(
                test_results, execution_report
            )
        )
        
        self.logger.info(f"Analysis completed. Overall confidence: {analysis_report.overall_confidence:.2f}")
        return analysis_report
    
    def _parse_test_results(self, execution_report: Dict[str, Any]) -> List[TestResult]:
        """Parse test results from execution report"""
        test_results = []
        
        for result_data in execution_report.get("test_results", []):
            # Convert dict back to TestResult object
            result = TestResult(
                test_id=result_data["test_id"],
                title=result_data["title"],
                status=result_data["status"],
                start_time=datetime.fromisoformat(result_data["start_time"]) if result_data.get("start_time") else None,
                end_time=datetime.fromisoformat(result_data["end_time"]) if result_data.get("end_time") else None,
                duration=result_data.get("duration"),
                executor_id=result_data.get("executor_id"),
                error_message=result_data.get("error_message"),
                artifacts=result_data.get("artifacts", [])
            )
            test_results.append(result)
        
        return test_results
    
    def _analyze_reliability(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """Analyze result reliability and consistency"""
        total_tests = len(test_results)
        passed_tests = len([r for r in test_results if r.status == "passed"])
        failed_tests = len([r for r in test_results if r.status == "failed"])
        
        # Check for execution consistency
        execution_times = [r.duration for r in test_results if r.duration and r.duration > 0]
        time_consistency = 1.0
        if len(execution_times) > 1:
            time_std = statistics.stdev(execution_times)
            time_mean = statistics.mean(execution_times)
            time_coefficient_variation = time_std / time_mean if time_mean > 0 else 1.0
            time_consistency = max(0, 1.0 - time_coefficient_variation)
        
        # Artifact completeness check
        artifact_completeness = self._check_artifact_completeness(test_results)
        
        # Calculate reliability score
        execution_success_rate = passed_tests / total_tests if total_tests > 0 else 0
        reliability_score = (
            execution_success_rate * 0.4 +
            time_consistency * 0.3 +
            artifact_completeness * 0.3
        )
        
        return {
            "score": round(reliability_score, 3),
            "execution_success_rate": round(execution_success_rate, 3),
            "time_consistency": round(time_consistency, 3),
            "artifact_completeness": round(artifact_completeness, 3),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "issues": self._identify_reliability_issues(test_results)
        }
    
    def _analyze_coverage(self, test_results: List[TestResult], execution_report: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test coverage and completeness"""
        # Extract coverage from execution report
        artifact_summary = execution_report.get("artifact_summary", {})
        total_artifacts = artifact_summary.get("total_artifacts", 0)
        artifact_types = artifact_summary.get("artifact_types", {})
        
        # Calculate coverage metrics
        screenshot_coverage = artifact_types.get("screenshot", 0) / len(test_results) if test_results else 0
        dom_coverage = artifact_types.get("dom_snapshot", 0) / len(test_results) if test_results else 0
        log_coverage = (artifact_types.get("console_log", 0) + artifact_types.get("network_log", 0)) / len(test_results) if test_results else 0
        
        # Overall coverage score
        coverage_score = (screenshot_coverage + dom_coverage + log_coverage) / 3
        
        return {
            "score": round(min(coverage_score, 1.0), 3),
            "screenshot_coverage": round(screenshot_coverage, 3),
            "dom_coverage": round(dom_coverage, 3), 
            "log_coverage": round(log_coverage, 3),
            "total_artifacts": total_artifacts,
            "artifact_distribution": artifact_types
        }
    
    def _analyze_quality(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """Analyze test execution quality"""
        total_tests = len(test_results)
        
        # Error message quality
        failed_tests_with_errors = [r for r in test_results if r.status == "failed" and r.error_message]
        error_message_quality = len(failed_tests_with_errors) / max(1, len([r for r in test_results if r.status == "failed"]))
        
        # Execution time reasonableness (not too fast, not too slow)
        reasonable_times = []
        for result in test_results:
            if result.duration:
                # Reasonable execution time: 5-120 seconds
                if 5 <= result.duration <= 120:
                    reasonable_times.append(result)
        
        time_reasonableness = len(reasonable_times) / total_tests if total_tests > 0 else 0
        
        # Artifact richness (multiple types per test)
        rich_artifacts = []
        for result in test_results:
            artifact_types = set()
            for artifact in result.artifacts or []:
                if isinstance(artifact, dict):
                    artifact_types.add(artifact.get("type", "unknown"))
                else:
                    artifact_types.add(getattr(artifact, "type", "unknown"))
            
            if len(artifact_types) >= 2:  # At least 2 different artifact types
                rich_artifacts.append(result)
        
        artifact_richness = len(rich_artifacts) / total_tests if total_tests > 0 else 0
        
        # Calculate quality score
        quality_score = (
            error_message_quality * 0.3 +
            time_reasonableness * 0.4 +
            artifact_richness * 0.3
        )
        
        return {
            "score": round(quality_score, 3),
            "error_message_quality": round(error_message_quality, 3),
            "time_reasonableness": round(time_reasonableness, 3),
            "artifact_richness": round(artifact_richness, 3),
            "quality_issues": self._identify_quality_issues(test_results)
        }
    
    def _analyze_performance(self, execution_report: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze execution performance"""
        execution_summary = execution_report.get("execution_summary", {})
        
        total_duration = execution_summary.get("total_duration", 0)
        avg_execution_time = execution_summary.get("avg_execution_time", 0)
        total_tests = execution_summary.get("total_tests", 0)
        
        # Performance efficiency (tests per minute)
        tests_per_minute = (total_tests / (total_duration / 60)) if total_duration > 0 else 0
        
        # Parallel efficiency
        executor_performance = execution_report.get("executor_performance", {})
        executor_utilization = len(executor_performance) / max(1, settings.max_parallel_executors)
        
        return {
            "total_duration": round(total_duration, 2),
            "avg_execution_time": round(avg_execution_time, 2),
            "tests_per_minute": round(tests_per_minute, 2),
            "executor_utilization": round(executor_utilization, 3),
            "performance_rating": self._rate_performance(tests_per_minute, avg_execution_time)
        }
    
    def _validate_results(self, test_results: List[TestResult]) -> List[ValidationResult]:
        """Validate individual test results"""
        validation_results = []
        
        for result in test_results:
            validation = ValidationResult(
                test_id=result.test_id,
                is_valid=self._is_result_valid(result),
                confidence_score=self._calculate_confidence(result),
                validation_notes=self._generate_validation_notes(result),
                recommended_action=self._recommend_action(result)
            )
            validation_results.append(validation)
        
        return validation_results
    
    def _is_result_valid(self, result: TestResult) -> bool:
        """Determine if a test result is valid"""
        # Check basic validity criteria
        if not result.test_id or not result.title:
            return False
        
        # Execution time should be reasonable
        if result.duration and (result.duration < 1 or result.duration > 300):
            return False
        
        # Failed tests should have error messages
        if result.status == "failed" and not result.error_message:
            return False
        
        # Should have some artifacts
        if not result.artifacts or len(result.artifacts) < 1:
            return False
        
        return True
    
    def _calculate_confidence(self, result: TestResult) -> float:
        """Calculate confidence score for test result"""
        confidence = 1.0
        
        # Reduce confidence for missing artifacts
        expected_artifacts = 3  # screenshot, dom, logs
        actual_artifacts = len(result.artifacts) if result.artifacts else 0
        artifact_ratio = min(actual_artifacts / expected_artifacts, 1.0)
        confidence *= (0.5 + 0.5 * artifact_ratio)
        
        # Reduce confidence for unreasonable execution times
        if result.duration:
            if result.duration < 5:  # Too fast, might be incomplete
                confidence *= 0.7
            elif result.duration > 60:  # Too slow, might have issues
                confidence *= 0.8
        
        # Reduce confidence for failed tests without clear errors
        if result.status == "failed" and not result.error_message:
            confidence *= 0.3
        
        return round(confidence, 3)
    
    def _generate_validation_notes(self, result: TestResult) -> List[str]:
        """Generate validation notes for test result"""
        notes = []
        
        if not result.artifacts or len(result.artifacts) < 2:
            notes.append("Insufficient artifacts captured")
        
        if result.duration and result.duration < 5:
            notes.append("Execution time unusually short")
        elif result.duration and result.duration > 60:
            notes.append("Execution time longer than expected")
        
        if result.status == "failed" and not result.error_message:
            notes.append("Failed test lacks error message")
        
        if result.status == "passed" and result.duration and result.duration < 2:
            notes.append("Passed test completed very quickly - verify completeness")
        
        return notes
    
    def _recommend_action(self, result: TestResult) -> str:
        """Recommend action based on test result"""
        if result.status == "passed":
            if self._calculate_confidence(result) >= 0.8:
                return "accept_result"
            else:
                return "rerun_for_confirmation"
        
        elif result.status == "failed":
            if result.error_message and self._calculate_confidence(result) >= 0.7:
                return "investigate_failure"
            else:
                return "rerun_with_debugging"
        
        else:
            return "manual_review_required"
    
    # Complete the rest of analyzer_agent.py

    def _check_artifact_completeness(self, test_results: List[TestResult]) -> float:
        """Check completeness of artifacts across all tests"""
        if not test_results:
            return 0.0
        
        complete_tests = 0
        for result in test_results:
            artifact_types = set()
            for artifact in result.artifacts or []:
                if isinstance(artifact, dict):
                    artifact_types.add(artifact.get("type", "unknown"))
                else:
                    artifact_types.add(getattr(artifact, "type", "unknown"))
            
            # Consider complete if has screenshot + at least one other type
            if "screenshot" in artifact_types and len(artifact_types) >= 2:
                complete_tests += 1
        
        return complete_tests / len(test_results)
    
    def _identify_reliability_issues(self, test_results: List[TestResult]) -> List[str]:
        """Identify reliability issues in test results"""
        issues = []
        
        failed_tests = [r for r in test_results if r.status == "failed"]
        if len(failed_tests) > len(test_results) * 0.5:
            issues.append("High failure rate indicates potential infrastructure issues")
        
        # Check for tests that failed without clear errors
        unclear_failures = [r for r in failed_tests if not r.error_message]
        if unclear_failures:
            issues.append(f"{len(unclear_failures)} tests failed without clear error messages")
        
        # Check for execution time anomalies
        execution_times = [r.duration for r in test_results if r.duration and r.duration > 0]
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            outliers = [t for t in execution_times if abs(t - avg_time) > avg_time]
            if len(outliers) > len(execution_times) * 0.3:
                issues.append("Inconsistent execution times detected")
        
        return issues
    
    def _identify_quality_issues(self, test_results: List[TestResult]) -> List[str]:
        """Identify quality issues in test execution"""
        issues = []
        
        # Check for tests with minimal artifacts
        minimal_artifacts = [r for r in test_results if not r.artifacts or len(r.artifacts) < 2]
        if minimal_artifacts:
            issues.append(f"{len(minimal_artifacts)} tests have insufficient artifacts")
        
        # Check for suspiciously fast tests
        fast_tests = [r for r in test_results if r.duration and r.duration < 5]
        if fast_tests:
            issues.append(f"{len(fast_tests)} tests completed very quickly - may be incomplete")
        
        return issues
    
    def _rate_performance(self, tests_per_minute: float, avg_execution_time: float) -> str:
        """Rate overall performance"""
        if tests_per_minute >= 2.0 and avg_execution_time <= 30:
            return "excellent"
        elif tests_per_minute >= 1.0 and avg_execution_time <= 45:
            return "good"
        elif tests_per_minute >= 0.5 and avg_execution_time <= 60:
            return "acceptable"
        else:
            return "needs_improvement"
    
    def _calculate_overall_confidence(self, reliability: Dict, coverage: Dict, quality: Dict) -> float:
        """Calculate overall confidence score"""
        reliability_weight = 0.4
        coverage_weight = 0.3
        quality_weight = 0.3
        
        overall = (
            reliability["score"] * reliability_weight +
            coverage["score"] * coverage_weight +
            quality["score"] * quality_weight
        )
        
        return round(overall, 3)
    
    def _generate_triage_recommendations(self, test_results: List[TestResult], 
                                       validations: List[ValidationResult]) -> List[Dict[str, Any]]:
        """Generate triage recommendations"""
        recommendations = []
        
        # High priority failed tests
        critical_failures = [r for r in test_results if r.status == "failed" and 
                           any(v.confidence_score >= 0.8 for v in validations if v.test_id == r.test_id)]
        
        if critical_failures:
            recommendations.append({
                "priority": "high",
                "category": "critical_failures",
                "description": f"{len(critical_failures)} critical test failures require immediate investigation",
                "affected_tests": [r.test_id for r in critical_failures]
            })
        
        # Low confidence results
        low_confidence = [v for v in validations if v.confidence_score < 0.5]
        if low_confidence:
            recommendations.append({
                "priority": "medium", 
                "category": "low_confidence_results",
                "description": f"{len(low_confidence)} test results have low confidence scores",
                "affected_tests": [v.test_id for v in low_confidence]
            })
        
        # Infrastructure issues
        infrastructure_issues = len([r for r in test_results if not r.artifacts or len(r.artifacts) < 1])
        if infrastructure_issues > 0:
            recommendations.append({
                "priority": "medium",
                "category": "infrastructure", 
                "description": f"{infrastructure_issues} tests show signs of infrastructure problems",
                "affected_tests": [r.test_id for r in test_results if not r.artifacts or len(r.artifacts) < 1]
            })
        
        return recommendations
    
    def _generate_actionable_insights(self, test_results: List[TestResult], 
                                    execution_report: Dict[str, Any]) -> List[str]:
        """Generate actionable insights"""
        insights = []
        
        # Success rate insights
        success_rate = execution_report.get("execution_summary", {}).get("success_rate", 0)
        if success_rate >= 90:
            insights.append("High success rate indicates stable application - consider expanding test coverage")
        elif success_rate < 50:
            insights.append("Low success rate suggests critical issues - focus on infrastructure and core functionality")
        
        # Performance insights
        avg_time = execution_report.get("execution_summary", {}).get("avg_execution_time", 0)
        if avg_time > 45:
            insights.append("Long execution times detected - optimize test steps and page load waits")
        
        # Coverage insights
        artifact_types = execution_report.get("artifact_summary", {}).get("artifact_types", {})
        if artifact_types.get("screenshot", 0) < len(test_results):
            insights.append("Missing screenshots in some tests - ensure visual verification is captured")
        
        # Error pattern insights
        error_messages = [r.error_message for r in test_results if r.error_message]
        common_errors = {}
        for error in error_messages:
            if error:
                # Simple error categorization
                if "timeout" in error.lower():
                    common_errors["timeout"] = common_errors.get("timeout", 0) + 1
                elif "not found" in error.lower() or "selector" in error.lower():
                    common_errors["selector"] = common_errors.get("selector", 0) + 1
        
        for error_type, count in common_errors.items():
            if count >= 2:
                insights.append(f"Multiple {error_type} errors detected - review {error_type} handling strategy")
        
        return insights


# Add these model classes to models/test_result.py

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