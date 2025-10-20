"use client"

import { useEffect, useState, useRef, useMemo } from "react"
import { YahooFinanceService, StockData, ChartData } from "@/services/yahooFinance"
import { ApiService, NewsArticle } from "@/services/api"
import { TrendingUp, TrendingDown, ChevronLeft, ChevronRight, X, Maximize2, FileText, ExternalLink } from "lucide-react"

interface StockGraphTickerProps {
  tickers: string[]
}

interface TickerWithChart {
  stock: StockData
  chartData: ChartData | null
  articles: NewsArticle[]
}

interface ArticleMarker {
  x: number
  y: number
  article: NewsArticle
  articles?: NewsArticle[] // Multiple articles grouped on same day
  index: number
  timestamp: number
}

type TimeFrame = '1D' | '1W' | '1M' | '1Y' | '5Y'

export function StockGraphTicker({ tickers }: StockGraphTickerProps) {
  const [tickerDataWithCharts, setTickerDataWithCharts] = useState<TickerWithChart[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedStock, setSelectedStock] = useState<TickerWithChart | null>(null)
  const [selectedArticle, setSelectedArticle] = useState<NewsArticle | null>(null)
  const [selectedTimeFrame, setSelectedTimeFrame] = useState<TimeFrame>('1D')
  const [timeFrameChartData, setTimeFrameChartData] = useState<ChartData | null>(null)
  const [loadingTimeFrame, setLoadingTimeFrame] = useState(false)
  const [timeFramePriceChange, setTimeFramePriceChange] = useState<{ change: number, changePercent: number } | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const articlesListRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const fetchData = async () => {
      if (!tickers || tickers.length === 0) {
        setLoading(false)
        return
      }

      try {
        const dataPromises = tickers.map(async (ticker) => {
          const [stock, chart, articles] = await Promise.all([
            YahooFinanceService.getStockQuote(ticker),
            YahooFinanceService.getChartData(ticker, "5m", "1d"), // 5-minute intervals for 1 day
            ApiService.getPersonalizedNews([ticker]).catch(() => []) // Fetch articles for this ticker
          ])

          return stock ? { stock, chartData: chart, articles: articles || [] } : null
        })

        const results = await Promise.all(dataPromises)
        const validData = results.filter((item): item is TickerWithChart => item !== null)
        setTickerDataWithCharts(validData)
      } catch (error) {
        console.error("Error fetching ticker data:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    // Refresh every 60 seconds
    const interval = setInterval(fetchData, 60000)
    return () => clearInterval(interval)
  }, [tickers])

  const scroll = (direction: 'left' | 'right') => {
    if (scrollContainerRef.current) {
      const scrollAmount = 200
      scrollContainerRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth'
      })
    }
  }

  // Fetch chart data for selected timeframe
  useEffect(() => {
    const fetchTimeFrameData = async () => {
      if (!selectedStock) return

      setLoadingTimeFrame(true)
      try {
        const timeFrameMap: Record<TimeFrame, { interval: string, range: string }> = {
          '1D': { interval: '5m', range: '1d' },
          '1W': { interval: '30m', range: '5d' },
          '1M': { interval: '1d', range: '1mo' },
          '1Y': { interval: '1d', range: '1y' },
          '5Y': { interval: '1wk', range: '5y' }
        }

        const { interval, range } = timeFrameMap[selectedTimeFrame]
        const chartData = await YahooFinanceService.getChartData(
          selectedStock.stock.symbol,
          interval,
          range
        )
        setTimeFrameChartData(chartData)

        // Calculate price change for this timeframe
        if (chartData && chartData.data.length > 0) {
          const firstPrice = chartData.data[0].close
          const lastPrice = chartData.data[chartData.data.length - 1].close
          const change = lastPrice - firstPrice
          const changePercent = (change / firstPrice) * 100
          setTimeFramePriceChange({ change, changePercent })
        }
      } catch (error) {
        console.error('Error fetching timeframe data:', error)
      } finally {
        setLoadingTimeFrame(false)
      }
    }

    fetchTimeFrameData()
  }, [selectedStock, selectedTimeFrame])

  if (loading) {
    return (
      <div className="bg-white border-b border-gray-300 py-2 flex items-center justify-center">
        <div className="animate-pulse text-xs text-gray-700">Loading market data...</div>
      </div>
    )
  }

  if (tickerDataWithCharts.length === 0) {
    return (
      <div className="bg-white border-b border-gray-300 py-2 flex items-center justify-center">
        <div className="text-xs text-gray-500">Add tickers to see live market data</div>
      </div>
    )
  }

  return (
    <>
      <div className="bg-white border-b border-gray-300">
        {/* Scrollable Container */}
        <div
          ref={scrollContainerRef}
          className="overflow-x-auto overflow-y-hidden scrollbar-hide py-3 px-2"
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        >
          <div className="flex flex-col gap-3">
            {tickerDataWithCharts.map((item) => (
              <div
                key={item.stock.symbol}
                onClick={() => setSelectedStock(item)}
                className="bg-gray-50 border border-gray-300 p-3 hover:bg-gray-100 transition-colors cursor-pointer group/card relative shadow-sm"
              >
                {/* Magnify icon on hover */}
                <div className="absolute top-2 right-2 opacity-0 group-hover/card:opacity-100 transition-opacity">
                  <Maximize2 className="w-3 h-3 text-gray-600" />
                </div>

                {/* Header: Symbol, Price, Change */}
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div
                      className="font-black text-base uppercase tracking-wide text-black"
                      style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}
                    >
                      {item.stock.symbol}
                    </div>
                    <div
                      className="text-xl font-semibold text-gray-900"
                      style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}
                    >
                      ${item.stock.price.toFixed(2)}
                    </div>
                  </div>
                  <div className={`flex items-center gap-0.5 text-xs font-medium px-2 py-1 ${
                    item.stock.changePercent >= 0
                      ? "bg-green-100 text-green-700"
                      : "bg-red-100 text-red-700"
                  }`}>
                    {item.stock.changePercent >= 0 ? (
                      <TrendingUp className="w-3 h-3" />
                    ) : (
                      <TrendingDown className="w-3 h-3" />
                    )}
                    <span>{item.stock.changePercent >= 0 ? '+' : ''}{item.stock.changePercent.toFixed(1)}%</span>
                  </div>
                </div>

                {/* Daily Return Chart */}
                {item.chartData && item.chartData.data.length > 0 && (
                  <div className="h-20 w-full bg-white border border-gray-200 p-2 relative">
                    <DailyReturnChart
                      data={item.chartData.data}
                      isPositive={item.stock.changePercent >= 0}
                      articles={item.articles}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* CSS for hiding scrollbar */}
        <style jsx>{`
          .scrollbar-hide::-webkit-scrollbar {
            display: none;
          }
        `}</style>
      </div>

      {/* Magnified Modal View */}
      {selectedStock && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[100] flex items-center justify-center p-4"
          onClick={() => setSelectedStock(null)}
        >
          <div
            className="bg-white border-2 border-gray-300 p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close Button */}
            <button
              onClick={() => setSelectedStock(null)}
              className="absolute top-4 right-4 bg-gray-100 hover:bg-gray-200 border border-gray-300 p-2 transition-colors"
            >
              <X className="w-5 h-5 text-gray-700" />
            </button>

            {/* Header: Symbol, Price, Change */}
            <div className="flex justify-between items-start mb-6">
              <div>
                <div
                  className="font-black text-3xl text-black uppercase tracking-wide"
                  style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}
                >
                  {selectedStock.stock.symbol}
                </div>
                <div
                  className="text-5xl font-semibold text-gray-900 mt-2"
                  style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}
                >
                  ${selectedStock.stock.price.toFixed(2)}
                </div>
              </div>
              <div className={`flex items-center gap-2 text-xl font-medium px-4 py-2 ${
                (timeFramePriceChange?.changePercent ?? selectedStock.stock.changePercent) >= 0
                  ? "bg-green-100 text-green-700"
                  : "bg-red-100 text-red-700"
              }`}>
                {(timeFramePriceChange?.changePercent ?? selectedStock.stock.changePercent) >= 0 ? (
                  <TrendingUp className="w-6 h-6" />
                ) : (
                  <TrendingDown className="w-6 h-6" />
                )}
                <span>
                  {(timeFramePriceChange?.changePercent ?? selectedStock.stock.changePercent) >= 0 ? '+' : ''}
                  {(timeFramePriceChange?.changePercent ?? selectedStock.stock.changePercent).toFixed(2)}%
                </span>
                <span className="text-base ml-1">
                  ({(timeFramePriceChange?.change ?? selectedStock.stock.change) >= 0 ? '+' : ''}
                  {(timeFramePriceChange?.change ?? selectedStock.stock.change).toFixed(2)})
                </span>
              </div>
            </div>

            {/* Timeframe Selector */}
            <div className="flex gap-2 mb-4">
              {(['1D', '1W', '1M', '1Y', '5Y'] as TimeFrame[]).map((tf) => (
                <button
                  key={tf}
                  onClick={() => setSelectedTimeFrame(tf)}
                  className={`px-4 py-2 text-sm font-medium transition-colors border ${
                    selectedTimeFrame === tf
                      ? 'bg-gray-900 text-white border-black'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                  style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}
                >
                  {tf}
                </button>
              ))}
            </div>

            {/* Large Chart with article markers */}
            {loadingTimeFrame ? (
              <div className="bg-gray-50 border border-gray-300 p-4 mb-6 h-80 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
              </div>
            ) : timeFrameChartData && timeFrameChartData.data.length > 0 ? (
              <div className="bg-white border border-gray-300 p-4 mb-6">
                <InteractiveChart
                  data={timeFrameChartData.data}
                  isPositive={(timeFramePriceChange?.changePercent ?? 0) >= 0}
                  articles={selectedStock.articles}
                  onArticleClick={(article) => setSelectedArticle(article)}
                  onMarkerLineClick={() => {
                    articlesListRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
                  }}
                  timeFrame={selectedTimeFrame}
                />
              </div>
            ) : (
              <div className="bg-gray-50 border border-gray-300 p-4 mb-6 h-80 flex items-center justify-center text-gray-600">
                No chart data available
              </div>
            )}

            {/* Detailed Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-gray-50 border border-gray-300 p-3">
                <div className="text-gray-600 text-sm uppercase tracking-wide" style={{ fontFamily: '"Georgia", "Times New Roman", serif', fontSize: '11px' }}>Open</div>
                <div className="text-xl font-semibold mt-1 text-gray-900" style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}>${selectedStock.stock.open.toFixed(2)}</div>
              </div>
              <div className="bg-gray-50 border border-gray-300 p-3">
                <div className="text-gray-600 text-sm uppercase tracking-wide" style={{ fontFamily: '"Georgia", "Times New Roman", serif', fontSize: '11px' }}>High</div>
                <div className="text-xl font-semibold mt-1 text-green-700" style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}>${selectedStock.stock.high.toFixed(2)}</div>
              </div>
              <div className="bg-gray-50 border border-gray-300 p-3">
                <div className="text-gray-600 text-sm uppercase tracking-wide" style={{ fontFamily: '"Georgia", "Times New Roman", serif', fontSize: '11px' }}>Low</div>
                <div className="text-xl font-semibold mt-1 text-red-700" style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}>${selectedStock.stock.low.toFixed(2)}</div>
              </div>
              <div className="bg-gray-50 border border-gray-300 p-3">
                <div className="text-gray-600 text-sm uppercase tracking-wide" style={{ fontFamily: '"Georgia", "Times New Roman", serif', fontSize: '11px' }}>Prev Close</div>
                <div className="text-xl font-semibold mt-1 text-gray-900" style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}>${selectedStock.stock.previousClose.toFixed(2)}</div>
              </div>
              {selectedStock.stock.volume && (
                <div className="bg-gray-50 border border-gray-300 p-3">
                  <div className="text-gray-600 text-sm uppercase tracking-wide" style={{ fontFamily: '"Georgia", "Times New Roman", serif', fontSize: '11px' }}>Volume</div>
                  <div className="text-xl font-semibold mt-1 text-gray-900" style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}>{(selectedStock.stock.volume / 1000000).toFixed(2)}M</div>
                </div>
              )}
              {selectedStock.stock.marketCap && (
                <div className="bg-gray-50 border border-gray-300 p-3">
                  <div className="text-gray-600 text-sm uppercase tracking-wide" style={{ fontFamily: '"Georgia", "Times New Roman", serif', fontSize: '11px' }}>Market Cap</div>
                  <div className="text-xl font-semibold mt-1 text-gray-900" style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}>${(selectedStock.stock.marketCap / 1000000000).toFixed(2)}B</div>
                </div>
              )}
              {selectedStock.stock.pe && (
                <div className="bg-gray-50 border border-gray-300 p-3">
                  <div className="text-gray-600 text-sm uppercase tracking-wide" style={{ fontFamily: '"Georgia", "Times New Roman", serif', fontSize: '11px' }}>P/E Ratio</div>
                  <div className="text-xl font-semibold mt-1 text-gray-900" style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}>{selectedStock.stock.pe.toFixed(2)}</div>
                </div>
              )}
              {selectedStock.stock.dividend && (
                <div className="bg-gray-50 border border-gray-300 p-3">
                  <div className="text-gray-600 text-sm uppercase tracking-wide" style={{ fontFamily: '"Georgia", "Times New Roman", serif', fontSize: '11px' }}>Dividend</div>
                  <div className="text-xl font-semibold mt-1 text-gray-900" style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}>${selectedStock.stock.dividend.toFixed(2)}</div>
                </div>
              )}
            </div>

            {/* Related Articles Section */}
            {selectedStock.articles.length > 0 && (
              <div ref={articlesListRef} className="border-t-2 border-black pt-6">
                <h3
                  className="text-xl font-black text-black mb-4 flex items-center gap-2 uppercase tracking-wide"
                  style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}
                >
                  <FileText className="w-5 h-5" />
                  Related Articles ({selectedStock.articles.length})
                </h3>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {selectedStock.articles.map((article) => (
                    <a
                      key={article.id}
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block bg-gray-50 hover:bg-gray-100 border border-gray-300 p-4 transition-colors group"
                    >
                      <div className="flex justify-between items-start gap-4">
                        <div className="flex-1">
                          <h4
                            className="text-gray-900 font-semibold mb-1 group-hover:text-blue-700 transition-colors"
                            style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}
                          >
                            {article.title}
                          </h4>
                          <p className="text-gray-600 text-sm line-clamp-2 mb-2">
                            {article.preview}
                          </p>
                          <div className="flex items-center gap-3 text-xs">
                            <span className="text-gray-500">{article.source}</span>
                            <span className="text-gray-500">{article.date}</span>
                            {article.sentiment && (
                              <span className={`px-2 py-0.5 ${
                                article.sentiment === 'positive' ? 'bg-green-100 text-green-700' :
                                article.sentiment === 'negative' ? 'bg-red-100 text-red-700' :
                                'bg-gray-200 text-gray-700'
                              }`}>
                                {article.sentiment}
                              </span>
                            )}
                          </div>
                        </div>
                        <ExternalLink className="w-4 h-4 text-gray-500 flex-shrink-0 group-hover:text-blue-600 transition-colors" />
                      </div>
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Article Preview Popup */}
      {selectedArticle && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[110] flex items-center justify-center p-4"
          onClick={() => setSelectedArticle(null)}
        >
          <div
            className="bg-white border-2 border-gray-300 p-6 max-w-2xl w-full shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-start mb-4">
              <h3
                className="text-2xl font-bold text-gray-900 pr-8"
                style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}
              >
                {selectedArticle.title}
              </h3>
              <button
                onClick={() => setSelectedArticle(null)}
                className="bg-gray-100 hover:bg-gray-200 border border-gray-300 p-2 transition-colors flex-shrink-0"
              >
                <X className="w-5 h-5 text-gray-700" />
              </button>
            </div>

            <div className="flex items-center gap-3 text-sm mb-4">
              <span className="text-gray-600">{selectedArticle.source}</span>
              <span className="text-gray-400">•</span>
              <span className="text-gray-600">{selectedArticle.date}</span>
              {selectedArticle.sentiment && (
                <>
                  <span className="text-gray-400">•</span>
                  <span className={`px-2 py-0.5 text-xs ${
                    selectedArticle.sentiment === 'positive' ? 'bg-green-100 text-green-700' :
                    selectedArticle.sentiment === 'negative' ? 'bg-red-100 text-red-700' :
                    'bg-gray-200 text-gray-700'
                  }`}>
                    {selectedArticle.sentiment}
                  </span>
                </>
              )}
            </div>

            <p className="text-gray-700 mb-6 leading-relaxed">
              {selectedArticle.preview}
            </p>

            <a
              href={selectedArticle.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 bg-gray-900 hover:bg-gray-800 text-white px-6 py-3 border border-black transition-colors font-medium"
              style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}
            >
              Read Full Article
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>
      )}
    </>
  )
}

// Daily return chart showing intraday price movement with article markers
function DailyReturnChart({
  data,
  isPositive,
  articles = [],
  interactive = false
}: {
  data: any[],
  isPositive: boolean,
  articles?: NewsArticle[],
  interactive?: boolean
}) {
  if (!data || data.length === 0) return null

  const prices = data.map(d => d.close).filter(p => p > 0)
  if (prices.length === 0) return null

  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const range = max - min || 1

  // Create path for area chart
  const width = 100
  const height = 100

  const points = prices.map((price, index) => {
    const x = (index / (prices.length - 1)) * width
    const y = height - ((price - min) / range) * height
    return { x, y }
  })

  const linePath = points.map((p, i) =>
    `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`
  ).join(' ')

  const areaPath = `${linePath} L ${width} ${height} L 0 ${height} Z`

  const color = isPositive ? "#10b981" : "#ef4444"
  const gradientId = `gradient-${isPositive ? 'positive' : 'negative'}-${Math.random()}`

  // Calculate article markers positions
  const articleMarkers = articles.map(article => {
    // Parse article date and find closest timestamp in chart data
    const articleDate = new Date(article.date)
    const articleTime = articleDate.getTime()

    // Find the closest data point
    let closestIndex = 0
    let minDiff = Infinity

    data.forEach((point, index) => {
      const pointTime = point.timestamp
      const diff = Math.abs(pointTime - articleTime)
      if (diff < minDiff) {
        minDiff = diff
        closestIndex = index
      }
    })

    // Only show markers for articles within the chart timeframe (within 24 hours)
    if (minDiff > 24 * 60 * 60 * 1000) return null

    const x = (closestIndex / (data.length - 1)) * width
    const price = data[closestIndex].close
    const y = height - ((price - min) / range) * height

    return { x, y, article, index: closestIndex }
  }).filter(m => m !== null)

  return (
    <svg className="w-full h-full" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.05" />
        </linearGradient>
      </defs>

      {/* Area fill */}
      <path
        d={areaPath}
        fill={`url(#${gradientId})`}
      />

      {/* Line */}
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
      />

      {/* Article markers */}
      {articleMarkers.map((marker, idx) => (
        <g key={idx}>
          {/* Vertical line indicator */}
          <line
            x1={marker.x}
            y1={marker.y}
            x2={marker.x}
            y2={height}
            stroke="#3b82f6"
            strokeWidth="0.5"
            strokeDasharray="2,2"
            opacity="0.6"
          />
          {/* Circle marker */}
          <circle
            cx={marker.x}
            cy={marker.y}
            r={interactive ? "2" : "1.5"}
            fill="#3b82f6"
            stroke="white"
            strokeWidth="0.5"
          >
            {interactive && (
              <title>{marker.article.title}</title>
            )}
          </circle>
          {/* Pulse animation for interactive mode */}
          {interactive && (
            <circle
              cx={marker.x}
              cy={marker.y}
              r="2"
              fill="#3b82f6"
              opacity="0.4"
            >
              <animate
                attributeName="r"
                from="2"
                to="4"
                dur="1.5s"
                repeatCount="indefinite"
              />
              <animate
                attributeName="opacity"
                from="0.4"
                to="0"
                dur="1.5s"
                repeatCount="indefinite"
              />
            </circle>
          )}
        </g>
      ))}
    </svg>
  )
}

// Interactive chart component with clickable article markers
function InteractiveChart({
  data,
  isPositive,
  articles,
  onArticleClick,
  onMarkerLineClick,
  timeFrame = '1D'
}: {
  data: any[],
  isPositive: boolean,
  articles: NewsArticle[],
  onArticleClick: (article: NewsArticle) => void,
  onMarkerLineClick?: () => void,
  timeFrame?: TimeFrame
}) {
  const [hoveredMarker, setHoveredMarker] = useState<ArticleMarker | null>(null)
  const chartRef = useRef<HTMLDivElement>(null)

  if (!data || data.length === 0) return null

  const prices = data.map(d => d.close).filter(p => p > 0)
  if (prices.length === 0) return null

  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const range = max - min || 1
  const color = isPositive ? "#10b981" : "#ef4444"

  // Format time labels based on timeframe
  const formatTimeLabel = (timestamp: number, tf: TimeFrame): string => {
    const date = new Date(timestamp)

    switch (tf) {
      case '1D':
        return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
      case '1W':
        return date.toLocaleDateString([], { weekday: 'short' })
      case '1M':
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
      case '1Y':
        return date.toLocaleDateString([], { month: 'short' })
      case '5Y':
        return date.getFullYear().toString()
      default:
        return ''
    }
  }

  // Calculate time labels for x-axis
  const timeLabels = []
  const labelCount = 5
  for (let i = 0; i < labelCount; i++) {
    const index = Math.floor((i / (labelCount - 1)) * (data.length - 1))
    const timestamp = data[index].timestamp
    const label = formatTimeLabel(timestamp, timeFrame)
    const x = (i / (labelCount - 1)) * 100
    timeLabels.push({ x, label })
  }

  // Step 1: Group articles by day (only depends on articles, not chart data)
  const articlesByDay = useMemo(() => {
    const grouped = new Map<number, NewsArticle[]>()

    if (timeFrame === '1D') return grouped // No articles on 1D timeframe

    articles.forEach(article => {
      if (!article.timestamp) return

      // Get start of day for this article
      const articleDate = new Date(article.timestamp)
      const dayStart = new Date(articleDate.getFullYear(), articleDate.getMonth(), articleDate.getDate()).getTime()

      if (!grouped.has(dayStart)) {
        grouped.set(dayStart, [])
      }
      grouped.get(dayStart)!.push(article)
    })

    return grouped
  }, [articles, timeFrame])

  // Step 2: Calculate marker positions based on chart data
  // This only recalculates positions, not article grouping
  const articleMarkers = useMemo(() => {
    const markers: (ArticleMarker & { articles: NewsArticle[] })[] = []

    if (timeFrame === '1D' || !data || data.length === 0) return markers

    const chartStart = data[0].timestamp
    const chartEnd = data[data.length - 1].timestamp

    articlesByDay.forEach((dayArticles, dayTimestamp) => {
      // Check if this day is within the chart timeframe
      if (dayTimestamp < chartStart || dayTimestamp > chartEnd + (24 * 60 * 60 * 1000)) {
        return // Skip articles outside timeframe
      }

      // Find closest chart point to this day
      let closestIndex = 0
      let minDiff = Infinity

      data.forEach((point, index) => {
        const pointTime = point.timestamp
        const diff = Math.abs(pointTime - dayTimestamp)
        if (diff < minDiff) {
          minDiff = diff
          closestIndex = index
        }
      })

      const x = (closestIndex / (data.length - 1)) * 100
      const price = data[closestIndex].close
      const y = 100 - ((price - min) / range) * 100

      markers.push({
        x,
        y,
        article: dayArticles[0], // Primary article for tooltip
        articles: dayArticles, // All articles from this day
        index: closestIndex,
        timestamp: dayTimestamp
      })
    })

    return markers
  }, [articlesByDay, data, min, range, timeFrame])

  // For 1D timeframe, show simple chart without article markers
  if (timeFrame === '1D') {
    return (
      <div ref={chartRef} className="relative w-full" style={{ height: '320px' }}>
        <div className="relative w-full h-full pb-8">
          <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            <defs>
              <linearGradient id={`gradient-interactive-${isPositive ? 'pos' : 'neg'}`} x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor={color} stopOpacity="0.3" />
                <stop offset="100%" stopColor={color} stopOpacity="0.05" />
              </linearGradient>
            </defs>
            <path
              d={`M ${prices.map((price, i) => `${(i / (prices.length - 1)) * 100},${100 - ((price - min) / range) * 100}`).join(' L ')} L 100,100 L 0,100 Z`}
              fill={`url(#gradient-interactive-${isPositive ? 'pos' : 'neg'})`}
            />
            <polyline
              points={prices.map((price, i) => `${(i / (prices.length - 1)) * 100},${100 - ((price - min) / range) * 100}`).join(' ')}
              fill="none"
              stroke={color}
              strokeWidth="1.5"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-8 flex justify-between items-center px-2 text-xs text-gray-400">
          {timeLabels.map((label, idx) => (
            <div key={idx} className="text-center">{label.label}</div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div ref={chartRef} className="relative w-full" style={{ height: '320px' }}>
      {/* Chart area */}
      <div className="relative w-full h-full pb-8">
        <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          <defs>
            <linearGradient id={`gradient-interactive-${isPositive ? 'pos' : 'neg'}`} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={color} stopOpacity="0.3" />
              <stop offset="100%" stopColor={color} stopOpacity="0.05" />
            </linearGradient>
          </defs>

          {/* Area and line */}
          <path
            d={`M ${prices.map((price, i) => `${(i / (prices.length - 1)) * 100},${100 - ((price - min) / range) * 100}`).join(' L ')} L 100,100 L 0,100 Z`}
            fill={`url(#gradient-interactive-${isPositive ? 'pos' : 'neg'})`}
          />
          <polyline
            points={prices.map((price, i) => `${(i / (prices.length - 1)) * 100},${100 - ((price - min) / range) * 100}`).join(' ')}
            fill="none"
            stroke={color}
            strokeWidth="1.5"
            vectorEffect="non-scaling-stroke"
          />

        </svg>

        {/* Clickable vertical lines for article markers overlay */}
        <div className="absolute inset-0 pointer-events-none">
          {articleMarkers.map((marker, idx) => {
            const rect = chartRef.current?.getBoundingClientRect()
            if (!rect) return null

            const xPos = (marker.x / 100) * rect.width

            return (
              <div
                key={`line-${idx}`}
                className="absolute pointer-events-auto cursor-pointer hover:bg-blue-500/10 transition-colors"
                style={{
                  left: `${xPos}px`,
                  top: '0',
                  bottom: '32px',
                  width: '12px',
                  transform: 'translateX(-50%)'
                }}
                onMouseEnter={() => setHoveredMarker(marker)}
                onMouseLeave={() => setHoveredMarker(null)}
                onClick={() => {
                  onArticleClick(marker.article)
                  onMarkerLineClick?.()
                }}
              >
                {/* Vertical dashed line */}
                <div
                  className={`absolute left-1/2 -translate-x-1/2 top-0 bottom-0 border-l-2 border-dashed transition-all ${
                    hoveredMarker === marker ? 'border-blue-400' : 'border-blue-500'
                  }`}
                  style={{
                    borderWidth: hoveredMarker === marker ? '2px' : '2px',
                    opacity: hoveredMarker === marker ? 1 : 0.6
                  }}
                />

                {/* Hover tooltip */}
                {hoveredMarker === marker && marker.articles && (
                  <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-gray-700 text-white text-xs px-3 py-2 rounded shadow-lg max-w-sm z-10 pointer-events-none">
                    <div className="font-semibold mb-1">
                      {new Date(marker.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </div>
                    <div className="text-gray-300 mb-1">
                      {marker.articles.length} {marker.articles.length === 1 ? 'article' : 'articles'}
                    </div>
                    {marker.articles.slice(0, 3).map((article, i) => (
                      <div key={i} className="text-[10px] text-gray-400 truncate">
                        • {article.title}
                      </div>
                    ))}
                    {marker.articles.length > 3 && (
                      <div className="text-[10px] text-gray-500 mt-1">
                        +{marker.articles.length - 3} more
                      </div>
                    )}
                    <div className="text-gray-400 text-[10px] mt-1.5 border-t border-gray-600 pt-1">Click to view {marker.articles.length > 1 ? 'articles' : 'article'}</div>
                    <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px">
                      <div className="border-4 border-transparent border-t-gray-700" />
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Time axis */}
      <div className="absolute bottom-0 left-0 right-0 h-8 flex justify-between items-center px-2 text-xs text-gray-400">
        {timeLabels.map((label, idx) => (
          <div key={idx} className="text-center">
            {label.label}
          </div>
        ))}
      </div>
    </div>
  )
}
