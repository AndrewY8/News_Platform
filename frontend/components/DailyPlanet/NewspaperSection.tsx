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
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  const articleLimit = section.config_json?.article_limit || 10

  return (
    <section
      ref={setNodeRef}
      style={style}
      className="bg-white border-2 border-black shadow-sm"
    >
      {/* Newspaper-style Header */}
      <div className="border-b-4 border-double border-black bg-white">
        <div className="px-4 py-2 flex items-center gap-3 bg-gray-50 border-b border-gray-300">
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
              className="text-2xl font-black text-black uppercase tracking-wide leading-tight"
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

      {/* Articles */}
      <div className="divide-y divide-gray-300">
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
          articles.slice(0, articleLimit).map((article) => (
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

      {/* Footer - More Articles */}
      {articles.length > articleLimit && (
        <div className="border-t-2 border-black bg-gray-50 px-4 py-2 text-center">
          <button
            className="text-xs font-bold text-black uppercase tracking-widest hover:underline"
            style={{ fontFamily: '"Georgia", serif' }}
          >
            {articles.length - articleLimit} More →
          </button>
        </div>
      )}
    </section>
  )
}
