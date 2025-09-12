# News Intelligence Backend

A sophisticated news aggregation and personalization system powered by Gemini AI and advanced filtering algorithms.

## 🚀 Features

- **AI-Powered Personalization**: Gemini 2.5 Flash analysis for relevance scoring
- **Smart News Filtering**: Advanced query strategies and source credibility evaluation
- **Real-time Chat Interface**: Conversational news discovery with actual articles
- **OAuth Authentication**: Google and GitHub integration with JWT tokens
- **Ticker-Based Personalization**: Stock-focused news filtering
- **Rate Limit Resilience**: Graceful fallback to cached articles

## 📁 Project Structure

```
backend/
├── app.py                    # Main FastAPI application
├── news_intelligence.py     # Consolidated AI news service
├── auth.py                  # OAuth authentication
├── ticker_validator.py     # Stock ticker validation
├── database_utils.py       # Database utilities
├── test_suite.py           # Comprehensive test suite
├── requirements.txt        # Dependencies
├── .env                   # Environment variables
└── secure_news.db         # SQLite database
```

## 🛠️ Setup & Installation

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\\Scripts\\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file:

```env
# Required API Keys
NEWSAPI_KEY=your_newsapi_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Optional OAuth (for production)
GOOGLE_OAUTH_CLIENT_ID=your_google_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_google_client_secret
GITHUB_OAUTH_CLIENT_ID=your_github_client_id
GITHUB_OAUTH_CLIENT_SECRET=your_github_client_secret

# Database (optional, defaults to SQLite)
DATABASE_URL=sqlite:///./secure_news.db
```

### 3. Database Initialization

```bash
# Initialize database schema
python database_utils.py init

# Check database status
python database_utils.py stats
```

### 4. Run Application

```bash
# Start the backend server
python app.py

# Server will run on http://localhost:8004
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Full test suite
python test_suite.py

# The test suite covers:
# - Environment setup
# - News intelligence core
# - Chat functionality  
# - API endpoints
# - Database operations
# - Rate limiting handling
# - End-to-end workflows
```

## 📡 API Endpoints

### Core Endpoints
- `GET /api/articles` - Personalized news feed
- `GET /api/articles/top` - Top news articles
- `GET /api/articles/saved` - User's saved articles
- `POST /api/chat` - Conversational news interface

### User Management
- `GET /api/user` - User profile
- `POST /api/user` - Update user preferences
- `POST /api/interactions` - Track user interactions

### Authentication
- `GET /auth/google` - Google OAuth
- `GET /auth/github` - GitHub OAuth
- `POST /auth/demo-login` - Demo authentication

## 🏗️ Architecture

### News Intelligence Pipeline

1. **Smart Query Generation**: Advanced search strategies based on user tickers
2. **Content Fetching**: Multi-source news aggregation with rate limit handling
3. **AI Analysis**: Gemini-powered relevance scoring and quality assessment
4. **Personalization**: User preference matching and ticker-based filtering
5. **Caching & Fallback**: Database fallback for rate-limited scenarios

### Key Components

#### NewsIntelligenceService
- Unified service combining news fetching and AI analysis
- Handles NewsAPI integration and Gemini AI processing
- Provides personalized feeds and conversational chat

#### Authentication System
- OAuth 2.0 with Google and GitHub
- JWT token management with refresh tokens
- Demo mode for development

#### Database Schema
- Users with ticker preferences and interaction history
- Articles with AI-generated relevance scores and metadata
- User interactions for learning and personalization

## 🔧 Configuration

### Rate Limits
- NewsAPI: 100 requests/24h (free tier)
- Gemini API: 50 requests/day (free tier)
- Automatic fallback to cached articles when limits exceeded

### AI Model Settings
- Model: `gemini-2.0-flash-exp`
- Temperature: 0.3 (consistent filtering)
- Max tokens: 2048

### News Sources
Quality financial sources prioritized:
- Tier 1: Reuters, Bloomberg, WSJ, Financial Times
- Tier 2: CNBC, MarketWatch, Yahoo Finance
- Tier 3: Specialized publications and local news

## 🚨 Troubleshooting

### Common Issues

1. **No articles returned**
   - Check API rate limits
   - Verify environment variables
   - Database fallback should provide cached articles

2. **Database errors**
   - Run: `python database_utils.py init`
   - Check database file permissions

3. **Authentication issues**
   - Verify OAuth credentials in `.env`
   - Demo mode works without OAuth setup

### Debug Commands

```bash
# Check database status
python database_utils.py stats

# Test API endpoints
curl http://localhost:8004/api/articles

# Run tests
python test_suite.py
```

## 📊 Performance

- **Response Time**: < 2s for cached articles, < 10s for fresh AI analysis
- **Rate Limit Handling**: Graceful fallback to database cache
- **Memory Usage**: ~50MB with full article cache
- **Database Size**: ~200KB with 100 articles

## 🔐 Security

- JWT tokens with secure signing
- Environment-based secret management
- SQL injection protection via SQLAlchemy ORM
- Rate limiting on all endpoints

## 🤝 Contributing

1. Follow the existing code structure
2. Add tests for new functionality
3. Update documentation
4. Test with the comprehensive test suite

## 📄 License

MIT License - see LICENSE file for details