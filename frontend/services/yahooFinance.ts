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
  // Base URL for Yahoo Finance API (using RapidAPI as it's more reliable)
  private static readonly BASE_URL = 'https://yh-finance.p.rapidapi.com'
  private static readonly API_KEY = process.env.NEXT_PUBLIC_RAPIDAPI_KEY || 'demo-key'

  // Get real-time stock quote
  static async getStockQuote(symbol: string): Promise<StockData | null> {
    try {
      const response = await fetch(`${this.BASE_URL}/stock/v2/get-summary?symbol=${symbol}`, {
        headers: {
          'X-RapidAPI-Key': this.API_KEY,
          'X-RapidAPI-Host': 'yh-finance.p.rapidapi.com'
        }
      })

      if (!response.ok) {
        console.warn(`Failed to fetch quote for ${symbol}: ${response.status}`)
        return this.getMockStockData(symbol)
      }

      const data = await response.json()
      
      if (data.price) {
        return {
          symbol: symbol.toUpperCase(),
          price: data.price.regularMarketPrice?.raw || 0,
          change: data.price.regularMarketChange?.raw || 0,
          changePercent: data.price.regularMarketChangePercent?.raw || 0,
          volume: data.price.regularMarketVolume?.raw || 0,
          marketCap: data.summaryDetail?.marketCap?.raw,
          pe: data.summaryDetail?.trailingPE?.raw,
          dividend: data.summaryDetail?.dividendRate?.raw,
          high: data.price.regularMarketDayHigh?.raw || 0,
          low: data.price.regularMarketDayLow?.raw || 0,
          open: data.price.regularMarketOpen?.raw || 0,
          previousClose: data.price.regularMarketPreviousClose?.raw || 0
        }
      }

      return this.getMockStockData(symbol)
    } catch (error) {
      console.error(`Error fetching stock quote for ${symbol}:`, error)
      return this.getMockStockData(symbol)
    }
  }

  // Get chart data for a stock
  static async getChartData(symbol: string, interval: string = '1d', range: string = '1mo'): Promise<ChartData | null> {
    try {
      const response = await fetch(`${this.BASE_URL}/stock/v3/get-chart?interval=${interval}&symbol=${symbol}&range=${range}`, {
        headers: {
          'X-RapidAPI-Key': this.API_KEY,
          'X-RapidAPI-Host': 'yh-finance.p.rapidapi.com'
        }
      })

      if (!response.ok) {
        console.warn(`Failed to fetch chart data for ${symbol}: ${response.status}`)
        return this.getMockChartData(symbol, interval)
      }

      const data = await response.json()
      
      if (data.chart?.result?.[0]?.timestamp) {
        const timestamps = data.chart.result[0].timestamp
        const quotes = data.chart.result[0].indicators.quote[0]
        
        const chartData: ChartDataPoint[] = timestamps.map((timestamp: number, index: number) => ({
          timestamp: timestamp * 1000, // Convert to milliseconds
          open: quotes.open?.[index] || 0,
          high: quotes.high?.[index] || 0,
          low: quotes.low?.[index] || 0,
          close: quotes.close?.[index] || 0,
          volume: quotes.volume?.[index] || 0
        }))

        return {
          symbol: symbol.toUpperCase(),
          interval,
          data: chartData
        }
      }

      return this.getMockChartData(symbol, interval)
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
