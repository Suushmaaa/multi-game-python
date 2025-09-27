const API_BASE = 'http://localhost:8000';

// DOM Elements
const statusElement = document.getElementById('current-status');
const generatedCount = document.getElementById('generated-count');
const selectedCount = document.getElementById('selected-count');
const executedCount = document.getElementById('executed-count');
const loadingElement = document.getElementById('loading');

const generateBtn = document.getElementById('generate-tests');
const rankBtn = document.getElementById('rank-tests');
const executeBtn = document.getElementById('execute-tests');
const viewResultsBtn = document.getElementById('view-results');
const resetBtn = document.getElementById('reset-session');
const refreshBtn = document.getElementById('refresh-status');

// Result display elements
const generateResult = document.getElementById('generate-result');
const rankResult = document.getElementById('rank-result');
const executeResult = document.getElementById('execute-result');
const resultsDisplay = document.getElementById('results-display');

// State
let currentSession = {
    status: 'idle',
    counts: { generated: 0, selected: 0, executed: 0 }
};

// Utility functions
function showLoading() {
    loadingElement.classList.remove('hidden');
}

function hideLoading() {
    loadingElement.classList.add('hidden');
}

function showResult(element, message, type = 'success') {
    element.innerHTML = message;
    element.className = `result ${type}`;
    element.style.display = 'block';
}

function updateUI() {
    // Update status display
    statusElement.textContent = currentSession.status;
    statusElement.className = currentSession.status;
    
    // Update counts
    generatedCount.textContent = currentSession.counts.generated;
    selectedCount.textContent = currentSession.counts.selected;
    executedCount.textContent = currentSession.counts.executed;
    
    // Update button states
    generateBtn.disabled = currentSession.status === 'generating';
    rankBtn.disabled = currentSession.status !== 'generated';
    executeBtn.disabled = currentSession.status !== 'ranked';
    viewResultsBtn.disabled = currentSession.status !== 'executed';
}

async function apiCall(endpoint, method = 'GET', data = null) {
    try {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

async function refreshStatus() {
    try {
        const status = await apiCall('/session-status');
        currentSession = status;
        updateUI();
    } catch (error) {
        console.error('Failed to refresh status:', error);
    }
}

async function generateTests() {
    showLoading();
    try {
        showResult(generateResult, 'Generating test cases...', 'info');
        
        const result = await apiCall('/generate-tests', 'POST');
        
        let message = `✅ ${result.message}\n\n`;
        message += `<div class="test-list">`;
        
        result.tests.slice(0, 5).forEach(test => {
            message += `<div class="test-item">
                <strong>${test.title}</strong><br>
                Type: ${test.test_type} | Priority: ${test.priority}
            </div>`;
        });
        
        if (result.tests.length > 5) {
            message += `<div class="test-item">... and ${result.tests.length - 5} more tests</div>`;
        }
        message += `</div>`;
        
        showResult(generateResult, message, 'success');
        await refreshStatus();
        
    } catch (error) {
        showResult(generateResult, `❌ Error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

async function rankTests() {
    showLoading();
    try {
        showResult(rankResult, 'Ranking and selecting tests...', 'info');
        
        const result = await apiCall('/rank-tests', 'POST');
        
        let message = `✅ ${result.message}\n\n`;
        message += `<div class="test-list">`;
        
        result.selected_tests.forEach((test, index) => {
            message += `<div class="test-item">
                <strong>#${index + 1}: ${test.title}</strong><br>
                Priority: ${test.priority} | Duration: ${test.estimated_duration}s
            </div>`;
        });
        message += `</div>`;
        
        showResult(rankResult, message, 'success');
        await refreshStatus();
        
    } catch (error) {
        showResult(rankResult, `❌ Error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

async function executeTests() {
    showLoading();
    try {
        showResult(executeResult, 'Executing selected tests...', 'info');
        
        const result = await apiCall('/execute-tests', 'POST');
        
        let message = `✅ ${result.message}\n\n`;
        message += `<div class="test-list">`;
        
        result.results.forEach(exec => {
            const statusIcon = exec.status === 'passed' ? '✅' : 
                             exec.status === 'failed' ? '❌' : '⚠️';
            message += `<div class="test-item">
                ${statusIcon} <strong>${exec.test_title}</strong><br>
                Status: ${exec.status} | ID: ${exec.execution_id}
            </div>`;
        });
        message += `</div>`;
        
        showResult(executeResult, message, 'success');
        await refreshStatus();
        
    } catch (error) {
        showResult(executeResult, `❌ Error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

async function viewResults() {
    try {
        const results = await apiCall('/execution-results');
        
        let message = `📊 <strong>Test Execution Summary</strong>\n\n`;
        
        const passed = results.filter(r => r.status === 'passed').length;
        const failed = results.filter(r => r.status === 'failed').length;
        const total = results.length;
        
        message += `<div style="margin-bottom: 15px;">
            <strong>Results:</strong> ${passed} passed, ${failed} failed, ${total} total<br>
            <strong>Success Rate:</strong> ${((passed/total) * 100).toFixed(1)}%
        </div>`;
        
        message += `<div class="test-list">`;
        results.forEach(result => {
            const statusIcon = result.status === 'passed' ? '✅' : '❌';
            message += `<div class="test-item">
                ${statusIcon} <strong>${result.test_case?.title || 'Test'}</strong><br>
                Status: ${result.status} | Agent: ${result.agent_id}
            </div>`;
        });
        message += `</div>`;
        
        showResult(resultsDisplay, message, 'info');
        
    } catch (error) {
        showResult(resultsDisplay, `❌ Error loading results: ${error.message}`, 'error');
    }
}

async function resetSession() {
    if (!confirm('Reset the current test session? This will clear all data.')) {
        return;
    }
    
    showLoading();
    try {
        await apiCall('/reset-session', 'POST');
        
        // Clear all result displays
        [generateResult, rankResult, executeResult, resultsDisplay].forEach(el => {
            el.style.display = 'none';
        });
        
        await refreshStatus();
        alert('Session reset successfully!');
        
    } catch (error) {
        alert(`Failed to reset session: ${error.message}`);
    } finally {
        hideLoading();
    }
}

// Event listeners
generateBtn.addEventListener('click', generateTests);
rankBtn.addEventListener('click', rankTests);
executeBtn.addEventListener('click', executeTests);
viewResultsBtn.addEventListener('click', viewResults);
resetBtn.addEventListener('click', resetSession);
refreshBtn.addEventListener('click', refreshStatus);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    refreshStatus();
    
    // Auto-refresh status every 5 seconds
    setInterval(refreshStatus, 5000);
});