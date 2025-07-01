// Content script for JobFlow Chrome Extension
// This script runs on job application pages to automate the application process

class JobFlowContentScript {
    constructor() {
        this.currentJob = null;
        this.isApplying = false;
        
        this.init();
    }
    
    init() {
        // Listen for messages from popup
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
            if (message.action === 'applyToJob') {
                this.handleApplyToJob(message.job);
                sendResponse({ success: true });
            }
        });
        
        // Listen for message from background to fill job application
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
            if (message.action === 'fillJobApplication') {
                this.automateAshbyApplication();
                sendResponse({ success: true });
            }
        });
        
        // Detect if we're on a job application page
        this.detectJobPlatform();
        
        // Listen for form submission to notify background script
        window.addEventListener('submit', function(e) {
            if (e.target && e.target.matches('form')) {
                chrome.runtime.sendMessage({ action: 'jobSubmitted' });
            }
        }, true);

        console.log('[JobFlow Extension] Content script loaded');

        // Listen for messages from the web page
        window.addEventListener("message", function(event) {
            if (event.data && event.data.type === "JOBFLOW_PING") {
                console.log('[JobFlow Extension] Received JOBFLOW_PING from web app');
                window.postMessage({ type: "JOBFLOW_PONG" }, "*");
                console.log('[JobFlow Extension] Sent JOBFLOW_PONG to web app');
            }
            if (event.data && event.data.type === "JOBFLOW_START_APPLYING") {
                console.log('[JobFlow Extension] Received JOBFLOW_START_APPLYING with jobs:', event.data.jobs);
                chrome.storage.local.set({ selectedJobs: event.data.jobs }, () => {
                    console.log('[JobFlow Extension] Saved selected jobs to storage');
                });
                chrome.runtime.sendMessage({
                    action: "startApplying",
                    jobs: event.data.jobs
                });
            }
            // Listen for session ID transfer
            if (event.data && event.data.type === "JOBFLOW_SESSION_ID") {
                chrome.storage.local.set({ sessionId: event.data.sessionId });
                console.log('[JobFlow Extension] Session ID received and saved:', event.data.sessionId);
            }
        });
    }
    
    detectJobPlatform() {
        const url = window.location.href;
        
        if (url.includes('jobs.ashbyhq.com')) {
            this.platform = 'ashby';
        } else if (url.includes('boards.greenhouse.io')) {
            this.platform = 'greenhouse';
        } else if (url.includes('jobs.lever.co')) {
            this.platform = 'lever';
        } else {
            this.platform = 'unknown';
        }
        
        console.log(`JobFlow: Detected platform: ${this.platform}`);
    }
    
    async handleApplyToJob(job) {
        this.currentJob = job;
        this.isApplying = true;
        
        console.log(`JobFlow: Starting application for ${job.title} at ${job.company}`);
        
        try {
            // Wait for page to be fully loaded
            await this.waitForPageLoad();
            
            // Apply based on platform
            switch (this.platform) {
                case 'ashby':
                    await this.applyToAshby();
                    break;
                case 'greenhouse':
                    await this.applyToGreenhouse();
                    break;
                case 'lever':
                    await this.applyToLever();
                    break;
                default:
                    throw new Error(`Unsupported platform: ${this.platform}`);
            }
            
            // Update status to backend
            await this.updateJobStatus('applied');
            
        } catch (error) {
            console.error('JobFlow: Application error:', error);
            await this.updateJobStatus('error');
        } finally {
            this.isApplying = false;
        }
    }
    
    async waitForPageLoad() {
        return new Promise((resolve) => {
            if (document.readyState === 'complete') {
                resolve();
            } else {
                window.addEventListener('load', resolve);
            }
        });
    }
    
    async applyToAshby() {
        console.log('JobFlow: Applying to Ashby job');
        
        // Wait for the application form to load
        await this.waitForElement('form[data-testid="application-form"]', 10000);
        
        // Fill out the application form
        await this.fillAshbyForm();
        
        // Submit the application
        await this.submitAshbyApplication();
    }
    
    async applyToGreenhouse() {
        console.log('JobFlow: Applying to Greenhouse job');
        
        // Wait for the application form to load
        await this.waitForElement('form[data-testid="application-form"]', 10000);
        
        // Fill out the application form
        await this.fillGreenhouseForm();
        
        // Submit the application
        await this.submitGreenhouseApplication();
    }
    
    async applyToLever() {
        console.log('JobFlow: Applying to Lever job');
        
        // Wait for the application form to load
        await this.waitForElement('form[data-testid="application-form"]', 10000);
        
        // Fill out the application form
        await this.fillLeverForm();
        
        // Submit the application
        await this.submitLeverApplication();
    }
    
    async fillAshbyForm() {
        // Load user profile from storage
        let profile = null;
        try {
            const result = await chrome.storage.local.get('userProfile');
            profile = result.userProfile;
            if (profile) {
                console.log('[JobFlow Extension] Using real user profile for form filling:', profile);
            } else {
                console.log('[JobFlow Extension] No user profile found, using dummy data.');
            }
        } catch (e) {
            console.log('[JobFlow Extension] Error loading user profile, using dummy data.');
        }
        // Use real info if available, else fallback
        const fields = {
            'input[name="firstName"]': profile?.full_name?.split(' ')[0] || 'John',
            'input[name="lastName"]': profile?.full_name?.split(' ').slice(1).join(' ') || 'Doe',
            'input[name="email"]': profile?.email || 'john.doe@example.com',
            'input[name="phone"]': profile?.phone || '+1234567890',
            'textarea[name="coverLetter"]': 'I am excited to apply for this role!',
        };
        for (const [selector, value] of Object.entries(fields)) {
            await this.fillField(selector, value);
        }
    }
    
    async fillGreenhouseForm() {
        // Fill out common form fields
        await this.fillCommonFields();
        
        // Greenhouse-specific fields
        const fields = {
            'input[name="first_name"]': 'John',
            'input[name="last_name"]': 'Doe',
            'input[name="email"]': 'john.doe@example.com',
            'input[name="phone"]': '+1234567890',
            'textarea[name="cover_letter"]': this.generateCoverLetter(),
            'input[name="resume"]': this.getResumeFile()
        };
        
        for (const [selector, value] of Object.entries(fields)) {
            await this.fillField(selector, value);
        }
    }
    
    async fillLeverForm() {
        // Fill out common form fields
        await this.fillCommonFields();
        
        // Lever-specific fields
        const fields = {
            'input[name="firstName"]': 'John',
            'input[name="lastName"]': 'Doe',
            'input[name="email"]': 'john.doe@example.com',
            'input[name="phone"]': '+1234567890',
            'textarea[name="coverLetter"]': this.generateCoverLetter(),
            'input[name="resume"]': this.getResumeFile()
        };
        
        for (const [selector, value] of Object.entries(fields)) {
            await this.fillField(selector, value);
        }
    }
    
    async fillCommonFields() {
        // Fill out any common fields that might exist across platforms
        const commonFields = {
            'input[type="email"]': 'john.doe@example.com',
            'input[type="tel"]': '+1234567890',
            'input[placeholder*="name" i]': 'John Doe',
            'input[placeholder*="email" i]': 'john.doe@example.com'
        };
        
        for (const [selector, value] of Object.entries(commonFields)) {
            await this.fillField(selector, value);
        }
    }
    
    async fillField(selector, value) {
        try {
            const element = await this.waitForElement(selector, 5000);
            if (element) {
                // Clear the field first
                element.value = '';
                element.focus();
                
                // Fill the field
                if (element.type === 'file') {
                    // Handle file upload
                    this.handleFileUpload(element, value);
                } else {
                    // Handle text input
                    element.value = value;
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                }
                
                console.log(`JobFlow: Filled field ${selector} with ${value}`);
            }
        } catch (error) {
            console.log(`JobFlow: Could not fill field ${selector}:`, error.message);
        }
    }
    
    handleFileUpload(element, filePath) {
        // For now, we'll just log that we need to handle file upload
        // In a real implementation, you'd need to create a File object
        console.log(`JobFlow: File upload needed for ${filePath}`);
    }
    
    generateCoverLetter() {
        // Generate a basic cover letter based on the job
        return `Dear Hiring Manager,

I am writing to express my interest in the ${this.currentJob.title} position at ${this.currentJob.company}.

Based on the job description, I believe my skills and experience align well with your requirements. I am excited about the opportunity to contribute to your team and help drive success at ${this.currentJob.company}.

Thank you for considering my application. I look forward to discussing how I can add value to your organization.

Best regards,
John Doe`;
    }
    
    getResumeFile() {
        // Return a placeholder for resume file path
        // In a real implementation, this would be the actual resume file
        return '/path/to/resume.pdf';
    }
    
    async submitAshbyApplication() {
        const submitButton = await this.waitForElement('button[type="submit"]', 5000);
        if (submitButton) {
            submitButton.click();
            console.log('JobFlow: Submitted Ashby application');
        }
    }
    
    async submitGreenhouseApplication() {
        const submitButton = await this.waitForElement('button[type="submit"]', 5000);
        if (submitButton) {
            submitButton.click();
            console.log('JobFlow: Submitted Greenhouse application');
        }
    }
    
    async submitLeverApplication() {
        const submitButton = await this.waitForElement('button[type="submit"]', 5000);
        if (submitButton) {
            submitButton.click();
            console.log('JobFlow: Submitted Lever application');
        }
    }
    
    async waitForElement(selector, timeout = 5000) {
        return new Promise((resolve) => {
            const element = document.querySelector(selector);
            if (element) {
                resolve(element);
                return;
            }
            
            const observer = new MutationObserver(() => {
                const element = document.querySelector(selector);
                if (element) {
                    observer.disconnect();
                    resolve(element);
                }
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
            
            // Timeout
            setTimeout(() => {
                observer.disconnect();
                resolve(null);
            }, timeout);
        });
    }
    
    async updateJobStatus(status) {
        try {
            // Send message to popup to update status
            chrome.runtime.sendMessage({
                action: 'jobApplied',
                jobId: this.currentJob.id,
                status: status
            });
            
            console.log(`JobFlow: Updated job ${this.currentJob.id} status to ${status}`);
        } catch (error) {
            console.error('JobFlow: Error updating job status:', error);
        }
    }
    
    async automateAshbyApplication() {
        if (this.platform !== 'ashby') {
            console.log('[JobFlow Extension] Not an Ashby job page, skipping automation.');
            return;
        }
        console.log('[JobFlow Extension] Starting Ashby automation...');
        // Try to click the Apply button if present
        const applyBtn = document.querySelector('button, a[href*="apply"], a[data-testid*="apply"]');
        if (applyBtn) {
            console.log('[JobFlow Extension] Clicking Apply button...');
            applyBtn.click();
            await new Promise(r => setTimeout(r, 1500)); // Wait for form to appear
        } else {
            console.log('[JobFlow Extension] No Apply button found, assuming form is visible.');
        }
        // Wait for the Ashby application form
        await this.waitForElement('form[data-testid="application-form"]', 10000);
        console.log('[JobFlow Extension] Ashby form detected, filling fields...');
        // Fill the form with dummy data
        await this.fillAshbyForm();
        // Do NOT auto-submit; user must click submit
        console.log('[JobFlow Extension] Form filled. Waiting for user to submit...');
    }
}

// Initialize content script
new JobFlowContentScript(); 