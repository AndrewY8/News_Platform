/**
 * Mock data for testing The Daily Planet UI
 * This provides sample data when the backend is not available
 */

import {
  UserPreferences,
  UserTopic,
  LayoutSection,
  ContentExclusion,
  HeroArticle,
} from "@/types/dailyplanet"
import { NewsArticle } from "@/types"

export const mockPreferences: UserPreferences = {
  id: "mock-pref-1",
  user_id: "demo_user_1",
  region: "Global",
  reading_level: "standard",
  update_frequency: "realtime",
  layout_density: 2,
  theme: "light",
  show_breaking_news: true,
  show_market_snapshot: true,
  enable_ai_learning: true,
  onboarding_completed: true,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}

export const mockTopics: UserTopic[] = [
  {
    id: "topic-1",
    topic_name: "Technology",
    topic_type: "industry",
    priority: 5,
    is_active: true,
    created_at: new Date().toISOString(),
  },
  {
    id: "topic-2",
    topic_name: "Artificial Intelligence",
    topic_type: "theme",
    priority: 4,
    is_active: true,
    created_at: new Date().toISOString(),
  },
  {
    id: "topic-3",
    topic_name: "Healthcare",
    topic_type: "industry",
    priority: 3,
    is_active: true,
    created_at: new Date().toISOString(),
  },
]

export const mockSections: LayoutSection[] = [
  {
    id: "section-1",
    section_id: "portfolio-news",
    section_type: "portfolio",
    section_name: "My Portfolio",
    display_order: 0,
    is_visible: true,
    config_json: {
      article_limit: 10,
      show_charts: true,
    },
  },
  {
    id: "section-2",
    section_id: "breaking-news",
    section_type: "breaking",
    section_name: "Breaking News",
    display_order: 1,
    is_visible: true,
    config_json: {
      article_limit: 8,
      max_age_hours: 24,
    },
  },
  {
    id: "section-3",
    section_id: "tech-news",
    section_type: "industry",
    section_name: "Technology",
    display_order: 2,
    is_visible: true,
    config_json: {
      article_limit: 10,
      industry: "Technology",
    },
  },
  {
    id: "section-4",
    section_id: "market-analysis",
    section_type: "market_analysis",
    section_name: "Market Analysis",
    display_order: 3,
    is_visible: true,
    config_json: {
      article_limit: 8,
    },
  },
]

export const mockExclusions: ContentExclusion[] = [
  {
    id: "exclusion-1",
    exclusion_type: "keyword",
    exclusion_value: "cryptocurrency",
    reason: "Not interested in crypto news",
    created_at: new Date().toISOString(),
  },
]

export const mockHeroArticle: HeroArticle = {
  id: "hero-1",
  date: "2h ago",
  title: "Tech Giants Report Record Earnings Amid AI Revolution",
  source: "The Wall Street Journal",
  preview: "Major technology companies are seeing unprecedented growth as artificial intelligence reshapes the industry landscape. Analysts predict this trend will continue through 2025.",
  fullPreview:
    "Major technology companies posted record-breaking earnings this quarter, driven largely by investments in artificial intelligence infrastructure and services. Industry leaders attribute the surge to increased enterprise adoption of AI tools and growing consumer demand for AI-powered products. Wall Street analysts are raising their forecasts, with many predicting sustained growth throughout 2025.",
  sentiment: "positive",
  tags: ["AAPL", "MSFT", "GOOGL", "AI", "Earnings"],
  url: "#",
  relevance_score: 0.95,
  category: "Technology",
  featured: true,
  timestamp: Date.now(),
}

