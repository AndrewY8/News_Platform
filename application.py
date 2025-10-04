#!/usr/bin/env python3
"""
AWS Elastic Beanstalk application entry point for News Platform.
This file imports the FastAPI app from the backend module.
"""

import os
import sys

# Add the backend directory to Python path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# Import the FastAPI app from backend/app.py
from app import app as application

# This is the WSGI application that Elastic Beanstalk will use
# The variable name 'application' is required by Elastic Beanstalk

if __name__ == "__main__":
    import uvicorn
    # For local testing only
    uvicorn.run(application, host="0.0.0.0", port=8000)