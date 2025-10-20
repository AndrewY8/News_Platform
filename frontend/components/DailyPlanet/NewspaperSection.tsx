"use client"

import { GripVertical, Eye, EyeOff, Settings, Trash2 } from "lucide-react"
import { LayoutSection } from "@/types/dailyplanet"
import { NewsArticle } from "@/types"
import { ArticleCard } from "./ArticleCard"

interface NewspaperSectionProps {
  section: LayoutSection
  articles: NewsArticle[]
  loading?: boolean
  onRemoveArticle?: (articleId: string, reason: string) => void
  onReadArticle?: (articleId: string, duration: number) => void
  editMode?: boolean
  onToggleVisibility?: (sectionId: string) => void
  onRemoveSection?: (sectionId: string) => void
  onConfigureSection?: (sectionId: string) => void
}

export function NewspaperSection({
  section,
  articles,
  loading,
  onRemoveArticle,
  onReadArticle,
  editMode,
  onToggleVisibility,
  onRemoveSection,
  onConfigureSection,
}: NewspaperSectionProps) {
  const getSectionIcon = () => {
    switch (section.section_type) {
      case "portfolio":
        return "📊"
      case "industry":
        return "🏭"
      case "breaking":
        return "⚡"
      case "market_analysis":
        return "📈"
      case "macro_political":
        return "🌍"
      case "custom":
        return "⭐"
      default:
        return "📰"
    }
  }

  const articleLimit = section.config_json?.article_limit || 10

  return (
    <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Section Header */}
      <div className={`border-b bg-gray-50 ${editMode ? 'bg-blue-50' : ''}`}>
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {editMode && (
              <button className="cursor-grab active:cursor-grabbing p-1 hover:bg-gray-200 rounded">
                <GripVertical className="w-5 h-5 text-gray-400" />
              </button>
            )}

            <span className="text-2xl">{getSectionIcon()}</span>

            <div>
              <h2 className="text-xl font-bold text-gray-900" style={{ fontFamily: 'serif' }}>
                {section.section_name}
              </h2>
              <p className="text-xs text-gray-500 capitalize">
                {section.section_type.replace('_', ' ')}
              </p>
            </div>
          </div>

          {editMode && (
            <div className="flex items-center gap-2">
              {onToggleVisibility && (
                <button
                  onClick={() => onToggleVisibility(section.section_id)}
                  className="p-2 hover:bg-gray-200 rounded-lg"
                  title={section.is_visible ? "Hide section" : "Show section"}
                >
                  {section.is_visible ? (
                    <Eye className="w-4 h-4 text-gray-600" />
                  ) : (
                    <EyeOff className="w-4 h-4 text-gray-400" />
                  )}
                </button>
              )}
              {onConfigureSection && (
                <button
                  onClick={() => onConfigureSection(section.section_id)}
                  className="p-2 hover:bg-gray-200 rounded-lg"
                  title="Configure section"
                >
                  <Settings className="w-4 h-4 text-gray-600" />
                </button>
              )}
              {onRemoveSection && (
                <button
                  onClick={() => onRemoveSection(section.section_id)}
                  className="p-2 hover:bg-red-100 rounded-lg"
                  title="Remove section"
                >
                  <Trash2 className="w-4 h-4 text-red-600" />
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Articles */}
      <div className="divide-y divide-gray-200">
        {loading ? (
          <div className="p-6">
            <div className="space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                </div>
              ))}
            </div>
          </div>
        ) : articles.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-500">No articles available for this section</p>
            <p className="text-sm text-gray-400 mt-1">
              Check back later or adjust your preferences
            </p>
          </div>
        ) : (
          articles.slice(0, articleLimit).map((article) => (
            <ArticleCard
              key={article.id}
              article={article}
              variant="compact"
              onRemove={onRemoveArticle}
              onRead={onReadArticle}
              showRemoveButton={!editMode}
            />
          ))
        )}
      </div>

      {/* Footer */}
      {articles.length > articleLimit && (
        <div className="border-t bg-gray-50 px-6 py-3 text-center">
          <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
            Show {articles.length - articleLimit} more articles
          </button>
        </div>
      )}
    </section>
  )
}
