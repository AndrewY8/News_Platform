// API service for backend communication
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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
  timestamp?: number // Raw timestamp in milliseconds for chart markers
}

export interface Ticker {
  symbol: string
  trend: 'up' | 'down'
  value: string
  change?: number
  changePercent?: number
}

export interface CompanyTopicData {
  company_ticker: string
  company_name: string
  topic: {
    id: number
    name: string
    description: string
    urgency: 'high' | 'medium' | 'low'
    articles: any[]
    article_count: number
  }
  highlight_topic_id: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  suggested_articles?: NewsArticle[]
  company_topic_data?: CompanyTopicData
}

export interface SearchQuery {
  id?: string
  query: string
  timestamp: Date
  response?: string
}

export interface CompanySubtopic {
  name: string
  confidence: number
  sources: string[]
  article_indices: number[]
  extraction_method: string
}

export interface CompanyArticle {
  id: number
  title: string
  url: string
  content?: string
  source: string
  source_domain?: string
  published_date?: string
  relevance_score: number
  contribution_strength: number
}

export interface CompanyTopic {
  id: number
  name: string
  description: string
  business_impact: string
  confidence: number
  urgency: 'high' | 'medium' | 'low'
  final_score?: number
  rank_position?: number
  subtopics: CompanySubtopic[]
  extraction_date: string
  articles: CompanyArticle[]
}

export interface CompanyData {
  ticker: string
  name: string
  topics: CompanyTopic[]
}

export interface CompanyFundamentals {
  market_cap?: number
  pe_ratio?: number
  forward_pe?: number
  dividend_yield?: number
  beta?: number
  '52_week_high'?: number
  '52_week_low'?: number
  avg_volume?: number
  revenue?: number
  revenue_growth?: number
  earnings_growth?: number
  profit_margin?: number
  operating_margin?: number
  roe?: number
  debt_to_equity?: number
  current_ratio?: number
  book_value?: number
  price_to_book?: number
}

export interface CompanyDetails {
  ticker: string
  name: string
  description: string
  business_areas: string[]
  industry: string
  sector?: string
  fundamentals: CompanyFundamentals
  topics: CompanyTopic[]
  has_research: boolean
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

  static async getPersonalizedNews(tickers?: string[]): Promise<NewsArticle[]> {
  try {
    const query = tickers && tickers.length > 0 ? `?tickers=${tickers.join(',')}` : ''
    const timeoutPromise = this.createTimeoutPromise(60000, this.getFallbackArticles())
    const fetchPromise = fetch(`${API_BASE_URL}/api/articles${query}`)
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

      // Handle new response format with status field
      if (data.status && data.articles !== undefined) {
        // New format: { status: 'no_results'|'error', message: '...', articles: [...] }
        console.log(`Search status: ${data.status}`, data.message)
        return this.transformArticles(data.articles)
      }

      // Handle array response (direct articles)
      return this.transformArticles(data)
    } catch (error) {
      console.error('Error searching news:', error)
      return []
    }
  }

