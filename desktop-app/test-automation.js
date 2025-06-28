const JobAutomation = require('./jobAutomation');

async function testRealTimeAutomation() {
    console.log('🧪 Testing Real-Time Job Automation...\n');
    
    const automation = new JobAutomation();
    
    // Mock jobs for testing
    const testJobs = [
        {
            id: 1,
            title: 'Software Engineer',
            company: 'Test Company 1',
            link: 'https://example.com/job1',
            status: 'pending'
        },
        {
            id: 2,
            title: 'Frontend Developer',
            company: 'Test Company 2',
            link: 'https://example.com/job2',
            status: 'pending'
        }
    ];
    
    // Mock progress callback
    const progressCallback = (progress) => {
        console.log(`📊 Progress Update:`);
        console.log(`   Status: ${progress.status}`);
        console.log(`   Message: ${progress.message || 'No message'}`);
        if (progress.currentJob) {
            console.log(`   Current Job: ${progress.currentJob.title} at ${progress.currentJob.company}`);
        }
        console.log(`   Progress: ${progress.currentIndex + 1}/${progress.totalJobs}\n`);
    };
    
    try {
        console.log('🚀 Starting automation test...');
        console.log('📱 Browser window will open to show real-time automation');
        console.log('👀 Watch as forms are filled automatically with visual highlights\n');
        
        await automation.startApplying(testJobs, progressCallback);
        
        console.log('✅ Test completed successfully!');
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
    } finally {
        await automation.cleanup();
    }
}

// Run test if this file is executed directly
if (require.main === module) {
    testRealTimeAutomation();
}

module.exports = { testRealTimeAutomation }; 