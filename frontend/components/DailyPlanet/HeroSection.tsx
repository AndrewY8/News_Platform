"use client"

import { ExternalLink, Clock, TrendingUp, TrendingDown } from "lucide-react"
import { HeroArticle } from "@/types/dailyplanet"

interface HeroSectionProps {
  article: HeroArticle | null
  loading?: boolean
}

export function HeroSection({ article, loading }: HeroSectionProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
        <div className="h-4 bg-gray-200 rounded w-1/4 mb-6"></div>
        <div className="h-32 bg-gray-200 rounded mb-4"></div>
        <div className="h-4 bg-gray-200 rounded w-full mb-2"></div>
        <div className="h-4 bg-gray-200 rounded w-5/6"></div>
      </div>
    )
  }

  if (!article) {
    return (
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border border-blue-200 p-8">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Above the Fold
          </h2>
          <p className="text-gray-600">
            Your most important story will appear here
          </p>
        </div>
      </div>
    )
  }

  const getSentimentIcon = () => {
    if (article.sentiment === "positive") {
      return <TrendingUp className="w-5 h-5 text-green-600" />
    }
    if (article.sentiment === "negative") {
      return <TrendingDown className="w-5 h-5 text-red-600" />
    }
    return null
  }

  const getSentimentColor = () => {
    if (article.sentiment === "positive") return "text-green-600"
    if (article.sentiment === "negative") return "text-red-600"
    return "text-gray-600"
  }

  return (
    <article className="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      <div className="grid md:grid-cols-2 gap-6 p-8">
        {/* Text Content */}
        <div className="flex flex-col justify-between">
          <div>
            {/* Meta */}
            <div className="flex items-center gap-4 mb-4">
              <span className="text-xs font-semibold text-blue-600 uppercase tracking-wide">
                Featured Story
              </span>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Clock className="w-4 h-4" />
                {article.date}
              </div>
              {getSentimentIcon() && (
                <div className="flex items-center gap-1">
                  {getSentimentIcon()}
                </div>
              )}
            </div>

            {/* Headline */}
            <h2 className="text-4xl font-bold text-gray-900 mb-4 leading-tight" style={{ fontFamily: 'serif' }}>
              {article.title}
            </h2>

            {/* Source */}
            <p className="text-sm text-gray-600 mb-4">
              {article.source}
            </p>

            {/* Preview */}
            <p className="text-lg text-gray-700 leading-relaxed mb-6">
              {article.fullPreview || article.preview}
            </p>

            {/* Tags */}
            {article.tags && article.tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-6">
                {article.tags.slice(0, 5).map((tag, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded-full font-medium"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* CTA */}
          <div>
            {article.url && (
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors"
              >
                Read Full Article
                <ExternalLink className="w-4 h-4" />
              </a>
            )}
            {article.relevance_score && (
              <div className="mt-4 text-sm text-gray-500">
                Relevance: {(article.relevance_score * 100).toFixed(0)}%
              </div>
            )}
          </div>
        </div>

        {/* Image Placeholder / Visual */}
        <div className="flex items-center justify-center">
          {article.imageUrl ? (
            <img
              src={article.imageUrl}
              alt={article.title}
              className="w-full h-full object-cover rounded-lg"
            />
          ) : (
            <div className="w-full h-full min-h-[300px] bg-gradient-to-br from-blue-100 to-indigo-100 rounded-lg flex items-center justify-center">
              <div className="text-center p-8">
                <div className={`text-6xl font-bold mb-2 ${getSentimentColor()}`}>
                  {article.sentiment === "positive" && "📈"}
                  {article.sentiment === "negative" && "📉"}
                  {article.sentiment === "neutral" && "📰"}
                </div>
                <p className="text-gray-600 font-medium">
                  {article.category || "News"}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </article>
  )
}
