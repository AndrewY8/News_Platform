// API service for backend communication  
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004'

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
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  suggested_articles?: NewsArticle[]
}

export interface SearchQuery {
  id?: string
  query: string
  timestamp: Date
  response?: string
}

export interface SecDocument {
  id: string
  title: string
  company: string
  ticker: string
  documentType: string
  filingDate: string
  url: string
  content?: string
  html_content?: string
  highlights?: Array<{
    text: string
    page: number
    position: { top: number; left: number; width: number; height: number }
  }>
}

export class ApiService {
  // Fallback articles for when backend is unavailable
  private static getFallbackArticles(): NewsArticle[] {
    return [
      {
        id: 'fallback-1',
        date: 'Today',
        title: 'Market Update: Tech Stocks Rally on Strong Earnings',
        source: 'Financial Times',
        preview: 'Technology stocks led a broad market rally as major companies reported stronger-than-expected quarterly results...',
        sentiment: 'positive',
        tags: ['AAPL', 'MSFT', 'NVDA'],
        url: '#',
        relevance_score: 0.9,
        category: 'Technology'
      },
      {
        id: 'fallback-2',
        date: 'Today',
        title: 'Federal Reserve Signals Potential Rate Cut',
        source: 'Reuters',
        preview: 'The Federal Reserve indicated it may consider cutting interest rates in the coming months...',
        sentiment: 'positive',
        tags: ['MACRO', 'FED'],
        url: '#',
        relevance_score: 0.8,
        category: 'Economy'
      },
      {
        id: 'fallback-3',
        date: 'Today',
        title: 'Oil Prices Surge on Supply Concerns',
        source: 'Bloomberg',
        preview: 'Crude oil prices jumped to their highest level in months amid growing concerns about supply disruptions...',
        sentiment: 'negative',
        tags: ['OIL', 'ENERGY'],
        url: '#',
        relevance_score: 0.7,
        category: 'Energy'
      },
      {
        id: 'fallback-4',
        date: 'Today',
        title: 'Cryptocurrency Market Shows Mixed Signals',
        source: 'CoinDesk',
        preview: 'Bitcoin and other major cryptocurrencies showed mixed performance as market sentiment remains uncertain...',
        sentiment: 'neutral',
        tags: ['BTC', 'ETH'],
        url: '#',
        relevance_score: 0.6,
        category: 'Cryptocurrency'
      },
      {
        id: 'fallback-5',
        date: 'Today',
        title: 'Healthcare Sector Faces Regulatory Changes',
        source: 'Wall Street Journal',
        preview: 'New regulations in the healthcare sector could impact pharmaceutical companies and insurers...',
        sentiment: 'neutral',
        tags: ['JNJ', 'UNH'],
        url: '#',
        relevance_score: 0.5,
        category: 'Healthcare'
      }
    ]
  }

  // Helper function to create a timeout promise
  private static createTimeoutPromise<T>(ms: number, fallback: T): Promise<T> {
    return new Promise((resolve) => {
      setTimeout(() => resolve(fallback), ms)
    })
  }

  // News endpoints with timeout fallback
  static async getTopNews(): Promise<NewsArticle[]> {
    try {
      const timeoutPromise = this.createTimeoutPromise(5000, this.getFallbackArticles())
      const fetchPromise = fetch(`${API_BASE_URL}/api/articles/top`)
        .then(response => {
          if (!response.ok) throw new Error(`Failed to fetch top news: ${response.status}`)
          return response.json()
        })
        .then(data => this.transformArticles(data))
        .catch(() => this.getFallbackArticles())

      const result = await Promise.race([fetchPromise, timeoutPromise])
      return result
    } catch (error) {
      console.error('Error fetching top news:', error)
      return this.getFallbackArticles()
    }
  }

  static async getPersonalizedNews(): Promise<NewsArticle[]> {
    try {
      const timeoutPromise = this.createTimeoutPromise(5000, this.getFallbackArticles())
      const fetchPromise = fetch(`${API_BASE_URL}/api/articles`)
        .then(response => {
          if (!response.ok) throw new Error(`Failed to fetch personalized news: ${response.status}`)
          return response.json()
        })
        .then(data => this.transformArticles(data))
        .catch(() => this.getFallbackArticles())

      const result = await Promise.race([fetchPromise, timeoutPromise])
      return result
    } catch (error) {
      console.error('Error fetching personalized news:', error)
      return this.getFallbackArticles()
    }
  }

