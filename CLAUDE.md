# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

News Platform is a full-stack financial news intelligence application with AI-powered personalization. It consists of a Next.js frontend (React/TypeScript) and a FastAPI backend (Python) with Gemini AI integration for news analysis and user interaction.

## Development Commands

### Frontend (Next.js/React)
```bash
# Start development server
cd frontend && npm run dev

# Quick start with startup script
./start_frontend.sh

# Build for production
cd frontend && npm run build

# Lint code
cd frontend && npm run lint
```

### Backend (FastAPI/Python)
```bash
# Start development server
cd backend && python app.py

# Quick start with startup script
./start_backend.sh

# Initialize database
cd backend && python database_utils.py init

# Check database status
cd backend && python database_utils.py stats

# Run comprehensive tests
cd backend && python test_suite.py
```

## Architecture Overview

### Frontend Structure (`frontend/`)
- **Main App**: `app/app.tsx` - Single-page application with navigation, news feed, chat, and market data
- **Services**: `services/api.ts` - Centralized API communication with backend
- **UI Components**: `components/ui/` - Radix UI components with shadcn/ui styling
- **Yahoo Finance Service**: `services/yahooFinance.ts` - Real-time stock data integration

### Backend Structure (`backend/`)
- **Main FastAPI App**: `app.py` - Core API endpoints and application logic
- **News Intelligence**: `news_intelligence.py` - Gemini AI-powered news analysis and personalization
- **Authentication**: `auth.py` - OAuth (Google/GitHub) and JWT token management
- **SEC Integration**: `sec_service.py`, `sec_api_server.py` - SEC document parsing and search
- **Database**: `database_utils.py` - SQLite database operations and utilities

### Key Integration Points

**News Flow**:
1. Frontend requests news via `/api/articles` with user tickers
2. Backend uses NewsIntelligenceService to fetch from NewsAPI
3. Gemini AI analyzes relevance and filters content
4. Personalized articles returned based on user preferences

**Chat System**:
1. User sends query through floating chat interface
2. Backend processes with Gemini AI via `/api/chat`
3. AI returns response and suggested articles
4. Articles dynamically inserted into news feed with animations

**Market Data**:
1. Frontend fetches real-time stock data via Yahoo Finance service
2. Ticker management integrated with user preferences
3. Chart data rendered using Chart.js/Recharts

## Environment Configuration

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8004
```

### Backend (.env)
```env
NEWSAPI_KEY=your_newsapi_key
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_OAUTH_CLIENT_ID=optional
GOOGLE_OAUTH_CLIENT_SECRET=optional
GITHUB_OAUTH_CLIENT_ID=optional
GITHUB_OAUTH_CLIENT_SECRET=optional
DATABASE_URL=sqlite:///./secure_news.db
```

## Key Features & Components

### Navigation System
- **Multi-column Dropdown**: Business news navigation with categorized industry sections
- **Hover Functionality**: Enhanced UX with smooth transitions and organized content display
- **Responsive Design**: Works across desktop and mobile viewports

### News Intelligence Pipeline
1. **Smart Query Generation**: Advanced search strategies based on user tickers and preferences
2. **Multi-source Aggregation**: NewsAPI integration with rate limit handling and fallback caching
3. **AI-Powered Analysis**: Gemini 2.0 Flash for relevance scoring and content quality assessment
4. **Personalization Engine**: User ticker-based filtering with interaction learning

### Real-time Features
- **Live Market Data**: Yahoo Finance integration for stock prices and charts
- **Dynamic News Updates**: Automatic article insertion with smooth animations
- **Conversational AI**: Chat interface for news discovery and investment questions

## Database Schema

**Users Table**:
- User preferences and ticker selections
- Interaction history for personalization
- Authentication tokens and sessions

**Articles Table**:
- News articles with AI-generated metadata
- Relevance scores and sentiment analysis
- Caching for rate limit scenarios

**Interactions Table**:
- User engagement tracking
- Click patterns and preferences
- Machine learning data collection

## Development Guidelines

### Frontend Patterns
- **State Management**: React hooks with props-based communication
- **API Calls**: Centralized through `services/api.ts` with proper error handling
- **Styling**: Tailwind CSS utility-first approach with shadcn/ui components
- **Animations**: CSS transitions and transforms for smooth UX

### Backend Patterns
- **API Design**: RESTful endpoints with FastAPI automatic documentation
- **Error Handling**: Graceful fallbacks with cached content when APIs fail
- **Rate Limiting**: Built-in protection with slowapi middleware
- **AI Integration**: Structured prompts and response parsing for consistent results

### Testing Approach
- **Backend**: Comprehensive test suite covering API endpoints, database operations, and AI integration
- **Frontend**: Component testing with proper mock data and error scenarios
- **Integration**: End-to-end testing for complete user workflows

## Common Issues & Solutions

**Rate Limits**: Backend automatically falls back to cached articles when NewsAPI/Gemini limits are reached

**Build Issues**: Frontend uses legacy peer deps flag for dependency resolution

**Database**: Initialize with `python database_utils.py init` if connection issues occur

**Authentication**: Demo mode available for development without OAuth setup

## API Rate Limits
- **NewsAPI**: 100 requests/24h (free tier)
- **Gemini AI**: 50 requests/day (free tier) 
- **Yahoo Finance**: No official limits but implement reasonable throttling

## Technology Stack
- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS, Radix UI
- **Backend**: FastAPI, Python 3.10+, SQLAlchemy, Gemini AI
- **Database**: SQLite (development), PostgreSQL (production ready)
- **External APIs**: NewsAPI, Yahoo Finance, SEC EDGAR, Google Gemini