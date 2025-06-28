const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const JobAutomation = require('./jobAutomation');

let mainWindow;
let jobAutomation;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true
    },
    icon: path.join(__dirname, 'assets/icon.png'),
    titleBarStyle: 'default',
    show: false
  });

  // Load the main HTML file
  mainWindow.loadFile('index.html');

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Handle window closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Open DevTools in development
  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools();
  }
}

// Initialize job automation
function initializeJobAutomation() {
  jobAutomation = new JobAutomation();
}

// IPC handlers for communication with renderer process
ipcMain.handle('connect-to-backend', async (event, sessionId) => {
  try {
    const jobs = await jobAutomation.connectToBackend(sessionId);
    return { success: true, jobs };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('start-applying', async (event, jobs) => {
  try {
    await jobAutomation.startApplying(jobs, (progress) => {
      mainWindow.webContents.send('application-progress', progress);
    });
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('stop-applying', async () => {
  try {
    await jobAutomation.stopApplying();
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('select-resume', async () => {
  try {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openFile'],
      filters: [
        { name: 'PDF Files', extensions: ['pdf'] },
        { name: 'Word Documents', extensions: ['doc', 'docx'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    });

    if (!result.canceled && result.filePaths.length > 0) {
      return { success: true, filePath: result.filePaths[0] };
    } else {
      return { success: false, error: 'No file selected' };
    }
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('get-user-profile', async () => {
  try {
    const profile = await jobAutomation.getUserProfile();
    return { success: true, profile };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('update-user-profile', async (event, profile) => {
  try {
    await jobAutomation.updateUserProfile(profile);
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// App event handlers
app.whenReady().then(() => {
  createWindow();
  initializeJobAutomation();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', async () => {
  if (jobAutomation) {
    await jobAutomation.cleanup();
  }
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
}); 