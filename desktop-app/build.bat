@echo off
echo Building JobFlow Desktop Application...

echo Installing dependencies...
npm install

echo Building for Windows...
npm run build:win

echo Build complete! Check the dist folder for the installer.
pause 