// Popup script for JobFlow Chrome Extension
class JobFlowPopup {
    constructor() {
        this.sessionId = null;
        this.jobs = [];
        this.isApplying = false;
        this.currentJobIndex = 0;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadStoredSession();
        this.updateUI();
    }
    
    bindEvents() {
        // Connect button
        document.getElementById('connectBtn').addEventListener('click', () => {
            this.connect();
        });
        
        // Disconnect button
        document.getElementById('disconnectBtn').addEventListener('click', () => {
            this.disconnect();
        });
        
        // Start applying button
        document.getElementById('startApplyingBtn').addEventListener('click', () => {
            this.startApplying();
        });
        
        // Stop applying button
        document.getElementById('stopApplyingBtn').addEventListener('click', () => {
            this.stopApplying();
        });
        
        // Session ID input
        document.getElementById('sessionId').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.connect();
            }
        });
    }
    
    async connect() {
        const sessionId = document.getElementById('sessionId').value.trim();
        
        if (!sessionId) {
            this.showError('Please enter a Session ID');
            return;
        }
        
        this.showLoading();
        
        try {
            // Fetch jobs from backend
            const response = await fetch(`http://localhost:8000/chrome-extension/jobs/${sessionId}`);
            
            if (!response.ok) {
                throw new Error('Failed to fetch jobs. Check your Session ID.');
            }
            
            const data = await response.json();
            
            this.sessionId = sessionId;
            this.jobs = data.jobs.map(job => ({
                ...job,
                status: 'pending'
            }));
            
            // Store session ID
            chrome.storage.local.set({ sessionId: sessionId });
            
            this.showConnected();
            this.updateJobsList();
            
        } catch (error) {
            console.error('Connection error:', error);
            this.showError(error.message);
        }
    }
    
    disconnect() {
        this.sessionId = null;
        this.jobs = [];
        this.isApplying = false;
        this.currentJobIndex = 0;
        
        // Clear stored session
        chrome.storage.local.remove('sessionId');
        
        this.showDisconnected();
        this.updateJobsList();
    }
    
    async startApplying() {
        if (this.jobs.length === 0) {
            this.showError('No jobs to apply to');
            return;
        }
        
        this.isApplying = true;
        this.currentJobIndex = 0;
        this.updateUI();
        
        // Start the application process
        this.processNextJob();
    }
    
    stopApplying() {
        this.isApplying = false;
        this.updateUI();
    }
    
    async processNextJob() {
        if (!this.isApplying || this.currentJobIndex >= this.jobs.length) {
            this.isApplying = false;
            this.updateUI();
            return;
        }
        
        const job = this.jobs[this.currentJobIndex];
        
        try {
            // Update job status to processing
            job.status = 'processing';
            this.updateJobsList();
            
            // Send message to content script to apply to this job
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            if (tab) {
                await chrome.tabs.sendMessage(tab.id, {
                    action: 'applyToJob',
                    job: job
                });
                
                // Wait a bit before processing next job
                setTimeout(() => {
                    this.currentJobIndex++;
                    this.processNextJob();
                }, 2000);
                
            } else {
                throw new Error('No active tab found');
            }
            
        } catch (error) {
            console.error('Error processing job:', error);
            job.status = 'error';
            this.updateJobsList();
            
            // Continue with next job
            this.currentJobIndex++;
            setTimeout(() => {
                this.processNextJob();
            }, 1000);
        }
    }
    
    async loadStoredSession() {
        try {
            const result = await chrome.storage.local.get('sessionId');
            if (result.sessionId) {
                document.getElementById('sessionId').value = result.sessionId;
                // Auto-connect if session ID is stored
                this.connect();
            }
        } catch (error) {
            console.error('Error loading stored session:', error);
        }
    }
    
    showLoading() {
        document.getElementById('status-disconnected').classList.add('hidden');
        document.getElementById('status-connected').classList.add('hidden');
        document.getElementById('status-loading').classList.remove('hidden');
    }
    
    showConnected() {
        document.getElementById('status-disconnected').classList.add('hidden');
        document.getElementById('status-loading').classList.add('hidden');
        document.getElementById('status-connected').classList.remove('hidden');
    }
    
    showDisconnected() {
        document.getElementById('status-loading').classList.add('hidden');
        document.getElementById('status-connected').classList.add('hidden');
        document.getElementById('status-disconnected').classList.remove('hidden');
    }
    
    showError(message) {
        this.showDisconnected();
        // You could add a toast notification here
        console.error(message);
    }
    
    updateJobsList() {
        const noJobsDiv = document.getElementById('noJobs');
        const jobsListDiv = document.getElementById('jobsList');
        
        if (this.jobs.length === 0) {
            noJobsDiv.classList.remove('hidden');
            jobsListDiv.classList.add('hidden');
            return;
        }
        
        noJobsDiv.classList.add('hidden');
        jobsListDiv.classList.remove('hidden');
        
        // Clear existing jobs
        jobsListDiv.innerHTML = '';
        
        // Add each job
        this.jobs.forEach((job, index) => {
            const jobElement = document.createElement('div');
            jobElement.className = 'job-item';
            
            const statusClass = this.getStatusClass(job.status);
            const statusText = this.getStatusText(job.status);
            
            jobElement.innerHTML = `
                <div class="job-title">${job.title}</div>
                <div class="job-company">${job.company}</div>
                <div class="job-status ${statusClass}">${statusText}</div>
            `;
            
            jobsListDiv.appendChild(jobElement);
        });
    }
    
    getStatusClass(status) {
        switch (status) {
            case 'pending': return 'status-pending';
            case 'applied': return 'status-applied';
            case 'error': return 'status-error';
            case 'processing': return 'status-pending';
            default: return 'status-pending';
        }
    }
    
    getStatusText(status) {
        switch (status) {
            case 'pending': return 'Pending';
            case 'applied': return 'Applied';
            case 'error': return 'Error';
            case 'processing': return 'Processing...';
            default: return 'Pending';
        }
    }
    
    updateUI() {
        const connectBtn = document.getElementById('connectBtn');
        const disconnectBtn = document.getElementById('disconnectBtn');
        const startApplyingBtn = document.getElementById('startApplyingBtn');
        const stopApplyingBtn = document.getElementById('stopApplyingBtn');
        const sessionIdInput = document.getElementById('sessionId');
        
        if (this.sessionId) {
            // Connected state
            connectBtn.classList.add('hidden');
            disconnectBtn.classList.remove('hidden');
            sessionIdInput.disabled = true;
            
            if (this.jobs.length > 0) {
                startApplyingBtn.disabled = this.isApplying;
                startApplyingBtn.classList.toggle('hidden', this.isApplying);
                stopApplyingBtn.classList.toggle('hidden', !this.isApplying);
            } else {
                startApplyingBtn.disabled = true;
                startApplyingBtn.classList.remove('hidden');
                stopApplyingBtn.classList.add('hidden');
            }
        } else {
            // Disconnected state
            connectBtn.classList.remove('hidden');
            disconnectBtn.classList.add('hidden');
            startApplyingBtn.classList.add('hidden');
            stopApplyingBtn.classList.add('hidden');
            sessionIdInput.disabled = false;
        }
    }
}

// Initialize popup when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new JobFlowPopup();
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'jobApplied') {
        // Update job status
        const jobId = message.jobId;
        const status = message.status;
        
        // You could update the UI here if needed
        console.log(`Job ${jobId} status updated to: ${status}`);
        
        sendResponse({ success: true });
    }
}); 