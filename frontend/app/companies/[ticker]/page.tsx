"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronDown, ExternalLink, Calendar, TrendingUp, Users, FileText, Building, User, Bookmark, Rss, Search } from "lucide-react"
import { ApiService, CompanyData, CompanyTopic } from "@/services/api"

// Use the interfaces from the API service instead of defining them here

export default function CompanyPage() {
  const params = useParams()
  const router = useRouter()
  const ticker = params?.ticker as string

  const [companyData, setCompanyData] = useState<CompanyData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedTopics, setExpandedTopics] = useState<Set<number>>(new Set())

  // Navigation tabs similar to main app
  const tabs = [
    { id: "personalized", label: "Personalized feed", icon: User, href: "/personalized-news" },
    { id: "business-news", label: "Business News", icon: Building, href: "#", hasDropdown: true },
    { id: "portfolio", label: "Portfolio", icon: Rss, href: "/portfolio" },
    { id: "saved", label: "Saved News", icon: Bookmark, href: "/saved-news" },
    { id: "sec-docs", label: "SEC Doc Searcher", icon: Search, href: "/sec-docs" },
  ]

  useEffect(() => {
    if (ticker) {
      loadCompanyData(ticker)
    }
  }, [ticker])

  const loadCompanyData = async (ticker: string) => {
    setLoading(true)
    setError(null)

    try {
      const data = await ApiService.getCompanyTopics(ticker)
      setCompanyData(data)
    } catch (err) {
      console.error('Error loading company data:', err)
      setError(err instanceof Error ? err.message : 'Failed to load company data')
    } finally {
      setLoading(false)
    }
  }

  const toggleTopicExpansion = (topicId: number) => {
    setExpandedTopics(prev => {
      const newSet = new Set(prev)
      if (newSet.has(topicId)) {
        newSet.delete(topicId)
      } else {
        newSet.add(topicId)
      }
      return newSet
    })
  }

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'high': return 'text-red-600 bg-red-50'
      case 'medium': return 'text-yellow-600 bg-yellow-50'
      case 'low': return 'text-green-600 bg-green-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-white font-sans">
        {/* Header Navigation */}
        <div className="bg-white border-b border-gray-200 pt-2 sm:pt-3 lg:pt-4 fixed top-0 left-0 right-0 z-50">
          <div className="flex flex-col gap-2 sm:gap-3 lg:gap-4">
            <div className="flex items-center justify-between px-4 sm:px-6 lg:px-8">
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-black" style={{letterSpacing: '0.1em'}}>Haven News</h1>
            </div>

            <div className="bg-gray-100 border-t border-b border-gray py-1">
              <div className="flex gap-2 sm:gap-4 lg:gap-8 overflow-visible px-4 sm:px-6 lg:px-8">
                {tabs.map((tab) => {
                  const Icon = tab.icon
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
        </div>

        <div className="pt-[80px] sm:pt-[100px] lg:pt-[160px]">
          <div className="max-w-6xl mx-auto px-4 py-8">
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600">Loading company data...</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white font-sans">
        {/* Header Navigation */}
        <div className="bg-white border-b border-gray-200 pt-2 sm:pt-3 lg:pt-4 fixed top-0 left-0 right-0 z-50">
          <div className="flex flex-col gap-2 sm:gap-3 lg:gap-4">
            <div className="flex items-center justify-between px-4 sm:px-6 lg:px-8">
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-black" style={{letterSpacing: '0.1em'}}>Haven News</h1>
            </div>

            <div className="bg-gray-100 border-t border-b border-gray py-1">
              <div className="flex gap-2 sm:gap-4 lg:gap-8 overflow-visible px-4 sm:px-6 lg:px-8">
                {tabs.map((tab) => {
                  const Icon = tab.icon
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
        </div>

        <div className="pt-[80px] sm:pt-[100px] lg:pt-[160px]">
          <div className="max-w-6xl mx-auto px-4 py-8">
            <Button
              onClick={() => router.back()}
              variant="ghost"
              className="mb-6 flex items-center gap-2"
            >
              <ChevronLeft className="h-4 w-4" />
              Back
            </Button>

            <div className="text-center py-12">
              <div className="text-red-600 mb-4">
                <FileText className="h-12 w-12 mx-auto mb-2" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Error Loading Company Data</h2>
              <p className="text-gray-600 mb-4">{error}</p>
              <Button onClick={() => loadCompanyData(ticker)}>
                Try Again
              </Button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!companyData) {
    return (
      <div className="min-h-screen bg-white font-sans">
        {/* Header Navigation */}
        <div className="bg-white border-b border-gray-200 pt-2 sm:pt-3 lg:pt-4 fixed top-0 left-0 right-0 z-50">
          <div className="flex flex-col gap-2 sm:gap-3 lg:gap-4">
            <div className="flex items-center justify-between px-4 sm:px-6 lg:px-8">
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-black" style={{letterSpacing: '0.1em'}}>Haven News</h1>
            </div>

            <div className="bg-gray-100 border-t border-b border-gray py-1">
              <div className="flex gap-2 sm:gap-4 lg:gap-8 overflow-visible px-4 sm:px-6 lg:px-8">
                {tabs.map((tab) => {
                  const Icon = tab.icon
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
        </div>

        <div className="pt-[80px] sm:pt-[100px] lg:pt-[160px]">
          <div className="max-w-6xl mx-auto px-4 py-8">
            <Button
              onClick={() => router.back()}
              variant="ghost"
              className="mb-6 flex items-center gap-2"
            >
              <ChevronLeft className="h-4 w-4" />
              Back
            </Button>

            <div className="text-center py-12">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Company Not Found</h2>
              <p className="text-gray-600">No data available for ticker: {ticker}</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white font-sans">
      {/* Header Navigation */}
      <div className="bg-white border-b border-gray-200 pt-2 sm:pt-3 lg:pt-4 fixed top-0 left-0 right-0 z-50">
        <div className="flex flex-col gap-2 sm:gap-3 lg:gap-4">
          <div className="flex items-center justify-between px-4 sm:px-6 lg:px-8">
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-black" style={{letterSpacing: '0.1em'}}>Haven News</h1>
          </div>

          <div className="bg-gray-100 border-t border-b border-gray py-1">
            <div className="flex gap-2 sm:gap-4 lg:gap-8 overflow-visible px-4 sm:px-6 lg:px-8">
              {tabs.map((tab) => {
                const Icon = tab.icon
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
      </div>

      <div className="pt-[80px] sm:pt-[100px] lg:pt-[160px]">
        <div className="max-w-6xl mx-auto px-4 py-8">
          {/* Header */}
          <div className="mb-8">
            <Button
              onClick={() => router.back()}
              variant="ghost"
              className="mb-6 flex items-center gap-2"
            >
              <ChevronLeft className="h-4 w-4" />
              Back
            </Button>

          <div className="flex items-center gap-4 mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{companyData.name}</h1>
              <p className="text-lg text-gray-600">{companyData.ticker}</p>
            </div>
          </div>

          <div className="flex items-center gap-6 text-sm text-gray-600">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              <span>{companyData.topics.length} Topics</span>
            </div>
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              <span>{companyData.topics.reduce((sum, topic) => sum + topic.articles.length, 0)} Articles</span>
            </div>
          </div>
        </div>

        {/* Topics */}
        <div className="space-y-6">
          {companyData.topics.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Topics Found</h3>
              <p className="text-gray-600">No research topics have been extracted for this company yet.</p>
            </div>
          ) : (
            companyData.topics.map((topic) => (
              <div key={topic.id} className="border border-gray-200 rounded-lg bg-white">
                {/* Topic Header */}
                <div
                  className="p-6 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => toggleTopicExpansion(topic.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h2 className="text-xl font-semibold text-gray-900">{topic.name}</h2>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getUrgencyColor(topic.urgency)}`}>
                          {topic.urgency.toUpperCase()}
                        </span>
                        <span className="text-sm text-gray-500">
                          Score: {topic.final_score?.toFixed(2) || 'N/A'}
                        </span>
                      </div>

                      <p className="text-gray-700 mb-3">{topic.description}</p>

                      <div className="flex items-center gap-4 text-sm text-gray-600">
                        <div className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          <span>{formatDate(topic.extraction_date)}</span>
                        </div>
                        <span>Confidence: {(topic.confidence * 100).toFixed(0)}%</span>
                        <span>{topic.subtopics.length} Subtopics</span>
                        <span>{topic.articles.length} Articles</span>
                      </div>
                    </div>

                    <ChevronLeft
                      className={`h-5 w-5 text-gray-400 transition-transform ${
                        expandedTopics.has(topic.id) ? 'rotate-[-90deg]' : 'rotate-[-180deg]'
                      }`}
                    />
                  </div>
                </div>

                {/* Expanded Content */}
                {expandedTopics.has(topic.id) && (
                  <div className="border-t border-gray-200">
                    {/* Business Impact */}
                    <div className="p-6 border-b border-gray-100">
                      <h3 className="text-lg font-medium text-gray-900 mb-2">Business Impact</h3>
                      <p className="text-gray-700">{topic.business_impact}</p>
                    </div>

                    {/* Subtopics */}
                    {topic.subtopics.length > 0 && (
                      <div className="p-6 border-b border-gray-100">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Subtopics</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {topic.subtopics.map((subtopic, index) => (
                            <div key={index} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                              <div className="flex items-center justify-between mb-2">
                                <h4 className="font-medium text-gray-900">{subtopic.name}</h4>
                                <span className="text-xs text-gray-500">
                                  {(subtopic.confidence * 100).toFixed(0)}%
                                </span>
                              </div>
                              <div className="text-sm text-gray-600">
                                <p>Sources: {subtopic.sources.length}</p>
                                <p>Method: {subtopic.extraction_method}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Articles */}
                    {topic.articles.length > 0 && (
                      <div className="p-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Related Articles</h3>
                        <div className="space-y-4">
                          {topic.articles.map((article) => (
                            <div key={article.id} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                              <div className="flex items-start justify-between gap-4">
                                <div className="flex-1">
                                  <h4 className="font-medium text-gray-900 mb-2 leading-tight">
                                    <a
                                      href={article.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="hover:text-blue-600 transition-colors"
                                    >
                                      {article.title}
                                    </a>
                                  </h4>

                                  <div className="flex items-center gap-4 text-sm text-gray-600 mb-2">
                                    <span className="font-medium">{article.source}</span>
                                    {article.published_date && (
                                      <span>{formatDate(article.published_date)}</span>
                                    )}
                                    <span>Relevance: {(article.relevance_score * 100).toFixed(0)}%</span>
                                  </div>

                                  {article.content && (
                                    <p className="text-gray-700 text-sm line-clamp-2">
                                      {article.content.substring(0, 200)}...
                                    </p>
                                  )}
                                </div>

                                <a
                                  href={article.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex-shrink-0 p-2 text-gray-400 hover:text-blue-600 transition-colors"
                                >
                                  <ExternalLink className="h-4 w-4" />
                                </a>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
        </div>
      </div>
    </div>
  )
}