"use client"

import { useState, useEffect, useReducer } from "react"
import { Settings, Edit3, X } from "lucide-react"
import { ApiService } from "@/services/api"
import { OnboardingWizard } from "./OnboardingWizard"
import { HeroSection } from "./HeroSection"
import { MarketSnapshot } from "./MarketSnapshot"
import { NewspaperSection } from "./NewspaperSection"
import { CustomizePanel } from "./CustomizePanel"
import {
  DailyPlanetState,
  DailyPlanetAction,
  OnboardingData,
  LayoutSection,
  UserPreferences,
  UserTopic,
  ContentExclusion,
} from "@/types/dailyplanet"
import { mockData } from "@/lib/mockDailyPlanetData"
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core"
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
} from "@dnd-kit/sortable"

interface DailyPlanetHubProps {
  userId?: string
  initialTickers?: string[]
}

// Reducer for state management
function dailyPlanetReducer(state: DailyPlanetState, action: DailyPlanetAction): DailyPlanetState {
  switch (action.type) {
    case "SET_PREFERENCES":
      return { ...state, preferences: action.payload }
    case "SET_TOPICS":
      return { ...state, topics: action.payload }
    case "ADD_TOPIC":
      return { ...state, topics: [...state.topics, action.payload] }
    case "REMOVE_TOPIC":
      return { ...state, topics: state.topics.filter(t => t.id !== action.payload) }
    case "SET_SECTIONS":
      return { ...state, sections: action.payload }
    case "ADD_SECTION":
      return { ...state, sections: [...state.sections, action.payload] }
    case "UPDATE_SECTION":
      return {
        ...state,
        sections: state.sections.map(s =>
          s.section_id === action.payload.sectionId
            ? { ...s, ...action.payload.section }
            : s
        ),
      }
    case "REMOVE_SECTION":
      return { ...state, sections: state.sections.filter(s => s.section_id !== action.payload) }
    case "REORDER_SECTIONS":
      return { ...state, sections: action.payload }
    case "SET_EXCLUSIONS":
      return { ...state, exclusions: action.payload }
    case "ADD_EXCLUSION":
      return { ...state, exclusions: [...state.exclusions, action.payload] }
    case "REMOVE_EXCLUSION":
      return { ...state, exclusions: state.exclusions.filter(e => e.id !== action.payload) }
    case "SET_SECTION_CONTENT":
      const newSectionContent = new Map(state.sectionContent)
      newSectionContent.set(action.payload.sectionId, action.payload.content)
      return { ...state, sectionContent: newSectionContent }
    case "TOGGLE_EDIT_MODE":
      return { ...state, editMode: !state.editMode }
    case "SET_LOADING":
      return { ...state, loading: action.payload }
    case "SET_ERROR":
      return { ...state, error: action.payload }
    case "COMPLETE_ONBOARDING":
      return { ...state, onboardingComplete: true }
    default:
      return state
  }
}

