const { ipcRenderer } = require('electron');

// DOM elements
const sessionIdInput = document.getElementById('sessionId');
const connectBtn = document.getElementById('connectBtn');
const connectionStatus = document.getElementById('connectionStatus');
const connectionText = document.getElementById('connectionText');
const startApplyingBtn = document.getElementById('startApplyingBtn');
const stopApplyingBtn = document.getElementById('stopApplyingBtn');
const progressContainer = document.getElementById('progressContainer');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const jobsList = document.getElementById('jobsList');

// Real-time status elements
const realTimeStatus = document.getElementById('realTimeStatus');
const statusMessage = document.getElementById('statusMessage');
const statusDetails = document.getElementById('statusDetails');

// Profile form elements
const firstNameInput = document.getElementById('firstName');
const lastNameInput = document.getElementById('lastName');
const emailInput = document.getElementById('email');
const phoneInput = document.getElementById('phone');
const selectResumeBtn = document.getElementById('selectResumeBtn');
const saveProfileBtn = document.getElementById('saveProfileBtn');

// State
let isConnected = false;
let isApplying = false;
let jobs = [];

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadUserProfile();
    setupEventListeners();
    setupIpcListeners();
});

function setupEventListeners() {
    // Connect to backend
    connectBtn.addEventListener('click', async () => {
        const sessionId = sessionIdInput.value.trim();
        if (!sessionId) {
            console.error('❌ Please enter a session ID');
            return;
        }
        
        await connectToBackend(sessionId);
    });
    
    // Start applying
    startApplyingBtn.addEventListener('click', async () => {
        if (jobs.length === 0) {
            console.error('❌ No jobs to apply to');
            return;
        }
        
        await startApplying();
    });
    
    // Stop applying
    stopApplyingBtn.addEventListener('click', async () => {
        await stopApplying();
    });
    
    // Select resume
    selectResumeBtn.addEventListener('click', async () => {
        await selectResume();
    });
    
    // Save profile
    saveProfileBtn.addEventListener('click', async () => {
        await saveProfile();
    });
}

function setupIpcListeners() {
    // Listen for application progress updates
    ipcRenderer.on('application-progress', (event, progress) => {
        updateProgress(progress);
    });
}

async function connectToBackend(sessionId) {
    try {
        setConnectionStatus('processing', 'Connecting...');
        
        const result = await ipcRenderer.invoke('connect-to-backend', sessionId);
        
        if (result.success) {
            jobs = result.jobs;
            isConnected = true;
            setConnectionStatus('connected', `Connected (${jobs.length} jobs)`);
            updateJobsList();
            startApplyingBtn.disabled = false;
            console.log(`✅ Successfully connected! Loaded ${jobs.length} jobs.`);
        } else {
            setConnectionStatus('disconnected', 'Connection failed');
            console.error(`❌ Connection failed: ${result.error}`);
        }
    } catch (error) {
        setConnectionStatus('disconnected', 'Connection failed');
        console.error(`❌ Connection error: ${error.message}`);
    }
}

async function startApplying() {
    try {
        isApplying = true;
        startApplyingBtn.disabled = true;
        stopApplyingBtn.disabled = false;
        progressContainer.classList.remove('hidden');
        realTimeStatus.classList.remove('hidden'); // Show real-time status
        
        console.log('🚀 Starting job applications... Browser window will open to show automation in real-time!');
        
        const result = await ipcRenderer.invoke('start-applying', jobs);
        
        if (result.success) {
            console.log('✅ Job applications completed successfully!');
        } else {
            console.error(`❌ Application failed: ${result.error}`);
        }
    } catch (error) {
        console.error(`❌ Application error: ${error.message}`);
    } finally {
        isApplying = false;
        startApplyingBtn.disabled = false;
        stopApplyingBtn.disabled = true;
        progressContainer.classList.add('hidden');
        // Keep real-time status visible for a while to show completion
        setTimeout(() => {
            realTimeStatus.classList.add('hidden');
        }, 5000);
    }
}

async function stopApplying() {
    try {
        const result = await ipcRenderer.invoke('stop-applying');
        
        if (result.success) {
            console.log('⏹️ Stopping job applications...');
        } else {
            console.error(`❌ Stop failed: ${result.error}`);
        }
    } catch (error) {
        console.error(`❌ Stop error: ${error.message}`);
    }
}

async function selectResume() {
    try {
        const result = await ipcRenderer.invoke('select-resume');
        
        if (result.success) {
            console.log(`📄 Resume selected: ${result.filePath}`);
        } else {
            console.error(`❌ Resume selection failed: ${result.error}`);
        }
    } catch (error) {
        console.error(`❌ Resume selection error: ${error.message}`);
    }
}

