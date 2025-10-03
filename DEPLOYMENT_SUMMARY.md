# Deployment Summary - Port Configuration Fix

## ✅ Problem Solved

The port confusion between 8000/8004 and localhost/0.0.0.0 has been completely resolved. The application now works consistently across all environments.

## 🎯 Current Configuration

### Standard Ports (Universal)
- **Frontend**: Port 3000
- **Backend**: Port 8000

### Environment-Specific URLs

| Environment | Access Frontend | Frontend → Backend | Backend CORS |
|------------|----------------|-------------------|--------------|
| **Local Dev** | http://localhost:3000 | http://localhost:8000 | http://localhost:3000 |
| **Docker (Dev)** | http://localhost:3000 | http://localhost:8000 | http://localhost:3000 |
| **Production (AWS)** | http://SERVER_IP:3000 | http://SERVER_IP:8000 | http://SERVER_IP:3000 |

## 📝 Key Changes Made

### 1. Backend Updates
- [backend/app.py](backend/app.py:1106): Changed from `port=8004` to `port=int(os.getenv("PORT", "8000"))`
- [backend/app.py](backend/app.py:260-272): Dynamic CORS using `FRONTEND_URL` environment variable
- [backend/run.py](backend/run.py:66-77): Uses `PORT` environment variable

### 2. Frontend Updates
- [frontend/services/api.ts](frontend/services/api.ts:2): Default changed from `:8004` to `:8000`
- [frontend/.env.local](frontend/.env.local): Set to `http://localhost:8000`

### 3. Docker Configuration
- [docker-compose.yml](docker-compose.yml):
  - Backend: `8000:8000` (was confused before)
  - Frontend: `NEXT_PUBLIC_API_URL=http://localhost:8000` (browser-accessible)
  - Backend: Added `FRONTEND_URL` for CORS
  - Backend: Added `.env` file loading

### 4. New Files Created
- [.env.example](.env.example): Template for environment variables
- [docker-compose.prod.yml](docker-compose.prod.yml): Production configuration
- [PORT_CONFIGURATION.md](PORT_CONFIGURATION.md): Comprehensive documentation
- [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md): This file

## 🚀 How to Use

### Development (Local - No Docker)
```bash
# Terminal 1 - Backend
cd backend
python run.py
# Runs on http://localhost:8000

# Terminal 2 - Frontend
cd frontend
npm run dev
# Runs on http://localhost:3000
# Connects to http://localhost:8000
```

### Development (Docker)
```bash
# One command - everything works
docker compose up -d

# Access:
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

### Production (AWS/Server)
```bash
# Set your server's public IP or domain
export NEXT_PUBLIC_API_URL=http://YOUR_SERVER_IP:8000
export FRONTEND_URL=http://YOUR_SERVER_IP:3000

# Deploy
docker compose -f docker-compose.prod.yml up -d --build

# Access from browser:
# http://YOUR_SERVER_IP:3000
```

## 🔑 Critical Understanding

### Why Browser Needs localhost (Not Container Names)

**The Issue**:
- Docker containers can talk to each other using container names (`backend`, `frontend`)
- Browsers run on your host machine, NOT inside Docker
- Browsers cannot resolve Docker container names

**The Solution**:
- `NEXT_PUBLIC_API_URL` must use URLs accessible from the browser
- Development: `http://localhost:8000`
- Production: `http://your-server-ip:8000` or `http://your-domain.com:8000`

**What Happens**:
1. Browser loads frontend from `http://localhost:3000`
2. Next.js serves the page with JavaScript that has `NEXT_PUBLIC_API_URL` baked in
3. Browser JavaScript makes API calls to that URL
4. Browser connects directly to backend at `localhost:8000` (or server IP in production)

## 📋 Environment Variables Reference

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000  # For development
# Production: Set to http://YOUR_SERVER_IP:8000 before building
```

### Backend (.env)
```bash
PORT=8000
FRONTEND_URL=http://localhost:3000  # For development
# Production: Set to http://YOUR_SERVER_IP:3000

NEWSAPI_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

## 🧪 Testing

```bash
# Test backend
curl http://localhost:8000/api/articles

# Test frontend
curl http://localhost:3000

# Check if frontend can reach backend (from browser console)
fetch('http://localhost:8000/api/articles')
  .then(r => r.json())
  .then(console.log)
```

## 📦 Docker Commands Reference

```bash
# Start services
docker compose up -d

# Rebuild after code changes
docker compose up -d --build

# View logs
docker logs frontend
docker logs backend

# Stop services
docker compose down

# Full rebuild (no cache)
docker compose build --no-cache
docker compose up -d
```

## 🐛 Troubleshooting

### "ERR_NAME_NOT_RESOLVED" for http://backend:8000
**Problem**: Frontend trying to connect to container name
**Solution**: Check `NEXT_PUBLIC_API_URL` is set to `localhost:8000` or public IP

### CORS Errors
**Problem**: Backend rejecting requests from frontend
**Solution**: Verify `FRONTEND_URL` matches where you're accessing frontend from

### Connection Refused
**Problem**: Backend not running or on wrong port
**Solution**:
- Check backend is running: `docker logs backend`
- Verify port: `docker ps` should show `0.0.0.0:8000->8000/tcp`

### Frontend Shows Old API URL
**Problem**: Environment variable cached in build
**Solution**: Rebuild frontend: `docker compose up -d --build frontend`

## ✨ Benefits of New Configuration

✅ **Consistent**: Same ports everywhere (3000, 8000)
✅ **Predictable**: Works the same locally and in Docker
✅ **Documented**: Clear guidance in PORT_CONFIGURATION.md
✅ **Flexible**: Easy to switch between dev/prod with environment variables
✅ **Maintainable**: No more hardcoded 8004 confusion

## 📚 Additional Resources

- [PORT_CONFIGURATION.md](PORT_CONFIGURATION.md) - Detailed port configuration guide
- [.env.example](.env.example) - Environment variable template
- [docker-compose.prod.yml](docker-compose.prod.yml) - Production Docker setup

## 🎉 Status: READY FOR DEPLOYMENT

Your application is now configured correctly for both development and production environments!
