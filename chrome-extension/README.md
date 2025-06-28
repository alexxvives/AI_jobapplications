# JobFlow Chrome Extension

A Chrome extension that automates job applications across multiple platforms including Ashby, Greenhouse, and Lever.

## Features

- **Multi-Platform Support**: Works with Ashby, Greenhouse, and Lever job boards
- **Session Management**: Connect to your JobFlow web app using a Session ID
- **Automated Applications**: Automatically fill out and submit job applications
- **Real-time Status**: Track application progress in real-time
- **Smart Form Detection**: Automatically detects and fills form fields
- **Cover Letter Generation**: Generates personalized cover letters

## Installation

### Prerequisites
- Google Chrome browser
- JobFlow web application running (backend at `http://localhost:8000`)
- Selected jobs from the JobFlow web app

### Steps

1. **Download the Extension**
   - Download the `chrome-extension` folder to your computer
   - Or clone the repository and navigate to the `chrome-extension` directory

2. **Open Chrome Extensions**
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode" in the top right corner

3. **Load the Extension**
   - Click "Load unpacked"
   - Select the `chrome-extension` folder
   - The extension should now appear in your extensions list

4. **Create Icons** (Optional)
   - Create icon files in the `icons/` directory:
     - `icon16.png` (16x16 pixels)
     - `icon32.png` (32x32 pixels)
     - `icon48.png` (48x48 pixels)
     - `icon128.png` (128x128 pixels)
   - See `icons/README.md` for detailed instructions

## Usage

### 1. Select Jobs in JobFlow Web App
1. Go to your JobFlow web application
2. Search for jobs
3. Select the jobs you want to apply to
4. Click "Start Applying"
5. Choose "Chrome Extension"
6. Copy the Session ID provided

### 2. Connect Extension
1. Click the JobFlow extension icon in Chrome
2. Paste your Session ID in the input field
3. Click "Connect"
4. Your selected jobs should appear in the list

### 3. Start Applying
1. Click "Start Applying" in the extension popup
2. The extension will automatically:
   - Navigate to each job's application page
   - Fill out the application form
   - Submit the application
   - Update the status

### 4. Monitor Progress
- Watch the real-time status updates in the extension popup
- Jobs will show as "Pending", "Processing", "Applied", or "Error"
- You can stop the process at any time by clicking "Stop Applying"

## Supported Platforms

### Ashby (`jobs.ashbyhq.com`)
- Automatically detects Ashby application forms
- Fills out personal information, cover letter, and resume upload
- Handles Ashby-specific form field names

### Greenhouse (`boards.greenhouse.io`)
- Supports Greenhouse application forms
- Fills out standard Greenhouse fields
- Handles Greenhouse-specific field naming conventions

### Lever (`jobs.lever.co`)
- Works with Lever application forms
- Fills out Lever-specific form fields
- Handles Lever's application flow

## Configuration

### Personal Information
The extension currently uses placeholder information:
- Name: John Doe
- Email: john.doe@example.com
- Phone: +1234567890

**To customize this information:**
1. Edit the `content.js` file
2. Update the values in the form filling functions
3. Reload the extension

### Cover Letter
The extension generates a basic cover letter template. To customize:
1. Edit the `generateCoverLetter()` function in `content.js`
2. Modify the template to match your preferences
3. Reload the extension

### Resume Upload
Currently, the extension logs that a resume upload is needed. To implement:
1. Add resume file handling in the `handleFileUpload()` function
2. Store resume file in extension storage
3. Create File objects for upload

## Troubleshooting

### Extension Not Loading
- Make sure Developer mode is enabled
- Check that all files are in the correct directory structure
- Verify the `manifest.json` file is valid

### Connection Issues
- Ensure your JobFlow backend is running at `http://localhost:8000`
- Check that the Session ID is correct
- Verify you're logged into the JobFlow web app

### Form Filling Issues
- Different job boards may have varying form structures
- Check the browser console for error messages
- The extension logs detailed information about form filling attempts

### Application Failures
- Some job boards may have anti-bot measures
- Check if the application form structure has changed
- Verify that all required fields are being filled

## Development

### File Structure
```
chrome-extension/
├── manifest.json          # Extension configuration
├── popup.html            # Extension popup interface
├── popup.js              # Popup functionality
├── content.js            # Content script for job pages
├── background.js         # Background service worker
├── icons/                # Extension icons
│   ├── icon16.png
│   ├── icon32.png
│   ├── icon48.png
│   └── icon128.png
└── README.md             # This file
```

### Making Changes
1. Edit the relevant files
2. Go to `chrome://extensions/`
3. Click the refresh icon on the JobFlow extension
4. Test your changes

### Debugging
- Open Chrome DevTools
- Check the Console tab for extension logs
- Use `console.log()` statements in your code
- Check the Extensions tab for background script logs

## Security Notes

- The extension only requests necessary permissions
- No sensitive data is stored in the extension
- All communication with the backend uses HTTPS (in production)
- Session IDs are temporary and expire

## Future Enhancements

- [ ] Custom user profile management
- [ ] Resume file upload support
- [ ] AI-powered cover letter generation
- [ ] Application tracking dashboard
- [ ] Support for more job platforms
- [ ] Advanced form field detection
- [ ] Application success rate analytics

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the browser console for error messages
3. Ensure all prerequisites are met
4. Verify the extension is properly installed

## License

This extension is part of the JobFlow project. See the main project license for details. 