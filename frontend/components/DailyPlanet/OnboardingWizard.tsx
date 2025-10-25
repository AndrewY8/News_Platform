"use client"

import { useState } from "react"
import { ChevronRight, ChevronLeft, Globe, BookOpen, Tag, Layout, Check } from "lucide-react"
import { OnboardingData, RegionType, ReadingLevel, SUGGESTED_TOPICS } from "@/types/dailyplanet"

interface OnboardingWizardProps {
  onComplete: (data: OnboardingData) => void
  onSkip?: () => void
  existingTickers?: string[]
}

export function OnboardingWizard({ onComplete, onSkip, existingTickers = [] }: OnboardingWizardProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [formData, setFormData] = useState<OnboardingData>({
    region: "Global",
    reading_level: "standard",
    topics: [],
    tickers: existingTickers,
    layout_density: 2,
  })

  const steps = [
    {
      title: "Welcome to The Daily Planet",
      description: "Your personalized financial news hub",
      icon: Globe,
    },
    {
      title: "Choose Your Region",
      description: "Select your primary market focus",
      icon: Globe,
    },
    {
      title: "Select Your Interests",
      description: "Pick topics you want to follow",
      icon: Tag,
    },
    {
      title: "Customize Your Experience",
      description: "Set your reading preferences",
      icon: Layout,
    },
  ]

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      onComplete(formData)
    }
  }

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleRegionSelect = (region: RegionType) => {
    setFormData({ ...formData, region })
  }

  const handleTopicToggle = (topicName: string) => {
    const newTopics = formData.topics.includes(topicName)
      ? formData.topics.filter(t => t !== topicName)
      : [...formData.topics, topicName]
    setFormData({ ...formData, topics: newTopics })
  }

  const handleReadingLevelSelect = (level: ReadingLevel) => {
    setFormData({ ...formData, reading_level: level })
  }

  const handleLayoutDensitySelect = (density: 1 | 2 | 3) => {
    setFormData({ ...formData, layout_density: density })
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Progress Bar */}
        <div className="h-2 bg-gray-200">
          <div
            className="h-full bg-blue-600 transition-all duration-300"
            style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
          />
        </div>

        {/* Content */}
        <div className="p-8 overflow-y-auto flex-1">
          {/* Step Indicator */}
          <div className="flex items-center justify-between mb-8">
            {steps.map((step, index) => {
              const StepIcon = step.icon
              return (
                <div
                  key={index}
                  className={`flex items-center ${index < steps.length - 1 ? 'flex-1' : ''}`}
                >
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      index === currentStep
                        ? 'bg-blue-600 text-white'
                        : index < currentStep
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-200 text-gray-400'
                    }`}
                  >
                    {index < currentStep ? (
                      <Check className="w-5 h-5" />
                    ) : (
                      <StepIcon className="w-5 h-5" />
                    )}
                  </div>
                  {index < steps.length - 1 && (
                    <div
                      className={`h-0.5 flex-1 mx-2 ${
                        index < currentStep ? 'bg-green-600' : 'bg-gray-200'
                      }`}
                    />
                  )}
                </div>
              )
            })}
          </div>

          {/* Step Content */}
          <div className="min-h-[400px]">
            {/* Step 0: Welcome */}
            {currentStep === 0 && (
              <div className="text-center py-12">
                <h1 className="text-4xl font-bold text-gray-900 mb-4">
                  Welcome to The Daily Planet
                </h1>
                <p className="text-xl text-gray-600 mb-8">
                  Your personalized financial news hub, tailored to your interests
                </p>
                <div className="max-w-md mx-auto text-left space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                      <Check className="w-4 h-4 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">AI-Powered Personalization</h3>
                      <p className="text-sm text-gray-600">
                        Articles curated based on your portfolio and interests
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                      <Check className="w-4 h-4 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">Customizable Layout</h3>
                      <p className="text-sm text-gray-600">
                        Drag and drop sections to create your perfect news experience
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                      <Check className="w-4 h-4 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">Learn Your Preferences</h3>
                      <p className="text-sm text-gray-600">
                        The more you use it, the smarter it gets
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Step 1: Region Selection */}
            {currentStep === 1 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                  {steps[currentStep].title}
                </h2>
                <p className="text-gray-600 mb-6">{steps[currentStep].description}</p>

                <div className="grid grid-cols-2 gap-4">
                  {(['US', 'EU', 'APAC', 'Global'] as RegionType[]).map((region) => (
                    <button
                      key={region}
                      onClick={() => handleRegionSelect(region)}
                      className={`p-6 rounded-lg border-2 transition-all ${
                        formData.region === region
                          ? 'border-blue-600 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="text-left">
                        <h3 className="font-semibold text-gray-900 mb-1">{region}</h3>
                        <p className="text-sm text-gray-600">
                          {region === 'US' && 'Focus on US markets and companies'}
                          {region === 'EU' && 'Focus on European markets'}
                          {region === 'APAC' && 'Focus on Asia-Pacific markets'}
                          {region === 'Global' && 'Worldwide market coverage'}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Step 2: Topic Selection */}
            {currentStep === 2 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                  {steps[currentStep].title}
                </h2>
                <p className="text-gray-600 mb-6">
                  {steps[currentStep].description} (select all that apply)
                </p>

                <div className="grid grid-cols-2 gap-3 max-h-[350px] overflow-y-auto pr-2">
                  {SUGGESTED_TOPICS.map((topic) => {
                    const isSelected = formData.topics.includes(topic.name)
                    return (
                      <button
                        key={topic.name}
                        onClick={() => handleTopicToggle(topic.name)}
                        className={`p-4 rounded-lg border-2 transition-all text-left ${
                          isSelected
                            ? 'border-blue-600 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-gray-900">{topic.name}</span>
                          {isSelected && (
                            <Check className="w-5 h-5 text-blue-600" />
                          )}
                        </div>
                        <span className="text-xs text-gray-500 capitalize">{topic.type}</span>
                      </button>
                    )
                  })}
                </div>

                <p className="text-sm text-gray-500 mt-4">
                  Selected: {formData.topics.length} topic{formData.topics.length !== 1 ? 's' : ''}
                </p>
              </div>
            )}

            {/* Step 3: Reading Preferences */}
            {currentStep === 3 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                  {steps[currentStep].title}
                </h2>
                <p className="text-gray-600 mb-6">{steps[currentStep].description}</p>

                <div className="space-y-6">
                  {/* Reading Level */}
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-3">Article Depth</h3>
                    <div className="grid grid-cols-3 gap-3">
                      {(['quick', 'standard', 'in-depth'] as ReadingLevel[]).map((level) => (
                        <button
                          key={level}
                          onClick={() => handleReadingLevelSelect(level)}
                          className={`p-4 rounded-lg border-2 transition-all ${
                            formData.reading_level === level
                              ? 'border-blue-600 bg-blue-50'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <div className="text-center">
                            <h4 className="font-medium text-gray-900 capitalize mb-1">
                              {level}
                            </h4>
                            <p className="text-xs text-gray-600">
                              {level === 'quick' && 'Brief summaries'}
                              {level === 'standard' && 'Balanced coverage'}
                              {level === 'in-depth' && 'Full analysis'}
                            </p>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Layout Density */}
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-3">Layout Density</h3>
                    <div className="grid grid-cols-3 gap-3">
                      {([1, 2, 3] as const).map((density) => (
                        <button
                          key={density}
                          onClick={() => handleLayoutDensitySelect(density)}
                          className={`p-4 rounded-lg border-2 transition-all ${
                            formData.layout_density === density
                              ? 'border-blue-600 bg-blue-50'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <div className="text-center">
                            <h4 className="font-medium text-gray-900 mb-1">
                              {density} Column{density > 1 ? 's' : ''}
                            </h4>
                            <div className="flex gap-1 justify-center mt-2">
                              {Array.from({ length: density }).map((_, i) => (
                                <div
                                  key={i}
                                  className="w-4 h-8 bg-blue-600 rounded"
                                />
                              ))}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Summary */}
                  <div className="bg-gray-50 rounded-lg p-4 mt-6">
                    <h3 className="font-semibold text-gray-900 mb-2">Your Preferences</h3>
                    <div className="space-y-1 text-sm text-gray-600">
                      <p><span className="font-medium">Region:</span> {formData.region}</p>
                      <p><span className="font-medium">Topics:</span> {formData.topics.length} selected</p>
                      <p><span className="font-medium">Reading Level:</span> {formData.reading_level}</p>
                      <p><span className="font-medium">Layout:</span> {formData.layout_density} columns</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Actions - Outside scrollable area so always visible */}
        <div className="p-8 pt-0">
          <div className="flex items-center justify-between pt-6 border-t">
            <div>
              {onSkip && currentStep === 0 && (
                <button
                  onClick={onSkip}
                  className="text-gray-600 hover:text-gray-900 text-sm font-medium"
                >
                  Skip Setup
                </button>
              )}
            </div>

            <div className="flex gap-3">
              {currentStep > 0 && (
                <button
                  onClick={handleBack}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Back
                </button>
              )}
              <button
                onClick={handleNext}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 font-medium"
              >
                {currentStep === steps.length - 1 ? (
                  <>
                    Complete Setup
                    <Check className="w-4 h-4" />
                  </>
                ) : (
                  <>
                    Continue
                    <ChevronRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
