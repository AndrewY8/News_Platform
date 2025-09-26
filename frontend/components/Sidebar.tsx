"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Search, Bookmark, Rss, User, Trash2, History, X } from "lucide-react"
import { TabId, ChatMessage, SearchQuery } from "@/types"
import { ApiService } from "@/services/api"

interface SidebarProps {
  activeTab: TabId
  onTabChange: (tab: TabId) => void
  searchQuery: string
  onSearchQueryChange: (query: string) => void
}

export function Sidebar({
  activeTab,
  onTabChange,
  searchQuery,
  onSearchQueryChange
}: SidebarProps) {
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [isChatLoading, setIsChatLoading] = useState(false)
  const [queryHistory, setQueryHistory] = useState<SearchQuery[]>([])
  const [showHistoryModal, setShowHistoryModal] = useState(false)

  // Thinking steps state
  const [thinkingSteps, setThinkingSteps] = useState<Array<{id: string, text: string, timestamp: number}>>([])
  const [showThinkingSteps, setShowThinkingSteps] = useState(false)

  const tabs = [
    { id: "top-news" as TabId, label: "Top News", icon: Rss },
    { id: "personalized" as TabId, label: "Personalized Feed", icon: User },
    { id: "saved" as TabId, label: "Saved News", icon: Bookmark },
    { id: "search" as TabId, label: "Search", icon: Search },
  ]

  // Load query history on component mount
  useEffect(() => {
    loadQueryHistory()
  }, [])

  const loadQueryHistory = async () => {
    try {
      // Load from localStorage for now, can be replaced with backend call
      const saved = localStorage.getItem('marathon-query-history')
      if (saved) {
        const history = JSON.parse(saved)
        setQueryHistory(history.slice(-20)) // Keep last 20 queries
      }
    } catch (error) {
      console.error('Failed to load query history:', error)
    }
  }

  const saveQueryToHistory = async (query: string) => {
    try {
      const newQuery: SearchQuery = {
        query,
        timestamp: new Date()
      }
      
      const updatedHistory = [newQuery, ...queryHistory.filter(q => q.query !== query)]
      const finalHistory = updatedHistory.slice(0, 20) // Keep only last 20
      
      setQueryHistory(finalHistory)
      localStorage.setItem('marathon-query-history', JSON.stringify(finalHistory))
      
      // Save to backend if endpoint exists
      try {
        await ApiService.saveQueryHistory(query)
      } catch (error) {
        console.warn('Failed to save query to backend:', error)
      }
    } catch (error) {
      console.error('Failed to save query history:', error)
    }
  }

  const deleteQueryFromHistory = (queryToDelete: string) => {
    const updatedHistory = queryHistory.filter(q => q.query !== queryToDelete)
    setQueryHistory(updatedHistory)
    localStorage.setItem('marathon-query-history', JSON.stringify(updatedHistory))
  }

  const addThinkingStep = (step: string) => {
    console.log('🎯 SIDEBAR - addThinkingStep called with:', step)
    console.log('🎯 SIDEBAR - Current showThinkingSteps:', showThinkingSteps)
    console.log('🎯 SIDEBAR - Current thinking steps count:', thinkingSteps.length)

    const newStep = {
      id: Date.now().toString(),
      text: step,
      timestamp: Date.now()
    }

    setThinkingSteps(prev => {
      const updated = [newStep, ...prev]
      console.log('🎯 SIDEBAR - Updated thinking steps:', updated.map(s => s.text))
      // Keep only the last 4 steps for the stacking effect
      return updated.slice(0, 4)
    })

    // Don't auto-remove individual steps - let the container control visibility
    // Individual step removal was causing the container to disappear prematurely
  }

  // Debug the thinking steps rendering
  useEffect(() => {
    console.log('🎭 SIDEBAR - Render state changed:', {
      showThinkingSteps,
      stepsLength: thinkingSteps.length,
      steps: thinkingSteps.map(s => s.text)
    })
  }, [showThinkingSteps, thinkingSteps])

  const handleChatSubmit = async () => {
    if (!searchQuery.trim() || isChatLoading) return

    const userMessage: ChatMessage = {
      role: 'user',
      content: searchQuery,
      timestamp: new Date()
    }

    setChatMessages(prev => [...prev, userMessage])
    setIsChatLoading(true)
    setShowThinkingSteps(true)
    setThinkingSteps([])
    console.log('🚀 SIDEBAR - State set: showThinkingSteps=true, thinkingSteps=[]')

    const query = searchQuery
    onSearchQueryChange("")

    try {
      // Save query to history
      await saveQueryToHistory(query)

      // Use streaming API for real-time thinking steps
      console.log('🚀 SIDEBAR - Calling sendChatMessageStreaming')
      await ApiService.sendChatMessageStreaming(
        query,
        // onThinkingStep
        (step: string) => {
          console.log('📨 SIDEBAR - onThinkingStep callback called with:', step)
          addThinkingStep(step)
        },
        // onResponse
        async (chatMessage: ChatMessage) => {
          // Keep thinking steps visible for a moment, then hide them
          setTimeout(() => {
            setShowThinkingSteps(false)
            // Clear the thinking steps array when hiding to reset for next query
            setThinkingSteps([])
          }, 2000)

          const assistantMessage: ChatMessage = {
            role: 'assistant',
            content: typeof chatMessage.content === 'string'
              ? chatMessage.content
              : JSON.stringify(chatMessage.content),
            timestamp: new Date(),
            suggested_articles: chatMessage.suggested_articles
          }

          setChatMessages(prev => [...prev, assistantMessage])
          setIsChatLoading(false)
        },
        // onError
        (error: string) => {
          setShowThinkingSteps(false)
          setThinkingSteps([]) // Clear thinking steps on error
          const errorMessage: ChatMessage = {
            role: 'assistant',
            content: error,
            timestamp: new Date()
          }
          setChatMessages(prev => [...prev, errorMessage])
          setIsChatLoading(false)
        }
      )
    } catch (error) {
      setShowThinkingSteps(false)
      setThinkingSteps([]) // Clear thinking steps on error
      console.error('Chat error:', error)
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      }
      setChatMessages(prev => [...prev, errorMessage])
      setIsChatLoading(false)
    }
  }

  const formatQueryTime = (timestamp: Date) => {
    const now = new Date()
    const diffMs = now.getTime() - new Date(timestamp).getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    
    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours}h ago`
    return new Date(timestamp).toLocaleDateString()
  }

  return (
    <div className="h-full flex flex-col">
      {/* Navigation tabs */}
      <div className="p-4 flex-shrink-0">
        <div className="space-y-2">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <Button
                key={tab.id}
                variant={activeTab === tab.id ? "default" : "ghost"}
                className={`w-full justify-start gap-3 h-10 text-xs ${
                  activeTab === tab.id
                    ? "bg-blue-600 text-white hover:bg-blue-700"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
                onClick={() => onTabChange(tab.id)}
              >
                <Icon className="h-3 w-3" />
                {tab.label}
              </Button>
            )
          })}
        </div>
      </div>

      {/* News Runner Chat - Expanded Section */}
      <div className="px-4 flex-1 flex flex-col">
        <div className="bg-blue-50 rounded-lg p-4 flex-1">
          <div className="mb-4 text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <div className="w-5 h-5 bg-blue-600 rounded flex items-center justify-center">
                <span className="text-white text-xs font-bold">▲</span>
              </div>
              <h3 className="text-lg font-semibold text-gray-900">News Runner</h3>
            </div>
            <span className="text-xs text-gray-500">Powered by Gemini Pro 2.5</span>
          </div>

          <div className="flex gap-2 mb-4">
            <Input
              placeholder="Ask about markets, stocks, or news..."
              className="flex-1 bg-white h-10 text-sm"
              value={searchQuery}
              onChange={(e) => onSearchQueryChange(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleChatSubmit()}
            />
            <Button 
              onClick={handleChatSubmit}
              disabled={isChatLoading || !searchQuery.trim()}
              className="h-10 px-4"
            >
              {isChatLoading ? "..." : "→"}
            </Button>
          </div>

          {/* Thinking Steps Display */}
          {showThinkingSteps && thinkingSteps.length > 0 && (
            <div className="mb-4">
              <div className="relative">
                {thinkingSteps.map((step, index) => {
                  const opacity = index === 0 ? 'opacity-100' :
                                index === 1 ? 'opacity-70' :
                                index === 2 ? 'opacity-40' : 'opacity-20'

                  const scale = index === 0 ? 'scale-100' :
                               index === 1 ? 'scale-95' :
                               index === 2 ? 'scale-90' : 'scale-85'

                  return (
                    <div
                      key={step.id}
                      className={`absolute inset-0 bg-white/90 backdrop-blur-sm border border-blue-200 rounded-lg shadow-sm px-3 py-2 w-full transition-all duration-500 ${opacity} ${scale}`}
                      style={{
                        transform: `translateY(${index * -6}px) ${scale}`,
                        zIndex: 40 - index
                      }}
                    >
                      <div className="flex items-center gap-2">
                        {index === 0 && (
                          <div className="animate-spin rounded-full h-2 w-2 border border-blue-500 border-t-transparent"></div>
                        )}
                        <span className="text-xs text-gray-600 line-clamp-2">{step.text}</span>
                      </div>
                    </div>
                  )
                })}
                {/* Spacer to maintain height */}
                <div className="invisible bg-white/90 backdrop-blur-sm border border-blue-200 rounded-lg shadow-sm px-3 py-2 w-full">
                  <div className="flex items-center gap-2">
                    <div className="rounded-full h-2 w-2"></div>
                    <span className="text-xs">Placeholder</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Chat Messages */}
          <div className="space-y-3 mb-4 flex-1 overflow-y-auto">
            {chatMessages.slice(-5).map((msg, index) => (
              <div key={index} className="text-left">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-gray-700 text-xs">
                    {msg.role === 'user' ? 'You' : 'AI'}:
                  </span>
                  <span className="text-gray-400 text-xs">
                    {formatQueryTime(msg.timestamp)}
                  </span>
                </div>
                <div className="bg-white rounded p-2 text-xs text-gray-600 leading-relaxed">
                  {msg.content}
                </div>
              </div>
            ))}
          </div>

          {/* Query History Section */}
          <div className="border-t border-blue-200 pt-3">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-gray-700 text-xs">Recent Queries</h4>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs text-blue-600 hover:text-blue-700"
                onClick={() => setShowHistoryModal(true)}
              >
                <History className="w-3 h-3 mr-1" />
                View All
              </Button>
            </div>
            
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {queryHistory.slice(0, 3).map((query, index) => (
                <div key={index} className="group flex items-center justify-between">
                  <button
                    onClick={() => onSearchQueryChange(query.query)}
                    className="text-left text-xs text-gray-600 hover:text-gray-900 flex-1 truncate"
                    title={query.query}
                  >
                    {query.query}
                  </button>
                  <button
                    onClick={() => deleteQueryFromHistory(query.query)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-100 rounded"
                    title="Delete query"
                  >
                    <Trash2 className="w-3 h-3 text-red-500" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 flex-shrink-0">
        <div className="space-y-1">
          <Button variant="ghost" className="w-full justify-start text-gray-600 hover:text-gray-900 h-7 text-xs">
            About
          </Button>
          <Button variant="ghost" className="w-full justify-start text-gray-600 hover:text-gray-900 h-7 text-xs">
            Subscription Plan
          </Button>
          <Button variant="ghost" className="w-full justify-start text-gray-600 hover:text-gray-900 h-7 text-xs">
            Account Information
          </Button>
        </div>
      </div>

      {/* Query History Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96 max-h-96 overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Query History</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowHistoryModal(false)}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-2">
              {queryHistory.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No queries yet</p>
              ) : (
                queryHistory.map((query, index) => (
                  <div key={index} className="group flex items-center justify-between p-2 hover:bg-gray-50 rounded">
                    <button
                      onClick={() => {
                        onSearchQueryChange(query.query)
                        setShowHistoryModal(false)
                      }}
                      className="text-left text-sm text-gray-700 hover:text-blue-600 flex-1 truncate"
                      title={query.query}
                    >
                      {query.query}
                    </button>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">
                        {formatQueryTime(query.timestamp)}
                      </span>
                      <button
                        onClick={() => deleteQueryFromHistory(query.query)}
                        className="p-1 hover:bg-red-100 rounded"
                        title="Delete query"
                      >
                        <Trash2 className="w-3 h-3 text-red-500" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
            
            <div className="border-t pt-4 mt-4">
              <Button
                variant="outline"
                onClick={() => {
                  setQueryHistory([])
                  localStorage.removeItem('marathon-query-history')
                }}
                className="w-full"
              >
                Clear All History
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
