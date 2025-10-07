from typing import List, Dict, Any
import asyncio
import concurrent.futures
from datetime import datetime
from .base_agent import BaseAgent
from .executor_agent import ExecutorAgent
from ..models.test_case import TestCase
from ..models.test_result import TestResult, TestStatus
from ..config import settings

class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__("OrchestratorAgent")
        self.executor_agents: List[ExecutorAgent] = []
        self.setup_executors()
    
    def setup_executors(self):
        """Initialize multiple executor agents for parallel execution"""
        num_executors = min(settings.max_parallel_executors, settings.num_selected_tests)
        
        for i in range(num_executors):
            executor = ExecutorAgent(f"ExecutorAgent_{i+1}")
            self.executor_agents.append(executor)
        
        self.logger.info(f"Initialized {len(self.executor_agents)} executor agents")
    
    def execute(self, test_cases: List[TestCase]) -> Dict[str, Any]:
        """Orchestrate test execution across multiple agents"""
        self.logger.info(f"Orchestrating execution of {len(test_cases)} test cases")
        
        start_time = datetime.utcnow()
        
        # Execute tests using thread pool for concurrent execution
        results = self._execute_parallel(test_cases)
        
        end_time = datetime.utcnow()
        total_duration = (end_time - start_time).total_seconds()
        
        # Compile execution report
        execution_report = self._compile_execution_report(results, total_duration)
        
        self.logger.info(f"Orchestration completed in {total_duration:.2f} seconds")
        return execution_report
    
    def _execute_parallel(self, test_cases: List[TestCase]) -> List[TestResult]:
        """Execute test cases in parallel using multiple executors"""
        results = []
        
        if len(test_cases) <= len(self.executor_agents):
            # Direct assignment - one test per executor
            results = self._execute_direct_assignment(test_cases)
        else:
            # Batch processing - distribute tests across executors
            results = self._execute_batch_processing(test_cases)
        
        return results
    
    def _execute_direct_assignment(self, test_cases: List[TestCase]) -> List[TestResult]:
        """Assign one test case per executor agent"""
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.executor_agents)) as executor:
            # Create futures for each test execution
            future_to_test = {}
            
            for i, test_case in enumerate(test_cases):
                if i < len(self.executor_agents):
                    future = executor.submit(
                        asyncio.run,
                        self.executor_agents[i]._execute_single_test_wrapper(test_case)
                    )
                    future_to_test[future] = test_case
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_test):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    test_case = future_to_test[future]
                    self.logger.error(f"Test execution failed for {test_case.title}: {e}")
                    # Create failed result
                    failed_result = TestResult(
                        test_id=test_case.test_id,
                        title=test_case.title,
                        status=TestStatus.FAILED,
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        error_message=str(e),
                        executor_id="failed_assignment"
                    )
                    results.append(failed_result)
        
        return results
    
    def _execute_batch_processing(self, test_cases: List[TestCase]) -> List[TestResult]:
        """Distribute test cases across executors in batches"""
        results = []
        batch_size = len(test_cases) // len(self.executor_agents) + 1
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.executor_agents)) as executor:
            future_to_batch = {}
            
            # Create batches and assign to executors
            for i, agent in enumerate(self.executor_agents):
                start_idx = i * batch_size
                end_idx = min(start_idx + batch_size, len(test_cases))
                batch = test_cases[start_idx:end_idx]
                
                if batch:  # Only submit non-empty batches
                    future = executor.submit(agent.execute, batch)
                    future_to_batch[future] = (agent.agent_id, batch)
            
            # Collect batch results
            for future in concurrent.futures.as_completed(future_to_batch):
                try:
                    batch_results = future.result()
                    results.extend(batch_results)
                except Exception as e:
                    agent_id, batch = future_to_batch[future]
                    self.logger.error(f"Batch execution failed for {agent_id}: {e}")
                    
                    # Create failed results for entire batch
                    for test_case in batch:
                        failed_result = TestResult(
                            test_id=test_case.test_id,
                            title=test_case.title,
                            status=TestStatus.FAILED,
                            start_time=datetime.utcnow(),
                            end_time=datetime.utcnow(),
                            error_message=f"Batch execution failed: {str(e)}",
                            executor_id=agent_id
                        )
                        results.append(failed_result)
        
        return results
    
    def _compile_execution_report(self, results: List[TestResult], total_duration: float) -> Dict[str, Any]:
        """Compile comprehensive execution report"""
        passed_tests = [r for r in results if r.status == TestStatus.PASSED]
        failed_tests = [r for r in results if r.status == TestStatus.FAILED]
        
        # Calculate statistics
        success_rate = (len(passed_tests) / len(results)) * 100 if results else 0
        avg_execution_time = sum(r.duration for r in results if r.duration) / len(results) if results else 0
        
        # Executor performance
        executor_stats = {}
        for result in results:
            executor_id = result.executor_id
            if executor_id not in executor_stats:
                executor_stats[executor_id] = {"passed": 0, "failed": 0, "total_time": 0}
            
            if result.status == TestStatus.PASSED:
                executor_stats[executor_id]["passed"] += 1
            else:
                executor_stats[executor_id]["failed"] += 1
                
            if result.duration:
                executor_stats[executor_id]["total_time"] += result.duration
        
        # Artifact summary
        total_artifacts = sum(len(r.artifacts) for r in results if r.artifacts)
        artifact_types = {}
        for result in results:
            if result.artifacts:
                for artifact in result.artifacts:
                    artifact_type = artifact.type
                    artifact_types[artifact_type] = artifact_types.get(artifact_type, 0) + 1
        
        report = {
            "execution_summary": {
                "total_tests": len(results),
                "passed": len(passed_tests),
                "failed": len(failed_tests),
                "success_rate": round(success_rate, 2),
                "total_duration": round(total_duration, 2),
                "avg_execution_time": round(avg_execution_time, 2)
            },
            "test_results": [self._serialize_test_result(r) for r in results],
            "executor_performance": executor_stats,
            "artifact_summary": {
                "total_artifacts": total_artifacts,
                "artifact_types": artifact_types
            },
            "failed_tests": [
                {
                    "test_id": r.test_id,
                    "title": r.title,
                    "error": r.error_message,
                    "executor": r.executor_id
                }
                for r in failed_tests
            ],
            "execution_metadata": {
                "orchestrator": self.agent_id,
                "num_executors": len(self.executor_agents),
                "execution_timestamp": datetime.utcnow().isoformat(),
                "parallel_execution": True
            }
        }
        
        return report
    
    def _serialize_test_result(self, result: TestResult) -> Dict[str, Any]:
        """Convert TestResult to serializable dictionary"""
        return {
            "test_id": result.test_id,
            "title": result.title,
            "status": result.status.value,
            "start_time": result.start_time.isoformat() if result.start_time else None,
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "duration": result.duration,
            "executor_id": result.executor_id,
            "error_message": result.error_message,
            "artifacts": [
                {
                    "type": artifact.type,
                    "filename": artifact.filename,
                    "timestamp": artifact.timestamp.isoformat(),
                    "size": len(artifact.content) if artifact.content else 0
                }
                for artifact in (result.artifacts or [])
            ]
        }