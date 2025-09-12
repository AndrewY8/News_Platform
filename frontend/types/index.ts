// Core application types
export interface NewsArticle {
  id: string
  date: string
  title: string
  source: string
  preview: string
  sentiment: 'positive' | 'negative' | 'neutral'
  tags: string[]
  url?: string
  relevance_score?: number
  category?: string
}

export interface Ticker {
  symbol: string
  trend: 'up' | 'down'
  value: string
  change?: number
  changePercent?: number
  volume?: number
  marketCap?: number
}

export interface UserProfile {
  id: string
  email: string
  username: string
  tickers: string[]
  preferences: {
    investment_style: string
    experience_level: string
    risk_tolerance: string
  }
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  suggested_articles?: NewsArticle[]
}

export interface SearchQuery {
  query: string
  timestamp: Date
}

export type TabId = 'top-news' | 'personalized' | 'saved' | 'search'
export type TimePeriod = '1D' | '1W' | '1M' | '3M' | '1Y'