  // Enhanced search using agent system
  static async searchNewsEnhanced(query: string, useAgent: boolean = true, limit: number = 10): Promise<{
    articles: NewsArticle[]
    searchMethod: string
    sourcesUsed: string[]
    totalFound: number
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/search/enhanced`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          user_id: 1, // TODO: Get from auth context
          use_agent: useAgent,
          limit
        })
      })
      
      if (!response.ok) throw new Error(`Failed to perform enhanced search: ${response.status}`)
      
      const data = await response.json()
      
      if (data.success) {
        return {
          articles: this.transformArticles(data.articles),
          searchMethod: data.search_method || 'unknown',
          sourcesUsed: data.sources_used || [],
          totalFound: data.total_found || 0
        }
      } else {
        throw new Error(data.error || 'Enhanced search failed')
      }
    } catch (error) {
      console.error('Error in enhanced search:', error)
      // Fallback to traditional search
      const fallbackArticles = await this.searchNews(query)
      return {
        articles: fallbackArticles,
        searchMethod: 'fallback_traditional',
        sourcesUsed: ['NewsAPI'],
        totalFound: fallbackArticles.length
      }
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

  // Streaming chat with thinking steps
  static async sendChatMessageStreaming(
    message: string,
    onThinkingStep: (step: string) => void,
    onResponse: (response: ChatMessage) => void,
    onError: (error: string) => void
  ): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          user_id: 1,
          conversation_history: []
        })
      })

      if (!response.ok) throw new Error(`Failed to send streaming chat message: ${response.status}`)

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body reader')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              console.log('🔍 Raw line received:', line)
              const data = JSON.parse(line.slice(6))
              console.log('📦 Parsed data:', data)

              if (data.type === 'thinking') {
                console.log('🤔 THINKING STEP RECEIVED:', data.step)
                onThinkingStep(data.step)
              } else if (data.type === 'response') {
                console.log('✅ RESPONSE RECEIVED:', data)
                onResponse({
                  role: 'assistant',
                  content: data.response,
                  timestamp: new Date(),
                  suggested_articles: data.suggested_articles ? this.transformArticles(data.suggested_articles) : [],
                  company_topic_data: data.company_topic_data || undefined
                })
              } else if (data.type === 'error') {
                onError(data.message)
              }
            } catch (e) {
              console.error('Error parsing stream data:', e)
            }
          }
        }
      }
    } catch (error) {
      console.error('Streaming chat error:', error)
      onError('I apologize, but I\'m experiencing technical difficulties right now. Please try again in a moment.')
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

    return data.map(article => {
      const rawTimestamp = article.published_date || article.datetime || article.publishedAt || article.date
      return {
        id: article.id || `article-${Math.random()}`,
        date: this.formatDate(rawTimestamp),
        title: article.headline || article.title || 'Untitled Article',
        source: this.extractSource(article),
        preview: article.summary || article.description || article.preview || 'No preview available',
        sentiment: this.determineSentiment(article.sentiment_score),
        tags: this.extractTags(article),
        url: article.url,
        relevance_score: article.relevance_score,
        category: article.category,
        // Store the raw timestamp for chart markers
        timestamp: this.parseTimestamp(rawTimestamp)
      }
    })
  }

  private static parseTimestamp(timestamp: string | number): number {
    try {
      if (typeof timestamp === 'number' || (typeof timestamp === 'string' && /^\d+$/.test(timestamp))) {
        const unixTimestamp = typeof timestamp === 'string' ? parseInt(timestamp) : timestamp
        return unixTimestamp * 1000 // Convert to milliseconds
      } else {
        const date = new Date(timestamp)
        return isNaN(date.getTime()) ? Date.now() : date.getTime()
      }
    } catch (error) {
      return Date.now()
    }
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

  // Company data endpoints
  static async getCompanyTopics(ticker: string): Promise<CompanyData> {
    try {
      const timeoutPromise = this.createTimeoutPromise(10000, null)
      const fetchPromise = fetch(`${API_BASE_URL}/api/companies/${ticker}/topics`)
        .then(response => {
          if (!response.ok) {
            throw new Error(`Failed to fetch company topics: ${response.status}`)
          }
          return response.json()
        })

      const result = await Promise.race([fetchPromise, timeoutPromise])
      if (result === null) {
        throw new Error('Request timed out')
      }

      return result
    } catch (error) {
      console.error('Error fetching company topics:', error)
      throw error
    }
  }

  static async getCompanyDetails(ticker: string): Promise<CompanyDetails> {
    try {
      const timeoutPromise = this.createTimeoutPromise(15000, null)
      const fetchPromise = fetch(`${API_BASE_URL}/api/companies/${ticker}/details`)
        .then(response => {
          if (!response.ok) {
            throw new Error(`Failed to fetch company details: ${response.status}`)
          }
          return response.json()
        })

      const result = await Promise.race([fetchPromise, timeoutPromise])
      if (result === null) {
        throw new Error('Request timed out')
      }

      return result
    } catch (error) {
      console.error('Error fetching company details:', error)
      throw error
    }
  }

  static async getAllTopics(limit: number = 50): Promise<any> {
    try {
      const timeoutPromise = this.createTimeoutPromise(10000, { topics: [] })
      const fetchPromise = fetch(`${API_BASE_URL}/api/topics/all?limit=${limit}`)
        .then(response => {
          if (!response.ok) {
            throw new Error(`Failed to fetch all topics: ${response.status}`)
          }
          return response.json()
        })

      const result = await Promise.race([fetchPromise, timeoutPromise])
      return result
    } catch (error) {
      console.error('Error fetching all topics:', error)
      return { topics: [] }
    }
  }

  static async getTopicsByInterests(tickers: string[]): Promise<any> {
    try {
      const tickersParam = tickers.join(',')
      const timeoutPromise = this.createTimeoutPromise(10000, { companies: [] })
      const fetchPromise = fetch(`${API_BASE_URL}/api/companies/topics-by-interest?tickers=${tickersParam}`)
        .then(response => {
          if (!response.ok) {
            throw new Error(`Failed to fetch topics by interests: ${response.status}`)
          }
          return response.json()
        })

      const result = await Promise.race([fetchPromise, timeoutPromise])
      return result
    } catch (error) {
      console.error('Error fetching topics by interests:', error)
      return { companies: [] }
    }
  }

  static async generateTopicsForTicker(ticker: string): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/companies/${ticker}/generate-topics`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to generate topics for ${ticker}: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error(`Error generating topics for ${ticker}:`, error)
      return { status: 'error', message: String(error) }
    }
  }

  // SEC RAG (Retrieval-Augmented Generation) methods for document-specific queries
  static async querySecDocumentRAG(documentId: string, query: string): Promise<{
    answer: string
    chunks: Array<{
      content: string
      similarity: number
      chunk_index: number
      metadata: any
    }>
    document_info?: any
    metadata?: any
    query: string
    error?: string
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/sec/rag/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          document_id: documentId,
          query: query,
          top_k: 5
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (error) {
      console.error('Error querying SEC document with RAG:', error)
      return {
        answer: 'I apologize, but I encountered an error while searching through this document. Please try again or rephrase your question.',
        chunks: [],
        query: query,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }

  static async processSecDocumentForRAG(documentId: string, forceRefresh: boolean = false): Promise<{
    status: string
    document_id: string
    message?: string
    chunk_count?: number
    processed_at?: string
    error?: string
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/sec/rag/process/${documentId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          force_refresh: forceRefresh
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (error) {
      console.error('Error processing SEC document for RAG:', error)
      return {
        status: 'error',
        document_id: documentId,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }

  static async getSecDocumentRAGStatus(documentId: string): Promise<{
    document_id: string
    status: string
    chunk_count: number
    processed_at?: string
    metadata?: any
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/sec/rag/status/${documentId}`)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (error) {
      console.error('Error getting SEC document RAG status:', error)
      return {
        document_id: documentId,
        status: 'error',
        chunk_count: 0
      }
    }
  }

  // ===========================
  // Daily Planet API Methods
  // ===========================

  // User Preferences
  static async getDailyPlanetPreferences(): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/preferences`)
      if (!response.ok) throw new Error(`Failed to fetch preferences: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error fetching Daily Planet preferences:', error)
      throw error
    }
  }

  static async updateDailyPlanetPreferences(preferences: any): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/preferences`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences)
      })
      if (!response.ok) throw new Error(`Failed to update preferences: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error updating Daily Planet preferences:', error)
      throw error
    }
  }

  // Topics
  static async getDailyPlanetTopics(): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/topics`)
      if (!response.ok) throw new Error(`Failed to fetch topics: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error fetching Daily Planet topics:', error)
      throw error
    }
  }

  static async addDailyPlanetTopic(topic: any): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/topics`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(topic)
      })
      if (!response.ok) throw new Error(`Failed to add topic: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error adding Daily Planet topic:', error)
      throw error
    }
  }

  static async updateDailyPlanetTopic(topicId: string, update: any): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/topics/${topicId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(update)
      })
      if (!response.ok) throw new Error(`Failed to update topic: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error updating Daily Planet topic:', error)
      throw error
    }
  }

  static async deleteDailyPlanetTopic(topicId: string): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/topics/${topicId}`, {
        method: 'DELETE'
      })
      if (!response.ok) throw new Error(`Failed to delete topic: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error deleting Daily Planet topic:', error)
      throw error
    }
  }

  // Layout Sections
  static async getDailyPlanetSections(): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/layout/sections`)
      if (!response.ok) throw new Error(`Failed to fetch sections: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error fetching Daily Planet sections:', error)
      throw error
    }
  }

  static async createDailyPlanetSection(section: any): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/layout/sections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(section)
      })
      if (!response.ok) throw new Error(`Failed to create section: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error creating Daily Planet section:', error)
      throw error
    }
  }

  static async updateDailyPlanetSection(sectionId: string, update: any): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/layout/sections/${sectionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(update)
      })
      if (!response.ok) throw new Error(`Failed to update section: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error updating Daily Planet section:', error)
      throw error
    }
  }

  static async reorderDailyPlanetSections(sectionOrders: any): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/layout/sections/reorder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_orders: sectionOrders })
      })
      if (!response.ok) throw new Error(`Failed to reorder sections: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error reordering Daily Planet sections:', error)
      throw error
    }
  }

  static async deleteDailyPlanetSection(sectionId: string): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/layout/sections/${sectionId}`, {
        method: 'DELETE'
      })
      if (!response.ok) throw new Error(`Failed to delete section: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error deleting Daily Planet section:', error)
      throw error
    }
  }

  // Exclusions
  static async getDailyPlanetExclusions(): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/exclusions`)
      if (!response.ok) throw new Error(`Failed to fetch exclusions: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error fetching Daily Planet exclusions:', error)
      throw error
    }
  }

  static async addDailyPlanetExclusion(exclusion: any): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/exclusions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(exclusion)
      })
      if (!response.ok) throw new Error(`Failed to add exclusion: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error adding Daily Planet exclusion:', error)
      throw error
    }
  }

  static async deleteDailyPlanetExclusion(exclusionId: string): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/exclusions/${exclusionId}`, {
        method: 'DELETE'
      })
      if (!response.ok) throw new Error(`Failed to delete exclusion: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error deleting Daily Planet exclusion:', error)
      throw error
    }
  }

  // Article Interactions
  static async trackArticleRemoval(articleId: string, removalData: any): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/articles/${articleId}/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(removalData)
      })
      if (!response.ok) throw new Error(`Failed to track removal: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error tracking article removal:', error)
      throw error
    }
  }

  static async trackArticleRead(articleId: string, readData: any): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/articles/${articleId}/track-read`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(readData)
      })
      if (!response.ok) throw new Error(`Failed to track read: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error tracking article read:', error)
      throw error
    }
  }

  // Onboarding
  static async completeDailyPlanetOnboarding(onboardingData: any): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/onboarding/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(onboardingData)
      })
      if (!response.ok) throw new Error(`Failed to complete onboarding: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error completing Daily Planet onboarding:', error)
      throw error
    }
  }

  // Natural Language Preferences
  static async submitNaturalLanguagePreference(message: string): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-planet/preferences/natural-language`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      })
      if (!response.ok) throw new Error(`Failed to process natural language preference: ${response.status}`)
      return await response.json()
    } catch (error) {
      console.error('Error submitting natural language preference:', error)
      throw error
    }
  }
}
