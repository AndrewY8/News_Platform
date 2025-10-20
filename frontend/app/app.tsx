"use client"

import { useState, useEffect, useRef} from "react"
import { useRouter, usePathname } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Search, Bookmark, Rss, User, X, Trash2, BarChart3, MessageCircle, Send, Minimize2, Maximize2, Settings, Plus, Edit, ChevronDown, Building } from "lucide-react"
import { ApiService, NewsArticle, ChatMessage, SearchQuery } from "@/services/api"
import { YahooFinanceService, StockData, ChartData } from "@/services/yahooFinance"
import { StockChart } from "@/components/StockChart"
import { StockGraphTicker } from "@/components/StockGraphTicker"
import { DailyPlanetHub } from "@/components/DailyPlanet"

export default function HavenNewsApp() {
  const router = useRouter()
  const pathname = usePathname()
  const [activeTab, setActiveTab] = useState("daily-planet")
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedTimePeriod, setSelectedTimePeriod] = useState("1D")
  const [tickers, setTickers] = useState<string[]>([])
  const [newTicker, setNewTicker] = useState("")
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(true)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [isChatLoading, setIsChatLoading] = useState(false)
  const [queryHistory, setQueryHistory] = useState<SearchQuery[]>([])
  const [showHistoryModal, setShowHistoryModal] = useState(false)
  const [showMobileSidebar, setShowMobileSidebar] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [isClosingChat, setIsClosingChat] = useState(false)
  const [chatInput, setChatInput] = useState("")
  const [showAllTickers, setShowAllTickers] = useState(false)
  const [isAnimating, setIsAnimating] = useState(false)
  const [newArticles, setNewArticles] = useState<Set<string>>(new Set())

  // Gemini chat response state
  const [chatResponse, setChatResponse] = useState<string>("")
  const [showChatResponse, setShowChatResponse] = useState(false)
  const [showExpandedResponse, setShowExpandedResponse] = useState(false)
  const [isChatResponseLoading, setIsChatResponseLoading] = useState(false)

  // Thinking steps state
  const [thinkingSteps, setThinkingSteps] = useState<Array<{id: string, text: string, timestamp: number}>>([])
  const [showThinkingSteps, setShowThinkingSteps] = useState(false)

  // Companies and topics state
  const [companiesData, setCompaniesData] = useState<any[]>([])
  const [expandedCompany, setExpandedCompany] = useState<string | null>(null)
  const [expandedTopics, setExpandedTopics] = useState<{[key: string]: boolean}>({})

  // Macro topics state
  const [macroTopics, setMacroTopics] = useState<any[]>([])
  const [politicalTopics, setPoliticalTopics] = useState<any[]>([])

  // Rainbow glow state for highlighted topics
  const [highlightedTopics, setHighlightedTopics] = useState<{[key: string]: number}>({})

  // Yahoo Finance state
  const [stockData, setStockData] = useState<StockData | null>(null)
  const [chartData, setChartData] = useState<ChartData | null>(null)
  const [selectedTicker, setSelectedTicker] = useState<string>("")
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>("1mo")
  const [tickerData, setTickerData] = useState<StockData[]>([])
  const [marketIndices, setMarketIndices] = useState<StockData[]>([])
  const [marketChartsData, setMarketChartsData] = useState<{[key: string]: ChartData}>({})
  const [marketTimeframe, setMarketTimeframe] = useState<string>('1d')
  const [selectedMarketIndex, setSelectedMarketIndex] = useState<string>('^GSPC') // Default to S&P 500

  // Portfolio company selector state
  const [selectedPortfolioCompany, setSelectedPortfolioCompany] = useState<string>("")
  const [showCompanyDropdown, setShowCompanyDropdown] = useState(false)

  // Cached articles state
  const [cachedPersonalized, setCachedPersonalized] = useState<NewsArticle[]>([])

  const tabs = [
    { id: "daily-planet", label: "The Daily Planet", icon: Rss, href: "/daily-planet" },
    { id: "personalized", label: "Personalized feed", icon: User, href: "/personalized-news" },
    { id: "business-news", label: "Business News", icon: Building, href: "#", hasDropdown: true },
    { id: "sec-docs", label: "SEC Doc Searcher", icon: Search, href: "/sec-docs" },
  ]

  const timePeriods = ["1D", "1W", "1M", "3M", "1Y"]

  // Set active tab based on current pathname (only on initial load)
  useEffect(() => {
    if (pathname === '/') {
      setActiveTab('daily-planet')
    }
  }, [])

  // Initialize app with data
const hasInitialized = useRef(false)

useEffect(() => {
  if (!hasInitialized.current) {
    initializeApp()
    // loadQueryHistory()
    hasInitialized.current = true
  }
}, [])

  // Load articles when tab changes (but not for portfolio - wait for user selection)
useEffect(() => {
  if (activeTab !== 'portfolio' && tickers.length > 0) {
    loadArticles(tickers)
  }
}, [activeTab, tickers])

  // Re-fetch articles when portfolio company changes
  useEffect(() => {
    if (activeTab === 'portfolio' && selectedPortfolioCompany) {
      loadArticles([selectedPortfolioCompany])
    }
  }, [selectedPortfolioCompany])

  const loadMarketIndices = async (timeframe: string = '1d') => {
    try {
      const indices = ['^DJI', '^IXIC', '^GSPC'] // Dow Jones, NASDAQ, S&P 500
      const indicesData = await Promise.all(
        indices.map(symbol => YahooFinanceService.getStockQuote(symbol))
      )
      setMarketIndices(indicesData.filter(data => data !== null) as StockData[])

      // Load chart data for all indices
      const timeframeMap: {[key: string]: {interval: string, range: string}} = {
        '1d': { interval: '5m', range: '1d' },
        '5d': { interval: '30m', range: '5d' },
        '1mo': { interval: '1d', range: '1mo' },
        '1y': { interval: '1d', range: '1y' }
      }
      const { interval, range } = timeframeMap[timeframe]

      const chartsData: {[key: string]: ChartData} = {}
      for (const symbol of indices) {
        const chart = await YahooFinanceService.getChartData(symbol, interval, range)
        if (chart) {
          chartsData[symbol] = chart
        }
      }
      setMarketChartsData(chartsData)
    } catch (error) {
      console.error('Failed to load market indices:', error)
    }
  }

  const loadMacroTopics = async () => {
    try {
      console.log("📈 Loading macro topics...")

      // Fetch macro topics
      const macroResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/macro-topics?topic_type=macro&limit=5`)
      if (macroResponse.ok) {
        const macroData = await macroResponse.json()
        setMacroTopics(macroData.topics || [])
        console.log("✅ Loaded macro topics:", macroData.topics?.length || 0)
      }

      // Fetch political topics
      const politicalResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/macro-topics?topic_type=political&limit=5`)
      if (politicalResponse.ok) {
        const politicalData = await politicalResponse.json()
        setPoliticalTopics(politicalData.topics || [])
        console.log("✅ Loaded political topics:", politicalData.topics?.length || 0)
      }
    } catch (error) {
      console.error('Failed to load macro topics:', error)
    }
  }

  const initializeApp = async () => {
    try {
      console.log("🚀 Initializing app...")
      // Set default tickers
      const defaultTickers = ["AAPL"]
      setTickers(defaultTickers)

      // Load initial ticker data
      await loadTickerData(defaultTickers)

      // Load market indices
      await loadMarketIndices()

      // Load macro and political topics
      await loadMacroTopics()

      //Load initial topics directly
      console.log("📊 Loading initial topics for tickers:", defaultTickers)
      try {
        const companiesResponse = await ApiService.getTopicsByInterests(defaultTickers)
        console.log("✅ Received topics:", companiesResponse)
        setCompaniesData(companiesResponse.companies || [])
      } catch (error) {
        console.error("❌ Failed to load initial topics:", error)
      }

      setLoading(false)
    } catch (error) {
      console.error('Failed to initialize app:', error)
      setLoading(false)
    }
  }

  const loadTickerData = async (symbols: string[]) => {
    try {
      const data = await YahooFinanceService.getMultipleStockQuotes(symbols)
      setTickerData(data)
      
      // Set first ticker as selected by default
      if (data.length > 0 && !selectedTicker) {
        setSelectedTicker(data[0].symbol)
        await loadChartData(data[0].symbol, selectedTimeframe)
      }
    } catch (error) {
      console.error('Failed to load ticker data:', error)
    }
  }

  const loadChartData = async (symbol: string, timeframe: string) => {
    try {
      const chart = await YahooFinanceService.getChartData(symbol, timeframe)
      setChartData(chart)
      
      // Update stock data for the selected ticker
      const stock = tickerData.find(t => t.symbol === symbol)
      if (stock) {
        setStockData(stock)
      }
    } catch (error) {
      console.error('Failed to load chart data:', error)
    }
  }

