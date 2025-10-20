/**
 * TypeScript Type Definitions for The Daily Planet
 * Personalized News Hub with layout customization
 */

import { NewsArticle } from "./index"

// ===========================
// Enums
// ===========================

export type RegionType = "US" | "EU" | "APAC" | "Global"

export type ReadingLevel = "quick" | "standard" | "in-depth"

export type UpdateFrequency = "realtime" | "hourly" | "daily"

export type ThemeType = "light" | "dark" | "newspaper"

export type TopicType = "industry" | "theme" | "custom"

export type SectionType =
  | "portfolio"
  | "industry"
  | "breaking"
  | "market_analysis"
  | "macro_political"
  | "custom"

export type InteractionType = "click" | "read" | "remove" | "save" | "share"

export type ExclusionType = "ticker" | "topic" | "source" | "keyword"

// ===========================
// User Preferences
// ===========================

export interface UserPreferences {
  id: string
  user_id: string
  region: RegionType
  reading_level: ReadingLevel
  update_frequency: UpdateFrequency
  layout_density: 1 | 2 | 3
  theme: ThemeType
  show_breaking_news: boolean
  show_market_snapshot: boolean
  enable_ai_learning: boolean
  onboarding_completed: boolean
  created_at: string
  updated_at: string
}

export interface PreferenceUpdate {
  region?: RegionType
  reading_level?: ReadingLevel
  update_frequency?: UpdateFrequency
  layout_density?: 1 | 2 | 3
  theme?: ThemeType
  show_breaking_news?: boolean
  show_market_snapshot?: boolean
  enable_ai_learning?: boolean
}

// ===========================
// Topics
// ===========================

export interface UserTopic {
  id: string
  topic_name: string
  topic_type: TopicType
  priority: 1 | 2 | 3 | 4 | 5
  is_active: boolean
  created_at: string
}

export interface TopicCreate {
  topic_name: string
  topic_type?: TopicType
  priority?: 1 | 2 | 3 | 4 | 5
}

export interface TopicUpdate {
  priority?: 1 | 2 | 3 | 4 | 5
  is_active?: boolean
}

export interface SuggestedTopic {
  name: string
  type: TopicType
  priority: number
}

// ===========================
// Layout Sections
// ===========================

export interface LayoutSection {
  id: string
  section_id: string
  section_type: SectionType
  section_name: string
  display_order: number
  is_visible: boolean
  config_json: SectionConfig
}

export interface SectionConfig {
  article_limit?: number
  show_charts?: boolean
  show_full_preview?: boolean
  max_age_hours?: number
  tickers?: string[]
  industry?: string
  keywords?: string[]
  sources?: string[]
  [key: string]: any // Allow additional custom config
}

export interface SectionCreate {
  section_type: SectionType
  section_name: string
  config_json?: SectionConfig
}

export interface SectionUpdate {
  section_name?: string
  is_visible?: boolean
  config_json?: SectionConfig
}

export interface SectionReorder {
  section_orders: Array<{
    section_id: string
    display_order: number
  }>
}

// ===========================
// Content Exclusions
// ===========================

export interface ContentExclusion {
  id: string
  exclusion_type: ExclusionType
  exclusion_value: string
  reason?: string
  created_at: string
}

export interface ExclusionCreate {
  exclusion_type: ExclusionType
  exclusion_value: string
  reason?: string
}

// ===========================
// Article Interactions
// ===========================

export interface ArticleRemoval {
  reason?: string
  article_category?: string
  article_tags?: string[]
  article_source?: string
}

export interface ReadTracking {
  duration_seconds: number
  scroll_depth: number // 0-1
}

export interface EnhancedInteraction {
  id: string
  user_id: string
  article_id: string
  interaction_type: InteractionType
  duration_seconds?: number
  scroll_depth?: number
  removed_reason?: string
  article_category?: string
  article_tags?: string[]
  article_source?: string
  timestamp: string
}

// ===========================
// Onboarding
// ===========================

export interface OnboardingData {
  region: RegionType
  reading_level: ReadingLevel
  topics: string[]
  tickers: string[]
  layout_density: 1 | 2 | 3
}

export interface OnboardingStep {
  step: number
  title: string
  description: string
  completed: boolean
}

// ===========================
// Natural Language Preferences
// ===========================

export interface NaturalLanguageRequest {
  message: string
  user_id?: string
}

export interface NaturalLanguageResponse {
  success: boolean
  message: string
  parsed_intent: {
    action: string
    entities: any[]
  }
  confirmation: string
}

// ===========================
// Section-Specific Content
// ===========================

export interface SectionContent {
  section: LayoutSection
  articles: NewsArticle[]
  loading: boolean
  error?: string
}

export interface HeroArticle extends NewsArticle {
  featured: true
  imageUrl?: string
  fullPreview?: string
}

// ===========================
// Daily Planet State
// ===========================

export interface DailyPlanetState {
  preferences: UserPreferences | null
  topics: UserTopic[]
  sections: LayoutSection[]
  exclusions: ContentExclusion[]
  sectionContent: Map<string, SectionContent>
  loading: boolean
  error: string | null
  editMode: boolean
  onboardingComplete: boolean
}

// ===========================
// Component Props
// ===========================

export interface DailyPlanetHubProps {
  userId?: string
}

export interface OnboardingWizardProps {
  onComplete: (data: OnboardingData) => void
  onSkip?: () => void
}

