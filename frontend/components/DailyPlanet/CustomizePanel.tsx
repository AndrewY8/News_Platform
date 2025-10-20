"use client"

import { useState } from "react"
import { Plus, X, Tag, Ban, Settings as SettingsIcon } from "lucide-react"
import {
  UserPreferences,
  UserTopic,
  ContentExclusion,
  PreferenceUpdate,
  TopicCreate,
  ExclusionCreate,
  RegionType,
  ReadingLevel,
  ThemeType,
  SUGGESTED_TOPICS,
} from "@/types/dailyplanet"

interface CustomizePanelProps {
  preferences: UserPreferences
  topics: UserTopic[]
  exclusions: ContentExclusion[]
  onUpdatePreferences: (update: PreferenceUpdate) => Promise<void>
  onAddTopic: (topic: TopicCreate) => Promise<void>
  onRemoveTopic: (topicId: string) => Promise<void>
  onAddExclusion: (exclusion: ExclusionCreate) => Promise<void>
  onRemoveExclusion: (exclusionId: string) => Promise<void>
}

export function CustomizePanel({
  preferences,
  topics,
  exclusions,
  onUpdatePreferences,
  onAddTopic,
  onRemoveTopic,
  onAddExclusion,
  onRemoveExclusion,
}: CustomizePanelProps) {
  const [activeTab, setActiveTab] = useState<"preferences" | "topics" | "exclusions">("preferences")
  const [newTopicName, setNewTopicName] = useState("")
  const [newExclusionValue, setNewExclusionValue] = useState("")

  const handlePreferenceChange = async (update: PreferenceUpdate) => {
    await onUpdatePreferences(update)
  }

  const handleAddTopic = async () => {
    if (newTopicName.trim()) {
      await onAddTopic({
        topic_name: newTopicName.trim(),
        topic_type: "custom",
        priority: 3,
      })
      setNewTopicName("")
    }
  }

  const handleAddExclusion = async () => {
    if (newExclusionValue.trim()) {
      await onAddExclusion({
        exclusion_type: "keyword",
        exclusion_value: newExclusionValue.trim(),
      })
      setNewExclusionValue("")
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Tabs */}
      <div className="border-b bg-white">
        <div className="flex gap-4 px-6 pt-6">
          <button
            onClick={() => setActiveTab("preferences")}
            className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
              activeTab === "preferences"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            <SettingsIcon className="w-4 h-4 inline mr-2" />
            Preferences
          </button>
          <button
            onClick={() => setActiveTab("topics")}
            className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
              activeTab === "topics"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            <Tag className="w-4 h-4 inline mr-2" />
            Topics ({topics.length})
          </button>
          <button
            onClick={() => setActiveTab("exclusions")}
            className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
              activeTab === "exclusions"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            <Ban className="w-4 h-4 inline mr-2" />
            Exclusions ({exclusions.length})
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Preferences Tab */}
        {activeTab === "preferences" && (
          <div className="space-y-6">
            {/* Region */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Region
              </label>
              <select
                value={preferences.region}
                onChange={(e) => handlePreferenceChange({ region: e.target.value as RegionType })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="US">United States</option>
                <option value="EU">Europe</option>
                <option value="APAC">Asia-Pacific</option>
                <option value="Global">Global</option>
              </select>
            </div>

            {/* Reading Level */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Article Depth
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(['quick', 'standard', 'in-depth'] as ReadingLevel[]).map((level) => (
                  <button
                    key={level}
                    onClick={() => handlePreferenceChange({ reading_level: level })}
                    className={`px-4 py-2 rounded-lg border-2 text-sm font-medium capitalize ${
                      preferences.reading_level === level
                        ? 'border-blue-600 bg-blue-50 text-blue-600'
                        : 'border-gray-300 text-gray-700 hover:border-gray-400'
                    }`}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </div>

            {/* Layout Density */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Layout Density
              </label>
              <div className="grid grid-cols-3 gap-2">
                {([1, 2, 3] as const).map((density) => (
                  <button
                    key={density}
                    onClick={() => handlePreferenceChange({ layout_density: density })}
                    className={`px-4 py-2 rounded-lg border-2 text-sm font-medium ${
                      preferences.layout_density === density
                        ? 'border-blue-600 bg-blue-50 text-blue-600'
                        : 'border-gray-300 text-gray-700 hover:border-gray-400'
                    }`}
                  >
                    {density} Column{density > 1 ? 's' : ''}
                  </button>
                ))}
              </div>
            </div>

            {/* Theme */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Theme
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(['light', 'dark', 'newspaper'] as ThemeType[]).map((theme) => (
                  <button
                    key={theme}
                    onClick={() => handlePreferenceChange({ theme })}
                    className={`px-4 py-2 rounded-lg border-2 text-sm font-medium capitalize ${
                      preferences.theme === theme
                        ? 'border-blue-600 bg-blue-50 text-blue-600'
                        : 'border-gray-300 text-gray-700 hover:border-gray-400'
                    }`}
                  >
                    {theme}
                  </button>
                ))}
              </div>
            </div>

            {/* Feature Toggles */}
            <div className="space-y-3">
              <label className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">
                  Show Breaking News
                </span>
                <input
                  type="checkbox"
                  checked={preferences.show_breaking_news}
                  onChange={(e) => handlePreferenceChange({ show_breaking_news: e.target.checked })}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
              </label>

              <label className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">
                  Show Market Snapshot
                </span>
                <input
                  type="checkbox"
                  checked={preferences.show_market_snapshot}
                  onChange={(e) => handlePreferenceChange({ show_market_snapshot: e.target.checked })}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
              </label>

              <label className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">
                  Enable AI Learning
                </span>
                <input
                  type="checkbox"
                  checked={preferences.enable_ai_learning}
                  onChange={(e) => handlePreferenceChange({ enable_ai_learning: e.target.checked })}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
              </label>
            </div>
          </div>
        )}

        {/* Topics Tab */}
        {activeTab === "topics" && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Select topics you're interested in to personalize your news feed.
            </p>

            {/* Add Topic */}
            <div className="flex gap-2">
              <input
                type="text"
                value={newTopicName}
                onChange={(e) => setNewTopicName(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddTopic()}
                placeholder="Add custom topic..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                onClick={handleAddTopic}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add
              </button>
            </div>

            {/* Suggested Topics */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Suggested Topics</h3>
              <div className="flex flex-wrap gap-2">
                {SUGGESTED_TOPICS.filter(
                  (st) => !topics.some((t) => t.topic_name === st.name)
                ).map((topic) => (
                  <button
                    key={topic.name}
                    onClick={() => onAddTopic({ topic_name: topic.name, topic_type: topic.type, priority: topic.priority })}
                    className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm hover:border-blue-600 hover:bg-blue-50"
                  >
                    {topic.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Current Topics */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Your Topics</h3>
              <div className="space-y-2">
                {topics.map((topic) => (
                  <div
                    key={topic.id}
                    className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg"
                  >
                    <div>
                      <span className="font-medium text-gray-900">{topic.topic_name}</span>
                      <span className="text-xs text-gray-500 ml-2 capitalize">
                        {topic.topic_type}
                      </span>
                    </div>
                    <button
                      onClick={() => onRemoveTopic(topic.id)}
                      className="p-1 hover:bg-red-100 rounded"
                    >
                      <X className="w-4 h-4 text-red-600" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Exclusions Tab */}
        {activeTab === "exclusions" && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Hide articles containing specific keywords, tickers, or sources.
            </p>

            {/* Add Exclusion */}
            <div className="flex gap-2">
              <input
                type="text"
                value={newExclusionValue}
                onChange={(e) => setNewExclusionValue(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddExclusion()}
                placeholder="Add keyword to exclude..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                onClick={handleAddExclusion}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center gap-2"
              >
                <Ban className="w-4 h-4" />
                Exclude
              </button>
            </div>

            {/* Current Exclusions */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">
                Active Exclusions
              </h3>
              {exclusions.length === 0 ? (
                <p className="text-sm text-gray-500">No exclusions set</p>
              ) : (
                <div className="space-y-2">
                  {exclusions.map((exclusion) => (
                    <div
                      key={exclusion.id}
                      className="flex items-center justify-between px-3 py-2 bg-red-50 rounded-lg"
                    >
                      <div>
                        <span className="font-medium text-gray-900">
                          {exclusion.exclusion_value}
                        </span>
                        <span className="text-xs text-gray-500 ml-2 capitalize">
                          {exclusion.exclusion_type}
                        </span>
                      </div>
                      <button
                        onClick={() => onRemoveExclusion(exclusion.id)}
                        className="p-1 hover:bg-red-200 rounded"
                      >
                        <X className="w-4 h-4 text-red-600" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
