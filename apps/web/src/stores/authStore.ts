import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { User } from "@/types"
import { authApi } from "@/lib/services/api"

export function syncSettingsToLocalStorage(settings: Record<string, any> | undefined) {
  if (!settings) return

  const keys = [
    "active_provider",
    "gemini_key",
    "gemini_model",
    "groq_key",
    "groq_model",
    "openai_key",
    "openai_model",
    "ollama_url",
    "ollama_model",
    "rag_mode",
    "chunk_limit",
    "llm_temperature",
    "theme",
    "language",
  ]
  keys.forEach((key) => {
    if (settings[key] !== undefined && settings[key] !== null) {
      localStorage.setItem(key, String(settings[key]))
    }
  })

  // Apply theme class
  const theme = settings.theme || "light"
  if (theme === "dark") {
    document.documentElement.classList.add("dark")
  } else {
    document.documentElement.classList.remove("dark")
  }

  // Trigger event for dynamic refresh
  window.dispatchEvent(new Event("llm_settings_changed"))
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
  checkAuth: () => Promise<void>
  clearError: () => void
  updateUserProfile: (data: { username?: string; email?: string; password?: string; settings?: Record<string, any> }) => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await authApi.login(email, password)
          localStorage.setItem("token", response.access_token)
          syncSettingsToLocalStorage(response.user.settings)
          set({
            user: response.user,
            token: response.access_token,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Login failed",
            isLoading: false,
          })
          throw error
        }
      },

      register: async (email: string, username: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await authApi.register(email, username, password)
          localStorage.setItem("token", response.access_token)
          syncSettingsToLocalStorage(response.user.settings)
          set({
            user: response.user,
            token: response.access_token,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Registration failed",
            isLoading: false,
          })
          throw error
        }
      },

      logout: () => {
        localStorage.removeItem("token")
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        })
      },

      checkAuth: async () => {
        const token = localStorage.getItem("token")
        if (!token) {
          set({ isAuthenticated: false, user: null, token: null })
          return
        }

        set({ isLoading: true })
        try {
          const user = await authApi.me()
          syncSettingsToLocalStorage(user.settings)
          set({
            user,
            token,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch {
          localStorage.removeItem("token")
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
          })
        }
      },

      clearError: () => set({ error: null }),

      updateUserProfile: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const updatedUser = await authApi.updateProfile(data)
          syncSettingsToLocalStorage(updatedUser.settings)
          set({
            user: updatedUser,
            isLoading: false,
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Update profile failed",
            isLoading: false,
          })
          throw error
        }
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
