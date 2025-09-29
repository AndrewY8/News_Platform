#!/usr/bin/env python3
"""
Ticker validation utilities
"""
import re
import requests
from typing import List, Dict

# Common valid ticker symbols for validation
COMMON_VALID_TICKERS = {
    # Major Tech
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'TSLA', 'NVDA', 'NFLX', 'AMD',
    # Finance
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'V', 'MA', 'PYPL', 'BRK.B',
    # Healthcare
    'JNJ', 'UNH', 'PFE', 'ABT', 'TMO', 'MDT', 'AMGN', 'GILD', 'BMY', 'ABBV',
    # Consumer
    'KO', 'PEP', 'WMT', 'TGT', 'HD', 'MCD', 'SBUX', 'NKE', 'DIS', 'NFLX',
    # Energy
    'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'HAL', 'OKE', 'EPD', 'MMP', 'KMI',
    # Industrial
    'GE', 'BA', 'CAT', 'MMM', 'HON', 'UPS', 'FDX', 'LMT', 'RTX', 'NOC',
    # Materials
    'LIN', 'APD', 'ECL', 'SHW', 'DD', 'DOW', 'PPG', 'NEM', 'FCX', 'NUE',
    # Utilities
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'XEL', 'WEC', 'ES', 'AWK',
    # REITs
    'AMT', 'PLD', 'CCI', 'EQIX', 'SPG', 'O', 'WELL', 'AVB', 'EQR', 'VTR',
    # Additional popular tickers
    'INTC', 'IBM', 'ORCL', 'CRM', 'ADBE', 'QCOM', 'TXN', 'AVGO', 'CSCO', 'INTU'
}

def is_valid_ticker_format(ticker: str) -> bool:
    """
    Check if ticker follows valid format:
    - 1-5 characters
    - Only uppercase letters
    - May contain a dot (for some tickers like BRK.B)
    """
    if not ticker:
        return False
    
    # Basic format check
    pattern = r'^[A-Z]{1,5}(\.[A-Z])?$' # Changed to allow 1-5 characters
    return bool(re.match(pattern, ticker.upper()))

def is_known_valid_ticker(ticker: str) -> bool:
    """Check if ticker is in our list of known valid tickers"""
    return ticker.upper() in COMMON_VALID_TICKERS

def validate_ticker(ticker: str) -> Dict[str, any]:
    """
    Comprehensive ticker validation
    Returns: {
        'valid': bool,
        'ticker': str (cleaned),
        'confidence': float (0-1),
        'reason': str
    }
    """
    if not ticker:
        return {
            'valid': False,
            'ticker': '',
            'confidence': 0.0,
            'reason': 'Empty ticker'
        }
    
    # Clean and normalize
    cleaned_ticker = ticker.strip().upper()
    
    # Format validation
    if not is_valid_ticker_format(cleaned_ticker):
        return {
            'valid': False,
            'ticker': cleaned_ticker,
            'confidence': 0.0,
            'reason': 'Invalid ticker format (must be 1-5 uppercase letters, optionally with .X)'
        }
    
    # Check against known valid tickers
    if is_known_valid_ticker(cleaned_ticker):
        return {
            'valid': True,
            'ticker': cleaned_ticker,
            'confidence': 1.0,
            'reason': 'Known valid ticker'
        }
    
    # Format is valid but ticker not in our known list
    return {
        'valid': True,  # Allow it but with lower confidence
        'ticker': cleaned_ticker,
        'confidence': 0.5,
        'reason': 'Valid format, unknown ticker (may be valid but not in common list)'
    }

def validate_ticker_list(tickers: List[str]) -> Dict[str, any]:
    """
    Validate a list of tickers
    Returns: {
        'valid_tickers': List[str],
        'invalid_tickers': List[Dict],
        'warnings': List[str]
    }
    """
    valid_tickers = []
    invalid_tickers = []
    warnings = []
    
    for ticker in tickers:
        result = validate_ticker(ticker)
        
        if result['valid']:
            valid_tickers.append(result['ticker'])
            
            # Add warning for low confidence tickers
            if result['confidence'] < 0.8:
                warnings.append(f"'{result['ticker']}': {result['reason']}")
        else:
            invalid_tickers.append({
                'ticker': ticker,
                'reason': result['reason']
            })
    
    return {
        'valid_tickers': valid_tickers,
        'invalid_tickers': invalid_tickers,
        'warnings': warnings
    }

def get_ticker_suggestions(partial: str, limit: int = 10) -> List[str]:
    """Get ticker suggestions based on partial input"""
    if not partial:
        return list(COMMON_VALID_TICKERS)[:limit]
    
    partial_upper = partial.upper()
    suggestions = []
    
    # Exact matches first
    for ticker in COMMON_VALID_TICKERS:
        if ticker.startswith(partial_upper):
            suggestions.append(ticker)
    
    # Partial matches
    for ticker in COMMON_VALID_TICKERS:
        if partial_upper in ticker and not ticker.startswith(partial_upper):
            suggestions.append(ticker)
    
    return suggestions[:limit]

if __name__ == "__main__":
    # Test the validator
    test_tickers = ['AAPL', 'FAKE', 'INVALID', 'TSLA', 'BRK.B', 'goog', 'xyz123', '']
    
    print("Testing individual tickers:")
    for ticker in test_tickers:
        result = validate_ticker(ticker)
        print(f"{ticker:10} -> {result}")
    
    print("\nTesting ticker list:")
    result = validate_ticker_list(test_tickers)
    print(f"Valid: {result['valid_tickers']}")
    print(f"Invalid: {result['invalid_tickers']}")
    print(f"Warnings: {result['warnings']}")
    
    print("\nTesting suggestions:")
    print(f"Suggestions for 'A': {get_ticker_suggestions('A', 5)}")
    print(f"Suggestions for 'APP': {get_ticker_suggestions('APP', 5)}")