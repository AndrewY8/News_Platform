#!/usr/bin/env python3
"""
Minimal AWS Elastic Beanstalk application for testing deployment
"""

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "healthy", "message": "Minimal app running"}

@app.get("/health")
def health():
    return {"status": "ok"}

# This is the WSGI application that Elastic Beanstalk will use
application = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(application, host="0.0.0.0", port=8000)