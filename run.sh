#!/bin/bash

# CreditSeer Startup Script

echo "Starting CreditSeer..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "WARNING: .env file not found!"
    echo "Please create a .env file with:"
    echo "  OPENAI_API_KEY=your_key_here"
    echo "  OPENAI_MODEL=gpt-4o-mini"
    echo "  MAX_CHUNK_CHAR_LIMIT=150000"
    echo ""
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create uploads directory
mkdir -p uploads

# Start Flask server
echo ""
echo "Starting Flask server on http://localhost:5000"
echo "Open http://localhost:5000 in your browser to access CreditSeer"
echo ""
python app.py

