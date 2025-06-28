const puppeteer = require('puppeteer');
const axios = require('axios');
const Store = require('electron-store');
const path = require('path');
const fs = require('fs');

class JobAutomation {
    constructor() {
        this.browser = null;
        this.page = null;
        this.isApplying = false;
        this.currentJobIndex = 0;
        this.jobs = [];
        this.sessionId = null;
        this.userProfile = null;
        this.resumePath = null;
        
        // Initialize storage
        this.store = new Store();
        
        // Load saved profile
        this.loadUserProfile();
    }
    
    async connectToBackend(sessionId) {
        try {
            this.sessionId = sessionId;
            
            // Fetch jobs from backend
            const response = await axios.get(`http://localhost:8000/chrome-extension/jobs/${sessionId}`);
            
            if (response.status === 200) {
                this.jobs = response.data.jobs.map(job => ({
                    ...job,
                    status: 'pending'
                }));
                
                console.log(`Connected to backend. Loaded ${this.jobs.length} jobs.`);
                return this.jobs;
            } else {
                throw new Error('Failed to fetch jobs from backend');
            }
        } catch (error) {
            console.error('Error connecting to backend:', error);
            throw new Error(`Failed to connect: ${error.message}`);
        }
    }
    
    async startApplying(jobs, progressCallback) {
        if (this.isApplying) {
            throw new Error('Already applying to jobs');
        }
        
        this.isApplying = true;
        this.currentJobIndex = 0;
        this.jobs = jobs;
        
        try {
            // Launch browser with visible window
            console.log('Launching browser for real-time automation...');
            await this.launchBrowser();
            
            // Process each job
            for (let i = 0; i < this.jobs.length && this.isApplying; i++) {
                this.currentJobIndex = i;
                const job = this.jobs[i];
                
                // Update progress
                progressCallback({
                    currentJob: job,
                    currentIndex: i,
                    totalJobs: this.jobs.length,
                    status: 'processing',
                    message: `Starting application to ${job.title} at ${job.company}...`
                });
                
                try {
                    console.log(`\n=== Applying to Job ${i + 1}/${this.jobs.length} ===`);
                    console.log(`Title: ${job.title}`);
                    console.log(`Company: ${job.company}`);
                    console.log(`URL: ${job.link}`);
                    
                    await this.applyToJob(job);
                    job.status = 'applied';
                    
                    // Update progress
                    progressCallback({
                        currentJob: job,
                        currentIndex: i,
                        totalJobs: this.jobs.length,
                        status: 'processing',
                        message: `Successfully applied to ${job.title}!`
                    });
                    
                    // Update backend
                    await this.updateJobStatus(job.id, 'applied');
                    
                } catch (error) {
                    console.error(`Error applying to job ${job.title}:`, error);
                    job.status = 'error';
                    job.error = error.message;
                    
                    // Update progress
                    progressCallback({
                        currentJob: job,
                        currentIndex: i,
                        totalJobs: this.jobs.length,
                        status: 'processing',
                        message: `Failed to apply to ${job.title}: ${error.message}`
                    });
                    
                    // Update backend
                    await this.updateJobStatus(job.id, 'error');
                }
                
                // Delay between jobs
                if (i < this.jobs.length - 1) {
                    progressCallback({
                        currentJob: job,
                        currentIndex: i,
                        totalJobs: this.jobs.length,
                        status: 'processing',
                        message: 'Waiting before next application...'
                    });
                    await this.delay(3000);
                }
            }
            
            progressCallback({
                status: 'completed',
                totalJobs: this.jobs.length,
                message: 'All applications completed!'
            });
            
        } catch (error) {
            console.error('Error in job application process:', error);
            throw error;
        } finally {
            this.isApplying = false;
            // Don't close browser immediately - let user see final results
            setTimeout(async () => {
                await this.closeBrowser();
            }, 5000);
        }
    }
    
    async stopApplying() {
        this.isApplying = false;
        console.log('Stopping job application process...');
    }
    