async function loadUserProfile() {
    try {
        const result = await ipcRenderer.invoke('get-user-profile');
        
        if (result.success) {
            const profile = result.profile;
            firstNameInput.value = profile.firstName || '';
            lastNameInput.value = profile.lastName || '';
            emailInput.value = profile.email || '';
            phoneInput.value = profile.phone || '';
        }
    } catch (error) {
        console.error('Error loading profile:', error);
    }
}

async function saveProfile() {
    try {
        const profile = {
            firstName: firstNameInput.value.trim(),
            lastName: lastNameInput.value.trim(),
            email: emailInput.value.trim(),
            phone: phoneInput.value.trim()
        };
        
        // Validate required fields
        if (!profile.firstName || !profile.lastName || !profile.email) {
            console.error('❌ Please fill in all required fields (First Name, Last Name, Email)');
            return;
        }
        
        const result = await ipcRenderer.invoke('update-user-profile', profile);
        
        if (result.success) {
            console.log('✅ Profile saved successfully!');
        } else {
            console.error(`❌ Profile save failed: ${result.error}`);
        }
    } catch (error) {
        console.error(`❌ Profile save error: ${error.message}`);
    }
}

function setConnectionStatus(status, text) {
    connectionStatus.className = `status-dot ${status}`;
    connectionText.textContent = text;
}

function updateProgress(progress) {
    if (progress.status === 'completed') {
        progressFill.style.width = '100%';
        progressText.textContent = progress.message || 'All applications completed!';
        progressText.className = 'text-green-600 font-semibold';
        
        // Update real-time status
        statusMessage.textContent = progress.message || 'All applications completed!';
        statusMessage.style.color = '#28a745';
        statusDetails.innerHTML = `
            <strong>Status:</strong> ✅ Completed<br>
            <strong>Total Jobs:</strong> ${progress.totalJobs} jobs processed<br>
            <strong>Browser:</strong> Will close in 5 seconds
        `;
        
        // Show completion log
        console.log('🎉 All job applications completed! Check the browser window to see the results.');
        
        // Re-enable start button after a delay
        setTimeout(() => {
            startApplyingBtn.disabled = false;
            stopApplyingBtn.disabled = true;
        }, 3000);
        
    } else if (progress.status === 'processing') {
        const percentage = ((progress.currentIndex + 1) / progress.totalJobs) * 100;
        progressFill.style.width = `${percentage}%`;
        
        // Show detailed progress information
        const currentJob = progress.currentJob;
        const message = progress.message || `Processing job ${progress.currentIndex + 1} of ${progress.totalJobs}`;
        
        progressText.innerHTML = `
            <div class="text-sm">
                <div class="font-semibold text-blue-600">${message}</div>
                ${currentJob ? `
                    <div class="text-xs text-gray-600 mt-1">
                        <strong>${currentJob.title}</strong> at <strong>${currentJob.company}</strong>
                    </div>
                ` : ''}
            </div>
        `;
        
        // Update real-time status
        statusMessage.textContent = message;
        statusMessage.style.color = '#007bff';
        statusDetails.innerHTML = `
            <strong>Current Job:</strong> ${currentJob ? currentJob.title : 'None'}<br>
            <strong>Company:</strong> ${currentJob ? currentJob.company : 'None'}<br>
            <strong>Progress:</strong> ${progress.currentIndex + 1}/${progress.totalJobs} jobs<br>
            <strong>Status:</strong> 🔄 Processing
        `;
        
        // Log progress updates
        console.log(`📊 Progress: ${message}`);
        if (currentJob) {
            console.log(`   Job: ${currentJob.title} at ${currentJob.company}`);
        }
        
        // Update job status in the list
        if (currentJob) {
            updateJobStatus(progress.currentIndex, 'processing');
        }
    }
}

function updateJobsList() {
    if (jobs.length === 0) {
        jobsList.innerHTML = '<p style="color: #666; text-align: center; padding: 40px;">No jobs selected</p>';
        return;
    }
    
    jobsList.innerHTML = jobs.map((job, index) => `
        <div class="job-item">
            <div class="job-info">
                <div class="job-title">${job.title}</div>
                <div class="job-company">${job.company}</div>
            </div>
            <div class="job-status ${job.status || 'pending'}">
                ${job.status || 'Pending'}
            </div>
        </div>
    `).join('');
}

function updateJobStatus(index, status) {
    const jobItems = jobsList.querySelectorAll('.job-item');
    if (jobItems[index]) {
        const statusElement = jobItems[index].querySelector('.job-status');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `job-status ${status}`;
        }
    }
}

// Handle window close
window.addEventListener('beforeunload', () => {
    if (isApplying) {
        return 'Job applications are still running. Are you sure you want to close?';
    }
}); 