export function DailyPlanetHub({ userId, initialTickers = [] }: DailyPlanetHubProps) {
  const [state, dispatch] = useReducer(dailyPlanetReducer, {
    preferences: null,
    topics: [],
    sections: [],
    exclusions: [],
    sectionContent: new Map(),
    loading: true,
    error: null,
    editMode: false,
    onboardingComplete: false,
  })

  const [showOnboarding, setShowOnboarding] = useState(false)
  const [showCustomize, setShowCustomize] = useState(false)
  const [columnSpans, setColumnSpans] = useState<Map<string, number>>(new Map())

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px movement required before drag starts
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Initial data fetch
  useEffect(() => {
    loadUserData()
  }, [])

  const loadUserData = async () => {
    try {
      dispatch({ type: "SET_LOADING", payload: true })

      // Try to load from backend, fall back to mock data
      try {
        const [prefsRes, topicsRes, sectionsRes, exclusionsRes] = await Promise.all([
          ApiService.getDailyPlanetPreferences().catch(() => null),
          ApiService.getDailyPlanetTopics().catch(() => ({ topics: [] })),
          ApiService.getDailyPlanetSections().catch(() => ({ sections: [] })),
          ApiService.getDailyPlanetExclusions().catch(() => ({ exclusions: [] })),
        ])

        if (prefsRes) {
          dispatch({ type: "SET_PREFERENCES", payload: prefsRes as UserPreferences })

          // Check if onboarding is complete
          if (!prefsRes.onboarding_completed) {
            setShowOnboarding(true)
          } else {
            dispatch({ type: "COMPLETE_ONBOARDING" })
          }
        } else {
          // No preferences found, use mock data
          console.log("Using mock data for Daily Planet")
          loadMockData()
          return
        }

        if (topicsRes.topics) {
          dispatch({ type: "SET_TOPICS", payload: topicsRes.topics })
        }

        if (sectionsRes.sections) {
          dispatch({ type: "SET_SECTIONS", payload: sectionsRes.sections })
        }

        if (exclusionsRes.exclusions) {
          dispatch({ type: "SET_EXCLUSIONS", payload: exclusionsRes.exclusions })
        }
      } catch (backendError) {
        console.log("Backend not available, using mock data", backendError)
        loadMockData()
        return
      }

      dispatch({ type: "SET_LOADING", payload: false })
    } catch (error) {
      console.error("Error loading user data:", error)
      dispatch({ type: "SET_ERROR", payload: "Failed to load your preferences" })
      dispatch({ type: "SET_LOADING", payload: false })
    }
  }

  const loadMockData = () => {
    // Load all mock data
    dispatch({ type: "SET_PREFERENCES", payload: mockData.preferences })
    dispatch({ type: "SET_TOPICS", payload: mockData.topics })
    dispatch({ type: "SET_SECTIONS", payload: mockData.sections })
    dispatch({ type: "SET_EXCLUSIONS", payload: mockData.exclusions })
    dispatch({ type: "COMPLETE_ONBOARDING" })

    // Load mock articles for each section
    mockData.sections.forEach((section) => {
      const articles = mockData.getArticlesForSection(section.section_type)
      dispatch({
        type: "SET_SECTION_CONTENT",
        payload: {
          sectionId: section.section_id,
          content: {
            section,
            articles,
            loading: false,
          },
        },
      })
    })

    dispatch({ type: "SET_LOADING", payload: false })
  }

  const handleOnboardingComplete = async (data: OnboardingData) => {
    try {
      await ApiService.completeDailyPlanetOnboarding(data)
      setShowOnboarding(false)
      dispatch({ type: "COMPLETE_ONBOARDING" })

      // Reload data
      await loadUserData()
    } catch (error) {
      console.error("Error completing onboarding:", error)
      dispatch({ type: "SET_ERROR", payload: "Failed to save your preferences" })
    }
  }

  const handleOnboardingSkip = () => {
    setShowOnboarding(false)
    dispatch({ type: "COMPLETE_ONBOARDING" })
  }

  const handleArticleRemove = async (articleId: string, reason: string) => {
    try {
      await ApiService.trackArticleRemoval(articleId, {
        reason,
        article_category: undefined,
        article_tags: undefined,
        article_source: undefined,
      })

      // Remove article from UI
      // TODO: Implement article removal from section content
    } catch (error) {
      console.error("Error removing article:", error)
    }
  }

  const handleArticleRead = async (articleId: string, duration: number) => {
    try {
      await ApiService.trackArticleRead(articleId, {
        duration_seconds: duration,
        scroll_depth: 0.8, // TODO: Calculate actual scroll depth
      })
    } catch (error) {
      console.error("Error tracking article read:", error)
    }
  }

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id) {
      const oldIndex = state.sections.findIndex((s) => s.section_id === active.id)
      const newIndex = state.sections.findIndex((s) => s.section_id === over.id)

      const reorderedSections = arrayMove(state.sections, oldIndex, newIndex).map(
        (section, index) => ({
          ...section,
          display_order: index,
        })
      )

      dispatch({ type: "REORDER_SECTIONS", payload: reorderedSections })

      try {
        await ApiService.updateDailyPlanetSections(reorderedSections)
        console.log("✅ Section order saved")
      } catch (error) {
        console.log("⚠️ Backend not available - order saved locally only")
        // Don't revert - keep the new order
      }
    }
  }

  const handleColumnSpanChange = (sectionId: string, newSpan: number) => {
    const visibleSections = state.sections
      .filter(section => section.is_visible)
      .sort((a, b) => a.display_order - b.display_order)

    const sectionIndex = visibleSections.findIndex(s => s.section_id === sectionId)
    if (sectionIndex === -1) return

    // Calculate which row this section is in
    let currentRow = 0
    let currentRowSpan = 0
    let rowStartIndex = 0

    for (let i = 0; i <= sectionIndex; i++) {
      const span = columnSpans.get(visibleSections[i].section_id) || 6
      if (currentRowSpan + span > 12) {
        // New row
        currentRow++
        currentRowSpan = span
        rowStartIndex = i
      } else {
        currentRowSpan += span
      }
    }

    // Find all sections in the same row
    const sectionsInRow: string[] = []
    let rowSpan = 0
    for (let i = rowStartIndex; i < visibleSections.length; i++) {
      const span = columnSpans.get(visibleSections[i].section_id) || 6
      if (rowSpan + span > 12) break
      sectionsInRow.push(visibleSections[i].section_id)
      rowSpan += span
    }

    // If there's only one section in the row, allow resize without adjustment
    if (sectionsInRow.length === 1) {
      setColumnSpans(prev => new Map(prev).set(sectionId, newSpan))
      return
    }

    // Find adjacent section to adjust
    const sectionIndexInRow = sectionsInRow.indexOf(sectionId)
    const adjacentIndex = sectionIndexInRow === 0 ? 1 : sectionIndexInRow - 1
    const adjacentSectionId = sectionsInRow[adjacentIndex]

    if (!adjacentSectionId) {
      setColumnSpans(prev => new Map(prev).set(sectionId, newSpan))
      return
    }

    const oldSpan = columnSpans.get(sectionId) || 6
    const spanChange = newSpan - oldSpan
    const adjacentOldSpan = columnSpans.get(adjacentSectionId) || 6
    const adjacentNewSpan = Math.max(3, Math.min(12, adjacentOldSpan - spanChange))

    // Update both spans
    setColumnSpans(prev => {
      const updated = new Map(prev)
      updated.set(sectionId, newSpan)
      updated.set(adjacentSectionId, adjacentNewSpan)
      return updated
    })
  }

  if (state.loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading The Daily Planet...</p>
        </div>
      </div>
    )
  }

  if (state.error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-600 mb-4">{state.error}</p>
          <button
            onClick={loadUserData}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full">
      {/* Onboarding Wizard */}
      {showOnboarding && (
        <OnboardingWizard
          onComplete={handleOnboardingComplete}
          onSkip={handleOnboardingSkip}
          existingTickers={initialTickers}
        />
      )}

      {/* Customize Panel */}
      {showCustomize && state.preferences && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[9999] flex items-center justify-end">
          <div className="bg-white h-full w-full max-w-2xl shadow-2xl overflow-y-auto">
            <div className="p-6 border-b bg-white sticky top-0 z-[10000]">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-900">Customize Your Daily Planet</h2>
                <button
                  onClick={() => setShowCustomize(false)}
                  className="p-2 hover:bg-gray-100 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
            <CustomizePanel
              preferences={state.preferences}
              topics={state.topics}
              exclusions={state.exclusions}
              onUpdatePreferences={async (update) => {
                await ApiService.updateDailyPlanetPreferences(update)
                await loadUserData()
              }}
              onAddTopic={async (topic) => {
                await ApiService.addDailyPlanetTopic(topic)
                await loadUserData()
              }}
              onRemoveTopic={async (topicId) => {
                await ApiService.deleteDailyPlanetTopic(topicId)
                dispatch({ type: "REMOVE_TOPIC", payload: topicId })
              }}
              onAddExclusion={async (exclusion) => {
                await ApiService.addDailyPlanetExclusion(exclusion)
                await loadUserData()
              }}
              onRemoveExclusion={async (exclusionId) => {
                await ApiService.deleteDailyPlanetExclusion(exclusionId)
                dispatch({ type: "REMOVE_EXCLUSION", payload: exclusionId })
              }}
            />
          </div>
        </div>
      )}

      {/* Page Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 mb-2" style={{ fontFamily: 'serif' }}>
              The Daily Planet
            </h1>
            <p className="text-sm text-gray-600">
              {new Date().toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
              })}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowCustomize(true)}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2 text-sm"
            >
              <Settings className="w-4 h-4" />
              Customize
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="w-full">
        {/* Dynamic Sections - Flexible grid with DnD */}
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={state.sections.filter(s => s.is_visible).map(s => s.section_id)}
            strategy={rectSortingStrategy}
          >
            <div
              className="grid gap-3"
              style={{
                gridTemplateColumns: 'repeat(12, 1fr)',
                gridAutoRows: 'min-content',
              }}
            >
              {state.sections
                .filter(section => section.is_visible)
                .sort((a, b) => a.display_order - b.display_order)
                .map((section) => {
                  const sectionContent = state.sectionContent.get(section.section_id)

                  return (
                    <NewspaperSection
                      key={section.section_id}
                      section={section}
                      articles={sectionContent?.articles || []}
                      loading={sectionContent?.loading || false}
                      onRemoveArticle={handleArticleRemove}
                      onReadArticle={handleArticleRead}
                      editMode={state.editMode}
                      columnSpan={columnSpans.get(section.section_id) || 6}
                      onColumnSpanChange={handleColumnSpanChange}
                    />
                  )
                })}
            </div>
          </SortableContext>
        </DndContext>

        {/* Empty State */}
        {state.sections.filter(s => s.is_visible).length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-600 mb-4">No sections configured yet</p>
            <button
              onClick={() => setShowCustomize(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Add Sections
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
