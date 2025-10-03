// Yahoo Finance API service for real-time stock data
export interface StockData {
  symbol: string
  price: number
  change: number
  changePercent: number
  volume: number
  marketCap?: number
  pe?: number
  dividend?: number
  high: number
  low: number
  open: number
  previousClose: number
}

export interface ChartDataPoint {
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface ChartData {
  symbol: string
  interval: string
  data: ChartDataPoint[]
}

export class YahooFinanceService {
  // Use backend proxy to avoid CORS issues
  private static readonly API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Get real-time stock quote
  static async getStockQuote(symbol: string): Promise<StockData | null> {
    try {
      const response = await fetch(`${this.API_URL}/api/finance/quote/${symbol}`)

      if (!response.ok) {
        console.warn(`Failed to fetch quote for ${symbol}: ${response.status}`)
        return this.getMockStockData(symbol)
      }

      const data = await response.json()

      if (data.error) {
        console.warn(`API error for ${symbol}: ${data.error}`)
        return this.getMockStockData(symbol)
      }

      return {
        symbol: data.symbol,
        price: data.price,
        change: data.change,
        changePercent: data.changePercent,
        volume: data.volume,
        marketCap: data.marketCap,
        pe: data.pe,
        dividend: data.dividend,
        high: data.high,
        low: data.low,
        open: data.open,
        previousClose: data.previousClose
      }
    } catch (error) {
      console.error(`Error fetching stock quote for ${symbol}:`, error)
      return this.getMockStockData(symbol)
    }
  }

  // Get chart data for a stock
  static async getChartData(symbol: string, interval: string = '1d', range: string = '1mo'): Promise<ChartData | null> {
    try {
      const response = await fetch(`${this.API_URL}/api/finance/chart/${symbol}?interval=${interval}&range=${range}`)

      if (!response.ok) {
        console.warn(`Failed to fetch chart data for ${symbol}: ${response.status}`)
        return this.getMockChartData(symbol, interval)
      }

      const data = await response.json()

      if (data.error) {
        console.warn(`API error for ${symbol}: ${data.error}`)
        return this.getMockChartData(symbol, interval)
      }

      return {
        symbol: data.symbol,
        interval: data.interval,
        data: data.data
      }
    } catch (error) {
      console.error(`Error fetching chart data for ${symbol}:`, error)
      return this.getMockChartData(symbol, interval)
    }
  }

  // Get multiple stock quotes
  static async getMultipleStockQuotes(symbols: string[]): Promise<StockData[]> {
    const quotes = await Promise.all(
      symbols.map(symbol => this.getStockQuote(symbol))
    )
    return quotes.filter((quote): quote is StockData => quote !== null)
  }

  // Mock data fallback when API is unavailable
  private static getMockStockData(symbol: string): StockData {
    const basePrice = 100 + Math.random() * 400
    const change = (Math.random() - 0.5) * 20
    const changePercent = (change / basePrice) * 100
    
    return {
      symbol: symbol.toUpperCase(),
      price: Math.round(basePrice * 100) / 100,
      change: Math.round(change * 100) / 100,
      changePercent: Math.round(changePercent * 100) / 100,
      volume: Math.floor(Math.random() * 10000000) + 1000000,
      marketCap: Math.floor(Math.random() * 1000000000000) + 10000000000,
      pe: Math.round((Math.random() * 30 + 10) * 100) / 100,
      dividend: Math.round((Math.random() * 5) * 100) / 100,
      high: Math.round((basePrice + Math.random() * 10) * 100) / 100,
      low: Math.round((basePrice - Math.random() * 10) * 100) / 100,
      open: Math.round((basePrice + (Math.random() - 0.5) * 5) * 100) / 100,
      previousClose: Math.round((basePrice - change) * 100) / 100
    }
  }

  private static getMockChartData(symbol: string, interval: string): ChartData {
    const basePrice = 100 + Math.random() * 400
    const data: ChartDataPoint[] = []
    const now = Date.now()
    const dayMs = 24 * 60 * 60 * 1000
    
    for (let i = 30; i >= 0; i--) {
      const timestamp = now - (i * dayMs)
      const priceVariation = (Math.random() - 0.5) * 10
      const price = basePrice + priceVariation
      
      data.push({
        timestamp,
        open: price + (Math.random() - 0.5) * 2,
        high: price + Math.random() * 3,
        low: price - Math.random() * 3,
        close: price,
        volume: Math.floor(Math.random() * 1000000) + 500000
      })
    }

    return {
      symbol: symbol.toUpperCase(),
      interval,
      data
    }
  }
}
