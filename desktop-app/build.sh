#!/bin/bash

echo "Building JobFlow Desktop Application..."

echo "Installing dependencies..."
npm install

echo "Building for current platform..."
npm run build

echo "Build complete! Check the dist folder for the installer." 