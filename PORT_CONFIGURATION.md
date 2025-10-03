# Port Configuration Guide

This document explains the systematic port configuration for both development and production environments.

## Standard Ports

- **Frontend**: Always runs on port **3000**
- **Backend**: Always runs on port **8000**

## Development (Local)

### Running Locally (Outside Docker)

1. **Backend**:
   ```bash
   cd backend
   python run.py
   # Runs on http://localhost:8000
   ```

2. **Frontend**:
   ```bash
   cd frontend
   npm run dev
   # Runs on http://localhost:3000
   # Connects to backend at http://localhost:8000
   ```

Configuration:
- Frontend uses `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Backend runs on port 8000 (configurable via `PORT` env var)

### Running with Docker (Development)

```bash
docker compose up -d
```

Configuration:
- Frontend runs on `http://localhost:3000`
  - **Browser JavaScript**: Connects to `http://localhost:8000` (NEXT_PUBLIC_API_URL)
  - **Note**: Browser cannot resolve Docker container names, must use localhost
- Backend runs on `http://localhost:8000`
  - **Inside Docker**: Container exposes port 8000
  - **From host/browser**: Accessible at `http://localhost:8000`

**Important**: `NEXT_PUBLIC_*` environment variables are embedded in the browser JavaScript bundle, so they must use URLs accessible from the browser (localhost for dev, or public IP/domain for production).

## Production (AWS/Server)

### Using Docker Compose

```bash
# Set your production URLs (replace with your actual server IP or domain)
export NEXT_PUBLIC_API_URL=http://your-server-ip:8000
export FRONTEND_URL=http://your-server-ip:3000

# Use production compose file
docker compose -f docker-compose.prod.yml up -d
```

Configuration in `.env`:
```bash
PORT=8000
FRONTEND_URL=http://your-server-ip:3000
NEWSAPI_KEY=your_key
GEMINI_API_KEY=your_key
```

**Critical**: Set `NEXT_PUBLIC_API_URL` to your server's public IP or domain before building, as it gets baked into the frontend bundle.

### Environment Variables

#### Frontend
- `NEXT_PUBLIC_API_URL`: URL where backend is accessible
  - Local dev: `http://localhost:8000`
  - Docker (internal): `http://backend:8000`
  - Production: Set in docker-compose.yml

#### Backend
- `PORT`: Port to run backend on (default: 8000)
- `FRONTEND_URL`: Frontend URL for CORS (e.g., `http://localhost:3000` or `http://your-domain.com:3000`)

## How It Works

### Docker Networking (Important!)

When running in Docker:
1. **Frontend container** runs Next.js server on port 3000
2. **Browser** (running on host) loads frontend from `http://localhost:3000`
3. **Browser JavaScript** makes API calls to `NEXT_PUBLIC_API_URL` (must be localhost or public IP, NOT container names)
4. **Backend** allows CORS from the `FRONTEND_URL` environment variable
5. Host machine can access:
   - Frontend: `http://localhost:3000`
   - Backend: `http://localhost:8000`

**Why localhost?** Browsers run on your host machine (not inside Docker), so they can't resolve Docker container names like `backend`. They need to use `localhost` or a public IP/domain.

### Browser Connections

1. User opens `http://localhost:3000` (or production URL)
2. Browser loads frontend from Next.js server
3. Frontend JavaScript makes API calls to `NEXT_PUBLIC_API_URL`
4. Backend receives requests and validates CORS based on `FRONTEND_URL`

## Troubleshooting

### CORS Errors

If you see CORS errors:
1. Check `FRONTEND_URL` in backend `.env` matches where you're accessing the frontend
2. Verify backend CORS origins include your frontend URL
3. Check browser console for the exact origin being rejected

### Connection Refused

If frontend can't connect to backend:
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check `NEXT_PUBLIC_API_URL` in frontend configuration
3. In Docker, verify both containers are on the same network: `docker network inspect news_platform_default`

### Wrong Port

If services are on unexpected ports:
1. Check `docker compose ps` to see actual port mappings
2. Verify `PORT` environment variable in backend
3. Check for conflicting services using `lsof -i :8000` and `lsof -i :3000`

## Migration from Old Configuration

If you were using port 8004:

1. Update any hardcoded `8004` references to `8000`
2. Update `.env.local` to use `NEXT_PUBLIC_API_URL=http://localhost:8000`
3. Rebuild Docker containers: `docker compose down && docker compose up -d --build`

## Quick Reference

| Environment | Frontend URL | Backend URL | Frontend → Backend |
|------------|--------------|-------------|-------------------|
| Local Dev | http://localhost:3000 | http://localhost:8000 | http://localhost:8000 |
| Docker Dev | http://localhost:3000 | http://localhost:8000 | http://backend:8000 |
| Production | http://server-ip:3000 | http://server-ip:8000 | http://backend:8000 |
