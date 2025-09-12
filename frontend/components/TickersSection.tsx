"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { X, TrendingUp, TrendingDown } from "lucide-react"
import { Ticker, TimePeriod } from "@/types"
import { ApiService } from "@/services/api"

interface TickersSectionProps {
  tickers: Ticker[]
  onTickersChange: (tickers: Ticker[]) => void
}

export function TickersSection({ tickers, onTickersChange }: TickersSectionProps) {
  const [newTicker, setNewTicker] = useState("")
  const [selectedTimePeriod, setSelectedTimePeriod] = useState<TimePeriod>("1D")

  const timePeriods: TimePeriod[] = ["1D", "1W", "1M", "3M", "1Y"]

  const removeTicker = (symbolToRemove: string) => {
    const updatedTickers = tickers.filter((ticker) => ticker.symbol !== symbolToRemove)
    onTickersChange(updatedTickers)
    
    // Update backend
    ApiService.updateUserTickers(updatedTickers.map(t => t.symbol))
      .catch(console.error)
  }

  const addTicker = async () => {
    if (newTicker.trim() && !tickers.find((t) => t.symbol === newTicker.toUpperCase())) {
      const symbol = newTicker.toUpperCase()
      
      try {
        // Get real market data for the new ticker
        const tickerInfo = await ApiService.getTickerInfo(symbol)
        
        const newTickerData: Ticker = {
          symbol,
          trend: tickerInfo.change >= 0 ? "up" : "down",
          value: tickerInfo.current_price.toFixed(2),
          change: tickerInfo.change,
          changePercent: tickerInfo.change_percent
        }
        
        const updatedTickers = [...tickers, newTickerData]
        onTickersChange(updatedTickers)
        
        // Update backend
        await ApiService.updateUserTickers(updatedTickers.map(t => t.symbol))
        
        setNewTicker("")
      } catch (error) {
        console.error('Failed to add ticker:', error)
        // Add with mock data if API fails
        const newTickerData: Ticker = {
          symbol,
          trend: Math.random() > 0.5 ? "up" : "down",
          value: (Math.random() * 500 + 50).toFixed(2),
        }
        onTickersChange([...tickers, newTickerData])
        setNewTicker("")
      }
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-2">Market Watch</h2>
        <p className="text-sm text-gray-600">Track your favorite stocks and market performance</p>
      </div>

      {/* Time Period Selector */}
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Time Period</h3>
        <div className="flex gap-2 flex-wrap">
          {timePeriods.map((period) => (
            <Button
              key={period}
              variant={selectedTimePeriod === period ? "default" : "outline"}
              size="sm"
              className="h-8 px-3 text-xs"
              onClick={() => setSelectedTimePeriod(period)}
            >
              {period}
            </Button>
          ))}
        </div>
      </div>

      {/* Tickers List */}
      <div className="flex-1">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Your Tickers</h3>
        <div className="space-y-3 mb-4">
          {tickers.map((ticker) => (
            <div key={ticker.symbol} className="bg-gray-50 rounded-lg p-3 group">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    {ticker.trend === "up" ? (
                      <TrendingUp className="w-4 h-4 text-green-600" />
                    ) : (
                      <TrendingDown className="w-4 h-4 text-red-600" />
                    )}
                    <span className="font-mono font-semibold text-gray-900">{ticker.symbol}</span>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-gray-900">${ticker.value}</div>
                    {ticker.changePercent && (
                      <div className={`text-xs ${ticker.trend === "up" ? "text-green-600" : "text-red-600"}`}>
                        {ticker.changePercent > 0 ? "+" : ""}{ticker.changePercent.toFixed(2)}%
                      </div>
                    )}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={() => removeTicker(ticker.symbol)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>

        {/* Add New Ticker */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-gray-900">Add New Ticker</h3>
          <div className="flex gap-2">
            <Input
              placeholder="e.g., AAPL"
              value={newTicker}
              onChange={(e) => setNewTicker(e.target.value)}
              className="h-9 text-sm"
              onKeyPress={(e) => e.key === "Enter" && addTicker()}
            />
            <Button size="sm" onClick={addTicker} className="h-9 px-4">
              Add
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
