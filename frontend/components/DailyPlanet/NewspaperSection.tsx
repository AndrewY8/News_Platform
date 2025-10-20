"use client"

import { GripVertical } from "lucide-react"
import { LayoutSection } from "@/types/dailyplanet"
import { NewsArticle } from "@/types"
import { ArticleCard } from "./ArticleCard"
import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"

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
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: section.section_id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition: transition || 'transform 200ms ease',
    opacity: isDragging ? 0.5 : 1,
  }

  const visibleArticles = 3
  const hasMoreArticles = articles.length > visibleArticles

  return (
    <section
      ref={setNodeRef}
      style={style}
      className="bg-white border border-gray-300 shadow-sm transition-all duration-200 hover:shadow-md flex flex-col"
    >
      {/* Newspaper-style Header */}
      <div className="border-b-2 border-black bg-white flex-shrink-0">
        <div className="px-4 py-2 flex items-center gap-3 bg-gray-50 border-b border-gray-200">
          {/* Drag Handle */}
          <button
            {...attributes}
            {...listeners}
            className="cursor-grab active:cursor-grabbing p-1 hover:bg-gray-200"
          >
            <GripVertical className="w-4 h-4 text-gray-600" />
          </button>

          {/* Section Title - Classic Newspaper Style */}
          <div className="flex-1">
            <h2
              className="text-xl font-black text-black uppercase tracking-wide leading-tight"
              style={{
                fontFamily: '"Georgia", "Times New Roman", serif',
                letterSpacing: '0.05em'
              }}
            >
              {section.section_name}
            </h2>
          </div>
        </div>
      </div>

      {/* Articles - Scrollable container */}
      <div className="overflow-y-auto max-h-[600px] divide-y divide-gray-200 flex-1">
        {loading ? (
          <div className="p-6">
            <div className="space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="animate-pulse">
                  <div className="h-4 bg-gray-200 w-3/4 mb-2"></div>
                  <div className="h-3 bg-gray-200 w-1/2"></div>
                </div>
              ))}
            </div>
          </div>
        ) : articles.length === 0 ? (
          <div className="p-8 text-center border-t border-dashed border-gray-400">
            <p
              className="text-gray-700 text-sm italic"
              style={{ fontFamily: '"Georgia", serif' }}
            >
              No articles available for this section
            </p>
          </div>
        ) : (
          articles.map((article) => (
            <ArticleCard
              key={article.id}
              article={article}
              variant="compact"
              onRemove={onRemoveArticle}
              onRead={onReadArticle}
              showRemoveButton={true}
            />
          ))
        )}
      </div>

      {/* Footer - Article count */}
      {hasMoreArticles && (
        <div className="border-t border-gray-200 bg-gray-50 px-4 py-2 text-center flex-shrink-0">
          <p className="text-xs text-gray-600 italic">
            Showing {visibleArticles} of {articles.length} articles • Scroll for more
          </p>
        </div>
      )}
    </section>
  )
}
