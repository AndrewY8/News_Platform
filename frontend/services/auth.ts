// Authentication service for Google OAuth
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface User {
  id: string
  email: string
  username: string
  full_name?: string
  avatar_url?: string
  verified: boolean
  trades: string[]
}

export class AuthService {
  private static TOKEN_KEY = 'haven_auth_token'

  static getToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem(this.TOKEN_KEY)
  }

  static setToken(token: string): void {
    if (typeof window === 'undefined') return
    localStorage.setItem(this.TOKEN_KEY, token)
  }

  static removeToken(): void {
    if (typeof window === 'undefined') return
    localStorage.removeItem(this.TOKEN_KEY)
  }

  static async signInWithGoogle(): Promise<void> {
    // Redirect to Google OAuth endpoint
    window.location.href = `${API_BASE_URL}/api/auth/google`
  }

  static async getCurrentUser(): Promise<User | null> {
    try {
      const token = this.getToken()
      if (!token) return null

      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        if (response.status === 401) {
          this.removeToken()
          return null
        }
        throw new Error(`Failed to get current user: ${response.status}`)
      }

      const user = await response.json()
      return user
    } catch (error) {
      console.error('Error getting current user:', error)
      return null
    }
  }

  static async logout(): Promise<void> {
    try {
      const token = this.getToken()
      if (token) {
        await fetch(`${API_BASE_URL}/api/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
      }
    } catch (error) {
      console.error('Error during logout:', error)
    } finally {
      this.removeToken()
    }
  }

  static isAuthenticated(): boolean {
    return this.getToken() !== null
  }
}
