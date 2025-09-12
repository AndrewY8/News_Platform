"use client"

import React, { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Search, FileText, X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, ExternalLink, User, Building, Rss, Bookmark, ChevronDown, MessageCircle, Send, BarChart3, ArrowLeft } from "lucide-react"
import { ApiService, SecDocument } from "@/services/api"
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from "@/components/ui/resizable"

export default function SecDocsPage() {
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState("")
  const [loading, setLoading] = useState(false)
  const [searchResults, setSearchResults] = useState<SecDocument[]>([])
  const [selectedDocument, setSelectedDocument] = useState<SecDocument | null>(null)
  const [documentContent, setDocumentContent] = useState<string>("")
  const [chatResponse, setChatResponse] = useState<string>("")
  const [isChatLoading, setIsChatLoading] = useState(false)
  const [showChatResponse, setShowChatResponse] = useState(false)
  const [secSearchResponse, setSecSearchResponse] = useState<string>("")
  const [isSecSearchLoading, setIsSecSearchLoading] = useState(false)
  const [showSecSearchResponse, setShowSecSearchResponse] = useState(false)
  const [documentZoom, setDocumentZoom] = useState(100)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [documentPages, setDocumentPages] = useState<string[]>([])
  const [isHtmlContent, setIsHtmlContent] = useState(false)
  const [viewerDimensions, setViewerDimensions] = useState({ width: 0, height: 0 })
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  
  // Chat functionality
  const [chatInput, setChatInput] = useState("")
  const [showExpandedResponse, setShowExpandedResponse] = useState(false)
  const [showMobileSidebar, setShowMobileSidebar] = useState(false)
  const [isDocumentFocusMode, setIsDocumentFocusMode] = useState(false)

  // Navigation tabs
  const tabs = [
    { id: "personalized", label: "Personalized feed", icon: User, href: "/personalized-news" },
    { id: "business-news", label: "Business News", icon: Building, href: "#", hasDropdown: true },
    { id: "portfolio", label: "Portfolio", icon: Rss, href: "/portfolio" },
    { id: "saved", label: "Saved News", icon: Bookmark, href: "/saved-news" },
    { id: "sec-docs", label: "SEC Doc Searcher", icon: Search, href: "/sec-docs" },
  ]


  const handleSearch = async (query: string) => {
    if (!query.trim()) return
    
    setLoading(true)
    setIsSecSearchLoading(true)
    setShowSecSearchResponse(true)
    setSecSearchResponse("Searching SEC documents...")
    
    try {
      // Search using real SEC API - get more documents to include 10-K reports
      const documents = await ApiService.searchSecDocuments(query, 50)
      
      setSearchResults(documents)
      
      // Generate AI response about the search with document type counts
      let responseText = `Found ${documents.length} SEC document${documents.length !== 1 ? 's' : ''} matching "${query}".`
      
      if (documents.length > 0) {
        // Group documents by type for summary
        const typeCounts: Record<string, number> = {}
        documents.forEach(doc => {
          typeCounts[doc.documentType] = (typeCounts[doc.documentType] || 0) + 1
        })
        
        const countSummary = Object.entries(typeCounts)
          .map(([type, count]) => `${count} ${type}${count !== 1 ? 's' : ''}`)
          .join(', ')
        
        responseText += ` Including: ${countSummary}. Click on any category below to expand and view individual documents.`
      } else {
        responseText += ' Try searching for company names like Apple, Tesla, or Microsoft, or document types like 10-K, 8-K, 10-Q.'
      }
      
      setSecSearchResponse(responseText)
      
    } catch (error) {
      console.error('Search error:', error)
      setSecSearchResponse("Error searching SEC documents. Please try again.")
      setSearchResults([])
    } finally {
      setLoading(false)
      setIsSecSearchLoading(false)
    }
  }

  const handleDocumentSelect = async (document: SecDocument) => {
    setSelectedDocument(document)
    setDocumentContent("Loading document content...")
    setCurrentPage(1)
    setDocumentPages([])
    setIsHtmlContent(false)
    setIsDocumentFocusMode(true)
    
    try {
      // Fetch full document content with highlighting
      const fullDocument = await ApiService.getSecDocument(document.id, searchQuery)
      if (fullDocument && (fullDocument.html_content || fullDocument.content)) {
        // Prefer HTML content over plain text
        const content = fullDocument.html_content || fullDocument.content || ""
        setDocumentContent(content)
        
        if (fullDocument.html_content) {
          // HTML content - split into pages (will be recalculated when dimensions are available)
          setIsHtmlContent(true)
          const pages = splitHtmlIntoPages(fullDocument.html_content)
          setDocumentPages(pages)
          setTotalPages(pages.length)
          setCurrentPage(1)
        } else {
          // Plain text content - use viewport-based pagination
          setIsHtmlContent(false)
          setDocumentPages([])
          const lines = content.split('\n')
          // Calculate lines per page based on viewport height and zoom
          const linesPerPage = calculateLinesPerPage()
          setTotalPages(Math.ceil(lines.length / linesPerPage))
          setCurrentPage(1)
        }
        
        // Update the selected document with the full content
        setSelectedDocument(prev => prev ? { 
          ...prev, 
          content: fullDocument.content,
          html_content: fullDocument.html_content,
          highlights: fullDocument.highlights 
        } : null)
      } else {
        setDocumentContent("Failed to load document content. Please try again.")
        setTotalPages(1)
      }
    } catch (error) {
      console.error('Error loading document:', error)
      setDocumentContent("Error loading document content. Please try again.")
      setTotalPages(1)
    }
  }

  const handleZoomIn = () => {
    setDocumentZoom(prev => {
      const newZoom = Math.min(prev + 25, 200)
      // Recalculate pages when zoom changes
      setTimeout(() => recalculatePages(newZoom), 100)
      return newZoom
    })
  }

  const handleZoomOut = () => {
    setDocumentZoom(prev => {
      const newZoom = Math.max(prev - 25, 50)
      // Recalculate pages when zoom changes
      setTimeout(() => recalculatePages(newZoom), 100)
      return newZoom
    })
  }

  // Calculate lines per page based on viewport height and zoom
  const calculateLinesPerPage = (): number => {
    if (viewerDimensions.height <= 0) return 66 // Default fallback
    
    // Base line height for plain text (monospace font)
    const baseLineHeight = 16 * (documentZoom / 100)
    // Available height minus padding and buffer
    const availableHeight = viewerDimensions.height - 100
    // Calculate how many lines fit
    const linesPerPage = Math.max(10, Math.floor(availableHeight / baseLineHeight))
    
    return linesPerPage
  }

  // Recalculate pages when dimensions or zoom change
  const recalculatePages = (zoom: number = documentZoom) => {
    if (!documentContent) return
    
    if (isHtmlContent && selectedDocument?.html_content) {
      const pages = splitHtmlIntoPages(selectedDocument.html_content)
      setDocumentPages(pages)
      setTotalPages(pages.length)
      // Keep current page within bounds
      setCurrentPage(prev => Math.min(prev, pages.length))
    } else if (!isHtmlContent) {
      const lines = documentContent.split('\n')
      // Use viewport-based line count
      const linesPerPage = calculateLinesPerPage()
      const newTotalPages = Math.ceil(lines.length / linesPerPage)
      setTotalPages(newTotalPages)
      // Keep current page within bounds
      setCurrentPage(prev => Math.min(prev, newTotalPages))
    }
  }

  // Effect to handle viewer dimension changes and recalculate pagination
  React.useEffect(() => {
    const handleResize = () => {
      // Get viewer element dimensions
      const viewerElement = document.querySelector('.document-content-viewer')
      if (viewerElement) {
        const rect = viewerElement.getBoundingClientRect()
        setViewerDimensions({ width: rect.width, height: rect.height })
      }
    }
    
    // Initial calculation
    handleResize()
    
    // Add resize listener
    window.addEventListener('resize', handleResize)
    
    // Also listen for panel resize events (from resizable panels)
    const observer = new ResizeObserver(handleResize)
    const viewerElement = document.querySelector('.document-content-viewer')
    if (viewerElement) {
      observer.observe(viewerElement)
    }
    
    return () => {
      window.removeEventListener('resize', handleResize)
      observer.disconnect()
    }
  }, [])

  // Effect to recalculate pages when dimensions change
  React.useEffect(() => {
    if (viewerDimensions.height > 0) {
      recalculatePages()
    }
  }, [viewerDimensions, documentZoom])

  const handlePreviousPage = () => {
    setCurrentPage(prev => Math.max(prev - 1, 1))
  }

  const handleNextPage = () => {
    setCurrentPage(prev => Math.min(prev + 1, totalPages))
  }

  // Split HTML content into pages - improved to match actual SEC document structure and viewport
  const splitHtmlIntoPages = (htmlContent: string) => {
    if (!htmlContent) return []
    
    // Clean the HTML content first
    const cleanedContent = htmlContent.trim()
    if (!cleanedContent) return []
    
    // For SEC documents, look for natural page breaks first
    // Many SEC docs have page break markers or specific patterns
    const pageBreakPatterns = [
      /<hr[^>]*>/gi,
      /<div[^>]*page-break[^>]*>/gi,
      /<p[^>]*style="[^"]*page-break[^"]*"[^>]*>/gi
    ]
    
    let contentToSplit = cleanedContent
    let hasNaturalBreaks = false
    
    // Check for natural page breaks
    for (const pattern of pageBreakPatterns) {
      if (pattern.test(contentToSplit)) {
        hasNaturalBreaks = true
        break
      }
    }
    
    // If we have natural breaks, use them but still respect viewport height
    if (hasNaturalBreaks) {
      const pages = contentToSplit.split(/<hr[^>]*>|<div[^>]*page-break[^>]*>|<p[^>]*style="[^"]*page-break[^"]*"[^>]*>/gi)
        .filter(page => page.trim().length > 0)
      
      // Check if natural pages fit in viewport, if not, split further
      if (viewerDimensions.height > 0) {
        const refinedPages: string[] = []
        for (const page of pages) {
          const subPages = splitPageByViewportHeight(page)
          refinedPages.push(...subPages)
        }
        return refinedPages.length > 0 ? refinedPages : [cleanedContent]
      }
      
      return pages.length > 0 ? pages : [contentToSplit]
    }
    
    // Otherwise, use viewport-based pagination
    return splitPageByViewportHeight(cleanedContent)
  }
  
  // Split content based on actual viewport height
  const splitPageByViewportHeight = (htmlContent: string): string[] => {
    if (!htmlContent || viewerDimensions.height <= 0) return [htmlContent]
    
    const parser = new DOMParser()
    const doc = parser.parseFromString(`<div>${htmlContent}</div>`, 'text/html')
    const container = doc.querySelector('div')
    if (!container) return [htmlContent]
    
    const pages: string[] = []
    let currentPageContent = ''
    let currentPageHeight = 0
    
    // Calculate available height: viewport height minus padding and margins
    // Account for document container padding (24px top+bottom) and some buffer
    const availableHeight = viewerDimensions.height - 100 // 48px padding + 52px buffer
    const maxPageHeight = Math.max(200, Math.floor(availableHeight * (documentZoom / 100))) // Min 200px
    
    const elements = Array.from(container.children)
    
    for (const element of elements) {
      const elementHeight = estimateElementHeight(element as HTMLElement, documentZoom)
      
      // Don't create pages with just whitespace
      const elementContent = element.textContent?.trim() || ''
      if (!elementContent) continue
      
      // If adding this element would exceed page height and we have content, start new page
      if (currentPageHeight + elementHeight > maxPageHeight && currentPageContent.trim()) {
        pages.push(currentPageContent.trim())
        currentPageContent = ''
        currentPageHeight = 0
      }
      
      currentPageContent += element.outerHTML + '\n'
      currentPageHeight += elementHeight
    }
    
    // Add the last page if there's meaningful content
    if (currentPageContent.trim()) {
      pages.push(currentPageContent.trim())
    }
    
    // Filter out empty pages and ensure minimum content per page
    const filteredPages = pages.filter(page => {
      const tempDiv = document.createElement('div')
      tempDiv.innerHTML = page
      const textLength = tempDiv.textContent?.trim().length || 0
      // Require at least 50 characters or significant HTML content
      return textLength > 50 || page.includes('<table') || page.includes('<hr')
    })
    
    return filteredPages.length > 0 ? filteredPages : [htmlContent]
  }
  
  // Estimate element height more accurately for SEC documents
  const estimateElementHeight = (element: HTMLElement, zoom: number = 100): number => {
    const tagName = element.tagName.toLowerCase()
    const textContent = element.textContent || ''
    const zoomFactor = zoom / 100
    
    // Base line height for SEC documents (typically 12pt = ~16px)
    const baseLineHeight = 16
    let baseHeight: number
    
    switch (tagName) {
      case 'table':
        const rows = element.querySelectorAll('tr').length
        const avgCellHeight = 20 // Average cell height in SEC tables
        baseHeight = Math.max(60, rows * avgCellHeight)
        break
      case 'div':
        // For divs, estimate based on content and line breaks
        const lineBreaks = (textContent.match(/\n/g) || []).length
        const divLines = Math.max(1, Math.ceil(textContent.length / 80) + lineBreaks)
        baseHeight = divLines * baseLineHeight
        break
      case 'p':
        // Paragraphs in SEC docs are typically single-spaced
        const paragraphLines = Math.max(1, Math.ceil(textContent.length / 80))
        baseHeight = paragraphLines * baseLineHeight + 8 // Add small margin
        break
      case 'h1': baseHeight = baseLineHeight * 2; break
      case 'h2': baseHeight = baseLineHeight * 1.8; break
      case 'h3': baseHeight = baseLineHeight * 1.6; break
      case 'h4': baseHeight = baseLineHeight * 1.4; break
      case 'h5': baseHeight = baseLineHeight * 1.2; break
      case 'h6': baseHeight = baseLineHeight * 1.1; break
      case 'hr': 
        baseHeight = 24 // HR tags often indicate page breaks
        break
      case 'ul':
      case 'ol':
        const listItems = element.querySelectorAll('li').length
        baseHeight = Math.max(32, listItems * baseLineHeight + 16)
        break
      case 'pre':
        const preLines = (textContent.match(/\n/g) || []).length + 1
        baseHeight = preLines * 14 // Monospace is typically smaller
        break
      default:
        // For other elements, estimate based on text length
        const defaultLines = Math.max(1, Math.ceil(textContent.length / 100))
        baseHeight = defaultLines * baseLineHeight
    }
    
    return Math.ceil(baseHeight * zoomFactor)
  }

  // Get content for current page
  const getCurrentPageContent = () => {
    if (!documentContent) return ""
    
    if (isHtmlContent && documentPages.length > 0) {
      const pageContent = documentPages[currentPage - 1] || ""
      // Ensure the page content is not empty
      return pageContent.trim() || (documentPages.length === 1 ? documentContent : "")
    }
    
    // For plain text, use viewport-based pagination
    const lines = documentContent.split('\n')
    const linesPerPage = calculateLinesPerPage()
    const startLine = (currentPage - 1) * linesPerPage
    const endLine = startLine + linesPerPage
    const pageLines = lines.slice(startLine, endLine)
    
    return pageLines.join('\n')
  }

  // Group documents by type with deduplication
  const groupedDocuments = React.useMemo(() => {
    // First, deduplicate by ID to prevent any backend duplicate issues
    const uniqueDocuments: Record<string, SecDocument> = {}
    searchResults.forEach(doc => {
      if (!uniqueDocuments[doc.id]) {
        uniqueDocuments[doc.id] = doc
      }
    })
    
    const deduplicatedDocs = Object.values(uniqueDocuments)
    console.log(`Deduplication: ${searchResults.length} -> ${deduplicatedDocs.length} documents`)
    
    const groups: Record<string, SecDocument[]> = {}
    deduplicatedDocs.forEach(doc => {
      if (!groups[doc.documentType]) {
        groups[doc.documentType] = []
      }
      groups[doc.documentType].push(doc)
    })
    
    // Sort each group by filing date (newest first)
    Object.keys(groups).forEach(type => {
      groups[type].sort((a, b) => new Date(b.filingDate).getTime() - new Date(a.filingDate).getTime())
    })
    
    // Log group sizes for debugging
    Object.keys(groups).forEach(type => {
      console.log(`${type}: ${groups[type].length} documents`)
    })
    
    return groups
  }, [searchResults])

  // Define document type order and descriptions
  const documentTypeInfo = {
    "10-K": { name: "Annual Reports (10-K)", description: "Comprehensive annual business reports" },
    "10-Q": { name: "Quarterly Reports (10-Q)", description: "Quarterly financial reports" },
    "8-K": { name: "Current Reports (8-K)", description: "Reports of significant events" },
    "DEF 14A": { name: "Proxy Statements", description: "Shareholder meeting information" }
  }

  const orderedDocumentTypes = ["10-K", "10-Q", "8-K", "DEF 14A"]

  // Toggle category expansion
  const toggleCategory = (docType: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev)
      if (newSet.has(docType)) {
        newSet.delete(docType)
      } else {
        newSet.add(docType)
      }
      return newSet
    })
  }

  // Return to document searcher view
  const handleBackToSearch = () => {
    setIsDocumentFocusMode(false)
    setSelectedDocument(null)
    setDocumentContent("")
    setChatResponse("")
    setShowChatResponse(false)
  }

  // Chat functionality
  const handleChatSubmit = async () => {
    if (!chatInput.trim() || isChatLoading) return

    const query = chatInput
    setChatInput("")
    
    setIsChatLoading(true)
    setShowChatResponse(true)
    setChatResponse("Analyzing SEC documents...")

    try {
      const chatMessage = await ApiService.sendChatMessage(query)
      
      const responseContent = typeof chatMessage.content === 'string' 
        ? chatMessage.content 
        : JSON.stringify(chatMessage.content)
      setChatResponse(responseContent)
      
    } catch (error) {
      console.error('Chat error:', error)
      setChatResponse("I apologize, but I'm experiencing technical difficulties. Please try again.")
    } finally {
      setIsChatLoading(false)
    }
  }


  return (
    <div className="min-h-screen bg-white font-sans">
      {/* Haven News Header */}
      <div className="bg-white border-b border-gray-200 pt-2 sm:pt-3 lg:pt-4 fixed top-0 left-0 right-0 z-10">
        <div className="flex flex-col gap-2 sm:gap-3 lg:gap-4">
          <div className="flex items-center justify-between px-48">
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-black" style={{letterSpacing: '0.1em'}}>Haven News</h1>
            <Button
              variant="ghost"
              size="sm"
              className="lg:hidden p-2"
              onClick={() => setShowMobileSidebar(true)}
            >
              <BarChart3 className="h-5 w-5" />
            </Button>
          </div>
          
          {/* Horizontal Navigation */}
          <div className="bg-gray-100 border-t border-b border-gray py-1">
            <div className="flex gap-2 sm:gap-4 lg:gap-8 overflow-x-auto px-48">
              {tabs.map((tab) => {
                if (tab.id === 'business-news') {
                  return (
                    <div 
                      key={tab.id} 
                      className="relative group"
                    >
                      <Button
                        variant="ghost"
                        className="flex items-center gap-2 sm:gap-3 px-3 sm:px-4 lg:px-6 py-1 sm:py-2 text-xs sm:text-sm tracking-wide whitespace-nowrap text-gray-500 hover:bg-gray-200"
                      >
                        {tab.label}
                        <ChevronDown className="h-3 w-3" />
                      </Button>
                      
                      {/* Business Industries Dropdown */}
                      <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-50 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
                        <div className="py-2">
                          {[
                            'Technology',
                            'Healthcare',
                            'Financial Services',
                            'Energy',
                            'Manufacturing',
                            'Real Estate',
                            'Retail',
                            'Automotive',
                            'Aerospace',
                            'Telecommunications'
                          ].map((industry) => (
                            <button
                              key={industry}
                              className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-black"
                            >
                              {industry}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  )
                }
                
                return (
                  <Button
                    key={tab.id}
                    variant="ghost"
                    className={`flex items-center gap-2 sm:gap-3 px-3 sm:px-4 lg:px-6 py-1 sm:py-2 text-xs sm:text-sm tracking-wide whitespace-nowrap hover:bg-gray-200 ${
                      tab.id === 'sec-docs' ? 'text-black bg-gray-200' : 'text-gray-500'
                    }`}
                    onClick={() => router.push(tab.href)}
                  >
                    {tab.label}
                  </Button>
                )
              })}
            </div>
          </div>
        </div>

        {/* Scrolling Banner Section */}
        <div className="bg-gray-900 text-white py-2 overflow-hidden">
          <div className="flex animate-marquee whitespace-nowrap">
            <span className="mx-8 text-sm font-medium">📈 AAPL up 2.3% after strong earnings report</span>
            <span className="mx-8 text-sm font-medium">🔥 TSLA announces new Gigafactory in Texas</span>
            <span className="mx-8 text-sm font-medium">💰 Bitcoin reaches new monthly high at $67,000</span>
            <span className="mx-8 text-sm font-medium">📊 S&P 500 closes at record levels for third consecutive day</span>
            <span className="mx-8 text-sm font-medium">⚡ NVDA partners with major automakers for AI development</span>
            <span className="mx-8 text-sm font-medium">🏦 Federal Reserve hints at potential rate cuts in Q4</span>
            <span className="mx-8 text-sm font-medium">🚀 Google unveils new AI breakthrough in quantum computing</span>
            <span className="mx-8 text-sm font-medium">💎 Microsoft Azure revenue grows 35% year-over-year</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="px-48 h-screen pt-[80px] sm:pt-[100px] lg:pt-[160px] overflow-hidden">
        {/* Document Focus Mode - Chat Only */}
        {isDocumentFocusMode && selectedDocument ? (
          <ResizablePanelGroup direction="horizontal" className="h-full w-full">
            {/* Back Button and Chat Interface */}
            <ResizablePanel defaultSize={25} minSize={20} maxSize={40}>
              <div className="border-r border-gray-200 flex flex-col bg-gray-50 h-full">
              {/* Back Button */}
              <div className="p-4 border-b border-gray-200 bg-white">
                <Button
                  variant="outline"
                  onClick={handleBackToSearch}
                  className="flex items-center gap-2 w-full justify-start"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back to Document Search
                </Button>
              </div>
              
              {/* Document Info */}
              <div className="p-4 border-b border-gray-200 bg-white">
                <h3 className="text-sm font-semibold text-gray-900 mb-1">{selectedDocument.title}</h3>
                <p className="text-xs text-gray-600">{selectedDocument.company} ({selectedDocument.ticker})</p>
                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800 mt-2">
                  {selectedDocument.documentType}
                </span>
              </div>
              
              {/* Chat Interface */}
              <div className="flex-1 flex flex-col">
                <div className="p-4 border-b border-gray-200 bg-white">
                  <h3 className="text-sm font-semibold text-gray-900 mb-2">Search Document</h3>
                  <p className="text-xs text-gray-600">Ask questions about this SEC document</p>
                </div>
                
                {/* Chat Messages Area */}
                <div className="flex-1 p-4 overflow-y-auto">
                  {showChatResponse && chatResponse && (
                    <div className="chat-message mb-4">
                      <div className="bg-white rounded-lg p-3 shadow-sm border border-gray-200">
                        <div className="flex items-start gap-2">
                          <div className="flex-shrink-0 w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center">
                            <MessageCircle className="h-3 w-3 text-white" />
                          </div>
                          <div className="flex-1 text-sm text-gray-700">
                            {isChatLoading ? (
                              <div className="flex items-center gap-2">
                                <div className="animate-spin rounded-full h-3 w-3 border-2 border-blue-600 border-t-transparent" />
                                Analyzing document...
                              </div>
                            ) : (
                              chatResponse
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Chat Input */}
                <div className="p-4 bg-white border-t border-gray-200">
                  <div className="flex gap-2">
                    <textarea
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder="Ask about this SEC document..."
                      className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      rows={3}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault()
                          handleChatSubmit()
                        }
                      }}
                    />
                    <Button
                      onClick={handleChatSubmit}
                      disabled={!chatInput.trim() || isChatLoading}
                      size="sm"
                      className="px-3 self-end"
                    >
                      <Send className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </div>
              </div>
            </ResizablePanel>
            
            <ResizableHandle withHandle />
            
            {/* Document Viewer - Full Width */}
            <ResizablePanel defaultSize={75}>
              <div className="flex flex-col bg-white h-full">
              {/* Document Header */}
              <div className="p-4 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h2 className="font-semibold text-gray-900">{selectedDocument.title}</h2>
                    <p className="text-sm text-gray-600">{selectedDocument.company} ({selectedDocument.ticker})</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => window.open(selectedDocument.url, '_blank')}
                      className="flex items-center gap-2"
                    >
                      <ExternalLink className="h-3 w-3" />
                      View Original
                    </Button>
                  </div>
                </div>
                
                {/* Document Controls */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handlePreviousPage}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="h-3 w-3" />
                    </Button>
                    <span className="text-sm text-gray-600">
                      Page {currentPage} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleNextPage}
                      disabled={currentPage === totalPages}
                    >
                      <ChevronRight className="h-3 w-3" />
                    </Button>
                    {isHtmlContent && (
                      <span className="text-xs text-gray-500 ml-4">
                        Formatted Document
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleZoomOut}
                      disabled={documentZoom <= 50}
                    >
                      <ZoomOut className="h-3 w-3" />
                    </Button>
                    <span className="text-sm text-gray-600 min-w-12 text-center">
                      {documentZoom}%
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleZoomIn}
                      disabled={documentZoom >= 200}
                    >
                      <ZoomIn className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </div>

              {/* Document Content */}
              <div className="flex-1 bg-white border-t border-gray-200 h-full overflow-hidden document-content-viewer">
                <div className="w-full h-full overflow-auto bg-gray-50 p-4">
                  <div 
                    className="bg-white shadow-sm border border-gray-200 p-6 min-h-full w-full"
                    style={{ 
                      fontSize: `${Math.max(10, documentZoom * 0.12)}px`,
                      lineHeight: 1.4
                    }}
                  >
                    {isHtmlContent ? (
                      <div 
                        dangerouslySetInnerHTML={{ __html: getCurrentPageContent() }} 
                        className="sec-document-html w-full"
                        style={{
                          fontSize: 'inherit',
                          lineHeight: 'inherit'
                        }}
                      />
                    ) : (
                      <pre 
                        className="whitespace-pre-wrap text-gray-800 font-mono leading-relaxed w-full"
                        style={{ 
                          fontSize: 'inherit',
                          lineHeight: 'inherit',
                          fontFamily: 'Courier New, monospace'
                        }}
                      >
                        {getCurrentPageContent()}
                      </pre>
                    )}
                  </div>
                </div>
              </div>
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        ) : (
          /* Normal Search Mode */
          <ResizablePanelGroup direction="horizontal" className="h-full w-full">
            {/* Left Side - Search/Chat Area */}
            <ResizablePanel defaultSize={selectedDocument ? 35 : 50} minSize={30} maxSize={70}>
              <div className="border-r border-gray-200 flex flex-col h-full">
          {/* Search Bar */}
          <div className="p-6 border-b border-gray-200 bg-gray-50">
            <div className="max-w-2xl">
              <h2 className="text-lg font-semibold mb-4">Search SEC Filings</h2>
              <div className="flex gap-2">
                <Input
                  placeholder="Search company names, tickers, or document types..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch(searchQuery)}
                  className="flex-1"
                />
                <Button 
                  onClick={() => handleSearch(searchQuery)}
                  disabled={!searchQuery.trim() || loading}
                  className="flex items-center gap-2"
                >
                  {loading ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                  Search
                </Button>
              </div>
            </div>
          </div>

          {/* AI Response */}
          {showSecSearchResponse && (
            <div className="p-6 border-b border-gray-200 bg-blue-50">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                  <Search className="h-4 w-4 text-white" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900 mb-1">Search Results</h3>
                  <p className="text-sm text-gray-700">
                    {isSecSearchLoading ? (
                      <div className="flex items-center gap-2">
                        <div className="animate-spin rounded-full h-3 w-3 border-2 border-blue-600 border-t-transparent" />
                        Analyzing documents...
                      </div>
                    ) : (
                      secSearchResponse
                    )}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowSecSearchResponse(false)}
                  className="h-6 w-6 p-0"
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            </div>
          )}

          {/* Search Results */}
          <div className={`${selectedDocument ? 'flex-shrink-0 max-h-60' : 'flex-1'} scrollable-content`}>
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-2 text-gray-600">Searching documents...</span>
              </div>
            ) : searchResults.length === 0 ? (
              <div className="text-center py-12 px-6">
                <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {searchQuery ? "No documents found" : "Enter a search query"}
                </h3>
                <p className="text-gray-600 mb-6">
                  {searchQuery 
                    ? "Try searching for company names like Apple, Tesla, or Microsoft" 
                    : "Search for SEC filings by company name, ticker symbol, or document type"
                  }
                </p>
                <div className="text-left max-w-md mx-auto bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-medium mb-2">Example searches:</h4>
                  <ul className="text-sm text-gray-600 space-y-1">
                    <li>• Apple (company name)</li>
                    <li>• TSLA (ticker symbol)</li> 
                    <li>• 10-K (document type)</li>
                    <li>• Microsoft earnings</li>
                  </ul>
                </div>
              </div>
            ) : (
              <div className="p-6">
                <h3 className="font-semibold text-gray-900 mb-2">
                  Found {searchResults.length} document{searchResults.length !== 1 ? 's' : ''} across {Object.keys(groupedDocuments).length} document type{Object.keys(groupedDocuments).length !== 1 ? 's' : ''}
                </h3>
                <p className="text-sm text-gray-600 mb-6">
                  Click on any category below to expand and view individual documents
                </p>
                
                {/* Display documents grouped by type with collapsible sections */}
                <div className="space-y-3">
                  {orderedDocumentTypes.map(docType => {
                    const documents = groupedDocuments[docType]
                    if (!documents || documents.length === 0) return null
                    
                    const typeInfo = documentTypeInfo[docType as keyof typeof documentTypeInfo]
                    const isExpanded = expandedCategories.has(docType)
                    
                    return (
                      <div key={docType} className="border rounded-lg bg-white shadow-sm">
                        {/* Category Header - Clickable to expand/collapse */}
                        <div 
                          className="category-header flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                          onClick={() => toggleCategory(docType)}
                        >
                          <div className="flex items-center gap-3">
                            <div className="flex items-center justify-center w-8 h-8 bg-blue-100 rounded-full">
                              <FileText className="h-4 w-4 text-blue-600" />
                            </div>
                            <div>
                              <h4 className="font-medium text-gray-900">{typeInfo.name}</h4>
                              <p className="text-sm text-gray-500">{documents.length} document{documents.length !== 1 ? 's' : ''} available</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                              {documents.length}
                            </span>
                            <ChevronDown 
                              className={`h-5 w-5 text-gray-400 transition-transform ${isExpanded ? 'transform rotate-180' : ''}`} 
                            />
                          </div>
                        </div>
                        
                        {/* Expandable Document List */}
                        {isExpanded && (
                          <div className="category-expanded-content border-t bg-gray-50 p-4">
                            <div className="space-y-3">
                              {documents.map((document) => (
                                <div
                                  key={document.id}
                                  className={`document-item border rounded-lg p-3 cursor-pointer hover:bg-white transition-colors bg-white ${
                                    selectedDocument?.id === document.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                                  }`}
                                  onClick={() => handleDocumentSelect(document)}
                                >
                                  <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                      <div className="flex items-center gap-2 mb-2">
                                        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                          {document.documentType}
                                        </span>
                                        <span className="text-sm text-gray-500">{document.ticker}</span>
                                        <span className="text-xs text-gray-400">Filed: {document.filingDate}</span>
                                      </div>
                                      <h5 className="font-medium text-gray-900 mb-1">{document.title}</h5>
                                      <p className="text-sm text-gray-600">{document.company}</p>
                                      
                                      {document.highlights && document.highlights.length > 0 && (
                                        <div className="mt-2">
                                          <p className="text-xs font-medium text-gray-700 mb-1">Relevant sections:</p>
                                          <div className="space-y-1">
                                            {document.highlights.slice(0, 1).map((highlight, index) => (
                                              <div key={index} className="text-xs text-gray-600 bg-yellow-50 p-1 rounded border-l-2 border-yellow-200">
                                                {highlight.text.substring(0, 100)}...
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                    <div className="flex-shrink-0 ml-4">
                                      <ExternalLink className="h-4 w-4 text-gray-400" />
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Expanded Chat Interface - Only show when document is selected */}
          {selectedDocument && (
            <div className="flex-1 flex flex-col border-t border-gray-200 bg-gray-50">
              <div className="p-4 border-b border-gray-200 bg-white">
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Search Document</h3>
                <p className="text-xs text-gray-600">Ask questions about the selected SEC document</p>
              </div>
              
              {/* Chat Messages Area */}
              <div className="flex-1 p-4 overflow-y-auto">
                {showChatResponse && chatResponse && (
                  <div className="chat-message mb-4">
                    <div className="bg-white rounded-lg p-3 shadow-sm border border-gray-200">
                      <div className="flex items-start gap-2">
                        <div className="flex-shrink-0 w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center">
                          <MessageCircle className="h-3 w-3 text-white" />
                        </div>
                        <div className="flex-1 text-sm text-gray-700">
                          {isChatLoading ? (
                            <div className="flex items-center gap-2">
                              <div className="animate-spin rounded-full h-3 w-3 border-2 border-blue-600 border-t-transparent" />
                              Analyzing document...
                            </div>
                          ) : (
                            chatResponse
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              
              {/* Chat Input */}
              <div className="p-4 bg-white border-t border-gray-200">
                <div className="flex gap-2">
                  <textarea
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Ask about this SEC document..."
                    className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={2}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleChatSubmit()
                      }
                    }}
                  />
                  <Button
                    onClick={handleChatSubmit}
                    disabled={!chatInput.trim() || isChatLoading}
                    size="sm"
                    className="px-3"
                  >
                    <Send className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            </div>
          )}
              </div>
            </ResizablePanel>
            
            <ResizableHandle withHandle />

            {/* Right Side - Document Viewer */}
            <ResizablePanel defaultSize={selectedDocument ? 65 : 50}>
              <div className="flex flex-col bg-white h-full">
          {selectedDocument ? (
            <>
              {/* Document Header */}
              <div className="p-4 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h2 className="font-semibold text-gray-900">{selectedDocument.title}</h2>
                    <p className="text-sm text-gray-600">{selectedDocument.company} ({selectedDocument.ticker})</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => window.open(selectedDocument.url, '_blank')}
                      className="flex items-center gap-2"
                    >
                      <ExternalLink className="h-3 w-3" />
                      View Original
                    </Button>
                  </div>
                </div>
                
                {/* Document Controls */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handlePreviousPage}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="h-3 w-3" />
                    </Button>
                    <span className="text-sm text-gray-600">
                      Page {currentPage} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleNextPage}
                      disabled={currentPage === totalPages}
                    >
                      <ChevronRight className="h-3 w-3" />
                    </Button>
                    {isHtmlContent && (
                      <span className="text-xs text-gray-500 ml-4">
                        Formatted Document
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleZoomOut}
                      disabled={documentZoom <= 50}
                    >
                      <ZoomOut className="h-3 w-3" />
                    </Button>
                    <span className="text-sm text-gray-600 min-w-12 text-center">
                      {documentZoom}%
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleZoomIn}
                      disabled={documentZoom >= 200}
                    >
                      <ZoomIn className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </div>

              {/* Document Content */}
              <div className="flex-1 bg-white border-t border-gray-200 h-full overflow-hidden document-content-viewer">
                <div className="w-full h-full overflow-auto bg-gray-50 p-4">
                  <div 
                    className="bg-white shadow-sm border border-gray-200 p-6 min-h-full w-full"
                    style={{ 
                      fontSize: `${Math.max(10, documentZoom * 0.12)}px`,
                      lineHeight: 1.4
                    }}
                  >
                    {isHtmlContent ? (
                      // Render HTML content page
                      <div 
                        dangerouslySetInnerHTML={{ __html: getCurrentPageContent() }} 
                        className="sec-document-html w-full"
                        style={{
                          fontSize: 'inherit',
                          lineHeight: 'inherit'
                        }}
                      />
                    ) : (
                      // Render plain text content page
                      <pre 
                        className="whitespace-pre-wrap text-gray-800 font-mono leading-relaxed w-full"
                        style={{ 
                          fontSize: 'inherit',
                          lineHeight: 'inherit',
                          fontFamily: 'Courier New, monospace'
                        }}
                      >
                        {getCurrentPageContent()}
                      </pre>
                    )}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center bg-gray-50">
              <div className="text-center">
                <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No document selected</h3>
                <p className="text-gray-600">
                  Search for and select a document to view it here
                </p>
              </div>
            </div>
              )}
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        )}
      </div>

      {/* Mobile Sidebar Modal */}
      {showMobileSidebar && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-end z-50 lg:hidden">
          <div className="bg-white w-80 h-full overflow-y-auto">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">SEC Documents</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowMobileSidebar(false)}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}



      {/* Expanded Response Modal */}
      {showExpandedResponse && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">AI Analysis</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowExpandedResponse(false)}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            
            <div className="overflow-y-auto max-h-96">
              <div className="prose prose-sm max-w-none">
                <div className="whitespace-pre-wrap text-gray-700 leading-relaxed">
                  {chatResponse}
                </div>
              </div>
            </div>
            
            <div className="flex justify-end mt-4 pt-4 border-t border-gray-200">
              <Button
                variant="outline"
                onClick={() => setShowExpandedResponse(false)}
                className="px-4"
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}