  static async getSavedNews(): Promise<NewsArticle[]> {
    try {
      const timeoutPromise = this.createTimeoutPromise(5000, this.getFallbackArticles())
      const fetchPromise = fetch(`${API_BASE_URL}/api/articles/saved`)
        .then(response => {
          if (!response.ok) throw new Error(`Failed to fetch saved news: ${response.status}`)
          return response.json()
        })
        .then(data => this.transformArticles(data))
        .catch(() => this.getFallbackArticles())

      const result = await Promise.race([fetchPromise, timeoutPromise])
      return result
    } catch (error) {
      console.error('Error fetching saved news:', error)
      return this.getFallbackArticles()
    }
  }

  static async searchNews(query: string): Promise<NewsArticle[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/articles/search?q=${encodeURIComponent(query)}`)
      if (!response.ok) throw new Error(`Failed to search news: ${response.status}`)
      
      const data = await response.json()
      return this.transformArticles(data)
    } catch (error) {
      console.error('Error searching news:', error)
      return []
    }
  }

  // Chat endpoints
  static async sendChatMessage(message: string): Promise<ChatMessage> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          user_id: 1, // TODO: Get from auth context
          conversation_history: []
        })
      })
      
      if (!response.ok) throw new Error(`Failed to send chat message: ${response.status}`)
      
      const data = await response.json()
      return {
        role: 'assistant',
        content: data.response || data.message || 'I received your message but encountered an error processing it.',
        timestamp: new Date(),
        suggested_articles: data.suggested_articles ? this.transformArticles(data.suggested_articles) : []
      }
    } catch (error) {
      console.error('Chat error:', error)
      // Return fallback response instead of throwing
      return {
        role: 'assistant',
        content: 'I apologize, but I\'m experiencing technical difficulties right now. Please try again in a moment.',
        timestamp: new Date(),
        suggested_articles: []
      }
    }
  }

  // Query history endpoints
  static async getQueryHistory(): Promise<SearchQuery[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/history`)
      if (!response.ok) throw new Error(`Failed to fetch query history: ${response.status}`)
      