const loadArticles = async (tickers?: string[]) => {
  if (cachedPersonalized.length == 0) {setLoading(true)}

  try {
    let fetchedArticles: NewsArticle[] = []

    switch (activeTab) {
      case 'personalized':
        console.log("Fetching topics by user interests...")
        // Fetch companies with their topics based on user interests
        const userTickers = (tickers && tickers.length > 0) ? tickers : ['AAPL', 'MSFT', 'GOOGL'] // Default tickers if none selected
        const companiesResponse = await ApiService.getTopicsByInterests(userTickers)

        setCompaniesData(companiesResponse.companies || [])
        fetchedArticles = [] // We'll use companiesData instead for display
        break

      case 'portfolio':
        if (selectedPortfolioCompany) {
          console.log("Fetching portfolio news for company:", selectedPortfolioCompany)
          const data = await ApiService.getPersonalizedNews([selectedPortfolioCompany])
          fetchedArticles = data
          // Clear existing articles when switching companies
          setArticles([])
        } else {
          // Don't load any articles if no company is selected
          fetchedArticles = []
        }
        break

      case 'saved':
        fetchedArticles = await ApiService.getSavedNews()
        break

      case 'sec-docs':
        fetchedArticles = []
        break

      default:
        fetchedArticles = []
    }

    setArticles(prevArticles => {
  const existingIds = new Set(prevArticles.map(a => a.id))
  const newUniqueArticles = fetchedArticles.filter(a => !existingIds.has(a.id))
  const combined = [...prevArticles, ...newUniqueArticles]

  combined.sort((a, b) => normalizeDate(b.date) - normalizeDate(a.date))

  return combined
})


  } catch (err) {
    console.error('Error loading articles:', err)
    setArticles([])
  } finally {
    setLoading(false)
  }
}

// Convert formatted date strings back to a comparable timestamp
const normalizeDate = (dateStr: string): number => {
  const now = new Date()
  
  // Handle "Just now" or "Today"
  if (dateStr === 'Just now' || dateStr === 'Today') return now.getTime()

  // Handle "10:30 AM" style (assume today)
  const timeMatch = dateStr.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/)
  if (timeMatch) {
    let hours = parseInt(timeMatch[1], 10)
    const minutes = parseInt(timeMatch[2], 10)
    const period = timeMatch[3]
    if (period === 'PM' && hours !== 12) hours += 12
    if (period === 'AM' && hours === 12) hours = 0
    const d = new Date(now)
    d.setHours(hours, minutes, 0, 0)
    return d.getTime()
  }

  // Handle "Mon" style (within last 7 days)
  const weekdays = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']
  if (weekdays.includes(dateStr)) {
    const d = new Date(now)
    const targetDay = weekdays.indexOf(dateStr)
    const diff = (d.getDay() - targetDay + 7) % 7
    d.setDate(d.getDate() - diff)
    d.setHours(0,0,0,0)
    return d.getTime()
  }

  // Handle "Apr 10" style
  const parsed = Date.parse(dateStr)
  if (!isNaN(parsed)) return parsed

  // Fallback
  return now.getTime()
}


  const handleSearch = async (query: string) => {
    if (!query.trim()) return
    
    setActiveTab('sec-docs')
    setLoading(true)
    try {
      const searchResults = await ApiService.searchNews(query)
      setArticles(searchResults)
    } catch (error) {
      console.error('Search error:', error)
      setArticles([])
    } finally {
      setLoading(false)
    }
  }

  const loadQueryHistory = async () => {
    try {
      const history = await ApiService.getQueryHistory()
      setQueryHistory(history)
    } catch (error) {
      console.error('Failed to load query history:', error)
    }
  }

  const removeTicker = (symbolToRemove: string) => {
    setTickers(tickers.filter((ticker) => ticker !== symbolToRemove))
    setTickerData(tickerData.filter((ticker) => ticker.symbol !== symbolToRemove))
    
    // If we're removing the selected ticker, select a different one
    if (selectedTicker === symbolToRemove) {
      const remainingTickers = tickerData.filter((ticker) => ticker.symbol !== symbolToRemove)
      if (remainingTickers.length > 0) {
        setSelectedTicker(remainingTickers[0].symbol)
        loadChartData(remainingTickers[0].symbol, selectedTimeframe)
      } else {
        setSelectedTicker("")
        setStockData(null)
        setChartData(null)
      }
    }
  }

const getEmoji = (article: NewsArticle) => {
  if (article.source === "EDGAR") return "📝"
  if (article.sentiment === "positive") return "📈"
  if (article.sentiment === "negative") return "📉"
  return "💡"
}