export const mockArticles: NewsArticle[] = [
  {
    id: "article-1",
    date: "1h ago",
    title: "Apple Announces New AI Features for iPhone",
    source: "Bloomberg",
    preview:
      "Apple unveiled a suite of AI-powered features coming to iPhone, including advanced photo editing and personalized health insights.",
    sentiment: "positive",
    tags: ["AAPL", "AI", "Consumer Tech"],
    url: "#",
    relevance_score: 0.92,
    category: "Technology",
    timestamp: Date.now() - 3600000,
  },
  {
    id: "article-2",
    date: "2h ago",
    title: "Federal Reserve Holds Interest Rates Steady",
    source: "Reuters",
    preview:
      "The Federal Reserve decided to maintain current interest rates, citing balanced economic indicators and stable inflation.",
    sentiment: "neutral",
    tags: ["MACRO", "FED", "Economy"],
    url: "#",
    relevance_score: 0.88,
    category: "Economy",
    timestamp: Date.now() - 7200000,
  },
  {
    id: "article-3",
    date: "3h ago",
    title: "Microsoft Azure Gains Market Share in Cloud Computing",
    source: "TechCrunch",
    preview:
      "Microsoft's cloud platform continues to narrow the gap with AWS, winning major enterprise contracts in Q4.",
    sentiment: "positive",
    tags: ["MSFT", "Cloud", "Enterprise"],
    url: "#",
    relevance_score: 0.89,
    category: "Technology",
    timestamp: Date.now() - 10800000,
  },
  {
    id: "article-4",
    date: "4h ago",
    title: "Tesla Recalls 200,000 Vehicles Over Software Issue",
    source: "CNBC",
    preview:
      "Tesla is recalling certain Model 3 and Model Y vehicles due to a software glitch affecting the backup camera display.",
    sentiment: "negative",
    tags: ["TSLA", "EV", "Automotive"],
    url: "#",
    relevance_score: 0.85,
    category: "Automotive",
    timestamp: Date.now() - 14400000,
  },
  {
    id: "article-5",
    date: "5h ago",
    title: "Google Launches New Healthcare AI Initiative",
    source: "The Verge",
    preview:
      "Google announced a partnership with major hospitals to develop AI tools for early disease detection and diagnosis.",
    sentiment: "positive",
    tags: ["GOOGL", "Healthcare", "AI"],
    url: "#",
    relevance_score: 0.87,
    category: "Healthcare",
    timestamp: Date.now() - 18000000,
  },
  {
    id: "article-6",
    date: "6h ago",
    title: "Oil Prices Surge on Middle East Tensions",
    source: "Financial Times",
    preview:
      "Crude oil prices jumped 5% amid escalating geopolitical tensions in the Middle East, raising concerns about supply disruptions.",
    sentiment: "negative",
    tags: ["OIL", "Energy", "Geopolitics"],
    url: "#",
    relevance_score: 0.78,
    category: "Energy",
    timestamp: Date.now() - 21600000,
  },
  {
    id: "article-7",
    date: "7h ago",
    title: "Amazon Expands Same-Day Delivery to 50 New Cities",
    source: "Business Insider",
    preview:
      "Amazon is rolling out same-day delivery services to 50 additional metropolitan areas, intensifying competition in e-commerce logistics.",
    sentiment: "positive",
    tags: ["AMZN", "E-commerce", "Logistics"],
    url: "#",
    relevance_score: 0.82,
    category: "Retail",
    timestamp: Date.now() - 25200000,
  },
  {
    id: "article-8",
    date: "8h ago",
    title: "Semiconductor Shortage Easing, Intel Reports",
    source: "MarketWatch",
    preview:
      "Intel CEO announces that the global semiconductor shortage is showing signs of improvement, with production capacity increasing.",
    sentiment: "positive",
    tags: ["INTC", "Semiconductors", "Supply Chain"],
    url: "#",
    relevance_score: 0.84,
    category: "Technology",
    timestamp: Date.now() - 28800000,
  },
  {
    id: "article-9",
    date: "9h ago",
    title: "JPMorgan Raises GDP Forecast for 2025",
    source: "Bloomberg",
    preview:
      "JPMorgan economists revised their GDP growth forecast upward, citing strong consumer spending and business investment.",
    sentiment: "positive",
    tags: ["JPM", "Economy", "GDP"],
    url: "#",
    relevance_score: 0.79,
    category: "Finance",
    timestamp: Date.now() - 32400000,
  },
  {
    id: "article-10",
    date: "10h ago",
    title: "Netflix Subscribers Decline in Key Markets",
    source: "Variety",
    preview:
      "Netflix reported a slight decrease in subscribers across North America and Europe, prompting concerns about market saturation.",
    sentiment: "negative",
    tags: ["NFLX", "Streaming", "Media"],
    url: "#",
    relevance_score: 0.76,
    category: "Media",
    timestamp: Date.now() - 36000000,
  },
  {
    id: "article-11",
    date: "11h ago",
    title: "Nvidia Unveils Next-Gen AI Chips",
    source: "The Verge",
    preview:
      "Nvidia announced its latest GPU architecture optimized for AI workloads, promising 3x performance improvements over previous generation.",
    sentiment: "positive",
    tags: ["NVDA", "AI", "Semiconductors"],
    url: "#",
    relevance_score: 0.91,
    category: "Technology",
    timestamp: Date.now() - 39600000,
  },
  {
    id: "article-12",
    date: "Yesterday",
    title: "FDA Approves Breakthrough Cancer Treatment",
    source: "Medical News Today",
    preview:
      "The FDA has approved a revolutionary CAR-T cell therapy for treating aggressive forms of lymphoma, marking a major advance in oncology.",
    sentiment: "positive",
    tags: ["Healthcare", "Biotech", "FDA"],
    url: "#",
    relevance_score: 0.73,
    category: "Healthcare",
    timestamp: Date.now() - 86400000,
  },
]

// Generate articles for specific sections
export function getArticlesForSection(sectionType: string): NewsArticle[] {
  switch (sectionType) {
    case "portfolio":
      return mockArticles.filter((a) =>
        a.tags.some((tag) => ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN", "NVDA"].includes(tag))
      )
    case "breaking":
      return mockArticles.slice(0, 8)
    case "industry":
      return mockArticles.filter((a) => a.category === "Technology")
    case "market_analysis":
      return mockArticles.filter(
        (a) => a.tags.includes("Economy") || a.tags.includes("MACRO") || a.tags.includes("GDP")
      )
    default:
      return mockArticles.slice(0, 10)
  }
}

export const mockData = {
  preferences: mockPreferences,
  topics: mockTopics,
  sections: mockSections,
  exclusions: mockExclusions,
  heroArticle: mockHeroArticle,
  articles: mockArticles,
  getArticlesForSection,
}
