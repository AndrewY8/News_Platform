"use client"

import { useState, useEffect } from "react"
import { ThumbsUp, ThumbsDown, Bookmark, ExternalLink } from "lucide-react"
import { NewsArticle, TabId } from "@/types"
import { ApiService } from "@/services/api"

interface NewsFeedProps {
  activeTab: TabId
  tickers: string[]
}

export function NewsFeed({ activeTab, tickers }: NewsFeedProps) {
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchArticles()
  }, [activeTab, tickers])

  const fetchArticles = async () => {
    setLoading(true)
    setError(null)
    
    try {
      let fetchedArticles: any[] = []
      
      switch (activeTab) {
        case 'top-news':
          fetchedArticles = await ApiService.getTopNews()
          break
        case 'personalized':
          fetchedArticles = await ApiService.getPersonalizedNews()
          break
        case 'saved':
          fetchedArticles = await ApiService.getSavedNews()
          break
        case 'search':
          // Search tab shows previous search results or empty state
          fetchedArticles = []
          break
      }
      
      // Handle empty or invalid responses
      if (!fetchedArticles || !Array.isArray(fetchedArticles)) {
        console.warn(`No articles returned for ${activeTab}`, fetchedArticles)
        fetchedArticles = []
      }
      
      // Transform backend data to frontend format
      const transformedArticles: NewsArticle[] = fetchedArticles.map(article => ({
        id: article.id || `article-${Math.random()}`,
        date: formatDate(article.datetime || article.publishedAt || article.date),
        title: article.headline || article.title || 'Untitled Article',
        source: article.source || 'Unknown',
        preview: article.summary || article.description || article.preview || 'No preview available',
        sentiment: determineSentiment(article.sentiment_score),
        tags: extractTags(article),
        url: article.url,
        relevance_score: article.relevance_score,
        category: article.category
      }))
      
      setArticles(transformedArticles)
    } catch (err) {
      console.error('Error fetching articles:', err)
      setError('Failed to load articles')
      // Set empty articles on error
      setArticles([])
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (timestamp: string | number): string => {
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

  const determineSentiment = (score?: number): 'positive' | 'negative' | 'neutral' => {
    if (!score) return 'neutral'
    if (score > 0.1) return 'positive'
    if (score < -0.1) return 'negative'
    return 'neutral'
  }

  const extractTags = (article: any): string[] => {
    if (article.tags && Array.isArray(article.tags)) {
      return article.tags
    }
    if (article.content_analysis) {
      try {
        const analysis = JSON.parse(article.content_analysis)
        return analysis.key_topics || []
      } catch {
        return []
      }
    }
    return []
  }

  const handleArticleClick = async (article: NewsArticle) => {
    if (article.url) {
      // Track interaction
      try {
        await ApiService.trackInteraction(article.id, 'click')
      } catch (error) {
        console.error('Failed to track interaction:', error)
      }
      
      // Open article in new tab
      window.open(article.url, '_blank', 'noopener,noreferrer')
    }
  }

  const handleSaveArticle = async (article: NewsArticle, e: React.MouseEvent) => {
    e.stopPropagation()
    
    try {
      if (activeTab === 'saved') {
        await ApiService.unsaveArticle(article.id)
        // Remove from saved list
        setArticles(prev => prev.filter(a => a.id !== article.id))
      } else {
        await ApiService.saveArticle(article.id)
        // Show success feedback
        showNotification('Article saved successfully!', 'success')
      }
    } catch (error) {
      console.error('Failed to save/unsave article:', error)
      showNotification('Failed to save article', 'error')
    }
  }

  const showNotification = (message: string, type: 'success' | 'error') => {
    const notification = document.createElement('div')
    notification.className = `fixed top-4 right-4 px-4 py-2 rounded-lg text-white font-medium z-50 ${
      type === 'success' ? 'bg-green-500' : 'bg-red-500'
    }`
    notification.textContent = message
    document.body.appendChild(notification)
    
    setTimeout(() => {
      notification.remove()
    }, 3000)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading articles...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center text-red-600 py-8">
        <p>{error}</p>
        <button 
          onClick={fetchArticles}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Try Again
        </button>
      </div>
    )
  }

  if (activeTab === 'search') {
    return (
      <div className="text-center text-gray-600 py-8">
        <p>Use the News Runner chat to search for specific news topics</p>
        <p className="text-sm mt-2">Ask questions like "What's happening with Apple?" or "Show me Tesla news"</p>
      </div>
    )
  }

  if (articles.length === 0) {
    // Show fallback articles for development
    const fallbackArticles: NewsArticle[] = [
      {
        id: 'fallback-1',
        date: '2h ago',
        title: 'Market Update: Tech Stocks Rally on Strong Earnings',
        source: 'Reuters',
        preview: 'Technology stocks led a broad market rally on Monday as investors cheered strong quarterly earnings reports from major companies.',
        sentiment: 'positive',
        tags: ['AAPL', 'MSFT', 'NVDA']
      },
      {
        id: 'fallback-2',
        date: '4h ago',
        title: 'Federal Reserve Signals Potential Rate Cut',
        source: 'Bloomberg',
        preview: 'Federal Reserve officials indicated they may consider cutting interest rates in the coming months amid signs of economic slowdown.',
        sentiment: 'neutral',
        tags: ['MACRO', 'FED']
      },
      {
        id: 'fallback-3',
        date: '6h ago',
        title: 'Tesla Reports Record Q3 Deliveries',
        source: 'CNBC',
        preview: 'Tesla Inc. reported record vehicle deliveries for the third quarter, exceeding analyst expectations and sending shares higher.',
        sentiment: 'positive',
        tags: ['TSLA', 'EV']
      }
    ]
    
    return (
      <div className="p-6">
        <div className="max-w-4xl space-y-0">
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-blue-800 text-sm">
              <strong>Development Mode:</strong> Showing sample articles. Backend integration required for live data.
            </p>
          </div>
          {fallbackArticles.map((article) => (
            <div 
              key={article.id} 
              className="border-b border-gray-200 py-3 h-16 flex items-center hover:bg-gray-50 cursor-pointer transition-colors"
            >
              <div className="flex gap-4 w-full">
                <div className="text-xs text-gray-500 font-medium min-w-[70px] flex items-center">
                  {article.date}
                </div>

                <div className="flex-shrink-0 flex items-center">
                  {article.sentiment === "positive" && (
                    <div className="w-6 h-6 bg-green-100 flex items-center justify-center">
                      <ThumbsUp className="w-3 h-3 text-green-600" />
                    </div>
                  )}
                  {article.sentiment === "negative" && (
                    <div className="w-6 h-6 bg-red-100 flex items-center justify-center">
                      <ThumbsDown className="w-3 h-3 text-red-600" />
                    </div>
                  )}
                  {article.sentiment === "neutral" && (
                    <div className="w-6 h-6 bg-gray-100 flex items-center justify-center">
                      <div className="w-3 h-0.5 bg-gray-600"></div>
                    </div>
                  )}
                </div>

                <div className="flex-1 flex flex-col justify-center">
                  <h3 className="font-semibold text-gray-900 mb-1 leading-tight text-xs">
                    {article.title} ({article.source})
                  </h3>
                  <p className="text-gray-600 text-[10px] leading-relaxed line-clamp-1">
                    {article.preview}
                  </p>
                </div>

                <div className="flex-shrink-0 flex items-center gap-2">
                  {article.tags.map((tag, index) => (
                    <div key={index} className="text-[10px] text-gray-500 font-mono bg-gray-100 px-1 py-0.5 rounded">
                      {tag}
                    </div>
                  ))}
                  
                  <button
                    onClick={(e) => e.preventDefault()}
                    className="p-1 hover:bg-gray-200 rounded transition-colors"
                    title="Save article (demo mode)"
                  >
                    <Bookmark className="w-3 h-3 text-gray-400" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="max-w-4xl space-y-0">
        {articles.map((article) => (
          <div 
            key={article.id} 
            className="border-b border-gray-200 py-3 h-16 flex items-center hover:bg-gray-50 cursor-pointer transition-colors"
            onClick={() => handleArticleClick(article)}
          >
            <div className="flex gap-4 w-full">
              <div className="text-xs text-gray-500 font-medium min-w-[70px] flex items-center">
                {article.date}
              </div>

              <div className="flex-shrink-0 flex items-center">
                {article.sentiment === "positive" && (
                  <div className="w-6 h-6 bg-green-100 flex items-center justify-center">
                    <ThumbsUp className="w-3 h-3 text-green-600" />
                  </div>
                )}
                {article.sentiment === "negative" && (
                  <div className="w-6 h-6 bg-red-100 flex items-center justify-center">
                    <ThumbsDown className="w-3 h-3 text-red-600" />
                  </div>
                )}
                {article.sentiment === "neutral" && (
                  <div className="w-6 h-6 bg-gray-100 flex items-center justify-center">
                    <div className="w-3 h-0.5 bg-gray-600"></div>
                  </div>
                )}
              </div>

              <div className="flex-1 flex flex-col justify-center">
                <h3 className="font-semibold text-gray-900 mb-1 leading-tight text-xs">
                  {article.title} ({article.source})
                </h3>
                <p className="text-gray-600 text-[10px] leading-relaxed line-clamp-1">
                  {article.preview}
                </p>
                {article.relevance_score && (
                  <div className="text-[9px] text-blue-600 mt-1">
                    Relevance: {(article.relevance_score * 100).toFixed(0)}%
                  </div>
                )}
              </div>

              <div className="flex-shrink-0 flex items-center gap-2">
                {article.tags.map((tag, index) => (
                  <div key={index} className="text-[10px] text-gray-500 font-mono bg-gray-100 px-1 py-0.5 rounded">
                    {tag}
                  </div>
                ))}
                
                <button
                  onClick={(e) => handleSaveArticle(article, e)}
                  className="p-1 hover:bg-gray-200 rounded transition-colors"
                  title={activeTab === 'saved' ? 'Remove from saved' : 'Save article'}
                >
                  <Bookmark className={`w-3 h-3 ${
                    activeTab === 'saved' ? 'text-red-500 fill-current' : 'text-gray-400'
                  }`} />
                </button>
                
                {article.url && (
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="p-1 hover:bg-gray-200 rounded transition-colors"
                    title="Open article"
                  >
                    <ExternalLink className="w-3 h-3 text-gray-400" />
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
