"use client"

import { useEffect, useRef, useState } from 'react'
import { ChartData, StockData } from '@/services/yahooFinance'
import { Button } from '@/components/ui/button'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface StockChartProps {
  stockData: StockData | null
  chartData: ChartData | null
  onTimeframeChange: (timeframe: string) => void
  selectedTimeframe: string
}

export function StockChart({ stockData, chartData, onTimeframeChange, selectedTimeframe }: StockChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const chartRef = useRef<any>(null)
  const [isLoading, setIsLoading] = useState(false)

  const timeframes = [
    { value: '1d', label: '1D' },
    { value: '5d', label: '5D' },
    { value: '1mo', label: '1M' },
    { value: '3mo', label: '3M' },
    { value: '6mo', label: '6M' },
    { value: '1y', label: '1Y' }
  ]

  useEffect(() => {
    if (!chartData || !canvasRef.current) return

    // Dynamically import Chart.js to avoid SSR issues
    const initChart = async () => {
      try {
        setIsLoading(true)
        const { Chart, registerables } = await import('chart.js')
        Chart.register(...registerables)

        // Destroy existing chart if it exists
        if (chartRef.current) {
          chartRef.current.destroy()
        }

        const ctx = canvasRef.current!.getContext('2d')
        if (!ctx) return

        // Prepare data for chart
        const labels = chartData.data.map(point => 
          new Date(point.timestamp).toLocaleDateString()
        )
        const prices = chartData.data.map(point => point.close)

        // Create gradient for chart
        const gradient = ctx.createLinearGradient(0, 0, 0, 400)
        const isPositive = stockData?.change && stockData.change >= 0
        gradient.addColorStop(0, isPositive ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)')
        gradient.addColorStop(1, 'rgba(255, 255, 255, 0)')

        chartRef.current = new Chart(ctx, {
          type: 'line',
          data: {
            labels,
            datasets: [{
              label: `${chartData.symbol} Price`,
              data: prices,
              borderColor: isPositive ? '#22c55e' : '#ef4444',
              backgroundColor: gradient,
              borderWidth: 2,
              fill: true,
              tension: 0.4,
              pointRadius: 0,
              pointHoverRadius: 6,
              pointHoverBackgroundColor: isPositive ? '#22c55e' : '#ef4444'
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                display: false
              },
              tooltip: {
                mode: 'index',
                intersect: false,
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                titleColor: '#fff',
                bodyColor: '#fff',
                borderColor: isPositive ? '#22c55e' : '#ef4444',
                borderWidth: 1,
                callbacks: {
                  label: function(context) {
                    return `$${context.parsed.y.toFixed(2)}`
                  }
                }
              }
            },
            scales: {
              x: {
                display: false,
                grid: {
                  display: false
                }
              },
              y: {
                display: false,
                grid: {
                  display: false
                }
              }
            },
            interaction: {
              intersect: false,
              mode: 'index'
            },
            elements: {
              point: {
                hoverRadius: 6
              }
            }
          }
        })
      } catch (error) {
        console.error('Error initializing chart:', error)
      } finally {
        setIsLoading(false)
      }
    }

    initChart()

    // Cleanup function
    return () => {
      if (chartRef.current) {
        chartRef.current.destroy()
      }
    }
  }, [chartData, stockData])

  if (!stockData) {
    return (
      <div className="bg-white rounded-lg p-4 border border-gray-200">
        <div className="text-center text-gray-500 py-8">
          <p>Select a ticker to view chart</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Header with stock info */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-gray-900">{stockData.symbol}</h3>
          <div className="flex items-center gap-2">
            {stockData.change >= 0 ? (
              <TrendingUp className="w-4 h-4 text-green-600" />
            ) : (
              <TrendingDown className="w-4 h-4 text-red-600" />
            )}
            <span className={`text-sm font-medium ${
              stockData.change >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              ${stockData.price.toFixed(2)}
            </span>
          </div>
        </div>
        
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1">
            <span className={`font-medium ${
              stockData.change >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {stockData.change >= 0 ? '+' : ''}{stockData.change.toFixed(2)}
            </span>
            <span className={`${
              stockData.change >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              ({stockData.changePercent >= 0 ? '+' : ''}{stockData.changePercent.toFixed(2)}%)
            </span>
          </div>
          <span className="text-gray-500">Vol: {stockData.volume.toLocaleString()}</span>
        </div>
      </div>

      {/* Timeframe selector */}
      <div className="px-4 py-2 border-b border-gray-200">
        <div className="flex gap-1">
          {timeframes.map((timeframe) => (
            <Button
              key={timeframe.value}
              variant={selectedTimeframe === timeframe.value ? "default" : "outline"}
              size="sm"
              onClick={() => onTimeframeChange(timeframe.value)}
              className="h-7 px-2 text-xs"
            >
              {timeframe.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="p-4">
        <div className="relative h-64">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <canvas ref={canvasRef} className="w-full h-full" />
          )}
        </div>
      </div>

      {/* Additional stock info */}
      <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Open:</span>
            <span className="ml-2 font-medium">${stockData.open.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-gray-500">High:</span>
            <span className="ml-2 font-medium">${stockData.high.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-gray-500">Low:</span>
            <span className="ml-2 font-medium">${stockData.low.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-gray-500">Prev Close:</span>
            <span className="ml-2 font-medium">${stockData.previousClose.toFixed(2)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
