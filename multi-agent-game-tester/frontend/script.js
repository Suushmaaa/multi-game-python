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
    session_id: null,
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
    generateBtn.disabled = currentSession.status !== 'idle' && currentSession.status !== 'failed' && currentSession.status !== 'completed';
    rankBtn.disabled = currentSession.status !== 'tests_generated';
    executeBtn.disabled = currentSession.status !== 'tests_selected';
    viewResultsBtn.disabled = currentSession.status !== 'completed';
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
            const errorDetail = await response.text();
            console.error('API Error Detail:', errorDetail);
            throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorDetail}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

async function refreshStatus() {
    if (!currentSession.session_id) {
        currentSession.status = 'idle';
        updateUI();
        return;
    }
    try {
        const status = await apiCall(`/api/session-status/${currentSession.session_id}`);
        currentSession.status = status.status;
        if (status.generated_count !== undefined) currentSession.counts.generated = status.generated_count;
        if (status.selected_count !== undefined) currentSession.counts.selected = status.selected_count;
        if (status.execution_summary && status.execution_summary.total_tests !== undefined) {
            currentSession.counts.executed = status.execution_summary.total_tests;
        }
        updateUI();
    } catch (error) {
        console.error('Failed to refresh status:', error);
    }
}

async function generateTests() {
    showLoading();
    try {
        showResult(generateResult, 'Generating test cases...', 'info');

        const gameUrl = document.getElementById('game-url')?.value || '';
        const data = {
            game_url: gameUrl,
            num_tests: 20,
            select_top: 10
        };
        const result = await apiCall('/api/generate-tests', 'POST', data);

        currentSession.session_id = result.session_id;
        currentSession.status = 'tests_generated';

        showResult(generateResult, `✅ ${result.message}`, 'success');
        await refreshStatus();

    } catch (error) {
        showResult(generateResult, `❌ Error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

async function rankTests() {
    if (!currentSession.session_id) {
        showResult(rankResult, '❌ No active session. Generate tests first.', 'error');
        return;
    }
    showLoading();
    try {
        showResult(rankResult, 'Ranking and selecting tests...', 'info');
        
        const result = await apiCall(`/api/rank-select/${currentSession.session_id}`, 'POST');
        
        showResult(rankResult, `✅ ${result.message}`, 'success');
        currentSession.status = 'tests_selected';
        await refreshStatus();
        
    } catch (error) {
        showResult(rankResult, `❌ Error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

async function executeTests() {
    if (!currentSession.session_id) {
        showResult(executeResult, '❌ No active session. Rank tests first.', 'error');
        return;
    }
    showLoading();
    try {
        showResult(executeResult, 'Executing selected tests...', 'info');
        
        const result = await apiCall(`/api/execute-tests/${currentSession.session_id}`, 'POST');
        
        showResult(executeResult, `✅ ${result.message}`, 'success');
        currentSession.status = 'executing';
        await refreshStatus();
        
    } catch (error) {
        showResult(executeResult, `❌ Error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

async function viewResults() {
    if (!currentSession.session_id) {
        showResult(resultsDisplay, '❌ No active session. Execute tests first.', 'error');
        return;
    }
    try {
        const report = await apiCall(`/api/report/${currentSession.session_id}`);
        
        let message = `📊 <strong>Test Execution Summary</strong><br><br>`;
        
        const exec_report = report.execution_report || report;
        const summary = exec_report.execution_summary;
        if (summary) {
            message += `
                Total Tests: ${summary.total_tests}<br>
                Passed: ${summary.passed}<br>
                Failed: ${summary.failed}<br>
                Success Rate: ${summary.success_rate}%<br>
                Total Duration: ${summary.total_duration}s
            <br><br>`;
        }
        
        const test_results = exec_report.test_results || [];
        if (test_results.length > 0) {
            message += `<div class="test-list">`;
            test_results.slice(0, 10).forEach(result => {  // Show top 10
                const statusIcon = result.status === 'passed' ? '✅' : '❌';
                message += `<div class="test-item">
                    ${statusIcon} <strong>${result.title}</strong><br>
                    Status: ${result.status} | Duration: ${result.duration}s | Executor: ${result.executor_id}
                    ${result.error_message ? `<br>Error: ${result.error_message}` : ''}
                </div>`;
            });
            if (test_results.length > 10) {
                message += `<div class="test-item">... and ${test_results.length - 10} more results</div>`;
            }
            message += `</div>`;
        } else {
            message += '<em>No test results available yet.</em>';
        }
        
        const analysis = report.analysis_report || report.analysis;
        if (analysis) {
            message += `<br><strong>Analysis Insights:</strong><br>`;
            analysis.actionable_insights?.forEach(insight => {
                message += `• ${insight}<br>`;
            });
        }
        
        showResult(resultsDisplay, message, 'info');
        
    } catch (error) {
        showResult(resultsDisplay, `❌ Error loading results: ${error.message}`, 'error');
    }
}

async function resetSession() {
    if (!currentSession.session_id || !confirm('Reset the current test session? This will clear all data.')) {
        return;
    }
    
    showLoading();
    try {
        await apiCall(`/api/session/${currentSession.session_id}`, 'DELETE');
        
        // Clear all result displays
        [generateResult, rankResult, executeResult, resultsDisplay].forEach(el => {
            el.style.display = 'none';
        });
        
        currentSession = {
            session_id: null,
            status: 'idle',
            counts: { generated: 0, selected: 0, executed: 0 }
        };
        updateUI();
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