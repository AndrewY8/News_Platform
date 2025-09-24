"""
Ticker Routes Module
Contains all ticker/market data related FastAPI endpoints that can be imported into the main app.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

# Import ticker validation utilities
from ticker_validator import validate_ticker_list, get_ticker_suggestions

logger = logging.getLogger(__name__)

# Initialize rate limiter (will use the same one from main app)
limiter = Limiter(key_func=get_remote_address)

# Check if yfinance is available
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except Exception as e:
    logger.warning(f"yfinance not available: {e}")
    YFINANCE_AVAILABLE = False
    yf = None

# Pydantic Models for Market Data
class TickerInfo(BaseModel):
    symbol: str
    name: str
    current_price: float
    previous_close: float
    change: float
    change_percent: float
    volume: Optional[int] = None
    market_cap: Optional[int] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    year_high: Optional[float] = None
    year_low: Optional[float] = None

class MarketSummary(BaseModel):
    tickers: List[TickerInfo]
    last_updated: str

# Ticker/Market Data Functions
def get_ticker_info(symbol: str) -> TickerInfo:
    """Get comprehensive ticker information from yfinance"""
    try:
        if not YFINANCE_AVAILABLE:
            return {"symbol": symbol, "price": 0.0, "change": 0.0, "changePercent": 0.0}
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Get current price and calculate change
        current_price = info.get("currentPrice", 0.0)
        previous_close = info.get("previousClose", 0.0)

        if current_price == 0.0:
            # Fallback to regular market price if currentPrice is not available
            current_price = info.get("regularMarketPrice", 0.0)

        change = current_price - previous_close if previous_close else 0.0
        change_percent = (change / previous_close * 100) if previous_close else 0.0

        return TickerInfo(
            symbol=symbol.upper(),
            name=info.get("longName", symbol),
            current_price=round(current_price, 2),
            previous_close=round(previous_close, 2),
            change=round(change, 2),
            change_percent=round(change_percent, 2),
            volume=info.get("volume"),
            market_cap=info.get("marketCap"),
            day_high=info.get("dayHigh"),
            day_low=info.get("dayLow"),
            year_high=info.get("fiftyTwoWeekHigh"),
            year_low=info.get("fiftyTwoWeekLow"),
        )
    except Exception as e:
        logger.error(f"Error fetching ticker info for {symbol}: {e}")
        # Return default ticker info on error
        return TickerInfo(
            symbol=symbol.upper(),
            name=symbol,
            current_price=0.0,
            previous_close=0.0,
            change=0.0,
            change_percent=0.0,
        )

# Route Functions
async def get_ticker_suggestions_endpoint(q: str = ""):
    """Get ticker suggestions for autocomplete"""
    suggestions = get_ticker_suggestions(q, limit=10)
    return {"suggestions": suggestions}

async def get_ticker(symbol: str, request: Request):
    """Get detailed information for a specific ticker"""
    return get_ticker_info(symbol)

async def get_market_summary(request: Request, tickers: str = "AAPL,TSLA,MSFT,GOOGL,AMZN"):
    """Get market summary for multiple tickers"""
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

    # Limit to 10 tickers to avoid rate limiting
    ticker_list = ticker_list[:10]

    ticker_data = []

    # Mock data for now since yfinance might not be working
    mock_data = {
        'AAPL': {'price': 175.20, 'change': 2.15, 'change_percent': 1.24},
        'MSFT': {'price': 378.85, 'change': -1.25, 'change_percent': -0.33},
        'NVDA': {'price': 821.67, 'change': 15.42, 'change_percent': 1.91},
        'TSLA': {'price': 195.33, 'change': -3.12, 'change_percent': -1.57},
        'AMZN': {'price': 152.74, 'change': 0.87, 'change_percent': 0.57},
        'GOOGL': {'price': 138.25, 'change': 1.34, 'change_percent': 0.98}
    }

    for ticker in ticker_list:
        ticker = ticker.strip().upper()
        if ticker in mock_data:
            data = mock_data[ticker]
            ticker_data.append({
                'symbol': ticker,
                'current_price': data['price'],
                'change': data['change'],
                'change_percent': data['change_percent']
            })
        else:
            # Default data for unknown tickers
            ticker_data.append({
                'symbol': ticker,
                'current_price': 100.0,
                'change': 0.0,
                'change_percent': 0.0
            })

    return {'tickers': ticker_data, 'last_updated': datetime.now().isoformat()}

async def get_user_market_data(request: Request, db: Session, User):
    """Get market data for user's preferred tickers"""

    # Get or create user (simplified for demo)
    user = db.query(User).filter(User.id == "demo_1").first()
    if not user:
        user = User(
            id="demo_1",
            username="demo_user",
            email="demo@example.com",
            provider="demo",
            provider_id="demo_1",
            trades=json.dumps([]),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Get user preferences from trades
    user_tickers = json.loads(user.trades) if user.trades else []
    tickers = user_tickers

    if not tickers:
        # Default tickers if user has no preferences
        tickers = ["AAPL", "TSLA", "MSFT"]

    # Get market data for user's tickers
    ticker_infos = []
    for symbol in tickers[:10]:  # Limit to 10 tickers
        ticker_info = get_ticker_info(symbol)
        ticker_infos.append(ticker_info)

    return MarketSummary(tickers=ticker_infos, last_updated=datetime.now().isoformat())

async def search_tickers(query: str, request: Request):
    """Search for tickers by company name or symbol"""
    try:
        # Use yfinance search functionality
        if not YFINANCE_AVAILABLE:
            return {"results": []}
        search_results = yf.search(query)

        # Format results
        results = []
        for result in search_results.head(10).iterrows():
            data = result[1]
            results.append(
                {
                    "symbol": data.get("symbol", ""),
                    "name": data.get("longname", ""),
                    "type": data.get("quoteType", ""),
                    "exchange": data.get("exchange", ""),
                }
            )

        return {"results": results}
    except Exception as e:
        logger.error(f"Error searching tickers for query '{query}': {e}")
        return {"results": []}

# Function to add all ticker routes to the FastAPI app
def add_ticker_routes(app, limiter_instance, get_db_func, User_model):
    """
    Add all ticker/market data routes to the FastAPI app

    Args:
        app: FastAPI application instance
        limiter_instance: Rate limiter instance from main app
        get_db_func: Database dependency function
        User_model: User SQLAlchemy model
    """
    global limiter
    limiter = limiter_instance

    # Ticker suggestion endpoint
    @app.get("/api/ticker-suggestions")
    async def ticker_suggestions_endpoint(q: str = ""):
        return await get_ticker_suggestions_endpoint(q)

    # Individual ticker endpoint
    @app.get("/api/market/ticker/{symbol}", response_model=TickerInfo)
    @limiter.limit("60/minute")
    async def ticker_endpoint(symbol: str, request: Request):
        return await get_ticker(symbol, request)

    # Market summary endpoint
    @app.get("/api/market/summary")
    @limiter.limit("30/minute")
    async def market_summary_endpoint(
        request: Request, tickers: str = "AAPL,TSLA,MSFT,GOOGL,AMZN"
    ):
        return await get_market_summary(request, tickers)

    # User market data endpoint
    @app.get("/api/market/user-tickers", response_model=MarketSummary)
    @limiter.limit("60/minute")
    async def user_market_endpoint(request: Request, db: Session = Depends(get_db_func)):
        return await get_user_market_data(request, db, User_model)

    # Ticker search endpoint
    @app.get("/api/market/search/{query}")
    @limiter.limit("30/minute")
    async def ticker_search_endpoint(query: str, request: Request):
        return await search_tickers(query, request)

    logger.info("✅ Ticker/Market data routes added to FastAPI app")