"use client"

import { useState, useRef, useEffect } from "react"
import { GripVertical, GripHorizontal } from "lucide-react"
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
  columnSpan?: number
  onColumnSpanChange?: (sectionId: string, span: number) => void
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
  columnSpan = 6,
  onColumnSpanChange,
}: NewspaperSectionProps) {
  const [height, setHeight] = useState(400)
  const [localColumnSpan, setLocalColumnSpan] = useState(columnSpan)
  const [isResizingVertical, setIsResizingVertical] = useState(false)
  const [isResizingHorizontal, setIsResizingHorizontal] = useState(false)
  const resizeRef = useRef<HTMLDivElement>(null)
  const startXRef = useRef<number>(0)
  const startSpanRef = useRef<number>(columnSpan)

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

  // Update local span when prop changes
  useEffect(() => {
    setLocalColumnSpan(columnSpan)
  }, [columnSpan])

  // Handle vertical resize
  const handleVerticalMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizingVertical(true)
  }

  // Handle horizontal resize
  const handleHorizontalMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsResizingHorizontal(true)
    startXRef.current = e.clientX
    startSpanRef.current = localColumnSpan
  }

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!resizeRef.current) return

      const rect = resizeRef.current.getBoundingClientRect()
      const parentRect = resizeRef.current.parentElement?.getBoundingClientRect()

      // Vertical resize
      if (isResizingVertical) {
        const newHeight = e.clientY - rect.top
        // Min height 200px, max height 1000px
        if (newHeight >= 200 && newHeight <= 1000) {
          setHeight(newHeight)
        }
      }

      // Horizontal resize - calculate column span change
      if (isResizingHorizontal && parentRect && onColumnSpanChange) {
        const deltaX = e.clientX - startXRef.current
        const parentWidth = parentRect.width
        const columnWidth = parentWidth / 12 // 12-column grid

        // Calculate how many columns the delta represents
        const columnDelta = Math.round(deltaX / columnWidth)
        const newSpan = Math.max(3, Math.min(12, startSpanRef.current + columnDelta))

        if (newSpan !== localColumnSpan) {
          setLocalColumnSpan(newSpan)
          onColumnSpanChange(section.section_id, newSpan)
        }
      }
    }

    const handleMouseUp = () => {
      setIsResizingVertical(false)
      setIsResizingHorizontal(false)
    }

    if (isResizingVertical || isResizingHorizontal) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizingVertical, isResizingHorizontal, localColumnSpan, onColumnSpanChange, section.section_id])

  return (
    <section
      ref={(node) => {
        setNodeRef(node)
        if (resizeRef) {
          resizeRef.current = node
        }
      }}
      style={{
        ...style,
        height: `${height}px`,
        gridColumn: `span ${localColumnSpan}`,
      }}
      className="bg-white border border-gray-300 shadow-sm transition-all duration-200 hover:shadow-md flex flex-col relative"
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
      <div className="overflow-y-auto divide-y divide-gray-200 flex-1">
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
              columnSpan={localColumnSpan}
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

      {/* Vertical Resize Handle (Bottom) */}
      <div
        onMouseDown={handleVerticalMouseDown}
        className={`absolute bottom-0 left-0 right-0 h-3 cursor-ns-resize flex items-center justify-center group hover:bg-blue-100 transition-colors ${
          isResizingVertical ? 'bg-blue-200' : ''
        }`}
      >
        <GripHorizontal className="w-4 h-4 text-gray-400 group-hover:text-blue-600" />
      </div>

      {/* Horizontal Resize Handle (Right) */}
      <div
        onMouseDown={handleHorizontalMouseDown}
        className={`absolute top-0 right-0 bottom-0 w-3 cursor-ew-resize flex items-center justify-center group hover:bg-blue-100 transition-colors ${
          isResizingHorizontal ? 'bg-blue-200' : ''
        }`}
      >
        <GripVertical className="w-4 h-4 text-gray-400 group-hover:text-blue-600" />
      </div>

      {/* Corner Resize Handle (Bottom-Right) - for both directions */}
      <div
        onMouseDown={(e) => {
          e.preventDefault()
          setIsResizingVertical(true)
          setIsResizingHorizontal(true)
        }}
        className={`absolute bottom-0 right-0 w-3 h-3 cursor-nwse-resize bg-gray-300 hover:bg-blue-400 transition-colors ${
          isResizingVertical && isResizingHorizontal ? 'bg-blue-500' : ''
        }`}
      />
    </section>
  )
}
