#!/bin/bash

# Frontend startup script for News Agent
cd "$(dirname "$0")/frontend"

echo "🚀 Starting News Agent Frontend..."
echo "=================================="

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies. Trying with legacy peer deps..."
        npm install --legacy-peer-deps
        if [ $? -ne 0 ]; then
            echo "❌ Installation failed. Please check the error messages above."
            exit 1
        fi
    fi
    echo "✅ Dependencies installed successfully"
else
    echo "✅ Dependencies already installed"
fi

# Check if Next.js is available
if ! command -v next &> /dev/null && [ ! -f "node_modules/.bin/next" ]; then
    echo "❌ Next.js not found. Reinstalling dependencies..."
    rm -rf node_modules package-lock.json
    npm install --legacy-peer-deps
fi

echo "🌐 Starting development server on http://localhost:3000"
echo "🛑 Press Ctrl+C to stop the server"
echo "=================================="

# Start the development server
npm run dev
