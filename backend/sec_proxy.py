#!/usr/bin/env python3
"""
SEC Proxy - Routes SEC API calls from main backend to SEC server
This adds SEC endpoints to the main backend by proxying to the SEC server
"""

import requests
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
import httpx

SEC_SERVER_URL = "http://localhost:8005"

async def proxy_sec_request(request: Request, path: str):
    """Proxy request to SEC server"""
    try:
        # Get the request method and body
        method = request.method
        url = f"{SEC_SERVER_URL}{path}"
        
        # Get headers (excluding host-related headers)
        headers = {
            key: value for key, value in request.headers.items() 
            if key.lower() not in ['host', 'content-length']
        }
        
        # Get query parameters
        params = dict(request.query_params)
        
        # Get request body if it exists
        body = None
        if method in ['POST', 'PUT', 'PATCH']:
            body = await request.body()
        
        # Make the proxied request
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                content=body
            )
            
            # Return the response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

# This will be imported into the main app.py
def add_sec_proxy_routes(app: FastAPI):
    """Add SEC proxy routes to the main FastAPI app"""
    
    @app.post("/api/sec/search")
    async def proxy_sec_search(request: Request):
        """Proxy SEC search requests"""
        return await proxy_sec_request(request, "/api/sec/search")
    
    @app.get("/api/sec/document/{doc_id}")
    async def proxy_sec_document(request: Request, doc_id: str):
        """Proxy SEC document requests"""
        return await proxy_sec_request(request, f"/api/sec/document/{doc_id}")
    
    @app.get("/api/sec/company/{ticker}")
    async def proxy_sec_company(request: Request, ticker: str):
        """Proxy SEC company requests"""
        return await proxy_sec_request(request, f"/api/sec/company/{ticker}")