const addTicker = async () => {
  if (!newTicker.trim()) return

  const newTickerSymbol = newTicker.toUpperCase()

  // Check if ticker already exists
  if (tickers.find((t) => t === newTickerSymbol)) {
    alert(`${newTickerSymbol} is already in your interests`)
    setNewTicker("")
    return
  }

  // Validate ticker with yfinance
  try {
    console.log(`Validating ticker ${newTickerSymbol} with yfinance...`)
    const stockData = await YahooFinanceService.getStockQuote(newTickerSymbol)

    if (!stockData) {
      alert(`${newTickerSymbol} is not a valid ticker symbol. Please check and try again.`)
      return
    }

    console.log(`✅ ${newTickerSymbol} is a valid ticker`)

    // Add to tickers list
    const updatedTickers = [...tickers, newTickerSymbol]
    setTickers(updatedTickers)
    setTickerData(prev => [...prev, stockData])

    // If this is the first ticker, select it
    if (tickers.length === 0) {
      setSelectedTicker(newTickerSymbol)
      await loadChartData(newTickerSymbol, selectedTimeframe)
    }

    // Check if topics already exist for this ticker
    console.log(`Checking if topics exist for ${newTickerSymbol}...`)
    const topicsResponse = await ApiService.getCompanyTopics(newTickerSymbol)

    if (topicsResponse.topics && topicsResponse.topics.length > 0) {
      console.log(`✅ Found ${topicsResponse.topics.length} existing topics for ${newTickerSymbol}`)
    } else {
      console.log(`⚠️ No topics found for ${newTickerSymbol}. Triggering deep search...`)

      // Trigger automatic topic generation
      const topicGenResponse = await ApiService.generateTopicsForTicker(newTickerSymbol)
      if (topicGenResponse.status === 'started') {
        console.log(`✅ Deep search started for ${newTickerSymbol}`)
      } else {
        console.warn(`⚠️ Topic generation failed for ${newTickerSymbol}:`, topicGenResponse.message)
      }
    }

    await loadArticles(updatedTickers)
    setNewTicker("")

  } catch (error) {
    console.error('Failed to add ticker:', error)
    alert(`Error adding ${newTickerSymbol}. Please try again.`)
  }
}

  const handleTickerSelect = async (symbol: string) => {
    setSelectedTicker(symbol)
    await loadChartData(symbol, selectedTimeframe)
  }

  const handleTimeframeChange = async (timeframe: string) => {
    setSelectedTimeframe(timeframe)
    if (selectedTicker) {
      await loadChartData(selectedTicker, timeframe)
    }
  }

  // Reusable function to insert article at any position with smooth animation
  const insertArticleAtPosition = (article: NewsArticle, targetPosition: number, delay: number = 0) => {
    setTimeout(() => {
      // Add article to the list and mark it as new for animation
      setArticles(prev => {
        const newArticles = [...prev]
        newArticles.splice(targetPosition, 0, article)
        return newArticles
      })
      
      setNewArticles(prev => new Set([...prev, article.id]))
      
      // Remove animation classes after animation completes
      setTimeout(() => {
        setNewArticles(prev => {
          const newSet = new Set(prev)
          newSet.delete(article.id)
          return newSet
        })
      }, 1500) // Allow time for animation to complete and settle
      
    }, delay)
  }

  const addThinkingStep = (step: string) => {
    console.log('🎯 MAIN APP - addThinkingStep called with:', step)
    console.log('🎯 MAIN APP - Current showThinkingSteps:', showThinkingSteps)
    console.log('🎯 MAIN APP - Current thinking steps count:', thinkingSteps.length)

    const newStep = {
      id: Date.now().toString(),
      text: step,
      timestamp: Date.now()
    }

    setThinkingSteps(prev => {
      const updated = [newStep, ...prev]
      console.log('🎯 MAIN APP - Updated thinking steps:', updated.map(s => s.text))
      // Keep only the last 4 steps for the stacking effect
      return updated.slice(0, 4)
    })

    // Don't auto-remove individual steps - let the container control visibility
    // Individual step removal was causing the container to disappear prematurely
  }

  // Debug the thinking steps rendering
  useEffect(() => {
    console.log('🎭 MAIN APP - Render state changed:', {
      showThinkingSteps,
      stepsLength: thinkingSteps.length,
      steps: thinkingSteps.map(s => s.text)
    })
  }, [showThinkingSteps, thinkingSteps])

  const handleChatSubmit = async () => {
    if (!chatInput.trim() || isChatResponseLoading) return

    // Store the query
    const query = chatInput
    setChatInput("")

    // Show loading state and thinking steps
    setIsChatResponseLoading(true)
    setShowThinkingSteps(true)
    setShowChatResponse(false)
    setThinkingSteps([])

    try {
      await ApiService.sendChatMessageStreaming(
        query,
        // onThinkingStep
        (step: string) => {
          addThinkingStep(step)
        },
        // onResponse
        async (chatMessage: ChatMessage) => {
          // Keep thinking steps visible for a moment, then show response
          setShowChatResponse(true)

          // Hide thinking steps after a delay to let user see final step
          setTimeout(() => {
            setShowThinkingSteps(false)
            // Clear the thinking steps array when hiding to reset for next query
            setThinkingSteps([])
          }, 2000)

          const responseContent = typeof chatMessage.content === 'string'
            ? chatMessage.content
            : JSON.stringify(chatMessage.content)
          setChatResponse(responseContent)

          // Save to history
          await ApiService.saveQueryHistory(query, responseContent)

          // Check if this is a company-specific response
          if (chatMessage.company_topic_data) {
            const { company_ticker, company_name, topic, highlight_topic_id } = chatMessage.company_topic_data
            console.log('🏢 Company-specific response detected:', company_ticker, topic.name)

            // Find if company already exists in companiesData
            const existingCompanyIndex = companiesData.findIndex(c => c.ticker === company_ticker)

            if (existingCompanyIndex >= 0) {
              // Company exists - inject topic
              setCompaniesData(prev => {
                const updated = [...prev]
                const company = updated[existingCompanyIndex]

                // Check if topic already exists
                const topicExists = company.topics.some((t: any) => t.id === topic.id)
                if (!topicExists) {
                  // Add topic to beginning of array
                  company.topics = [topic, ...company.topics]
                }

                return updated
              })
            } else {
              // Company doesn't exist - fetch or create company data
              const newCompany = {
                ticker: company_ticker,
                company_name: company_name,
                topics: [topic]
              }
              setCompaniesData(prev => [newCompany, ...prev])
            }

            // Set rainbow glow highlight for 20 seconds
            const topicKey = `${company_ticker}-${highlight_topic_id}`
            setHighlightedTopics(prev => ({
              ...prev,
              [topicKey]: Date.now() + 20000 // 20 seconds from now
            }))

            // Auto-expand this topic
            setExpandedTopics(prev => ({
              ...prev,
              [topicKey]: true
            }))

            // Remove highlight after 20 seconds
            setTimeout(() => {
              setHighlightedTopics(prev => {
                const updated = { ...prev }
                delete updated[topicKey]
                return updated
              })
            }, 20000)

            // Scroll to company section after a brief delay
            setTimeout(() => {
              const companyElement = document.getElementById(`company-${company_ticker}`)
              if (companyElement) {
                companyElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }
            }, 500)
          }
          // If there are suggested articles, insert them into the feed
          else if (chatMessage.suggested_articles && chatMessage.suggested_articles.length > 0) {
            setIsAnimating(true)
            chatMessage.suggested_articles.forEach((article, index) => {
              insertArticleAtPosition(article, index, index * 800)
            })

            // End animation after all articles are done
            setTimeout(() => {
              setIsAnimating(false)
            }, chatMessage.suggested_articles.length * 800 + 1500)
          }

          setIsChatResponseLoading(false)
        },
        // onError
        (error: string) => {
          setShowThinkingSteps(false)
          setThinkingSteps([]) // Clear thinking steps on error
          setShowChatResponse(true)
          setChatResponse(error)
          setIsChatResponseLoading(false)
        }
      )
    } catch (error) {
      console.error('Chat error:', error)
      setShowThinkingSteps(false)
      setThinkingSteps([]) // Clear thinking steps on error
      setShowChatResponse(true)
      setChatResponse("I apologize, but I'm experiencing technical difficulties. Please try again.")
      setIsChatResponseLoading(false)
    }
  }

  const handleCloseChat = () => {
    setIsClosingChat(true)
    setTimeout(() => {
      setShowChat(false)
      setIsClosingChat(false)
    }, 600)
  }

  const deleteQueryFromHistory = async (queryId: string) => {
    try {
      await ApiService.deleteQueryHistory(queryId)
      await loadQueryHistory()
    } catch (error) {
      console.error('Failed to delete query:', error)
    }
  }

  const formatQueryTime = (timestamp: Date) => {
    const now = new Date()
    const diffMs = now.getTime() - timestamp.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    
    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours}h ago`
    return timestamp.toLocaleDateString()
  }

  // Single Index Market Chart Component
  function SingleIndexChart() {
    const chart = marketChartsData[selectedMarketIndex]

    if (!chart || chart.data.length === 0) {
      return <div className="h-80 bg-gray-50 rounded flex items-center justify-center text-sm text-gray-400">Loading chart data...</div>
    }

    const indexColors: {[key: string]: string} = {
      '^DJI': '#2563eb',   // Blue for Dow Jones
      '^IXIC': '#10b981',  // Green for NASDAQ
      '^GSPC': '#f59e0b'   // Orange for S&P 500
    }

    const prices = chart.data.map(d => d.close).filter(p => p > 0)
    if (prices.length === 0) return null

    const min = Math.min(...prices)
    const max = Math.max(...prices)
    const range = max - min || 1

    const points = prices.map((price, index) => {
      const x = (index / (prices.length - 1)) * 100
      const y = 100 - ((price - min) / range) * 100
      return `${x},${y}`
    }).join(' ')

    const areaPath = `M ${points} L 100,100 L 0,100 Z`
    const linePath = `M ${points}`
    const color = indexColors[selectedMarketIndex] || '#2563eb'

    // Calculate Y-axis labels with round numbers
    const yLabels = []

    // Determine appropriate step size based on range
    let step = 100
    if (range > 10000) {
      step = 5000
    } else if (range > 5000) {
      step = 1000
    } else if (range > 1000) {
      step = 500
    } else if (range > 500) {
      step = 100
    } else if (range > 100) {
      step = 50
    } else {
      step = 10
    }

    // Calculate nice round min and max
    const roundMin = Math.floor(min / step) * step
    const roundMax = Math.ceil(max / step) * step
    const roundRange = roundMax - roundMin

    // Generate 5 evenly spaced round labels
    for (let i = 0; i < 5; i++) {
      const price = roundMin + (roundRange * i / 4)
      const y = 100 - (((price - min) / range) * 100)
      yLabels.push({ price, y })
    }

    // Calculate X-axis labels (time)
    const xLabels = []
    const labelCount = 5
    for (let i = 0; i < labelCount; i++) {
      const index = Math.floor((i / (labelCount - 1)) * (chart.data.length - 1))
      const timestamp = chart.data[index].timestamp
      const date = new Date(timestamp)
      let label = ''

      if (marketTimeframe === '1d') {
        label = date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
      } else if (marketTimeframe === '5d') {
        label = date.toLocaleDateString([], { weekday: 'short' })
      } else if (marketTimeframe === '1mo') {
        label = date.toLocaleDateString([], { month: 'short', day: 'numeric' })
      } else if (marketTimeframe === '1y') {
        label = date.toLocaleDateString([], { month: 'short' })
      }

      const x = (i / (labelCount - 1)) * 100
      xLabels.push({ x, label })
    }

    return (
      <div className="h-80 bg-gray-50 rounded p-4 relative">
        {/* Y-axis labels */}
        <div className="absolute left-0 top-4 bottom-12 w-16 flex flex-col justify-between text-xs text-gray-600">
          {yLabels.reverse().map((item, i) => (
            <div key={i} className="text-right pr-2">{item.price.toFixed(0)}</div>
          ))}
        </div>

        {/* Chart area with padding for axes */}
        <div className="ml-16 mr-2 h-full pb-8">
          <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            <defs>
              <linearGradient id={`market-gradient-${selectedMarketIndex.replace('^', '')}`} x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor={color} stopOpacity="0.3" />
                <stop offset="100%" stopColor={color} stopOpacity="0.05" />
              </linearGradient>
            </defs>
            <path d={areaPath} fill={`url(#market-gradient-${selectedMarketIndex.replace('^', '')})`} />
            <path d={linePath} fill="none" stroke={color} strokeWidth="2" vectorEffect="non-scaling-stroke" />
          </svg>
        </div>

        {/* X-axis labels */}
        <div className="absolute bottom-0 left-16 right-2 h-8 flex justify-between items-center text-xs text-gray-600">
          {xLabels.map((item, i) => (
            <div key={i} className="text-center">{item.label}</div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen font-sans" style={{ backgroundColor: '#FFFFFF' }}>
      {/* Fixed Navigation Bar */}
      <div className="fixed top-0 left-0 right-0 z-50" style={{ backgroundColor: '#FFFFFF' }}>
        <div className="border-b border-gray-200 py-3 px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            {/* Logo and Navigation Combined */}
            <div className="flex items-center gap-6">
              <h1 className="text-sm font-bold text-black whitespace-nowrap" style={{letterSpacing: '0.1em'}}>Haven News</h1>

              {/* Horizontal Navigation - Same Line */}
              <div className="hidden lg:flex gap-4 overflow-visible">
              {tabs.map((tab) => {
                const Icon = tab.icon
                
                if (tab.id === 'business-news') {
                  return (
                    <div 
                      key={tab.id} 
                      className="relative group"
                    >
                      <Button
                        variant="ghost"
                        className="flex items-center gap-1 px-3 py-1 text-sm tracking-wide whitespace-nowrap text-gray-700 hover:bg-white/50"
                      >
                        {tab.label}
                        <ChevronDown className="h-3 w-3" />
                      </Button>
                      
                      {/* Business Industries Dropdown - Multi-Column Layout */}
                      <div className="absolute top-full left-0 mt-1 w-[600px] bg-white border border-gray-200 rounded-lg shadow-xl z-[9999] opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-300 transform translate-y-0">
                        <div className="p-4">
                          <h3 className="text-sm font-semibold text-gray-900 mb-3 border-b border-gray-100 pb-2">Business Categories</h3>
                          <div className="grid grid-cols-3 gap-6">
                            {/* Column 1: Tech & Innovation */}
                            <div className="space-y-1">
                              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Tech & Innovation</h4>
                              {[
                                'Technology',
                                'Software',
                                'Artificial Intelligence',
                                'Cybersecurity',
                                'Semiconductors',
                                'Cloud Computing'
                              ].map((industry) => (
                                <button
                                  key={industry}
                                  className="block w-full text-left px-2 py-1.5 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 rounded transition-colors"
                                >
                                  {industry}
                                </button>
                              ))}
                            </div>

                            {/* Column 2: Traditional Industries */}
                            <div className="space-y-1">
                              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Traditional</h4>
                              {[
                                'Financial Services',
                                'Healthcare',
                                'Energy',
                                'Manufacturing',
                                'Automotive',
                                'Aerospace'
                              ].map((industry) => (
                                <button
                                  key={industry}
                                  className="block w-full text-left px-2 py-1.5 text-sm text-gray-700 hover:bg-green-50 hover:text-green-700 rounded transition-colors"
                                >
                                  {industry}
                                </button>
                              ))}
                            </div>

                            {/* Column 3: Consumer & Services */}
                            <div className="space-y-1">
                              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Consumer & Services</h4>
                              {[
                                'Retail',
                                'Real Estate',
                                'Telecommunications',
                                'Media & Entertainment',
                                'Travel & Hospitality',
                                'Consumer Goods'
                              ].map((industry) => (
                                <button
                                  key={industry}
                                  className="block w-full text-left px-2 py-1.5 text-sm text-gray-700 hover:bg-purple-50 hover:text-purple-700 rounded transition-colors"
                                >
                                  {industry}
                                </button>
                              ))}
                            </div>
                          </div>
                          
                          {/* Footer with popular topics */}
                          <div className="mt-4 pt-3 border-t border-gray-100">
                            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Trending Topics</h4>
                            <div className="flex flex-wrap gap-2">
                              {['Earnings', 'IPOs', 'Mergers & Acquisitions', 'Market Analysis', 'Startups'].map((topic) => (
                                <button
                                  key={topic}
                                  className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
                                >
                                  {topic}
                                </button>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                }
                
                return (
                  <Button
                    key={tab.id}
                    variant="ghost"
                    className={`flex items-center gap-1 px-3 py-1 text-sm tracking-wide whitespace-nowrap ${
                      activeTab === tab.id
                        ? 'text-blue-700 bg-blue-50 font-medium'
                        : 'text-gray-700 hover:bg-white/50'
                    }`}
                    onClick={() => setActiveTab(tab.id)}
                  >
                    {tab.label}
                  </Button>
                )
              })}
              </div>
            </div>

            {/* Mobile Menu Button */}
            <Button
              variant="ghost"
              size="sm"
              className="lg:hidden p-2"
              onClick={() => setShowMobileSidebar(true)}
            >
              <BarChart3 className="h-5 w-5" />
            </Button>
          </div>
        </div>

        {/* Stock Ticker Graph Bar - directly below navigation, no margins */}
        <div className="pb-1">
          <StockGraphTicker tickers={tickers} />
        </div>
      </div>

      {/* Main content area with proper spacing */}
      <div className="min-h-screen pt-[170px] sm:pt-[200px] lg:pt-[250px]">
        {/* Main Content - Full Width */}
        <div className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <div className="pt-2 pb-3 sm:pt-3 sm:pb-4 lg:pt-4 lg:pb-6">
            {/* Daily Planet has its own loading/data management */}
            {activeTab === 'daily-planet' ? (
              <DailyPlanetHub
                userId="demo_user_1"
                initialTickers={tickers}
              />
            ) : loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-2 text-gray-600">Loading articles...</span>
              </div>
            ) : (activeTab === 'personalized' ? companiesData.length === 0 : articles.length === 0) ? (
              <div className="text-center text-gray-600 py-8">
                {activeTab === 'sec-docs' ? (
                  <div className="max-w-md mx-auto">
                    <Search className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">SEC Document Searcher</h3>
                    <p className="text-gray-600 mb-4">Search for SEC filings, company documents, and regulatory information.</p>
                    <div className="flex gap-2">
                      <Input
                        placeholder="Search SEC filings..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyPress={(e) => e.key === "Enter" && handleSearch(searchQuery)}
                        className="flex-1"
                      />
                      <Button
                        onClick={() => handleSearch(searchQuery)}
                        disabled={!searchQuery.trim()}
                      >
                        Search
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <p>No articles available for {activeTab}</p>
                    {activeTab === 'personalized' && tickers.length === 0 && (
                      <p className="text-sm mt-2">Add some tickers to get personalized news!</p>
                    )}
                  </>
                )}
              </div>
            ) : (
              <div className="w-full">
                {/* Render based on active tab */}
                {activeTab === 'personalized' ? (
                  <>
                    {/* Market Overview and Headlines Row */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                      {/* Market Indices Card - 1/2 width */}
                      {marketIndices.length > 0 && (
                        <div className="border rounded-lg p-4 shadow-lg" style={{ backgroundColor: '#FFFFFF' }}>
                          <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-bold text-gray-900">Market Overview</h3>

                            {/* Timeframe Selector */}
                            <div className="flex gap-2">
                              {['1d', '5d', '1mo', '1y'].map((tf) => (
                                <button
                                  key={tf}
                                  onClick={() => {
                                    setMarketTimeframe(tf)
                                    loadMarketIndices(tf)
                                  }}
                                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                                    marketTimeframe === tf
                                      ? 'bg-blue-600 text-white'
                                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                  }`}
                                >
                                  {tf.toUpperCase()}
                                </button>
                              ))}
                            </div>
                          </div>

                          {/* Single Index Chart */}
                          <SingleIndexChart />

                          {/* Clickable Index Stats Below Chart */}
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
                            {marketIndices.map((index) => {
                              const indexName = index.symbol === '^DJI' ? 'Dow Jones' :
                                              index.symbol === '^IXIC' ? 'NASDAQ' :
                                              index.symbol === '^GSPC' ? 'S&P 500' : index.symbol
                              const isSelected = index.symbol === selectedMarketIndex
                              const indexColors: {[key: string]: string} = {
                                '^DJI': '#2563eb',
                                '^IXIC': '#10b981',
                                '^GSPC': '#f59e0b'
                              }
                              return (
                                <button
                                  key={index.symbol}
                                  onClick={() => setSelectedMarketIndex(index.symbol)}
                                  className={`flex flex-col p-4 rounded-lg transition-all cursor-pointer text-left ${
                                    isSelected ? 'ring-2 ring-offset-2' : 'hover:bg-gray-100'
                                  }`}
                                  style={isSelected ? {
                                    ringColor: indexColors[index.symbol],
                                    backgroundColor: `${indexColors[index.symbol]}10`
                                  } : {}}
                                >
                                  <div className="text-sm text-gray-600 mb-1">{indexName}</div>
                                  <div className="text-2xl font-bold text-gray-900">{index.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                                  <div className={`text-sm font-medium ${index.changePercent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {index.changePercent >= 0 ? '▲' : '▼'} {index.change >= 0 ? '+' : ''}{index.change.toFixed(2)} ({index.changePercent >= 0 ? '+' : ''}{index.changePercent.toFixed(2)}%)
                                  </div>
                                </button>
                              )
                            })}
                          </div>
                        </div>
                      )}

                      {/* Market Headlines Card - 1/2 width */}
                      {(macroTopics.length > 0 || politicalTopics.length > 0) && (
                        <div className="border rounded-lg p-4 shadow-lg overflow-auto" style={{ backgroundColor: '#FFFFFF', maxHeight: '600px' }}>
                          <h3 className="text-lg font-bold text-gray-900 mb-4">Market Headlines</h3>

                          {/* Macro Topics */}
                          {macroTopics.length > 0 && (
                            <div className="mb-4">
                              <h4 className="text-sm font-semibold text-gray-700 mb-2">Macro & Economic</h4>
                              <div className="space-y-2">
                                {macroTopics.slice(0, 3).map((topic: any) => {
                                  const urgency = topic.urgency || 'medium'
                                  const urgencyColor = urgency === 'high' ? 'bg-red-100 text-red-700' :
                                                     urgency === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                                     'bg-green-100 text-green-700'
                                  const topicKey = `macro-${topic.id}`
                                  const isExpanded = expandedTopics[topicKey] || false
                                  return (
                                    <div key={topic.id} className="border rounded-lg p-2 shadow-sm bg-white">
                                      <div className="cursor-pointer" onClick={() => setExpandedTopics(prev => ({...prev, [topicKey]: !prev[topicKey]}))}>
                                        <div className="flex items-start justify-between mb-1">
                                          <div className="flex items-center gap-1 flex-1">
                                            <h5 className="text-[11px] font-bold text-gray-900">{topic.name}</h5>
                                            <ChevronDown className={`h-2.5 w-2.5 text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} />
                                          </div>
                                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-semibold ${urgencyColor}`}>{urgency.toUpperCase()}</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-[9px] text-gray-500">
                                          <span>{topic.articles?.length || 0} source{(topic.articles?.length || 0) !== 1 ? 's' : ''}</span>
                                        </div>
                                      </div>
                                      <div className={`overflow-hidden transition-all duration-300 ease-in-out ${isExpanded ? 'max-h-64 opacity-100 mt-2' : 'max-h-0 opacity-0'}`}>
                                        {topic.articles && topic.articles.length > 0 && (
                                          <div className="space-y-1 border-t pt-2">
                                            {topic.articles.map((article: any) => (
                                              <a key={article.id} href={article.url} target="_blank" rel="noopener noreferrer" className="block p-1 rounded hover:bg-gray-50 transition-colors">
                                                <h6 className="text-[10px] font-medium text-gray-900 mb-0.5 line-clamp-2">{article.title}</h6>
                                                <p className="text-[9px] text-gray-500">{article.source}</p>
                                              </a>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  )
                                })}
                              </div>
                            </div>
                          )}

                          {/* Political Topics */}
                          {politicalTopics.length > 0 && (
                            <div>
                              <h4 className="text-sm font-semibold text-gray-700 mb-2">Political & Policy</h4>
                              <div className="space-y-2">
                                {politicalTopics.slice(0, 3).map((topic: any) => {
                                  const urgency = topic.urgency || 'medium'
                                  const urgencyColor = urgency === 'high' ? 'bg-red-100 text-red-700' :
                                                     urgency === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                                     'bg-green-100 text-green-700'
                                  const topicKey = `political-${topic.id}`
                                  const isExpanded = expandedTopics[topicKey] || false
                                  return (
                                    <div key={topic.id} className="border rounded-lg p-2 shadow-sm bg-white">
                                      <div className="cursor-pointer" onClick={() => setExpandedTopics(prev => ({...prev, [topicKey]: !prev[topicKey]}))}>
                                        <div className="flex items-start justify-between mb-1">
                                          <div className="flex items-center gap-1 flex-1">
                                            <h5 className="text-[11px] font-bold text-gray-900">{topic.name}</h5>
                                            <ChevronDown className={`h-2.5 w-2.5 text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} />
                                          </div>
                                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-semibold ${urgencyColor}`}>{urgency.toUpperCase()}</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-[9px] text-gray-500">
                                          <span>{topic.articles?.length || 0} source{(topic.articles?.length || 0) !== 1 ? 's' : ''}</span>
                                        </div>
                                      </div>
                                      <div className={`overflow-hidden transition-all duration-300 ease-in-out ${isExpanded ? 'max-h-64 opacity-100 mt-2' : 'max-h-0 opacity-0'}`}>
                                        {topic.articles && topic.articles.length > 0 && (
                                          <div className="space-y-1 border-t pt-2">
                                            {topic.articles.map((article: any) => (
                                              <a key={article.id} href={article.url} target="_blank" rel="noopener noreferrer" className="block p-1 rounded hover:bg-gray-50 transition-colors">
                                                <h6 className="text-[10px] font-medium text-gray-900 mb-0.5 line-clamp-2">{article.title}</h6>
                                                <p className="text-[9px] text-gray-500">{article.source}</p>
                                              </a>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  )
                                })}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Your Interests Section - Now Below */}
                    <div className="mb-6">
                      <div className="border rounded-lg p-4 shadow-lg" style={{ backgroundColor: '#FFFFFF' }}>
                        <h3 className="text-lg font-bold text-gray-900 mb-4">Your Interests</h3>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 mb-4">
                          {tickerData.slice(0, 6).map((ticker) => (
                            <button
                              key={ticker.symbol}
                              onClick={() => handleTickerSelect(ticker.symbol)}
                              className={`p-2 bg-gray-50 border border-gray-200 rounded text-left hover:bg-gray-100 transition-colors ${selectedTicker === ticker.symbol ? 'bg-blue-50 border-blue-200' : ''}`}
                            >
                              <div className="flex items-center gap-2 mb-1">
                                <img
                                  src={`https://img.logokit.com/ticker/${ticker.symbol}?token=${process.env.NEXT_PUBLIC_LOGO_API_KEY}`}
                                  alt={`${ticker.symbol} logo`}
                                  className="w-6 h-6 rounded object-cover"
                                  onError={(e) => { e.currentTarget.style.display = 'none' }}
                                />
                                <div className="font-medium text-gray-900">{ticker.symbol}</div>
                              </div>
                              <div className={`text-sm ${ticker.changePercent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {ticker.changePercent >= 0 ? '▲' : '▼'} {ticker.changePercent >= 0 ? '+' : ''}{ticker.changePercent.toFixed(2)}%
                              </div>
                            </button>
                          ))}
                        </div>
                        <div className="flex gap-2">
                          <Input
                            placeholder="Add ticker (e.g., AAPL)"
                            value={newTicker}
                            onChange={(e) => setNewTicker(e.target.value)}
                            className="flex-1 h-9 text-sm"
                            onKeyPress={(e) => e.key === "Enter" && addTicker()}
                          />
                          <Button onClick={addTicker} className="h-9 text-sm">
                            <Plus className="h-4 w-4 mr-1" />
                            Add Interest
                          </Button>
                        </div>
                      </div>
                    </div>

                    {/* Remove old macro section duplicate below */}
                    {false && (macroTopics.length > 0 || politicalTopics.length > 0) && (
                      <div className="mb-8">
                        <h2 className="text-2xl font-bold text-gray-900 mb-6">Market Overview</h2>

                        {/* Macro Topics */}
                        {macroTopics.length > 0 && (
                          <div className="mb-6">
                            <h3 className="text-lg font-semibold text-gray-700 mb-3">Macro & Economic</h3>
                            <div className="space-y-3">
                              {macroTopics.map((topic: any) => {
                                const urgency = topic.urgency || 'medium'
                                const urgencyColor = urgency === 'high' ? 'bg-red-100 text-red-700' :
                                                   urgency === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                                   'bg-green-100 text-green-700'

                                const topicKey = `macro-${topic.id}`
                                const isExpanded = expandedTopics[topicKey] || false

                                return (
                                  <div key={topic.id} className="border rounded-lg p-4 shadow-lg bg-white">
                                    <div
                                      className="cursor-pointer"
                                      onClick={() => setExpandedTopics(prev => ({...prev, [topicKey]: !prev[topicKey]}))}
                                    >
                                      <div className="flex items-start justify-between mb-2">
                                        <div className="flex items-center gap-2 flex-1">
                                          <h4 className="text-sm font-bold text-gray-900">{topic.name}</h4>
                                          <ChevronDown
                                            className={`h-3 w-3 text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                                          />
                                        </div>
                                        <div className="flex items-center gap-2">
                                          {topic.sector && (
                                            <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
                                              {topic.sector}
                                            </span>
                                          )}
                                          <span className={`px-2 py-0.5 rounded text-xs font-semibold ${urgencyColor}`}>
                                            {urgency.toUpperCase()}
                                          </span>
                                        </div>
                                      </div>
                                      {topic.description && (
                                        <p className="text-xs text-gray-600 mb-1">{topic.description}</p>
                                      )}
                                      <div className="flex items-center gap-2 text-xs text-gray-500">
                                        <span>{topic.articles?.length || 0} source{(topic.articles?.length || 0) !== 1 ? 's' : ''}</span>
                                      </div>
                                    </div>

                                    {/* Expandable Articles Section */}
                                    <div
                                      className={`overflow-hidden transition-all duration-300 ease-in-out ${
                                        isExpanded ? 'max-h-96 opacity-100 mt-3' : 'max-h-0 opacity-0'
                                      }`}
                                    >
                                      {topic.articles && topic.articles.length > 0 && (
                                        <div className="space-y-2 border-t pt-3">
                                          {topic.articles.map((article: any) => (
                                            <a
                                              key={article.id}
                                              href={article.url}
                                              target="_blank"
                                              rel="noopener noreferrer"
                                              className="block p-2 rounded hover:bg-gray-50 transition-colors"
                                            >
                                              <div className="flex items-start justify-between gap-2">
                                                <div className="flex-1">
                                                  <h5 className="text-xs font-medium text-gray-900 mb-0.5">
                                                    {article.title}
                                                  </h5>
                                                  <p className="text-xs text-gray-500">{article.source}</p>
                                                </div>
                                                {article.published_date && (
                                                  <span className="text-xs text-gray-400 whitespace-nowrap">
                                                    {new Date(article.published_date).toLocaleDateString()}
                                                  </span>
                                                )}
                                              </div>
                                            </a>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        )}

                        {/* Political Topics */}
                        {politicalTopics.length > 0 && (
                          <div className="mb-6">
                            <h3 className="text-lg font-semibold text-gray-700 mb-3">Political & Policy</h3>
                            <div className="space-y-3">
                              {politicalTopics.map((topic: any) => {
                                const urgency = topic.urgency || 'medium'
                                const urgencyColor = urgency === 'high' ? 'bg-red-100 text-red-700' :
                                                   urgency === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                                   'bg-green-100 text-green-700'

                                const topicKey = `political-${topic.id}`
                                const isExpanded = expandedTopics[topicKey] || false

                                return (
                                  <div key={topic.id} className="border rounded-lg p-4 shadow-lg bg-white">
                                    <div
                                      className="cursor-pointer"
                                      onClick={() => setExpandedTopics(prev => ({...prev, [topicKey]: !prev[topicKey]}))}
                                    >
                                      <div className="flex items-start justify-between mb-2">
                                        <div className="flex items-center gap-2 flex-1">
                                          <h4 className="text-sm font-bold text-gray-900">{topic.name}</h4>
                                          <ChevronDown
                                            className={`h-3 w-3 text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                                          />
                                        </div>
                                        <div className="flex items-center gap-2">
                                          {topic.sector && (
                                            <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
                                              {topic.sector}
                                            </span>
                                          )}
                                          <span className={`px-2 py-0.5 rounded text-xs font-semibold ${urgencyColor}`}>
                                            {urgency.toUpperCase()}
                                          </span>
                                        </div>
                                      </div>
                                      {topic.description && (
                                        <p className="text-xs text-gray-600 mb-1">{topic.description}</p>
                                      )}
                                      <div className="flex items-center gap-2 text-xs text-gray-500">
                                        <span>{topic.articles?.length || 0} source{(topic.articles?.length || 0) !== 1 ? 's' : ''}</span>
                                      </div>
                                    </div>

                                    {/* Expandable Articles Section */}
                                    <div
                                      className={`overflow-hidden transition-all duration-300 ease-in-out ${
                                        isExpanded ? 'max-h-96 opacity-100 mt-3' : 'max-h-0 opacity-0'
                                      }`}
                                    >
                                      {topic.articles && topic.articles.length > 0 && (
                                        <div className="space-y-2 border-t pt-3">
                                          {topic.articles.map((article: any) => (
                                            <a
                                              key={article.id}
                                              href={article.url}
                                              target="_blank"
                                              rel="noopener noreferrer"
                                              className="block p-2 rounded hover:bg-gray-50 transition-colors"
                                            >
                                              <div className="flex items-start justify-between gap-2">
                                                <div className="flex-1">
                                                  <h5 className="text-xs font-medium text-gray-900 mb-0.5">
                                                    {article.title}
                                                  </h5>
                                                  <p className="text-xs text-gray-500">{article.source}</p>
                                                </div>
                                                {article.published_date && (
                                                  <span className="text-xs text-gray-400 whitespace-nowrap">
                                                    {new Date(article.published_date).toLocaleDateString()}
                                                  </span>
                                                )}
                                              </div>
                                            </a>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Section Heading */}
                    <h2 className="text-2xl font-bold text-gray-900 mb-6">Companies</h2>

                    {/* Single Column Layout - One Company Per Row */}
                    <div className="space-y-6">
                      {companiesData.map((company: any) => {
                        if (!company.topics || company.topics.length === 0) return null

                        // Get stock data for this company if available
                        const stockData = tickerData.find(t => t.symbol === company.ticker)

                        // Get only the 3 most urgent topics
                        const topTopics = company.topics.slice(0, 3)

                        return (
                          <div key={company.ticker} id={`company-${company.ticker}`} className="border rounded-lg p-4 shadow-lg bg-white">
                            {/* Company Header - Clickable */}
                            <div
                              className="mb-4 pb-3 border-b border-gray-300 cursor-pointer hover:bg-gray-50 transition-colors rounded-lg p-2 -m-2"
                              onClick={() => router.push(`/company/${company.ticker}`)}
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                  <img
                                    src={`https://img.logokit.com/ticker/${company.ticker}?token=${process.env.NEXT_PUBLIC_LOGO_API_KEY}`}
                                    alt={`${company.ticker} logo`}
                                    className="w-12 h-12 rounded-lg object-cover"
                                    onError={(e) => {
                                      e.currentTarget.style.display = 'none'
                                    }}
                                  />
                                  <div>
                                    <h2 className="text-xl font-bold text-gray-900 hover:text-blue-600 transition-colors">
                                      {company.company_name || company.ticker}
                                    </h2>
                                    <p className="text-sm text-gray-600 mt-0.5">
                                      {company.ticker} • {company.topics.length} topic{company.topics.length !== 1 ? 's' : ''} • Click to view details
                                    </p>
                                  </div>
                                </div>
                                {stockData && (
                                  <div className="text-right">
                                    <div className="text-lg font-semibold text-gray-900">
                                      ${stockData.price.toFixed(2)}
                                    </div>
                                    <div className={`text-sm font-medium ${stockData.changePercent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                      {stockData.changePercent >= 0 ? '▲' : '▼'} {stockData.changePercent >= 0 ? '+' : ''}{stockData.changePercent.toFixed(2)}%
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* Topics as Rows */}
                            <div className="space-y-3">
                              {topTopics.map((topic: any) => {
                                const urgency = topic.urgency || 'medium'
                                const urgencyColor = urgency === 'high' ? 'bg-red-100 text-red-700' :
                                                   urgency === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                                   'bg-green-100 text-green-700'

                                const topicKey = `${company.ticker}-${topic.id}`
                                const isExpanded = expandedTopics[topicKey] || false
                                const isHighlighted = highlightedTopics[topicKey] && highlightedTopics[topicKey] > Date.now()

                                return (
                                  <div
                                    key={topic.id}
                                    className={`border rounded-lg p-3 bg-white transition-all duration-300 ${isHighlighted ? 'rainbow-glow' : ''}`}
                                  >
                                    {/* Topic Header - Clickable */}
                                    <div
                                      className="cursor-pointer"
                                      onClick={() => setExpandedTopics(prev => ({...prev, [topicKey]: !prev[topicKey]}))}
                                    >
                                      <div className="flex items-start justify-between mb-1">
                                        <div className="flex items-center gap-2 flex-1">
                                          <h3 className="text-sm font-bold text-gray-900">{topic.name || topic.topic}</h3>
                                          <ChevronDown
                                            className={`h-3 w-3 text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                                          />
                                        </div>
                                        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${urgencyColor}`}>
                                          {urgency.toUpperCase()}
                                        </span>
                                      </div>
                                      {topic.description && (
                                        <p className="text-xs text-gray-600 mb-1">{topic.description}</p>
                                      )}
                                      <div className="flex items-center gap-2 text-xs text-gray-500">
                                        <span>{topic.articles?.length || 0} source{(topic.articles?.length || 0) !== 1 ? 's' : ''}</span>
                                      </div>
                                    </div>

                                    {/* Expandable Articles Section with Animation */}
                                    <div
                                      className={`overflow-hidden transition-all duration-300 ease-in-out ${
                                        isExpanded ? 'max-h-96 opacity-100 mt-3' : 'max-h-0 opacity-0'
                                      }`}
                                    >
                                      {topic.articles && topic.articles.length > 0 && (
                                        <ul className="space-y-1.5 border-t border-gray-200 pt-2">
                                          {topic.articles.map((article: any, idx: number) => (
                                            <li key={`${topic.id}-${idx}`} className="flex items-start gap-2">
                                              <span className="text-gray-400 mt-1">•</span>
                                              <div className="flex-1">
                                                <a
                                                  href={article.url}
                                                  target="_blank"
                                                  rel="noopener noreferrer"
                                                  className="text-sm font-medium text-gray-900 hover:text-blue-600 hover:underline transition-colors"
                                                >
                                                  {article.title}
                                                </a>
                                                {article.description && (
                                                  <p className="text-xs text-gray-600 mt-0.5 line-clamp-2">{article.description}</p>
                                                )}
                                              </div>
                                            </li>
                                          ))}
                                        </ul>
                                      )}
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </>
                ) : (
                  // Group articles by topic for other tabs
                  (() => {
                    const groupedArticles = articles.reduce((acc: any, article: NewsArticle) => {
                      const topic = article.tags && article.tags.length > 0
                        ? (typeof article.tags[0] === 'string' ? article.tags[0] : article.tags[0]?.name || 'Uncategorized')
                        : 'Uncategorized'

                      if (!acc[topic]) {
                        acc[topic] = []
                      }
                      acc[topic].push(article)
                      return acc
                    }, {})

                    return Object.entries(groupedArticles).map(([topic, topicArticles]: [string, any]) => {
                      if (!topicArticles || topicArticles.length === 0) return null

                      const firstArticle = topicArticles[0]
                      const urgency = firstArticle?.urgency || 'medium'
                      const description = firstArticle?.topic_description || firstArticle?.preview || ''
                      const company = firstArticle?.category || ''

                      // Urgency badge color
                      const urgencyColor = urgency === 'high' ? 'bg-red-100 text-red-700' :
                                         urgency === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                         'bg-green-100 text-green-700'

                      return (
                      <div key={topic} className="border rounded-lg p-4 bg-white">
                        {/* Topic Header */}
                        <div className="mb-3 pb-3 border-b border-gray-200">
                          <div className="flex items-start justify-between mb-2">
                            <h3 className="text-lg font-bold text-gray-900 flex-1">{topic}</h3>
                            <span className={`px-2 py-1 rounded text-xs font-semibold ${urgencyColor}`}>
                              {urgency.toUpperCase()}
                            </span>
                          </div>
                          {description && (
                            <p className="text-sm text-gray-600 mb-2">{description}</p>
                          )}
                          <div className="flex items-center gap-3 text-xs text-gray-500">
                            {company && <span className="font-medium">{company}</span>}
                            {company && <span>•</span>}
                            <span>{topicArticles.length} article{topicArticles.length > 1 ? 's' : ''}</span>
                            <span>•</span>
                            <span>{firstArticle.date}</span>
                          </div>
                        </div>

                        {/* Articles as bullets */}
                        <ul className="space-y-2">
                          {topicArticles.map((article: NewsArticle) => (
                            <li key={article.id} className="flex items-start gap-2">
                              <span className="text-gray-400 mt-1">•</span>
                              <div className="flex-1">
                                <a
                                  href={article.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-sm font-medium text-gray-900 hover:text-blue-600 hover:underline transition-colors"
                                >
                                  {article.title}
                                </a>
                                <p className="text-xs text-gray-600 mt-1 line-clamp-2">{article.preview}</p>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                      )
                    })
                  })()
                )}
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Mobile Sidebar Modal */}
      {showMobileSidebar && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-end z-50 lg:hidden">
          <div className="bg-white w-80 h-full overflow-y-auto">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Market Data</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowMobileSidebar(false)}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            
            {/* Chart Section */}
            <div className="p-4">
              <StockChart
                stockData={stockData}
                chartData={chartData}
                onTimeframeChange={handleTimeframeChange}
                selectedTimeframe={selectedTimeframe}
              />
            </div>

            {/* Interests List */}
            <div className="p-4 space-y-2">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Your Interests</h4>
              <div className="grid grid-cols-2 gap-1">
                {tickerData.slice(0, 6).map((ticker) => (
                  <div key={ticker.symbol} className="relative group">
                    <button
                      onClick={() => {
                        handleTickerSelect(ticker.symbol)
                        setShowMobileSidebar(false)
                      }}
                      className={`w-full p-1.5 bg-white border border-gray-200 rounded text-left hover:bg-gray-50 transition-colors text-xs ${
                        selectedTicker === ticker.symbol ? 'bg-blue-50 border-blue-200' : ''
                      }`}
                    >
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <img
                          src={`https://img.logokit.com/ticker/${ticker.symbol}?token=${process.env.NEXT_PUBLIC_LOGO_API_KEY}`}
                          alt={`${ticker.symbol} logo`}
                          className="w-5 h-5 rounded object-cover"
                          onError={(e) => {
                            e.currentTarget.style.display = 'none'
                          }}
                        />
                        <div className="font-medium text-gray-900">{ticker.symbol}</div>
                      </div>
                      <div className="text-gray-600 mb-0.5">${ticker.price.toFixed(2)}</div>
                      <div className={`font-medium ${
                        ticker.change >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {ticker.change >= 0 ? '+' : ''}{ticker.changePercent.toFixed(1)}%
                      </div>
                    </button>
                    <button
                      onClick={() => {
                        setShowMobileSidebar(false)
                        router.push(`/companies/${ticker.symbol}`)
                      }}
                      className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity bg-blue-600 text-white rounded px-1 py-0.5 text-[8px] hover:bg-blue-700"
                      title={`View ${ticker.symbol} company page`}
                    >
                      VIEW
                    </button>
                  </div>
                ))}
                {tickerData.length > 6 && (
                  <button
                    onClick={() => {
                      setShowAllTickers(true)
                      setShowMobileSidebar(false)
                    }}
                    className="p-1.5 bg-gray-100 border border-gray-300 rounded text-center hover:bg-gray-200 transition-colors text-xs text-gray-600 flex items-center justify-center"
                  >
                    <span>+{tickerData.length - 6} more...</span>
                  </button>
                )}
              </div>
              
              {/* Add New Interest */}
              <div className="space-y-2">
                <Input
                  placeholder="Enter Interests (Ticker, news, etc.)"
                  value={newTicker}
                  onChange={(e) => setNewTicker(e.target.value)}
                  className="w-full h-8 text-sm"
                  onKeyPress={(e) => e.key === "Enter" && addTicker()}
                />
                <Button onClick={addTicker} className="w-full h-8 text-sm">
                  Add Interest
                </Button>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* All Tickers Modal */}
      {showAllTickers && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">All Your Interests</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowAllTickers(false)}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            
            <div className="overflow-y-auto max-h-96">
              <div className="grid grid-cols-3 gap-2">
                {tickerData.map((ticker) => (
                  <div key={ticker.symbol} className="relative group">
                    <button
                      onClick={() => {
                        handleTickerSelect(ticker.symbol)
                        setShowAllTickers(false)
                      }}
                      className={`w-full p-2 bg-white border border-gray-200 rounded text-left hover:bg-gray-50 transition-colors text-sm ${
                        selectedTicker === ticker.symbol ? 'bg-blue-50 border-blue-200' : ''
                      }`}
                    >
                      <div className="font-semibold text-gray-900 mb-1">{ticker.symbol}</div>
                      <div className="text-gray-600 mb-1">${ticker.price.toFixed(2)}</div>
                      <div className={`font-medium text-sm ${
                        ticker.change >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {ticker.change >= 0 ? '+' : ''}{ticker.change.toFixed(2)} ({ticker.changePercent >= 0 ? '+' : ''}{ticker.changePercent.toFixed(2)}%)
                      </div>
                    </button>
                    <button
                      onClick={() => {
                        setShowAllTickers(false)
                        router.push(`/companies/${ticker.symbol}`)
                      }}
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-blue-600 text-white rounded px-2 py-1 text-xs hover:bg-blue-700"
                      title={`View ${ticker.symbol} company page`}
                    >
                      VIEW
                    </button>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="flex justify-end mt-4 pt-4 border-t border-gray-200">
              <Button
                variant="outline"
                onClick={() => setShowAllTickers(false)}
                className="px-4"
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Query History Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Query History</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowHistoryModal(false)}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            
            <div className="overflow-y-auto max-h-64">
              {queryHistory.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No queries yet. Start chatting to build your history!</p>
              ) : (
                <div className="space-y-3">
                  {queryHistory.map((query, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <p className="font-medium text-gray-900 mb-1">{query.query}</p>
                          {query.response && (
                            <p className="text-sm text-gray-600 line-clamp-2">{query.response}</p>
                          )}
                          <p className="text-xs text-gray-400 mt-2">
                            {formatQueryTime(query.timestamp)}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSearchQuery(query.query)
                              setShowHistoryModal(false)
                            }}
                            className="h-7 px-2 text-xs"
                          >
                            Use
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => deleteQueryFromHistory(query.id || '')}
                            className="h-7 px-2 text-xs text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="w-3 h-3 mr-1" />
                            Delete
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <div className="flex justify-end mt-4 pt-4 border-t border-gray-200">
              <Button
                variant="outline"
                onClick={() => setShowHistoryModal(false)}
                className="px-4"
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Thinking Steps Display */}
      {showThinkingSteps && thinkingSteps.length > 0 && (
        <div className="fixed bottom-28 left-0 right-0 z-40 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className="relative">
              {thinkingSteps.map((step, index) => {
                const opacity = index === 0 ? 'opacity-100' :
                              index === 1 ? 'opacity-70' :
                              index === 2 ? 'opacity-40' : 'opacity-20'

                const scale = index === 0 ? 'scale-100' :
                             index === 1 ? 'scale-95' :
                             index === 2 ? 'scale-90' : 'scale-85'

                const blur = index === 0 ? '' :
                            index === 1 ? 'backdrop-blur-sm' : 'backdrop-blur-xs'

                return (
                  <div
                    key={step.id}
                    className={`absolute inset-0 bg-white/20 backdrop-blur-md border border-gray-300/30 rounded-2xl shadow-lg px-4 py-3 w-full transition-all duration-500 ${opacity} ${scale} ${blur}`}
                    style={{
                      transform: `translateY(${index * -8}px) ${scale}`,
                      zIndex: 40 - index
                    }}
                  >
                    <div className="flex items-center gap-2">
                      {index === 0 && (
                        <div className="animate-spin rounded-full h-3 w-3 border-2 border-blue-600 border-t-transparent"></div>
                      )}
                      <span className="text-sm text-gray-700 line-clamp-2">{step.text}</span>
                    </div>
                  </div>
                )
              })}
              {/* Spacer to maintain height */}
              <div className="invisible bg-white/20 backdrop-blur-md border border-gray-300/30 rounded-2xl shadow-lg px-4 py-3 w-full">
                <div className="flex items-center gap-2">
                  <div className="rounded-full h-3 w-3"></div>
                  <span className="text-sm">Placeholder</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Gemini Response Box */}
      {showChatResponse && (
        <div className="fixed bottom-28 left-0 right-0 z-40 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className="bg-white/20 backdrop-blur-md border border-gray-300/30 rounded-2xl shadow-lg px-4 py-3 w-full">
              <div className="flex items-start gap-3">
                <div className="flex-1">
                  <div className="text-sm text-gray-700 line-clamp-3">
                    {isChatResponseLoading ? (
                      <div className="flex items-center gap-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div>
                        <span>Thinking...</span>
                      </div>
                    ) : (
                      chatResponse
                    )}
                  </div>
                </div>
                {!isChatResponseLoading && (
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowExpandedResponse(true)}
                      className="h-6 w-6 p-0 hover:bg-gray-200/50"
                      title="Expand response"
                    >
                      <Maximize2 className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowChatResponse(false)}
                      className="h-6 w-6 p-0 hover:bg-gray-200/50"
                      title="Close response"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Floating Chat Box - Same width as Your Interests */}
      {showChat ? (
        <div className="fixed bottom-6 left-0 right-0 z-50 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className={`bg-white/20 backdrop-blur-md border border-gray-300/30 rounded-2xl shadow-lg px-4 py-3 w-full transform transition-all duration-200 ease-out origin-bottom-right ${
              isClosingChat
                ? 'translate-y-4 translate-x-4 opacity-0 scale-75'
                : 'translate-y-0 translate-x-0 opacity-100 scale-100'
            }`}>
              <div className="flex gap-2">
                <textarea
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask me anything about the news..."
                  className="flex-1 resize-none rounded-lg border border-gray-300/50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent bg-white/10 backdrop-blur-sm placeholder-gray-600"
                  rows={2}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      if (chatInput.trim()) {
                        setSearchQuery(chatInput)
                        handleChatSubmit()
                        setChatInput("")
                      }
                    }
                  }}
                />
                <Button
                  size="sm"
                  onClick={() => {
                    if (chatInput.trim()) {
                      setSearchQuery(chatInput)
                      handleChatSubmit()
                      setChatInput("")
                    }
                  }}
                  disabled={!chatInput.trim()}
                  className="h-auto px-3 bg-blue-600 hover:bg-blue-700"
                >
                  <Send className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCloseChat}
                  className="h-auto px-2 hover:bg-gray-200/50"
                >
                  <Minimize2 className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="fixed bottom-6 z-50" style={{ right: 'calc(16.67% + 2rem)' }}>
          <Button
            onClick={() => setShowChat(true)}
            className="bg-blue-600/90 hover:bg-blue-700/90 backdrop-blur-sm text-white rounded-full h-12 w-12 shadow-lg border border-blue-500/20 transition-all duration-200 hover:scale-105"
            size="sm"
          >
            <MessageCircle className="h-5 w-5" />
          </Button>
        </div>
      )}

      {/* Expanded Response Modal */}
      {showExpandedResponse && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Gemini Response</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowExpandedResponse(false)}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            
            <div className="overflow-y-auto max-h-96">
              <div className="prose prose-sm max-w-none">
                <div className="whitespace-pre-wrap text-gray-700 leading-relaxed">
                  {chatResponse}
                </div>
              </div>
            </div>
            
            <div className="flex justify-end mt-4 pt-4 border-t border-gray-200">
              <Button
                variant="outline"
                onClick={() => setShowExpandedResponse(false)}
                className="px-4"
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}