export interface HeroSectionProps {
  article: HeroArticle | null
  loading?: boolean
}

export interface MarketSnapshotProps {
  tickers: string[]
  compact?: boolean
}

export interface NewspaperSectionProps {
  section: LayoutSection
  articles: NewsArticle[]
  loading?: boolean
  onRemoveArticle?: (articleId: string, reason: string) => void
  onReadArticle?: (articleId: string, duration: number) => void
  editMode?: boolean
}

export interface ArticleCardProps {
  article: NewsArticle
  variant?: "compact" | "standard" | "featured"
  onRemove?: (articleId: string, reason: string) => void
  onRead?: (articleId: string, duration: number) => void
  showRemoveButton?: boolean
}

export interface SectionManagerProps {
  sections: LayoutSection[]
  onReorder: (newOrder: SectionReorder) => void
  onAddSection: (section: SectionCreate) => void
  onRemoveSection: (sectionId: string) => void
  onUpdateSection: (sectionId: string, update: SectionUpdate) => void
}

export interface CustomizePanelProps {
  preferences: UserPreferences
  topics: UserTopic[]
  exclusions: ContentExclusion[]
  onUpdatePreferences: (update: PreferenceUpdate) => void
  onAddTopic: (topic: TopicCreate) => void
  onRemoveTopic: (topicId: string) => void
  onAddExclusion: (exclusion: ExclusionCreate) => void
  onRemoveExclusion: (exclusionId: string) => void
}

export interface NaturalLanguagePrefsProps {
  onSubmit: (message: string) => Promise<NaturalLanguageResponse>
  examples?: string[]
}

// ===========================
// API Response Types
// ===========================

export interface ApiResponse<T> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

export interface PreferencesResponse {
  id: string
  user_id: string
  region: string
  reading_level: string
  update_frequency: string
  layout_density: number
  theme: string
  show_breaking_news: boolean
  show_market_snapshot: boolean
  enable_ai_learning: boolean
  onboarding_completed: boolean
  created_at: string | null
  updated_at: string | null
}

export interface TopicsResponse {
  topics: UserTopic[]
  suggested_topics: SuggestedTopic[]
}

export interface SectionsResponse {
  sections: LayoutSection[]
}

export interface ExclusionsResponse {
  exclusions: ContentExclusion[]
}

// ===========================
// Utility Types
// ===========================

export type DailyPlanetAction =
  | { type: "SET_PREFERENCES"; payload: UserPreferences }
  | { type: "SET_TOPICS"; payload: UserTopic[] }
  | { type: "ADD_TOPIC"; payload: UserTopic }
  | { type: "REMOVE_TOPIC"; payload: string }
  | { type: "SET_SECTIONS"; payload: LayoutSection[] }
  | { type: "ADD_SECTION"; payload: LayoutSection }
  | { type: "UPDATE_SECTION"; payload: { sectionId: string; section: Partial<LayoutSection> } }
  | { type: "REMOVE_SECTION"; payload: string }
  | { type: "REORDER_SECTIONS"; payload: LayoutSection[] }
  | { type: "SET_EXCLUSIONS"; payload: ContentExclusion[] }
  | { type: "ADD_EXCLUSION"; payload: ContentExclusion }
  | { type: "REMOVE_EXCLUSION"; payload: string }
  | { type: "SET_SECTION_CONTENT"; payload: { sectionId: string; content: SectionContent } }
  | { type: "TOGGLE_EDIT_MODE" }
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SET_ERROR"; payload: string | null }
  | { type: "COMPLETE_ONBOARDING" }

// ===========================
// Default/Template Values
// ===========================

export const DEFAULT_PREFERENCES: Partial<UserPreferences> = {
  region: "Global",
  reading_level: "standard",
  update_frequency: "realtime",
  layout_density: 2,
  theme: "light",
  show_breaking_news: true,
  show_market_snapshot: true,
  enable_ai_learning: true,
  onboarding_completed: false,
}

export const DEFAULT_SECTIONS: Partial<SectionCreate>[] = [
  {
    section_type: "breaking",
    section_name: "Above the Fold",
    config_json: { article_limit: 1, show_full_preview: true },
  },
  {
    section_type: "portfolio",
    section_name: "My Portfolio",
    config_json: { article_limit: 15, show_charts: true },
  },
  {
    section_type: "market_analysis",
    section_name: "Market Analysis",
    config_json: { article_limit: 10 },
  },
  {
    section_type: "breaking",
    section_name: "Breaking News",
    config_json: { article_limit: 8, max_age_hours: 24 },
  },
]

export const SUGGESTED_TOPICS: SuggestedTopic[] = [
  { name: "Technology", type: "industry", priority: 3 },
  { name: "Healthcare", type: "industry", priority: 3 },
  { name: "Finance", type: "industry", priority: 3 },
  { name: "Energy", type: "industry", priority: 3 },
  { name: "Consumer", type: "industry", priority: 3 },
  { name: "Artificial Intelligence", type: "theme", priority: 3 },
  { name: "Climate Change", type: "theme", priority: 3 },
  { name: "Cryptocurrency", type: "theme", priority: 3 },
]

export const NLP_EXAMPLES: string[] = [
  "Show me more biotech articles",
  "Less Tesla news please",
  "I want more in-depth analysis",
  "Hide articles from this source",
  "Focus on electric vehicles but exclude TSLA",
  "Show me breaking news from the last 6 hours",
]
