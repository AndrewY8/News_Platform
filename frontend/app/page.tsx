"use client"

import { useEffect, useState, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import HavenNewsApp from './app'
import { AuthService } from "@/services/auth"

function AuthHandler() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Check for OAuth callback token in URL
    const token = searchParams.get('token')
    const error = searchParams.get('error')

    if (token) {
      AuthService.setToken(token)
      // Remove token from URL
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

  return <HavenNewsApp />
}

export default function HomePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        <div className="text-white">Loading...</div>
      </div>
    }>
      <AuthHandler />
    </Suspense>
  )
}