    async applyToJob(job) {
        console.log(`Applying to job: ${job.title} at ${job.company}`);
        
        try {
            // Navigate to job page with progress update
            await this.page.goto(job.link, { waitUntil: 'networkidle2' });
            
            // Add a small delay so user can see the page load
            await this.delay(1000);
            
            // Detect platform and apply accordingly
            const platform = this.detectPlatform(job.link);
            
            switch (platform) {
                case 'ashby':
                    await this.applyToAshby(job);
                    break;
                case 'greenhouse':
                    await this.applyToGreenhouse(job);
                    break;
                case 'lever':
                    await this.applyToLever(job);
                    break;
                default:
                    throw new Error(`Unsupported platform: ${platform}`);
            }
            
            console.log(`Successfully applied to ${job.title}`);
            
        } catch (error) {
            console.error(`Failed to apply to ${job.title}:`, error);
            throw error;
        }
    }
    
    async applyToAshby(job) {
        // Wait for application form to load
        await this.page.waitForSelector('form[data-testid="application-form"]', { timeout: 10000 });
        
        // Fill out the form
        await this.fillAshbyForm(job);
        
        // Submit the application
        await this.page.click('button[type="submit"]');
        
        // Wait for submission
        await this.page.waitForTimeout(3000);
    }
    
    async applyToGreenhouse(job) {
        // Wait for application form to load
        await this.page.waitForSelector('form[data-testid="application-form"]', { timeout: 10000 });
        
        // Fill out the form
        await this.fillGreenhouseForm(job);
        
        // Submit the application
        await this.page.click('button[type="submit"]');
        
        // Wait for submission
        await this.page.waitForTimeout(3000);
    }
    
    async applyToLever(job) {
        // Wait for application form to load
        await this.page.waitForSelector('form[data-testid="application-form"]', { timeout: 10000 });
        
        // Fill out the form
        await this.fillLeverForm(job);
        
        // Submit the application
        await this.page.click('button[type="submit"]');
        
        // Wait for submission
        await this.page.waitForTimeout(3000);
    }
    
    async fillAshbyForm(job) {
        const profile = this.userProfile || this.getDefaultProfile();
        
        console.log('Filling Ashby application form...');
        
        // Fill common fields with visual feedback
        await this.fillField('input[name="firstName"]', profile.firstName);
        await this.delay(500); // Small delay for visual feedback
        
        await this.fillField('input[name="lastName"]', profile.lastName);
        await this.delay(500);
        
        await this.fillField('input[name="email"]', profile.email);
        await this.delay(500);
        
        await this.fillField('input[name="phone"]', profile.phone);
        await this.delay(500);
        
        // Fill cover letter
        console.log('Generating and filling cover letter...');
        const coverLetter = this.generateCoverLetter(job, profile);
        await this.fillField('textarea[name="coverLetter"]', coverLetter);
        await this.delay(1000); // Longer delay for cover letter
        
        // Upload resume if available
        if (this.resumePath) {
            console.log('Uploading resume...');
            await this.uploadResume('input[type="file"]');
            await this.delay(2000); // Wait for upload
        }
        
        console.log('Ashby form filled successfully');
    }
    
    async fillGreenhouseForm(job) {
        const profile = this.userProfile || this.getDefaultProfile();
        
        // Fill common fields
        await this.fillField('input[name="first_name"]', profile.firstName);
        await this.fillField('input[name="last_name"]', profile.lastName);
        await this.fillField('input[name="email"]', profile.email);
        await this.fillField('input[name="phone"]', profile.phone);
        
        // Fill cover letter
        const coverLetter = this.generateCoverLetter(job, profile);
        await this.fillField('textarea[name="cover_letter"]', coverLetter);
        
        // Upload resume if available
        if (this.resumePath) {
            await this.uploadResume('input[name="resume"]');
        }
    }
    
    async fillLeverForm(job) {
        const profile = this.userProfile || this.getDefaultProfile();
        
        // Fill common fields
        await this.fillField('input[name="firstName"]', profile.firstName);
        await this.fillField('input[name="lastName"]', profile.lastName);
        await this.fillField('input[name="email"]', profile.email);
        await this.fillField('input[name="phone"]', profile.phone);
        
        // Fill cover letter
        const coverLetter = this.generateCoverLetter(job, profile);
        await this.fillField('textarea[name="coverLetter"]', coverLetter);
        
        // Upload resume if available
        if (this.resumePath) {
            await this.uploadResume('input[name="resume"]');
        }
    }
    
