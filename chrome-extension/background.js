// Background service worker for JobFlow Chrome Extension

// Set backend URL (change here if needed)
const BACKEND_URL = 'http://localhost:8000';

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
    let asyncHandled = false;
    switch (message.action) {
        case 'jobApplied':
            handleJobApplied(message).then(() => sendResponse({ success: true })).catch(e => sendResponse({ success: false, error: e.message }));
            asyncHandled = true;
            break;
        case 'getJobs':
            handleGetJobs(sendResponse);
            asyncHandled = true;
            break;
        case 'updateJobStatus':
            handleUpdateJobStatus(message).then(() => sendResponse({ success: true })).catch(e => sendResponse({ success: false, error: e.message }));
            asyncHandled = true;
            break;
        case 'startJobAutomation':
            automateJobs(message.jobs).then(() => sendResponse({ success: true })).catch(e => sendResponse({ success: false, error: e.message }));
            asyncHandled = true;
            break;
        default:
            console.log('JobFlow: Unknown message action:', message.action);
            sendResponse({ success: false, error: 'Unknown action' });
    }
    // Return true if we handled async
    return asyncHandled;
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
            const response = await fetch(`${BACKEND_URL}/chrome-extension/update-status/${sessionId}`, {
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
            const response = await fetch(`${BACKEND_URL}/chrome-extension/jobs/${sessionId}`);
            
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
                // Fetch user profile from backend
                fetchUserProfile();
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

async function automateJobs(jobs) {
    for (const job of jobs) {
        // Open job link in a new tab
        const tab = await chrome.tabs.create({ url: job.link, active: true });
        // Wait for the tab to finish loading
        await waitForTabLoad(tab.id);
        // Send candidate info to content script
        await chrome.tabs.sendMessage(tab.id, {
            action: 'fillJobApplication',
            candidateInfo: job.candidateInfo
        });
        // Notify user that the job is ready for review
        chrome.notifications.create({
            type: 'basic',
            iconUrl: 'icons/icon48.png',
            title: 'JobFlow: Review Application',
            message: 'Please review and submit your application for this job.'
        });
        // Wait for the user to submit (content script can send a message back when done)
        await waitForUserSubmission(tab.id);
        // Leave the tab open and move to the next job
    }
}

function waitForTabLoad(tabId) {
    return new Promise((resolve) => {
        function checkTab() {
            chrome.tabs.get(tabId, (tab) => {
                if (tab.status === 'complete') {
                    resolve();
                } else {
                    setTimeout(checkTab, 500);
                }
            });
        }
        checkTab();
    });
}

function waitForUserSubmission(tabId) {
    return new Promise((resolve) => {
        function onMessage(message, sender) {
            if (sender.tab && sender.tab.id === tabId && message.action === 'jobSubmitted') {
                chrome.runtime.onMessage.removeListener(onMessage);
                resolve();
            }
        }
        chrome.runtime.onMessage.addListener(onMessage);
    });
}

async function fetchUserProfile() {
    try {
        // Get token from storage if needed, or use session
        const result = await chrome.storage.local.get('sessionId');
        const sessionId = result.sessionId;
        // Assume token is not needed for /profile (if needed, add logic)
        const response = await fetch(`${BACKEND_URL}/profile`, {
            credentials: 'include'
        });
        if (response.ok) {
            const profile = await response.json();
            await chrome.storage.local.set({ userProfile: profile });
            console.log('JobFlow: User profile fetched and saved:', profile);
        } else {
            console.error('JobFlow: Failed to fetch user profile');
        }
    } catch (error) {
        console.error('JobFlow: Error fetching user profile:', error);
    }
} 