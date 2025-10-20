"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"

export default function SignInPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function handleGoogleSignIn() {
    setIsLoading(true)
    setError(null)

    // Direct redirect to backend OAuth endpoint
    window.location.href = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/auth/google`
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-white">
      <div className="w-full max-w-md px-8">
        <div className="flex flex-col items-center space-y-8">
          {/* Logo/Brand */}
          <div className="flex flex-col items-center space-y-2">
            <h1 className="text-3xl font-normal text-gray-800">Haven News</h1>
          </div>

          {/* Sign in card */}
          <div className="w-full border border-gray-300 rounded-lg p-12 bg-white shadow-sm">
            <div className="flex flex-col items-center space-y-6">
              <h2 className="text-2xl font-normal text-gray-800">
                Sign in
              </h2>

              <p className="text-sm text-gray-600 text-center">
                to continue to Haven News
              </p>

              {error && (
                <div className="w-full p-3 text-sm text-red-700 bg-red-50 rounded border border-red-300">
                  {error}
                </div>
              )}

              <div className="w-full pt-4">
                <Button
                  onClick={handleGoogleSignIn}
                  disabled={isLoading}
                  variant="outline"
                  className="w-full h-12 border-gray-300 hover:bg-gray-50 text-gray-700 font-medium"
                >
                  <svg className="mr-3 h-5 w-5" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    />
                  </svg>
                  {isLoading ? "Signing in..." : "Continue with Google"}
                </Button>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center space-x-4 text-xs text-gray-600">
            <a href="#" className="hover:text-gray-800">Help</a>
            <a href="#" className="hover:text-gray-800">Privacy</a>
            <a href="#" className="hover:text-gray-800">Terms</a>
          </div>
        </div>
      </div>
    </div>
  )
}
