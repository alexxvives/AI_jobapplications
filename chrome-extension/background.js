// Background service worker for JobFlow Chrome Extension

// Handle extension installation
chrome.runtime.onInstalled.addListener((details) => {
    if (details.reason === 'install') {
        console.log('JobFlow: Extension installed');
        
        // Set default settings
        chrome.storage.local.set({
            sessionId: null,
            isConnected: false,
            jobs: []
        });
    }
});

// Handle messages from content scripts and popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('JobFlow: Background received message:', message);
    
    switch (message.action) {
        case 'jobApplied':
            handleJobApplied(message);
            break;
        case 'getJobs':
            handleGetJobs(sendResponse);
            break;
        case 'updateJobStatus':
            handleUpdateJobStatus(message);
            break;
        default:
            console.log('JobFlow: Unknown message action:', message.action);
    }
    
    // Return true to indicate we'll send a response asynchronously
    return true;
});

// Handle job application completion
async function handleJobApplied(message) {
    try {
        const { jobId, status } = message;
        
        // Get current session ID
        const result = await chrome.storage.local.get('sessionId');
        const sessionId = result.sessionId;
        
        if (sessionId) {
            // Update status in backend
            const response = await fetch(`http://localhost:8000/chrome-extension/update-status/${sessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    job_id: jobId,
                    status: status
                })
            });
            
            if (response.ok) {
                console.log(`JobFlow: Successfully updated job ${jobId} status to ${status}`);
            } else {
                console.error(`JobFlow: Failed to update job ${jobId} status`);
            }
        }
    } catch (error) {
        console.error('JobFlow: Error handling job applied:', error);
    }
}

// Handle get jobs request
async function handleGetJobs(sendResponse) {
    try {
        const result = await chrome.storage.local.get('sessionId');
        const sessionId = result.sessionId;
        
        if (sessionId) {
            const response = await fetch(`http://localhost:8000/chrome-extension/jobs/${sessionId}`);
            
            if (response.ok) {
                const data = await response.json();
                sendResponse({ success: true, jobs: data.jobs });
            } else {
                sendResponse({ success: false, error: 'Failed to fetch jobs' });
            }
        } else {
            sendResponse({ success: false, error: 'No session ID' });
        }
    } catch (error) {
        console.error('JobFlow: Error getting jobs:', error);
        sendResponse({ success: false, error: error.message });
    }
}

// Handle job status update
async function handleUpdateJobStatus(message) {
    try {
        const { jobId, status } = message;
        
        // Update local storage
        const result = await chrome.storage.local.get('jobs');
        const jobs = result.jobs || [];
        
        const updatedJobs = jobs.map(job => {
            if (job.id === jobId) {
                return { ...job, status: status };
            }
            return job;
        });
        
        await chrome.storage.local.set({ jobs: updatedJobs });
        
        console.log(`JobFlow: Updated job ${jobId} status to ${status}`);
    } catch (error) {
        console.error('JobFlow: Error updating job status:', error);
    }
}

// Handle tab updates to inject content script when needed
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        // Check if we're on a supported job platform
        const supportedPlatforms = [
            'jobs.ashbyhq.com',
            'boards.greenhouse.io',
            'jobs.lever.co'
        ];
        
        const isSupportedPlatform = supportedPlatforms.some(platform => 
            tab.url.includes(platform)
        );
        
        if (isSupportedPlatform) {
            console.log(`JobFlow: Detected supported platform: ${tab.url}`);
            
            // Inject content script if not already injected
            chrome.scripting.executeScript({
                target: { tabId: tabId },
                files: ['content.js']
            }).catch(error => {
                // Content script might already be injected
                console.log('JobFlow: Content script injection error (likely already injected):', error);
            });
        }
    }
});

// Handle extension icon click
chrome.action.onClicked.addListener((tab) => {
    // Open popup when extension icon is clicked
    chrome.action.setPopup({ popup: 'popup.html' });
});

// Handle storage changes
chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === 'local') {
        console.log('JobFlow: Storage changed:', changes);
        
        // Handle session ID changes
        if (changes.sessionId) {
            const newSessionId = changes.sessionId.newValue;
            if (newSessionId) {
                console.log('JobFlow: New session ID set:', newSessionId);
            } else {
                console.log('JobFlow: Session ID cleared');
            }
        }
        
        // Handle jobs changes
        if (changes.jobs) {
            const newJobs = changes.jobs.newValue;
            console.log('JobFlow: Jobs updated:', newJobs?.length || 0, 'jobs');
        }
    }
});

// Handle extension startup
chrome.runtime.onStartup.addListener(() => {
    console.log('JobFlow: Extension started');
});

// Handle extension shutdown
chrome.runtime.onSuspend.addListener(() => {
    console.log('JobFlow: Extension suspended');
});

// Utility function to check if we're connected
async function isConnected() {
    try {
        const result = await chrome.storage.local.get('sessionId');
        return !!result.sessionId;
    } catch (error) {
        return false;
    }
}

// Utility function to get current jobs
async function getCurrentJobs() {
    try {
        const result = await chrome.storage.local.get('jobs');
        return result.jobs || [];
    } catch (error) {
        return [];
    }
}

// Export utility functions for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        isConnected,
        getCurrentJobs,
        handleJobApplied,
        handleGetJobs,
        handleUpdateJobStatus
    };
} 