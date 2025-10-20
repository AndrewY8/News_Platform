"use client"

import { useState, useEffect } from "react"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"

interface MarketSnapshotProps {
  tickers: string[]
  compact?: boolean
}

interface TickerData {
  symbol: string
  price: string
  change: number
  changePercent: number
  trend: "up" | "down" | "neutral"
}

export function MarketSnapshot({ tickers, compact = false }: MarketSnapshotProps) {
  const [tickerData, setTickerData] = useState<TickerData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMarketData()
    // Refresh every 60 seconds
    const interval = setInterval(fetchMarketData, 60000)
    return () => clearInterval(interval)
  }, [tickers])

  const fetchMarketData = async () => {
    if (tickers.length === 0) {
      setLoading(false)
      return
    }

    try {
      // TODO: Replace with actual API call
      // const data = await ApiService.getMarketData(tickers)

      // Mock data for now
      const mockData: TickerData[] = tickers.slice(0, 6).map(ticker => {
        const change = (Math.random() - 0.5) * 10
        return {
          symbol: ticker,
          price: (Math.random() * 500 + 50).toFixed(2),
          change: change,
          changePercent: (Math.random() - 0.5) * 5,
          trend: change > 0 ? "up" : change < 0 ? "down" : "neutral",
        }
      })

      setTickerData(mockData)
      setLoading(false)
    } catch (error) {
      console.error("Error fetching market data:", error)
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className={`bg-gray-100 ${compact ? 'py-2' : 'py-4'}`}>
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-4 overflow-x-auto">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="flex-shrink-0 animate-pulse">
                <div className="h-4 bg-gray-300 rounded w-16 mb-1"></div>
                <div className="h-3 bg-gray-300 rounded w-12"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (tickerData.length === 0) {
    return null
  }

  const getTrendIcon = (trend: "up" | "down" | "neutral") => {
    if (trend === "up") return <TrendingUp className="w-3 h-3" />
    if (trend === "down") return <TrendingDown className="w-3 h-3" />
    return <Minus className="w-3 h-3" />
  }

  const getTrendColor = (trend: "up" | "down" | "neutral") => {
    if (trend === "up") return "text-green-600"
    if (trend === "down") return "text-red-600"
    return "text-gray-600"
  }

  return (
    <div className={`bg-gray-100 border-t ${compact ? 'py-2' : 'py-4'}`}>
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center gap-6 overflow-x-auto scrollbar-hide">
          {!compact && (
            <div className="flex-shrink-0">
              <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
                Market
              </span>
            </div>
          )}

          {tickerData.map((ticker) => (
            <div
              key={ticker.symbol}
              className="flex-shrink-0 flex items-center gap-2"
            >
              <div>
                <div className="flex items-center gap-1">
                  <span className="font-semibold text-gray-900 text-sm">
                    {ticker.symbol}
                  </span>
                  <span className="text-gray-600 text-sm">
                    ${ticker.price}
                  </span>
                </div>
                <div className={`flex items-center gap-1 text-xs ${getTrendColor(ticker.trend)}`}>
                  {getTrendIcon(ticker.trend)}
                  <span>
                    {ticker.change > 0 ? '+' : ''}{ticker.change.toFixed(2)}
                  </span>
                  <span>
                    ({ticker.changePercent > 0 ? '+' : ''}{ticker.changePercent.toFixed(2)}%)
                  </span>
                </div>
              </div>
            </div>
          ))}

          {tickers.length > 6 && (
            <div className="flex-shrink-0 text-sm text-gray-500">
              +{tickers.length - 6} more
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
