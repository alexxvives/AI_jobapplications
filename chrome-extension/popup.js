// Popup script for JobFlow Chrome Extension
class JobFlowPopup {
    constructor() {
        this.jobs = [];
        this.isApplying = false;
        this.currentJobIndex = 0;
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadJobsFromStorage();
        this.updateUI();
    }
    
    bindEvents() {
        document.getElementById('startApplyingBtn').addEventListener('click', () => {
            this.startApplying();
        });
        document.getElementById('stopApplyingBtn').addEventListener('click', () => {
            this.stopApplying();
        });
    }
    
    async loadJobsFromStorage() {
        try {
            const result = await chrome.storage.local.get('selectedJobs');
            this.jobs = result.selectedJobs || [];
            console.log('[JobFlow Popup] Loaded jobs from storage:', this.jobs);
            this.updateJobsList();
            this.updateUI();
        } catch (error) {
            console.error('Error loading jobs from storage:', error);
        }
    }
    
    startApplying() {
        if (this.jobs && this.jobs.length > 0) {
            chrome.runtime.sendMessage({
                action: 'startJobAutomation',
                jobs: this.jobs
            });
            this.isApplying = true;
            this.updateUI();
        }
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
            job.status = 'processing';
            this.updateJobsList();
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            if (tab) {
                await chrome.tabs.sendMessage(tab.id, {
                    action: 'applyToJob',
                    job: job
                });
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
            this.currentJobIndex++;
            setTimeout(() => {
                this.processNextJob();
            }, 1000);
        }
    }
    
    showError(message) {
        // Optionally show a toast or error message
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
        jobsListDiv.innerHTML = '';
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
        console.log('[JobFlow Popup] Displayed jobs:', this.jobs);
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
        const startApplyingBtn = document.getElementById('startApplyingBtn');
        const stopApplyingBtn = document.getElementById('stopApplyingBtn');
        if (this.jobs && this.jobs.length > 0) {
            startApplyingBtn.disabled = this.isApplying;
            startApplyingBtn.classList.toggle('hidden', this.isApplying);
            stopApplyingBtn.classList.toggle('hidden', !this.isApplying);
        } else {
            startApplyingBtn.disabled = true;
            startApplyingBtn.classList.remove('hidden');
            stopApplyingBtn.classList.add('hidden');
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