      const data = await response.json()
      return data.map((item: any) => ({
        id: item.id,
        query: item.query,
        timestamp: new Date(item.timestamp),
        response: item.response
      }))
    } catch (error) {
      console.error('Error fetching query history:', error)
      return []
    }
  }

  static async saveQueryHistory(query: string, responseText?: string): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          response: responseText,
          timestamp: new Date().toISOString()
        })
      })
      
      if (!response.ok) throw new Error(`Failed to save query history: ${response.status}`)
    } catch (error) {
      console.error('Error saving query history:', error)
      // Don't throw - this is optional functionality
    }
  }

  static async deleteQueryHistory(queryId: string): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/history/${queryId}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) throw new Error(`Failed to delete query history: ${response.status}`)
    } catch (error) {
      console.error('Error deleting query history:', error)
      throw error
    }
  }

  // Ticker endpoints
  static async getMarketData(symbols: string[]): Promise<Ticker[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/market/summary?tickers=${symbols.join(',')}`)
      if (!response.ok) throw new Error(`Failed to fetch market data: ${response.status}`)
      
      const data = await response.json()
      return this.transformTickers(data)
    } catch (error) {
      console.error('Error fetching market data:', error)
      return []
    }
  }

  static async updateUserTickers(tickers: string[]): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trades: tickers })
      })
      
      if (!response.ok) throw new Error(`Failed to update tickers: ${response.status}`)
    } catch (error) {
      console.error('Error updating tickers:', error)
      throw error
    }
  }

  // Article actions
  static async saveArticle(articleId: string): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/articles/${articleId}/save`, {
        method: 'POST'
      })
      
      if (!response.ok) throw new Error(`Failed to save article: ${response.status}`)
    } catch (error) {
      console.error('Error saving article:', error)
      throw error
    }
  }

  static async unsaveArticle(articleId: string): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/articles/${articleId}/unsave`, {
        method: 'POST'
      })
      
      if (!response.ok) throw new Error(`Failed to unsave article: ${response.status}`)
    } catch (error) {
      console.error('Error unsaving article:', error)
      throw error
    }
  }

  // Helper methods
  private static transformArticles(data: any[]): NewsArticle[] {
    if (!Array.isArray(data)) return []
    
    return data.map(article => ({
      id: article.id || `article-${Math.random()}`,
      date: this.formatDate(article.datetime || article.publishedAt || article.date),
      title: article.headline || article.title || 'Untitled Article',
      source: this.extractSource(article),
      preview: article.summary || article.description || article.preview || 'No preview available',
      sentiment: this.determineSentiment(article.sentiment_score),
      tags: this.extractTags(article),
      url: article.url,
      relevance_score: article.relevance_score,
      category: article.category
    }))
  }

  private static extractSource(article: any): string {
    // Handle different source formats
    if (typeof article.source === 'string') {
      return article.source
    } else if (article.source && typeof article.source === 'object') {
      return article.source.name || article.source.id || 'Unknown'
    }
    return 'Unknown'
  }

  private static transformTickers(data: any): Ticker[] {
    if (!data.tickers || !Array.isArray(data.tickers)) return []
    
    return data.tickers.map((ticker: any) => ({
      symbol: ticker.symbol,
      trend: ticker.change >= 0 ? 'up' : 'down',
      value: ticker.current_price?.toFixed(2) || '0.00',
      change: ticker.change,
      changePercent: ticker.change_percent
    }))
  }

  private static formatDate(timestamp: string | number): string {
    try {
      let date: Date
      
      if (typeof timestamp === 'number' || (typeof timestamp === 'string' && /^\d+$/.test(timestamp))) {
        const unixTimestamp = typeof timestamp === 'string' ? parseInt(timestamp) : timestamp
        date = new Date(unixTimestamp * 1000)
      } else {
        date = new Date(timestamp)
      }
      
      if (isNaN(date.getTime())) return 'Today'
      
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
      
      if (diffHours < 24) {
        return date.toLocaleTimeString([], {hour: 'numeric', minute:'2-digit'})
      } else if (diffHours < 168) {
        return date.toLocaleDateString('en-US', { weekday: 'short' })
      } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      }
    } catch (error) {
      return 'Today'
    }
  }

  private static determineSentiment(score?: number): 'positive' | 'negative' | 'neutral' {
    if (!score) return 'neutral'
    if (score > 0.1) return 'positive'
    if (score < -0.1) return 'negative'
    return 'neutral'
  }

  private static extractTags(article: any): string[] {
    if (article.tags && Array.isArray(article.tags)) {
      // Handle both string tags and object tags with name property
      return article.tags.map((tag: any) => {
        if (typeof tag === 'string') {
          return tag
        } else if (tag && typeof tag === 'object' && tag.name) {
          return tag.name
        } else {
          return String(tag)
        }
      })
    }
    if (article.content_analysis) {
      try {
        const analysis = JSON.parse(article.content_analysis)
        const topics = analysis.key_topics || []
        return topics.map((topic: any) => {
          if (typeof topic === 'string') {
            return topic
          } else if (topic && typeof topic === 'object' && topic.name) {
            return topic.name
          } else {
            return String(topic)
          }
        })
      } catch {
        return []
      }
    }
    return []
  }

  // SEC Document API methods
  static async searchSecDocuments(query: string, limit: number = 50): Promise<SecDocument[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/sec/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query, limit })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data.documents || []
    } catch (error) {
      console.error('Error searching SEC documents:', error)
      return []
    }
  }

  static async getSecDocument(docId: string, query?: string): Promise<SecDocument | null> {
    try {
      const url = new URL(`${API_BASE_URL}/api/sec/document/${docId}`)
      if (query) {
        url.searchParams.append('query', query)
      }

      const response = await fetch(url.toString())

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const document = await response.json()
      return document
    } catch (error) {
      console.error('Error getting SEC document:', error)
      return null
    }
  }

  static async getCompanyFilings(ticker: string, limit: number = 10): Promise<SecDocument[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/sec/company/${ticker}?limit=${limit}`)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data.documents || []
    } catch (error) {
      console.error('Error getting company filings:', error)
      return []
    }
  }
}
