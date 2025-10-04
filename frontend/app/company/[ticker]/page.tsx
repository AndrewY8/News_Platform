"use client"

import { useState, useEffect } from "react"
import { useRouter, useParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { ArrowLeft, ChevronDown, ExternalLink } from "lucide-react"
import { ApiService, CompanyDetails } from "@/services/api"
import { YahooFinanceService, StockData, ChartData } from "@/services/yahooFinance"
import { StockChart } from "@/components/StockChart"

export default function CompanyDetailPage() {
  const router = useRouter()
  const params = useParams()
  const ticker = params.ticker as string

  const [companyDetails, setCompanyDetails] = useState<CompanyDetails | null>(null)
  const [stockData, setStockData] = useState<StockData | null>(null)
  const [chartData, setChartData] = useState<ChartData | null>(null)
  const [selectedPeriod, setSelectedPeriod] = useState("1D")
  const [loading, setLoading] = useState(true)
  const [expandedTopics, setExpandedTopics] = useState<{[key: number]: boolean}>({})

  const periods = [
    { label: "1D", range: "1d", interval: "5m" },
    { label: "1W", range: "5d", interval: "15m" },
    { label: "1M", range: "1mo", interval: "1d" },
    { label: "3M", range: "3mo", interval: "1d" },
    { label: "1Y", range: "1y", interval: "1wk" },
  ]

  useEffect(() => {
    loadCompanyData()
  }, [ticker])

  useEffect(() => {
    const period = periods.find(p => p.label === selectedPeriod)
    if (period && ticker) {
      loadChartData(period.interval, period.range)
    }
  }, [selectedPeriod, ticker])

  const loadCompanyData = async () => {
    try {
      setLoading(true)

      // Load company details and stock data in parallel
      const [details, stock] = await Promise.all([
        ApiService.getCompanyDetails(ticker.toUpperCase()),
        YahooFinanceService.getStockQuote(ticker.toUpperCase())
      ])

      setCompanyDetails(details)
      setStockData(stock)
    } catch (error) {
      console.error("Error loading company data:", error)
    } finally {
      setLoading(false)
    }
  }

  const loadChartData = async (interval: string, range: string) => {
    try {
      const data = await YahooFinanceService.getChartData(ticker.toUpperCase(), interval, range)
      setChartData(data)
    } catch (error) {
      console.error("Error loading chart data:", error)
    }
  }

  const formatNumber = (num: number | undefined, decimals: number = 2): string => {
    if (num === undefined || num === null) return "N/A"
    if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`
    return `$${num.toFixed(decimals)}`
  }

  const formatPercent = (num: number | undefined): string => {
    if (num === undefined || num === null) return "N/A"
    return `${(num * 100).toFixed(2)}%`
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading {ticker} data...</p>
        </div>
      </div>
    )
  }

  if (!companyDetails) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Company data not available</p>
          <Button onClick={() => router.back()} className="mt-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Go Back
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header with Back Button */}
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={() => router.back()}
            className="mb-4"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Home
          </Button>

          {/* Company Header */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <img
                  src={`https://img.logokit.com/ticker/${ticker}?token=${process.env.NEXT_PUBLIC_LOGO_API_KEY}`}
                  alt={`${ticker} logo`}
                  className="w-16 h-16 rounded-lg object-cover"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none'
                  }}
                />
                <div>
                  <h1 className="text-3xl font-bold text-gray-900">{companyDetails.name}</h1>
                  <p className="text-gray-600 mt-1">
                    {ticker} • {companyDetails.industry}
                  </p>
                </div>
              </div>

              {stockData && (
                <div className="text-right">
                  <div className="text-3xl font-bold text-gray-900">
                    ${stockData.price.toFixed(2)}
                  </div>
                  <div className={`text-lg font-semibold ${stockData.changePercent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {stockData.changePercent >= 0 ? '▲' : '▼'} {stockData.changePercent >= 0 ? '+' : ''}{stockData.changePercent.toFixed(2)}%
                  </div>
                  <div className="text-sm text-gray-500">
                    {stockData.changePercent >= 0 ? '+' : ''}{stockData.change.toFixed(2)}
                  </div>
                </div>
              )}
            </div>

            {/* Key Metrics */}
            {stockData && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t">
                <div>
                  <p className="text-sm text-gray-500">Market Cap</p>
                  <p className="text-lg font-semibold">{formatNumber(companyDetails.fundamentals.market_cap)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">P/E Ratio</p>
                  <p className="text-lg font-semibold">
                    {companyDetails.fundamentals.pe_ratio?.toFixed(2) || "N/A"}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Volume</p>
                  <p className="text-lg font-semibold">
                    {stockData.volume ? (stockData.volume / 1e6).toFixed(2) + 'M' : 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Dividend Yield</p>
                  <p className="text-lg font-semibold">
                    {formatPercent(companyDetails.fundamentals.dividend_yield)}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Stock Chart */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">Price Chart</h2>
            <div className="flex gap-2">
              {periods.map((period) => (
                <Button
                  key={period.label}
                  variant={selectedPeriod === period.label ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSelectedPeriod(period.label)}
                >
                  {period.label}
                </Button>
              ))}
            </div>
          </div>
          {stockData && chartData && (
            <StockChart
              stockData={stockData}
              chartData={chartData}
              onTimeframeChange={(timeframe) => {
                const period = periods.find(p => p.range === timeframe)
                if (period) setSelectedPeriod(period.label)
              }}
              selectedTimeframe={periods.find(p => p.label === selectedPeriod)?.range || "1d"}
            />
          )}
        </div>

        {/* Company Description */}
        {companyDetails.description && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">About</h2>
            <p className="text-gray-700 leading-relaxed">{companyDetails.description}</p>

            {companyDetails.business_areas.length > 0 && (
              <div className="mt-4">
                <h3 className="font-semibold text-gray-900 mb-2">Business Areas</h3>
                <div className="flex flex-wrap gap-2">
                  {companyDetails.business_areas.map((area, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm"
                    >
                      {area}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Fundamentals */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Key Fundamentals</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            <div className="border-l-4 border-blue-500 pl-3">
              <p className="text-sm text-gray-500">52-Week High</p>
              <p className="text-lg font-semibold">${companyDetails.fundamentals['52_week_high']?.toFixed(2) || 'N/A'}</p>
            </div>
            <div className="border-l-4 border-red-500 pl-3">
              <p className="text-sm text-gray-500">52-Week Low</p>
              <p className="text-lg font-semibold">${companyDetails.fundamentals['52_week_low']?.toFixed(2) || 'N/A'}</p>
            </div>
            <div className="border-l-4 border-green-500 pl-3">
              <p className="text-sm text-gray-500">Profit Margin</p>
              <p className="text-lg font-semibold">{formatPercent(companyDetails.fundamentals.profit_margin)}</p>
            </div>
            <div className="border-l-4 border-purple-500 pl-3">
              <p className="text-sm text-gray-500">Revenue Growth</p>
              <p className="text-lg font-semibold">{formatPercent(companyDetails.fundamentals.revenue_growth)}</p>
            </div>
            <div className="border-l-4 border-yellow-500 pl-3">
              <p className="text-sm text-gray-500">Beta</p>
              <p className="text-lg font-semibold">{companyDetails.fundamentals.beta?.toFixed(2) || 'N/A'}</p>
            </div>
            <div className="border-l-4 border-indigo-500 pl-3">
              <p className="text-sm text-gray-500">ROE</p>
              <p className="text-lg font-semibold">{formatPercent(companyDetails.fundamentals.roe)}</p>
            </div>
            <div className="border-l-4 border-pink-500 pl-3">
              <p className="text-sm text-gray-500">Debt to Equity</p>
              <p className="text-lg font-semibold">{companyDetails.fundamentals.debt_to_equity?.toFixed(2) || 'N/A'}</p>
            </div>
            <div className="border-l-4 border-teal-500 pl-3">
              <p className="text-sm text-gray-500">Current Ratio</p>
              <p className="text-lg font-semibold">{companyDetails.fundamentals.current_ratio?.toFixed(2) || 'N/A'}</p>
            </div>
          </div>
        </div>

        {/* Research Topics */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Research Topics {companyDetails.has_research && `(${companyDetails.topics.length})`}
          </h2>

          {companyDetails.has_research && companyDetails.topics.length > 0 ? (
            <div className="space-y-4">
              {companyDetails.topics.map((topic) => {
                const isExpanded = expandedTopics[topic.id] || false
                const urgencyColor = topic.urgency === 'high' ? 'bg-red-100 text-red-700' :
                                   topic.urgency === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                   'bg-green-100 text-green-700'

                return (
                  <div key={topic.id} className="border rounded-lg p-4">
                    <div
                      className="cursor-pointer"
                      onClick={() => setExpandedTopics(prev => ({...prev, [topic.id]: !prev[topic.id]}))}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2 flex-1">
                          <h3 className="text-lg font-bold text-gray-900">{topic.name}</h3>
                          <ChevronDown
                            className={`h-4 w-4 text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                          />
                        </div>
                        <span className={`px-3 py-1 rounded text-xs font-semibold ${urgencyColor}`}>
                          {topic.urgency.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{topic.description}</p>
                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        <span>{topic.article_count || topic.articles.length} articles</span>
                        {topic.final_score && <span>Score: {topic.final_score.toFixed(2)}</span>}
                      </div>
                    </div>

                    {isExpanded && topic.articles && topic.articles.length > 0 && (
                      <div className="mt-4 pt-4 border-t space-y-2">
                        {topic.articles.map((article, idx) => (
                          <a
                            key={idx}
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block p-3 rounded hover:bg-gray-50 transition-colors group"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex-1">
                                <h4 className="text-sm font-medium text-gray-900 group-hover:text-blue-600 flex items-center gap-1">
                                  {article.title}
                                  <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                                </h4>
                                <p className="text-xs text-gray-500 mt-1">{article.source}</p>
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
                )
              })}
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-600 mb-4">No research topics available for {ticker}</p>
              <p className="text-sm text-gray-500">Research can be initiated from the main page</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
