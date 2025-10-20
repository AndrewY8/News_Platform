"use client"

import { useState, useEffect, useRef } from "react"
import { ExternalLink, Bookmark, X, ThumbsUp, ThumbsDown, Clock } from "lucide-react"
import { NewsArticle } from "@/types"

interface ArticleCardProps {
  article: NewsArticle
  variant?: "compact" | "standard" | "featured"
  onRemove?: (articleId: string, reason: string) => void
  onRead?: (articleId: string, duration: number) => void
  showRemoveButton?: boolean
  columnSpan?: number // For responsive hiding
}

export function ArticleCard({
  article,
  variant = "standard",
  onRemove,
  onRead,
  showRemoveButton = true,
  columnSpan = 6,
}: ArticleCardProps) {
  const [showRemoveMenu, setShowRemoveMenu] = useState(false)
  const [readStartTime, setReadStartTime] = useState<number | null>(null)
  const cardRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Track when article comes into view
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !readStartTime) {
            setReadStartTime(Date.now())
          } else if (!entry.isIntersecting && readStartTime) {
            // Article left view, track reading time
            const duration = Math.floor((Date.now() - readStartTime) / 1000)
            if (duration > 3 && onRead) {
              // Only track if read for more than 3 seconds
              onRead(article.id, duration)
            }
            setReadStartTime(null)
          }
        })
      },
      { threshold: 0.5 }
    )

    if (cardRef.current) {
      observer.observe(cardRef.current)
    }

    return () => {
      if (cardRef.current) {
        observer.unobserve(cardRef.current)
      }
    }
  }, [readStartTime, article.id, onRead])

  const handleRemove = (reason: string) => {
    if (onRemove) {
      onRemove(article.id, reason)
    }
    setShowRemoveMenu(false)
  }

  const handleArticleClick = () => {
    if (article.url) {
      window.open(article.url, '_blank', 'noopener,noreferrer')
    }
  }

  const getSentimentIcon = () => {
    if (article.sentiment === "positive") {
      return <ThumbsUp className="w-4 h-4 text-green-600" />
    }
    if (article.sentiment === "negative") {
      return <ThumbsDown className="w-4 h-4 text-red-600" />
    }
    return <div className="w-4 h-4 bg-gray-400 rounded-full" style={{ width: '16px', height: '2px' }} />
  }

  if (variant === "compact") {
    // Determine what to hide based on column span
    // columnSpan: 3-4 = very small, 5-6 = small, 7+ = normal
    const isVerySmall = columnSpan <= 4
    const isSmall = columnSpan <= 6

    return (
      <div
        ref={cardRef}
        className="relative group hover:bg-gray-50 transition-colors"
      >
        <div className="px-4 py-3 flex items-start gap-3">
          {/* Time - hide when very small */}
          {!isVerySmall && (
            <div className="flex-shrink-0 w-14 text-xs text-gray-500 pt-1">
              {article.date}
            </div>
          )}

          {/* Sentiment - hide when very small */}
          {!isVerySmall && (
            <div className="flex-shrink-0 pt-1">
              {getSentimentIcon()}
            </div>
          )}

          {/* Content */}
          <div
            className="flex-1 cursor-pointer min-w-0"
            onClick={handleArticleClick}
          >
            <h3 className={`font-semibold text-gray-900 leading-snug mb-1 hover:text-blue-600 ${
              isVerySmall ? 'text-xs' : 'text-sm'
            }`}>
              {article.title}
            </h3>
            <p className={`text-gray-600 ${
              isVerySmall ? 'line-clamp-2 text-xs' : isSmall ? 'line-clamp-3 text-xs' : 'line-clamp-4 text-xs'
            }`}>
              {article.preview}
            </p>
            {!isSmall && (
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-gray-500">{article.source}</span>
              </div>
            )}
          </div>

          {/* Tags & Actions - make smaller and stack when small */}
          <div className={`flex-shrink-0 flex items-center gap-1.5 ${
            isSmall ? 'flex-col' : 'flex-row'
          }`}>
            {!isVerySmall && article.tags.slice(0, isSmall ? 2 : 3).map((tag, index) => (
              <span
                key={index}
                className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded font-mono"
                style={{ fontSize: '10px' }}
              >
                {tag}
              </span>
            ))}

            {showRemoveButton && (
              <div className="relative">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setShowRemoveMenu(!showRemoveMenu)
                  }}
                  className="p-1 hover:bg-red-100 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Remove article"
                >
                  <X className="w-3 h-3 text-red-600" />
                </button>

                {showRemoveMenu && (
                  <div className="absolute right-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-10">
                    <div className="p-2">
                      <p className="text-xs font-medium text-gray-700 mb-2 px-2">
                        Why remove this?
                      </p>
                      <button
                        onClick={() => handleRemove("not_interested")}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 rounded"
                      >
                        Not interested
                      </button>
                      <button
                        onClick={() => handleRemove("irrelevant")}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 rounded"
                      >
                        Not relevant to me
                      </button>
                      <button
                        onClick={() => handleRemove("poor_quality")}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 rounded"
                      >
                        Poor quality
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Standard variant
  return (
    <div
      ref={cardRef}
      className="relative group bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
    >
      {showRemoveButton && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            setShowRemoveMenu(!showRemoveMenu)
          }}
          className="absolute top-4 right-4 p-2 hover:bg-red-100 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity z-10"
          title="Remove article"
        >
          <X className="w-4 h-4 text-red-600" />
        </button>
      )}

      {showRemoveMenu && (
        <div className="absolute top-12 right-4 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-20">
          <div className="p-2">
            <p className="text-xs font-medium text-gray-700 mb-2 px-2">
              Why remove this?
            </p>
            <button
              onClick={() => handleRemove("not_interested")}
              className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 rounded"
            >
              Not interested
            </button>
            <button
              onClick={() => handleRemove("irrelevant")}
              className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 rounded"
            >
              Not relevant to me
            </button>
            <button
              onClick={() => handleRemove("poor_quality")}
              className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 rounded"
            >
              Poor quality
            </button>
          </div>
        </div>
      )}

      <div className="cursor-pointer" onClick={handleArticleClick}>
        {/* Meta */}
        <div className="flex items-center gap-3 mb-3">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Clock className="w-4 h-4" />
            {article.date}
          </div>
          <span className="text-sm text-gray-500">{article.source}</span>
          {getSentimentIcon()}
        </div>

        {/* Title */}
        <h3 className="text-xl font-bold text-gray-900 mb-2 hover:text-blue-600 leading-tight">
          {article.title}
        </h3>

        {/* Preview */}
        <p className="text-gray-700 mb-4 leading-relaxed">
          {article.preview}
        </p>

        {/* Tags */}
        {article.tags && article.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {article.tags.slice(0, 5).map((tag, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded font-mono"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {article.category && (
              <span className="text-sm text-gray-500">
                {article.category}
              </span>
            )}
          </div>

          {article.url && (
            <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-blue-600" />
          )}
        </div>
      </div>
    </div>
  )
}
