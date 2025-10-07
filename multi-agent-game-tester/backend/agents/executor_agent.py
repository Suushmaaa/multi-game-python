from typing import List, Dict, Any, Optional
import asyncio
import json
import time
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser
from .base_agent import BaseAgent
from ..models.test_case import TestCase
from ..models.test_result import TestResult, TestStatus, ExecutionArtifact
from ..config import settings

class ExecutorAgent(BaseAgent):
    def __init__(self, agent_id: str = "ExecutorAgent"):
        super().__init__(agent_id)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.artifacts: List[ExecutionArtifact] = []

    async def setup_browser(self):
        """Initialize browser for test execution"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=settings.headless_mode,
                args=['--disable-web-security', '--disable-features=VizDisplayCompositor']
            )
            
            context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            self.page = await context.new_page()
            
            # Setup console and network logging
            self.page.on('console', self._log_console_message)
            self.page.on('response', self._log_network_response)
            
            self.logger.info(f"Browser setup complete for {self.agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Browser setup failed: {e}")
            return False

    async def execute_test(self, test_case: TestCase) -> TestResult:
        """Execute a single test case"""
        self.logger.info(f"Executing test: {test_case.title}")
        
        result = TestResult(
            test_id=test_case.test_id,
            title=test_case.title,
            status=TestStatus.RUNNING,
            start_time=datetime.utcnow(),
            executor_id=self.agent_id
        )
        
        try:
            if not self.browser:
                await self.setup_browser()
            
            # Clear artifacts for new test
            self.artifacts = []
            
            # Execute test steps
            for i, step in enumerate(test_case.steps):
                step_success = await self._execute_step(step, i)
                
                if not step_success:
                    result.status = TestStatus.FAILED
                    result.error_message = f"Step {i+1} failed: {step.action}"
                    break
            
            # If all steps passed
            if result.status == TestStatus.RUNNING:
                result.status = TestStatus.PASSED
            
            # Final screenshot
            await self._capture_screenshot(f"final_result")
            
        except Exception as e:
            self.logger.error(f"Test execution failed: {e}")
            result.status = TestStatus.FAILED
            result.error_message = str(e)
        
        finally:
            result.end_time = datetime.utcnow()
            result.duration = (result.end_time - result.start_time).total_seconds()
            result.artifacts = self.artifacts.copy()
            
        self.logger.info(f"Test completed: {result.status.value}")
        return result

    async def _execute_single_test_wrapper(self, test_case: TestCase) -> TestResult:
        """Wrapper for single test execution with proper setup/cleanup"""
        try:
            await self.setup_browser()
            result = await self.execute_test(test_case)
            return result
        finally:
            await self.cleanup()

    async def _execute_step(self, step, step_index: int) -> bool:
        """Execute individual test step"""
        try:
            self.logger.info(f"Executing step {step_index + 1}: {step.action}")
            
            if step.action == "navigate":
                await self.page.goto(step.target, wait_until='networkidle')
                await self._capture_screenshot(f"step_{step_index + 1}_navigate")
                
            elif step.action == "click":
                await self.page.click(step.target, timeout=10000)
                await self._capture_screenshot(f"step_{step_index + 1}_click")
                
            elif step.action == "type" or step.action == "input":
                # Find input field and type
                input_selector = "input[type='number'], input[type='text'], input, textarea"
                await self.page.fill(input_selector, step.target)
                await self._capture_screenshot(f"step_{step_index + 1}_input")
                
            elif step.action == "submit":
                await self.page.click("button[type='submit'], input[type='submit'], .submit, button")
                await self._capture_screenshot(f"step_{step_index + 1}_submit")
                
            elif step.action == "wait":
                await self.page.wait_for_selector(step.target, timeout=10000)
                
            elif step.action == "verify":
                element = await self.page.query_selector(step.target)
                if not element:
                    self.logger.warning(f"Verification failed: {step.target} not found")
                    return False
                await self._capture_screenshot(f"step_{step_index + 1}_verify")
                
            elif step.action == "measure":
                # Performance measurement
                start_time = time.time()
                await self.page.reload()
                load_time = time.time() - start_time
                
                artifact = ExecutionArtifact(
                    type="performance",
                    filename=f"load_time_step_{step_index + 1}.json",
                    content=json.dumps({"load_time": load_time, "threshold": 5.0}),
                    timestamp=datetime.utcnow()
                )
                self.artifacts.append(artifact)
            
            # Wait time if specified
            if hasattr(step, 'wait_time') and step.wait_time > 0:
                await asyncio.sleep(step.wait_time)
            
            # Capture DOM snapshot
            await self._capture_dom_snapshot(f"step_{step_index + 1}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Step execution failed: {e}")
            await self._capture_screenshot(f"step_{step_index + 1}_error")
            return False

    async def _capture_screenshot(self, name: str):
        """Capture screenshot artifact"""
        try:
            screenshot = await self.page.screenshot(full_page=True)
            artifact = ExecutionArtifact(
                type="screenshot",
                filename=f"{name}.png",
                content=screenshot.hex(),  # Store as hex string
                timestamp=datetime.utcnow()
            )
            self.artifacts.append(artifact)
        except Exception as e:
            self.logger.warning(f"Screenshot capture failed: {e}")

    async def _capture_dom_snapshot(self, name: str):
        """Capture DOM snapshot"""
        try:
            html_content = await self.page.content()
            artifact = ExecutionArtifact(
                type="dom_snapshot",
                filename=f"{name}.html", 
                content=html_content,
                timestamp=datetime.utcnow()
            )
            self.artifacts.append(artifact)
        except Exception as e:
            self.logger.warning(f"DOM snapshot failed: {e}")

    def _log_console_message(self, msg):
        """Log browser console messages"""
        artifact = ExecutionArtifact(
            type="console_log",
            filename=f"console_{int(time.time())}.json",
            content=json.dumps({
                "level": msg.type,
                "text": msg.text,
                "timestamp": datetime.utcnow().isoformat()
            }),
            timestamp=datetime.utcnow()
        )
        self.artifacts.append(artifact)

    def _log_network_response(self, response):
        """Log network responses"""
        artifact = ExecutionArtifact(
            type="network_log",
            filename=f"network_{int(time.time())}.json",
            content=json.dumps({
                "url": response.url,
                "status": response.status,
                "headers": dict(response.headers),
                "timestamp": datetime.utcnow().isoformat()
            }),
            timestamp=datetime.utcnow()
        )
        self.artifacts.append(artifact)

    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
    
    def execute(self, test_cases: List[TestCase]) -> List[TestResult]:
        """Synchronous wrapper for async execution"""
        return asyncio.run(self._execute_multiple(test_cases))

    async def _execute_multiple(self, test_cases: List[TestCase]) -> List[TestResult]:
        """Execute multiple test cases"""
        results = []
        
        try:
            await self.setup_browser()
            
            for test_case in test_cases:
                result = await self.execute_test(test_case)
                results.append(result)
                
                # Brief pause between tests
                await asyncio.sleep(1)
                
        finally:
            await self.cleanup()
            
            
        return results