"use client"

import { useState, useEffect, useRef} from "react"
import { useRouter, usePathname } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Search, Bookmark, Rss, User, X, Trash2, BarChart3, MessageCircle, Send, Minimize2, Maximize2, Settings, Plus, Edit, ChevronDown, Building } from "lucide-react"
import { ApiService, NewsArticle, ChatMessage, SearchQuery } from "@/services/api"
import { YahooFinanceService, StockData, ChartData } from "@/services/yahooFinance"
import { StockChart } from "@/components/StockChart"

export default function HavenNewsApp() {
  const router = useRouter()
  const pathname = usePathname()
  const [activeTab, setActiveTab] = useState("personalized")
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
  const [showSystemPromptsModal, setShowSystemPromptsModal] = useState(false)
  const [systemPrompts, setSystemPrompts] = useState<Array<{id: string, name: string, content: string}>>([])
  const [editingPrompt, setEditingPrompt] = useState<{id: string, name: string, content: string} | null>(null)
  
  // Yahoo Finance state
  const [stockData, setStockData] = useState<StockData | null>(null)
  const [chartData, setChartData] = useState<ChartData | null>(null)
  const [selectedTicker, setSelectedTicker] = useState<string>("")
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>("1mo")
  const [tickerData, setTickerData] = useState<StockData[]>([])

  // Portfolio company selector state
  const [selectedPortfolioCompany, setSelectedPortfolioCompany] = useState<string>("")
  const [showCompanyDropdown, setShowCompanyDropdown] = useState(false)

  const tabs = [
    { id: "personalized", label: "Personalized feed", icon: User, href: "/personalized-news" },
    { id: "business-news", label: "Business News", icon: Building, href: "#", hasDropdown: true },
    { id: "portfolio", label: "Portfolio", icon: Rss, href: "/portfolio" },
    { id: "saved", label: "Saved News", icon: Bookmark, href: "/saved-news" },
    { id: "sec-docs", label: "SEC Doc Searcher", icon: Search, href: "/sec-docs" },
  ]

  const timePeriods = ["1D", "1W", "1M", "3M", "1Y"]

  const COMPANIES = [
    { ticker: "AAPL", name: "Apple Inc." },
    { ticker: "MSFT", name: "Microsoft Corporation" },
    { ticker: "GOOGL", name: "Alphabet Inc." },
    { ticker: "AMZN", name: "Amazon.com Inc." },
    { ticker: "NVDA", name: "NVIDIA Corporation" },
    { ticker: "TSLA", name: "Tesla Inc." },
    { ticker: "META", name: "Meta Platforms Inc." },
    { ticker: "JPM", name: "JPMorgan Chase & Co." },
    { ticker: "V", name: "Visa Inc." },
    { ticker: "WMT", name: "Walmart Inc." },
    { ticker: "JNJ", name: "Johnson & Johnson" },
    { ticker: "PG", name: "Procter & Gamble Co." },
    { ticker: "XOM", name: "Exxon Mobil Corporation" },
    { ticker: "BAC", name: "Bank of America Corp." },
    { ticker: "DIS", name: "The Walt Disney Company" },
    { ticker: "NFLX", name: "Netflix Inc." },
    { ticker: "INTC", name: "Intel Corporation" },
    { ticker: "AMD", name: "Advanced Micro Devices Inc." },
    { ticker: "PYPL", name: "PayPal Holdings Inc." },
    { ticker: "ADBE", name: "Adobe Inc." },
  ].sort((a, b) => a.name.localeCompare(b.name))

  // Fake news data for testing
  const fakeNewsData: NewsArticle[] = [
    {
      id: '1',
      title: 'Apple Reports Record Q4 Earnings Amid Strong iPhone 15 Sales',
      preview: 'Apple Inc. exceeded Wall Street expectations with quarterly revenue of $89.5 billion, driven by robust iPhone sales and growing services revenue.',
      source: 'Reuters',
      date: '2h ago',
      sentiment: 'positive',
      tags: ['AAPL', 'earnings']
    },
    {
      id: '2', 
      title: 'Tesla Stock Drops 5% After Cybertruck Production Delays',
      preview: 'Tesla shares fell in after-hours trading following news of further delays in Cybertruck manufacturing due to supply chain constraints.',
      source: 'Bloomberg',
      date: '4h ago',
      sentiment: 'negative',
      tags: ['TSLA', 'production']
    },
    {
      id: '3',
      title: 'Microsoft Azure Cloud Revenue Grows 29% Year-over-Year',
      preview: 'Microsoft Corporation reported strong cloud growth as enterprises continue digital transformation initiatives amid AI integration.',
      source: 'CNBC',
      date: '6h ago', 
      sentiment: 'positive',
      tags: ['MSFT', 'cloud']
    },
    {
      id: '4',
      title: 'NVIDIA Partners with Major Automakers for AI Chip Development',
      preview: 'The semiconductor giant announced new partnerships to develop specialized AI processing units for autonomous vehicle systems.',
      source: 'TechCrunch',
      date: '8h ago',
      sentiment: 'positive', 
      tags: ['NVDA', 'AI']
    },
    {
      id: '5',
      title: 'Amazon Prime Day Sales Hit All-Time High Despite Economic Concerns',
      preview: 'Amazon Web Services reported record-breaking Prime Day performance with over $12 billion in sales across 48 hours.',
      source: 'Wall Street Journal',
      date: '12h ago',
      sentiment: 'positive',
      tags: ['AMZN', 'retail']
    },
    {
      id: '6',
      title: 'Google Faces New Antitrust Investigation in European Union', 
      preview: 'EU regulators launch probe into Alphabet subsidiary practices regarding search engine dominance and advertising revenue.',
      source: 'Financial Times',
      date: '14h ago',
      sentiment: 'negative',
      tags: ['GOOGL', 'regulation']
    },
    {
      id: '7',
      title: 'Meta Announces Major Investment in Virtual Reality Infrastructure',
      preview: 'The social media giant plans to invest $15 billion over next three years in VR technology and metaverse development.',
      source: 'The Verge', 
      date: '16h ago',
      sentiment: 'neutral',
      tags: ['META', 'VR']
    },
    {
      id: '8',
      title: 'Federal Reserve Signals Potential Interest Rate Cuts in 2024',
      preview: 'Fed Chair Jerome Powell indicated flexibility on monetary policy as inflation shows signs of cooling across major sectors.',
      source: 'Associated Press',
      date: '18h ago',
      sentiment: 'positive',
      tags: ['FED', 'rates']
    },
    {
      id: '9',
      title: 'Oil Prices Surge 3% on Middle East Supply Chain Disruptions',
      preview: 'Crude oil futures climbed to $87 per barrel as geopolitical tensions raise concerns about global energy supply stability.',
      source: 'MarketWatch',
      date: '20h ago', 
      sentiment: 'negative',
      tags: ['OIL', 'geopolitics']
    },
    {
      id: '10',
      title: 'Cryptocurrency Market Cap Reaches $2.5 Trillion Milestone',
      preview: 'Bitcoin and Ethereum lead rally as institutional adoption accelerates and regulatory clarity improves across major markets.',
      source: 'CoinDesk',
      date: '22h ago',
      sentiment: 'positive',
      tags: ['BTC', 'ETH']
    },
    {
      id: '11',
      title: 'JPMorgan Chase Reports Strong Q3 Results Despite Economic Headwinds',
      preview: 'The banking giant posted earnings of $4.33 per share, beating analyst expectations on strong trading revenue and loan growth.',
      source: 'Financial Times',
      date: '1d ago',
      sentiment: 'positive',
      tags: ['JPM', 'banking']
    },
    {
      id: '12',
      title: 'Intel Announces $20 Billion Investment in New Ohio Semiconductor Facility',
      preview: 'The chip manufacturer plans to create 3,000 jobs as part of its strategy to compete with Taiwan Semiconductor and Samsung.',
      source: 'TechCrunch',
      date: '1d ago',
      sentiment: 'positive',
      tags: ['INTC', 'manufacturing']
    },
    {
      id: '13',
      title: 'Warner Bros Discovery Stock Plunges on Streaming Subscriber Losses',
      preview: 'The media conglomerate lost 1.8 million HBO Max subscribers in Q3, raising concerns about its streaming strategy competitiveness.',
      source: 'Variety',
      date: '1d ago',
      sentiment: 'negative',
      tags: ['WBD', 'streaming']
    },
    {
      id: '14',
      title: 'Palantir Technologies Secures $178 Million Government Contract',
      preview: 'The data analytics company won a multi-year deal with the Department of Defense for AI-powered intelligence solutions.',
      source: 'Defense News',
      date: '1d ago',
      sentiment: 'positive',
      tags: ['PLTR', 'defense']
    },
    {
      id: '15',
      title: 'Zoom Video Communications Faces Antitrust Investigation in Europe',
      preview: 'EU regulators are examining the company\'s market dominance in video conferencing and potential anti-competitive practices.',
      source: 'Reuters',
      date: '2d ago',
      sentiment: 'negative',
      tags: ['ZM', 'regulation']
    },
    {
      id: '16',
      title: 'Netflix Beats Subscriber Growth Expectations with 8.5 Million New Users',
      preview: 'The streaming giant added more subscribers than anticipated, driven by popular original content and international expansion.',
      source: 'The Hollywood Reporter',
      date: '2d ago',
      sentiment: 'positive',
      tags: ['NFLX', 'streaming']
    },
    {
      id: '17',
      title: 'Salesforce Announces 10% Workforce Reduction Amid Economic Uncertainty',
      preview: 'The cloud software company will lay off approximately 8,000 employees as it focuses on core business operations and cost reduction.',
      source: 'San Francisco Chronicle',
      date: '2d ago',
      sentiment: 'negative',
      tags: ['CRM', 'layoffs']
    },
    {
      id: '18',
      title: 'Ford Motor Company Increases EV Production Target by 40%',
      preview: 'The automaker plans to produce 2 million electric vehicles annually by 2026, accelerating its transition from traditional cars.',
      source: 'Automotive News',
      date: '2d ago',
      sentiment: 'positive',
      tags: ['F', 'EV']
    },
    {
      id: '19',
      title: 'Shopify Partners with TikTok for Enhanced Social Commerce Integration',
      preview: 'The e-commerce platform will allow merchants to sell directly through TikTok videos, expanding social shopping capabilities.',
      source: 'TechCrunch',
      date: '3d ago',
      sentiment: 'positive',
      tags: ['SHOP', 'social']
    },
    {
      id: '20',
      title: 'Johnson & Johnson Settles Talc Lawsuits for $8.9 Billion',
      preview: 'The healthcare giant reached a settlement agreement to resolve thousands of lawsuits alleging its talc products caused cancer.',
      source: 'Wall Street Journal',
      date: '3d ago',
      sentiment: 'negative',
      tags: ['JNJ', 'legal']
    },
    {
      id: '21',
      title: 'Airbnb Reports Record Bookings Despite Economic Slowdown Concerns',
      preview: 'The home-sharing platform saw 115 million nights booked in Q3, with strong international travel demand offsetting domestic weakness.',
      source: 'Travel Weekly',
      date: '3d ago',
      sentiment: 'positive',
      tags: ['ABNB', 'travel']
    },
    {
      id: '22',
      title: 'Uber Stock Rises on Autonomous Vehicle Partnership with Waymo',
      preview: 'The ride-sharing company announced expansion of its self-driving car pilot program to three additional cities.',
      source: 'The Verge',
      date: '3d ago',
      sentiment: 'positive',
      tags: ['UBER', 'autonomous']
    },
    {
      id: '23',
      title: 'Disney+ Subscriber Growth Stalls as Streaming Wars Intensify',
      preview: 'The entertainment giant added only 100,000 new subscribers globally, well below analyst expectations of 2 million additions.',
      source: 'Entertainment Weekly',
      date: '4d ago',
      sentiment: 'negative',
      tags: ['DIS', 'streaming']
    },
    {
      id: '24',
      title: 'Advanced Micro Devices Gains Market Share from Intel in Server CPUs',
      preview: 'AMD\'s EPYC processors now hold 35% of the server CPU market, up from 25% last year, according to Mercury Research.',
      source: 'AnandTech',
      date: '4d ago',
      sentiment: 'positive',
      tags: ['AMD', 'semiconductors']
    },
    {
      id: '25',
      title: 'PayPal Faces Regulatory Scrutiny Over Cryptocurrency Operations',
      preview: 'The SEC is investigating the payment company\'s crypto trading services and stablecoin operations for compliance violations.',
      source: 'CoinTelegraph',
      date: '4d ago',
      sentiment: 'negative',
      tags: ['PYPL', 'crypto']
    }
  ]

  // Fake top-ranked articles for query results
  const topRankedArticles: NewsArticle[] = [
    {
      id: 'top-1',
      title: 'Breaking: Major Tech Acquisition Reshapes AI Industry Landscape',
      preview: 'Industry sources confirm a landmark $47 billion deal that will consolidate AI infrastructure and accelerate autonomous technology development across multiple sectors.',
      source: 'TechCrunch',
      date: 'Just now',
      sentiment: 'positive',
      tags: ['AI', 'M&A']
    },
    {
      id: 'top-2',
      title: 'Federal Reserve Chair Signals Aggressive Rate Policy Shift',
      preview: 'In surprise testimony, Powell indicates potential emergency measures as economic indicators point to unprecedented market volatility in coming quarters.',
      source: 'Wall Street Journal',
      date: '5m ago',
      sentiment: 'negative',
      tags: ['FED', 'policy']
    },
    {
      id: 'top-3',
      title: 'Quantum Computing Breakthrough Threatens Current Encryption Standards',
      preview: 'Researchers demonstrate practical quantum supremacy in cryptography, prompting urgent security reviews across financial and government sectors.',
      source: 'Nature',
      date: '12m ago',
      sentiment: 'neutral',
      tags: ['QUANTUM', 'security']
    },
    {
      id: 'top-4',
      title: 'Global Energy Crisis Triggers Emergency Supply Chain Protocols',
      preview: 'Multiple nations activate strategic reserves as renewable infrastructure failures create widespread shortages affecting manufacturing and transportation.',
      source: 'Reuters',
      date: '18m ago',
      sentiment: 'negative',
      tags: ['ENERGY', 'crisis']
    },
    {
      id: 'top-5',
      title: 'Biotech Firm Announces Revolutionary Cancer Treatment Results',
      preview: 'Phase III trials show 94% efficacy rate for new immunotherapy, potentially transforming oncology treatment protocols worldwide.',
      source: 'Medical Journal',
      date: '25m ago',
      sentiment: 'positive',
      tags: ['BIOTECH', 'health']
    }
  ]

  // Set active tab based on current pathname
  useEffect(() => {
    const pathToTab = {
      '/': 'personalized',
      '/personalized-news': 'personalized',
      '/portfolio': 'portfolio',
      '/saved-news': 'saved',
      '/sec-docs': 'sec-docs'
    }
    const currentTab = pathToTab[pathname as keyof typeof pathToTab] || 'personalized'
    setActiveTab(currentTab)
  }, [pathname])

  // Initialize app with data
const hasInitialized = useRef(false)

useEffect(() => {
  if (!hasInitialized.current) {
    initializeApp()
    // loadQueryHistory()
    loadSystemPrompts()
    hasInitialized.current = true
  }
}, [])

  const loadSystemPrompts = () => {
    try {
      const saved = localStorage.getItem('systemPrompts')
      if (saved) {
        const prompts = JSON.parse(saved)
        setSystemPrompts(Array.isArray(prompts) ? prompts : [])
      }
    } catch (error) {
      console.error('Error loading system prompts:', error)
    }
  }

  const addNewPrompt = () => {
    const newPrompt = {
      id: Date.now().toString(),
      name: '',
      content: ''
    }
    setEditingPrompt(newPrompt)
  }

  const savePrompt = () => {
    if (!editingPrompt || !editingPrompt.name.trim() || !editingPrompt.content.trim()) return

    const updatedPrompts = systemPrompts.some(p => p.id === editingPrompt.id)
      ? systemPrompts.map(p => p.id === editingPrompt.id ? editingPrompt : p)
      : [...systemPrompts, editingPrompt]

    setSystemPrompts(updatedPrompts)
    localStorage.setItem('systemPrompts', JSON.stringify(updatedPrompts))
    setEditingPrompt(null)
  }

  const deletePrompt = (id: string) => {
    const updatedPrompts = systemPrompts.filter(p => p.id !== id)
    setSystemPrompts(updatedPrompts)
    localStorage.setItem('systemPrompts', JSON.stringify(updatedPrompts))
  }

  const editPrompt = (prompt: {id: string, name: string, content: string}) => {
    setEditingPrompt({ ...prompt })
  }

  // Load articles when tab changes (but not for portfolio - wait for user selection)
useEffect(() => {
  if (activeTab !== 'portfolio') {
    const defaultTickers = ["AAPL"]
    loadArticles(defaultTickers)
  }
}, [activeTab])

  // Re-fetch articles when portfolio company changes
  useEffect(() => {
    if (activeTab === 'portfolio' && selectedPortfolioCompany) {
      loadArticles([selectedPortfolioCompany])
    }
  }, [selectedPortfolioCompany])

  const initializeApp = async () => {
    try {
      // Set default tickers
      const defaultTickers = ["AAPL"]
      setTickers(defaultTickers)
      
      // Load initial ticker data
      await loadTickerData(defaultTickers)
      
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
const [cachedPersonalized, setCachedPersonalized] = useState<NewsArticle[]>([])

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
        console.log("Fetching personalized news for tickers:", tickers)
        const data = await ApiService.getPersonalizedNews(tickers)
        setCachedPersonalized(data)
        fetchedArticles = data
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
  if (newTicker.trim() && !tickers.find((t) => t === newTicker.toUpperCase())) {
    const newTickerSymbol = newTicker.toUpperCase()
    const updatedTickers = [...tickers, newTickerSymbol]
    setTickers(updatedTickers)

    // Load data for the new ticker
    try {
      const stockData = await YahooFinanceService.getStockQuote(newTickerSymbol)
      if (stockData) {
        setTickerData(prev => [...prev, stockData])

        // If this is the first ticker, select it
        if (tickers.length === 0) {
          setSelectedTicker(newTickerSymbol)
          await loadChartData(newTickerSymbol, selectedTimeframe)
        }
      }

      // 🔥 Fetch personalized articles for the updated tickers
      console.log("Getting articles for tickers:", updatedTickers)

    } catch (error) {
      console.error('Failed to load new ticker data:', error)
    }

    await loadArticles([newTickerSymbol])
    setNewTicker("")
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

          // If there are suggested articles, insert them into the feed
          if (chatMessage.suggested_articles && chatMessage.suggested_articles.length > 0) {
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

  return (
    <div className="min-h-screen bg-white font-sans">
      <div className="bg-white border-b border-gray-200 pt-2 sm:pt-3 lg:pt-4 fixed top-0 left-0 right-0 z-50">
        <div className="flex flex-col gap-2 sm:gap-3 lg:gap-4">
          <div className="flex items-center justify-between px-4 sm:px-6 lg:px-8">
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-black" style={{letterSpacing: '0.1em'}}>Haven News</h1>
            <Button
              variant="ghost"
              size="sm"
              className="lg:hidden p-2"
              onClick={() => setShowMobileSidebar(true)}
            >
              <BarChart3 className="h-5 w-5" />
            </Button>
          </div>
          
          {/* Horizontal Navigation */}
          <div className="bg-gray-100 border-t border-b border-gray py-1">
            <div className="flex gap-2 sm:gap-4 lg:gap-8 overflow-visible px-4 sm:px-6 lg:px-8">
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
                        className="flex items-center gap-2 sm:gap-3 px-3 sm:px-4 lg:px-6 py-1 sm:py-2 text-xs sm:text-sm tracking-wide whitespace-nowrap text-gray-500 hover:bg-gray-200"
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
                    className="flex items-center gap-2 sm:gap-3 px-3 sm:px-4 lg:px-6 py-1 sm:py-2 text-xs sm:text-sm tracking-wide whitespace-nowrap text-gray-500 hover:bg-gray-200"
                    onClick={() => router.push(tab.href)}
                  >
                    {tab.label}
                  </Button>
                )
              })}
            </div>
          </div>
        </div>

        {/* Scrolling Banner Section */}
        <div className="bg-gray-900 text-white py-2 overflow-hidden">
  <div className="flex animate-marquee whitespace-nowrap">
    {articles.slice(0, 10).map((article) => (
      <a
        key={article.id}
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mx-8 text-sm font-medium hover:underline flex items-center gap-1"
      >
        {getEmoji(article)} {article.title}
      </a>
    ))}
  </div>
</div>

      </div>

      <div className="flex px-4 sm:px-6 lg:px-8 min-h-screen pt-[80px] sm:pt-[100px] lg:pt-[160px]">
        {/* Main Content - Articles */}
        <div className="flex-1 lg:mr-6">
          <div className="py-3 sm:py-4 lg:py-6">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-2 text-gray-600">Loading articles...</span>
              </div>
            ) : articles.length === 0 ? (
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
              <div className="w-full space-y-1 sm:space-y-2">
                
                {/* Existing articles */}
                {articles.map((article: NewsArticle, index: number) => (
                  <div 
                    key={article.id} 
                    className={`border rounded-lg p-3 bg-white hover:bg-gray-50 transition-all duration-300 flex items-center w-full ${
                      newArticles.has(article.id)
                        ? 'animate-slide-in-right border-blue-500'
                        : 'border-gray-200'
                    }`}
                  >
                    <div className="flex gap-4 w-full">
                      <div className="text-xs text-gray-500 font-medium min-w-[60px] sm:min-w-[80px] flex items-center tracking-wide">
                        {article.date.includes(':') && <span className="mr-1">🔥</span>}
                        {article.date}
                      </div>

                      <div className="flex-1 flex flex-col justify-center">
                        <h3 className="font-semibold text-gray-900 mb-1 leading-tight text-xs lg:text-sm tracking-wide">
                          <a href={article.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                            {article.title}
                          </a>
                        </h3>
                        <p className="text-gray-600 text-xs leading-tight tracking-wide">{article.preview}</p>
                      </div>

                      <div className="flex-shrink-0 text-right flex items-center">
                        {(article.tags || []).map((tag: any, index: number) => {
                          const tagText = typeof tag === 'string' ? tag : (tag?.name || String(tag))
                          return (
                            <div key={index} className="text-xs text-gray-500 font-mono tracking-wide mx-0.5 sm:mx-1">
                              {tagText}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Sidebar - News Summary and Tickers */}
        <div className="hidden lg:flex w-80 bg-gray-50 border-l border-gray-200 flex-col sticky top-[80px] sm:top-[100px] lg:top-[160px] h-[calc(100vh-80px)] sm:h-[calc(100vh-100px)] lg:h-[calc(100vh-160px)] overflow-y-auto self-start">
          <div className="p-3 lg:p-4 border-b border-gray-200 flex-shrink-0">
            <h3 className="font-semibold text-gray-900 mb-3">News Summary</h3>
            
            {/* News Overview Summary */}
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 mb-3">News Overview</h4>
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-600">Total Articles</span>
                    <span className="text-sm font-semibold text-gray-900">{articles.length}</span>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-600">Current Section</span>
                    <span className="text-sm font-semibold text-gray-900 capitalize">
                      {activeTab === 'personalized' ? 'Personalized Feed' :
                       activeTab === 'portfolio' ? (selectedPortfolioCompany ? COMPANIES.find(c => c.ticker === selectedPortfolioCompany)?.ticker || 'Portfolio News' : 'Portfolio News') :
                       activeTab === 'saved' ? 'Saved Articles' : 'SEC Documents'}
                    </span>
                  </div>

                  {articles.length > 0 && (
                    <>
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-600">Latest Article</span>
                        <span className="text-sm font-medium text-gray-700">{articles[0]?.date}</span>
                      </div>
                      
                      <div className="pt-2 border-t border-gray-100">
                        <p className="text-xs text-gray-600 mb-1">Recent Activity</p>
                        <p className="text-xs text-gray-800 leading-relaxed">
                          {articles.filter(a => a.sentiment === 'positive').length} positive, {' '}
                          {articles.filter(a => a.sentiment === 'negative').length} negative, {' '}
                          {articles.filter(a => a.sentiment === 'neutral').length} neutral articles
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Portfolio Company Selector - Only show on portfolio page */}
            {activeTab === 'portfolio' && (
              <div className="mb-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">Select Company</h4>
                <div className="relative">
                  <button
                    onClick={() => setShowCompanyDropdown(!showCompanyDropdown)}
                    className="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-left flex items-center justify-between hover:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  >
                    <span className={selectedPortfolioCompany ? "text-gray-900" : "text-gray-500"}>
                      {selectedPortfolioCompany
                        ? `${COMPANIES.find(c => c.ticker === selectedPortfolioCompany)?.name} (${selectedPortfolioCompany})`
                        : "Choose a company..."}
                    </span>
                    <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${showCompanyDropdown ? 'rotate-180' : ''}`} />
                  </button>

                  {showCompanyDropdown && (
                    <div className="absolute z-10 mt-2 w-full bg-white border border-gray-200 rounded-lg shadow-xl max-h-64 overflow-y-auto">
                      {COMPANIES.map((company) => (
                        <button
                          key={company.ticker}
                          onClick={() => {
                            setSelectedPortfolioCompany(company.ticker)
                            setShowCompanyDropdown(false)
                          }}
                          className={`w-full text-left px-3 py-2 hover:bg-blue-50 transition-colors text-xs ${
                            selectedPortfolioCompany === company.ticker ? 'bg-blue-100' : ''
                          }`}
                        >
                          <div className="font-medium text-gray-900">{company.name}</div>
                          <div className="text-xs text-gray-500">{company.ticker}</div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Interests List */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Your Interests</h4>
              <div className="grid grid-cols-2 gap-1">
                {tickerData.slice(0, 6).map((ticker) => (
                  <button
                    key={ticker.symbol}
                    onClick={() => handleTickerSelect(ticker.symbol)}
                    className={`p-1.5 bg-white border border-gray-200 rounded text-left hover:bg-gray-50 transition-colors text-xs ${
                      selectedTicker === ticker.symbol ? 'bg-blue-50 border-blue-200' : ''
                    }`}
                  >
                    <div className="font-medium text-gray-900 mb-0.5">{ticker.symbol}</div>
                    <div className="text-gray-600 mb-0.5">${ticker.price.toFixed(2)}</div>
                    <div className={`font-medium ${
                      ticker.change >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {ticker.change >= 0 ? '+' : ''}{ticker.changePercent.toFixed(1)}%
                    </div>
                  </button>
                ))}
                {tickerData.length > 6 && (
                  <button
                    onClick={() => setShowAllTickers(true)}
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

            {/* System Prompts Section */}
            <div className="mt-6 pt-4 border-t border-gray-300">
              <h4 className="text-sm font-medium text-gray-700 mb-3">System Prompts</h4>
              <p className="text-xs text-gray-600 mb-3">
                Customize how the AI assistant responds to your queries by modifying the system prompts.
              </p>
              <Button 
                onClick={() => setShowSystemPromptsModal(true)}
                variant="outline"
                className="w-full h-8 text-sm flex items-center gap-2"
              >
                <Settings className="h-3 w-3" />
                Configure Prompts
              </Button>
            </div>

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
                  <button
                    key={ticker.symbol}
                    onClick={() => {
                      handleTickerSelect(ticker.symbol)
                      setShowMobileSidebar(false)
                    }}
                    className={`p-1.5 bg-white border border-gray-200 rounded text-left hover:bg-gray-50 transition-colors text-xs ${
                      selectedTicker === ticker.symbol ? 'bg-blue-50 border-blue-200' : ''
                    }`}
                  >
                    <div className="font-medium text-gray-900 mb-0.5">{ticker.symbol}</div>
                    <div className="text-gray-600 mb-0.5">${ticker.price.toFixed(2)}</div>
                    <div className={`font-medium ${
                      ticker.change >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {ticker.change >= 0 ? '+' : ''}{ticker.changePercent.toFixed(1)}%
                    </div>
                  </button>
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
                  <button
                    key={ticker.symbol}
                    onClick={() => {
                      handleTickerSelect(ticker.symbol)
                      setShowAllTickers(false)
                    }}
                    className={`p-2 bg-white border border-gray-200 rounded text-left hover:bg-gray-50 transition-colors text-sm ${
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
        <div className="fixed bottom-28 left-48 right-48 lg:left-48 lg:right-[512px] z-40">
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
      )}

      {/* Gemini Response Box */}
      {showChatResponse && (
        <div className="fixed bottom-28 left-48 right-48 lg:left-48 lg:right-[512px] z-40">
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
      )}

      {/* Floating Chat Box */}
      <div className="fixed bottom-6 left-48 right-48 lg:left-48 lg:right-[512px] z-50">
        {showChat ? (
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
        ) : (
          <div className="fixed bottom-6 right-48 lg:right-[512px] z-50">
            <Button
              onClick={() => setShowChat(true)}
              className="bg-blue-600/90 hover:bg-blue-700/90 backdrop-blur-sm text-white rounded-full h-12 w-12 shadow-lg border border-blue-500/20 transition-all duration-200 hover:scale-105"
              size="sm"
            >
              <MessageCircle className="h-5 w-5" />
            </Button>
          </div>
        )}
      </div>

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

      {/* System Prompts Modal */}
      {showSystemPromptsModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">System Prompts Configuration</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowSystemPromptsModal(false)
                  setEditingPrompt(null)
                }}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            
            {editingPrompt ? (
              // Editing/Adding Prompt Interface
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Prompt Name
                  </label>
                  <Input
                    value={editingPrompt.name}
                    onChange={(e) => setEditingPrompt({...editingPrompt, name: e.target.value})}
                    placeholder="Enter a name for this prompt (e.g., 'Financial Analysis', 'News Summarizer')"
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    System Prompt Content
                  </label>
                  <textarea
                    value={editingPrompt.content}
                    onChange={(e) => setEditingPrompt({...editingPrompt, content: e.target.value})}
                    className="w-full h-64 p-3 border border-gray-300 rounded-md resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                    placeholder="Enter the system prompt content. This will guide how the AI responds to queries..."
                  />
                </div>
                <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                  <Button
                    variant="outline"
                    onClick={() => setEditingPrompt(null)}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={savePrompt}
                    disabled={!editingPrompt.name.trim() || !editingPrompt.content.trim()}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300"
                  >
                    Save Prompt
                  </Button>
                </div>
              </div>
            ) : (
              // List of Prompts Interface
              <div className="space-y-4">
                {systemPrompts.length === 0 ? (
                  <div className="text-center py-8">
                    <Settings className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No Custom Prompts</h3>
                    <p className="text-gray-600 mb-4">
                      Create custom system prompts to personalize how the AI assistant responds to your queries.
                    </p>
                    <Button
                      onClick={addNewPrompt}
                      className="bg-blue-600 hover:bg-blue-700 flex items-center gap-2"
                    >
                      <Plus className="h-4 w-4" />
                      Add System Prompt
                    </Button>
                  </div>
                ) : (
                  <>
                    <div className="flex justify-between items-center">
                      <p className="text-gray-600">Manage your custom system prompts</p>
                      <Button
                        onClick={addNewPrompt}
                        className="bg-blue-600 hover:bg-blue-700 flex items-center gap-2"
                        size="sm"
                      >
                        <Plus className="h-4 w-4" />
                        Add System Prompt
                      </Button>
                    </div>
                    <div className="max-h-96 overflow-y-auto space-y-3">
                      {systemPrompts.map((prompt) => (
                        <div key={prompt.id} className="border border-gray-200 rounded-lg p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1">
                              <h4 className="font-medium text-gray-900 mb-1">{prompt.name}</h4>
                              <p className="text-sm text-gray-600 line-clamp-2">
                                {prompt.content}
                              </p>
                            </div>
                            <div className="flex gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => editPrompt(prompt)}
                                className="h-7 px-2 text-xs"
                              >
                                <Edit className="w-3 h-3 mr-1" />
                                Edit
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => deletePrompt(prompt.id)}
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
                  </>
                )}
                <div className="flex justify-end pt-4 border-t border-gray-200">
                  <Button
                    variant="outline"
                    onClick={() => setShowSystemPromptsModal(false)}
                  >
                    Close
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}