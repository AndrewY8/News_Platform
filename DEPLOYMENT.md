# AWS Elastic Beanstalk Backend Deployment Guide

This guide covers deploying the News Platform **Backend** to AWS Elastic Beanstalk with automatic GitHub deployment.

## 🏗️ Architecture Overview

- **Backend Platform**: Python 3.12 on AWS Elastic Beanstalk (FastAPI)
- **Frontend**: Next.js/React/TypeScript (deploy separately to Vercel/Netlify)
- **Database**: Supabase (PostgreSQL)
- **Deployment**: Backend automated via GitHub Actions, Frontend deployed separately

## 📋 Prerequisites

1. AWS Account with Elastic Beanstalk access
2. GitHub repository with this codebase
3. Supabase account and project setup
4. Required API keys:
   - NewsAPI key
   - Google Gemini API key
   - Supabase URL and Key
   - Optional: OAuth credentials (Google/GitHub)

## 🚀 Backend Deployment

### Option 1: Manual Backend Deployment

1. **Prepare backend deployment package**:
   ```bash
   python prepare_deployment.py
   ```

2. **Upload to Elastic Beanstalk**:
   - Go to [AWS Elastic Beanstalk Console](https://console.aws.amazon.com/elasticbeanstalk/)
   - Create new application: "news-platform-backend"
   - Choose "Python 3.12" platform
   - Upload the generated backend ZIP file

3. **Configure environment variables** (see section below)

### Option 2: Automatic GitHub Backend Deployment

1. **Set up GitHub Secrets**:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

2. **Update workflow configuration**:
   Edit `.github/workflows/deploy.yml`:
   ```yaml
   application_name: news-platform-backend
   environment_name: news-platform-backend-env
   region: your-aws-region
   ```

3. **Push to main branch** - backend deployment happens automatically!

## 🌐 Frontend Deployment (Separate)

Your Next.js/React/TypeScript frontend should be deployed to a platform that supports dynamic React applications:

### Recommended Platforms:
- **Vercel** (easiest for Next.js)
- **Netlify**
- **AWS Amplify**
- **Railway**

### Frontend Environment Variables:
Set in your frontend deployment platform:
```env
NEXT_PUBLIC_API_URL=https://your-backend.region.elasticbeanstalk.com
```

## ⚙️ Backend Environment Variables

Configure these in the Elastic Beanstalk console:

### Required
- `NEWSAPI_KEY`: Your NewsAPI.org API key
- `GEMINI_API_KEY`: Google Gemini API key
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon/public key
- `SECRET_KEY`: Secure random string for sessions
- `BACKEND_URL`: Your EB app URL (e.g., `https://yourapp.region.elasticbeanstalk.com`)

### Optional (for OAuth)
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GITHUB_OAUTH_CLIENT_ID`
- `GITHUB_OAUTH_CLIENT_SECRET`

## 📁 Deployment Files

- `application.py` - EB entry point
- `.ebextensions/` - EB configuration
- `.ebignore` - Files to exclude from deployment
- `Procfile` - Process configuration
- `.github/workflows/deploy.yml` - GitHub Actions workflow

## 🔧 Configuration Details

### Backend Only Deployment
The FastAPI app serves API endpoints only. Frontend is deployed separately.

### Database
- Supabase PostgreSQL database (configured via environment variables)
- Persistent cloud database with built-in auth and real-time features
- Connection handled by supabase-py client

### Logging
- CloudWatch logs enabled for 7 days
- Application logs in `/var/log/news-platform/`

## 🔍 Troubleshooting

### Build Issues
```bash
# Test frontend build locally
cd frontend && npm run build

# Test backend locally
python backend/app.py
```

### Deployment Package Too Large
The deployment package must be < 512 MB. Common solutions:
- Ensure `node_modules` is excluded
- Remove test files and logs
- Check `.ebignore` configuration

### Environment Variable Issues
- Verify all required keys are set in EB console
- Check CloudWatch logs for startup errors
- Use EB CLI for debugging: `eb logs`

### Static Files Not Loading
- Confirm `frontend/out/` directory exists
- Check CORS configuration in `backend/app.py`
- Verify static file mounting in logs

## 📊 Monitoring

### Health Checks
- EB health dashboard shows application status
- Custom health check endpoint: `/health`

### CloudWatch Metrics
- CPU, memory, and request metrics
- Application logs for debugging
- 7-day log retention configured

## 🔒 Security

### HTTPS
- Enable HTTPS in EB configuration
- Update `BACKEND_URL` to use HTTPS
- Configure proper CORS origins

### Secrets Management
- Never commit API keys to repository
- Use EB environment variables
- Consider AWS Secrets Manager for production

## 🔄 Updates

### Automatic Updates (GitHub Actions)
- Push to `main` branch triggers deployment
- Build, test, and deploy automatically
- Version labeled with commit SHA

### Manual Updates
1. Run `prepare_deployment.py`
2. Upload new ZIP to EB console
3. Deploy to environment

## 📈 Scaling

### Auto Scaling
Configure in EB console:
- Min/max instances
- Scaling triggers (CPU, requests)
- Load balancer settings

### Database Scaling
For production:
- Migrate to RDS PostgreSQL
- Update `DATABASE_URL` environment variable
- Configure connection pooling

## 🆘 Support

### AWS Resources
- [Elastic Beanstalk Documentation](https://docs.aws.amazon.com/elasticbeanstalk/)
- [Python Platform Guide](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/create-deploy-python-apps.html)

### Application Issues
- Check CloudWatch logs
- Review GitHub Actions workflow logs
- Test locally with `python application.py`

---

**🎉 Congratulations!** Your News Platform should now be deployed and accessible at your Elastic Beanstalk URL.