    async fillField(selector, value) {
        try {
            await this.page.waitForSelector(selector, { timeout: 5000 });
            
            // Highlight the field being filled
            await this.page.evaluate((sel) => {
                const element = document.querySelector(sel);
                if (element) {
                    element.style.border = '2px solid #667eea';
                    element.style.boxShadow = '0 0 10px rgba(102, 126, 234, 0.5)';
                    element.style.transition = 'all 0.3s ease';
                }
            }, selector);
            
            // Clear the field first
            await this.page.click(selector);
            await this.page.keyboard.down('Control');
            await this.page.keyboard.press('KeyA');
            await this.page.keyboard.up('Control');
            await this.page.keyboard.press('Backspace');
            
            // Type the value with human-like delays
            await this.page.type(selector, value, { delay: 50 }); // 50ms delay between characters
            
            // Remove highlighting after a delay
            setTimeout(async () => {
                await this.page.evaluate((sel) => {
                    const element = document.querySelector(sel);
                    if (element) {
                        element.style.border = '';
                        element.style.boxShadow = '';
                    }
                }, selector);
            }, 2000);
            
            console.log(`Filled field ${selector} with: ${value}`);
        } catch (error) {
            console.error(`Error filling field ${selector}:`, error);
            throw error;
        }
    }
    
    async uploadResume(selector) {
        try {
            const input = await this.page.$(selector);
            if (input && this.resumePath) {
                await input.uploadFile(this.resumePath);
                console.log(`Uploaded resume: ${this.resumePath}`);
            }
        } catch (error) {
            console.log('Could not upload resume:', error.message);
        }
    }
    
    generateCoverLetter(job, profile) {
        return `Dear Hiring Manager,

I am writing to express my interest in the ${job.title} position at ${job.company}.

Based on the job description, I believe my skills and experience align well with your requirements. I am excited about the opportunity to contribute to your team and help drive success at ${job.company}.

${profile.coverLetter || 'I am confident that my background and skills would make me a valuable addition to your organization.'}

Thank you for considering my application. I look forward to discussing how I can add value to your organization.

Best regards,
${profile.firstName} ${profile.lastName}`;
    }
    
    detectPlatform(url) {
        if (url.includes('jobs.ashbyhq.com')) return 'ashby';
        if (url.includes('boards.greenhouse.io')) return 'greenhouse';
        if (url.includes('jobs.lever.co')) return 'lever';
        return 'unknown';
    }
    
    async launchBrowser() {
        try {
            // Launch browser with visible window for real-time viewing
            this.browser = await puppeteer.launch({
                headless: false, // Show browser window
                defaultViewport: { width: 1280, height: 720 },
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            });
            
            this.page = await this.browser.newPage();
            
            // Set user agent to avoid detection
            await this.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
            
            // Enable console logging for debugging
            this.page.on('console', msg => {
                console.log('Browser Console:', msg.text());
            });
            
            console.log('Browser launched successfully');
        } catch (error) {
            console.error('Error launching browser:', error);
            throw error;
        }
    }
    
    async closeBrowser() {
        if (this.browser) {
            await this.browser.close();
            this.browser = null;
            this.page = null;
        }
    }
    
    async updateJobStatus(jobId, status) {
        try {
            if (this.sessionId) {
                await axios.post(`http://localhost:8000/chrome-extension/update-status/${this.sessionId}`, {
                    job_id: jobId,
                    status: status
                });
            }
        } catch (error) {
            console.error('Error updating job status:', error);
        }
    }
    
    async getUserProfile() {
        return this.userProfile || this.getDefaultProfile();
    }
    
    async updateUserProfile(profile) {
        this.userProfile = profile;
        this.store.set('userProfile', profile);
    }
    
    loadUserProfile() {
        this.userProfile = this.store.get('userProfile') || this.getDefaultProfile();
    }
    
    getDefaultProfile() {
        return {
            firstName: 'John',
            lastName: 'Doe',
            email: 'john.doe@example.com',
            phone: '+1234567890',
            coverLetter: 'I am confident that my background and skills would make me a valuable addition to your organization.'
        };
    }
    
    setResumePath(filePath) {
        this.resumePath = filePath;
    }
    
    async delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    async cleanup() {
        this.isApplying = false;
        await this.closeBrowser();
    }
}

module.exports = JobAutomation; 