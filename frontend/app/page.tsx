"use client"

import { useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import HavenNewsApp from './app'
import { AuthService } from "@/services/auth"

export default function HomePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [isLoading, setIsLoading] = useState(true)
  const [needsOnboarding, setNeedsOnboarding] = useState(false)

  useEffect(() => {
    // Check for OAuth callback token in URL
    const token = searchParams.get('token')
    const error = searchParams.get('error')
    const needsOnboardingParam = searchParams.get('needs_onboarding')

    if (token) {
      AuthService.setToken(token)

      // Check if this is a new user who needs onboarding
      if (needsOnboardingParam === 'true') {
        setNeedsOnboarding(true)
      }

      // Remove token and onboarding params from URL
      router.replace('/')
      setIsLoading(false)
      return
    }

    if (error) {
      // Handle authentication error
      router.push('/sign-in?error=' + error)
      return
    }

    // Check if user is authenticated
    if (!AuthService.isAuthenticated()) {
      router.push('/sign-in')
      return
    }

    setIsLoading(false)
  }, [searchParams, router])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        <div className="text-white">Loading...</div>
      </div>
    )
  }

  return <HavenNewsApp initialShowOnboarding={needsOnboarding} />
}
