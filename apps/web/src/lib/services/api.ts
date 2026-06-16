import type { TokenResponse, User, Session, Message, Document, IngestJob, QueryResponse } from "@/types"

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1"
const DEFAULT_TIMEOUT_MS = 30000

const GROQ_LEGACY_MODEL_MAP: Record<string, string> = {
  "llama3-70b-8192": "llama-3.3-70b-versatile",
  "llama3-8b-8192": "llama-3.1-8b-instant",
  "mixtral-8x7b-32768": "llama-3.3-70b-versatile",
}

function getGroqModel() {
  const model = localStorage.getItem("groq_model") || "llama-3.3-70b-versatile"
  const normalized = GROQ_LEGACY_MODEL_MAP[model] || model
  if (normalized !== model) {
    localStorage.setItem("groq_model", normalized)
  }
  return normalized
}

async function getToken() {
  return localStorage.getItem("token")
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, { ...options, signal: controller.signal })
  } finally {
    clearTimeout(timeoutId)
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getToken()

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  try {
    const response = await fetchWithTimeout(`${API_BASE}${endpoint}`, { ...options, headers })

    if (response.status === 401) {
      if (endpoint === "/auth/login") {
        throw new Error("Email hoặc mật khẩu không chính xác.")
      }
      localStorage.removeItem("token")
      window.dispatchEvent(new CustomEvent("auth:expired"))
      throw new Error("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Request failed" }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    if (response.status === 204) {
      return {} as T
    }

    return response.json()
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error(`Yêu cầu bị timeout sau ${DEFAULT_TIMEOUT_MS / 1000}s. Vui lòng thử lại.`)
    }
    throw err
  }
}

// === AUTH ===
export const authApi = {
  async login(email: string, password: string): Promise<TokenResponse> {
    return request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    })
  },

  async register(email: string, username: string, password: string): Promise<TokenResponse> {
    return request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, username, password }),
    })
  },

  async me(): Promise<User> {
    return request("/auth/me")
  },

  async updateProfile(data: { username?: string; email?: string; password?: string; settings?: Record<string, any> }): Promise<User> {
    return request("/auth/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    })
  },
}

// === SESSIONS ===
export const sessionsApi = {
  async list(): Promise<{ sessions: Session[]; total: number }> {
    return request("/sessions")
  },

  async create(title?: string): Promise<Session> {
    return request("/sessions", {
      method: "POST",
      body: JSON.stringify({ title }),
    })
  },

  async get(id: string): Promise<Session> {
    return request(`/sessions/${id}`)
  },

  async messages(id: string): Promise<{ messages: Message[]; total: number }> {
    return request(`/sessions/${id}/messages`)
  },

  async update(id: string, title: string): Promise<Session> {
    return request(`/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    })
  },

  async delete(id: string): Promise<void> {
    return request(`/sessions/${id}`, {
      method: "DELETE",
    })
  },
}

function sanitizeKey(key: string | null): string {
  if (!key) return ""
  if (key === "••••••••" || key === "********") return "********"
  return key
}

// === QUERY ===
export const queryApi = {
  async query(data: { query: string; session_id?: string; filters?: Record<string, unknown> }): Promise<QueryResponse> {
    return request("/query", {
      method: "POST",
      headers: {
        "X-Active-Provider": localStorage.getItem("active_provider") || "gemini",
        "X-Gemini-Key": sanitizeKey(localStorage.getItem("gemini_key")),
        "X-Gemini-Model": localStorage.getItem("gemini_model") || "gemini-1.5-pro",
        "X-Groq-Key": sanitizeKey(localStorage.getItem("groq_key")),
        "X-Groq-Model": getGroqModel(),
        "X-OpenAI-Key": sanitizeKey(localStorage.getItem("openai_key")),
        "X-OpenAI-Model": localStorage.getItem("openai_model") || "gpt-4o",
        "X-Ollama-Url": localStorage.getItem("ollama_url") || "http://localhost:11434",
        "X-Ollama-Model": localStorage.getItem("ollama_model") || "llama3",
        "X-RAG-Mode": localStorage.getItem("rag_mode") || "hybrid",
        "X-Chunk-Limit": localStorage.getItem("chunk_limit") || "8",
        "X-LLM-Temperature": localStorage.getItem("llm_temperature") || "0.1",
      },
      body: JSON.stringify(data),
    })
  },

  async streamQuery(
    data: { query: string; session_id?: string; filters?: Record<string, unknown> },
    onChunk: (data: Record<string, unknown>) => void,
    signal?: AbortSignal
  ): Promise<void> {
    const token = localStorage.getItem("token")

    const response = await fetch(`${API_BASE}/query/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        "X-Active-Provider": localStorage.getItem("active_provider") || "gemini",
        "X-Gemini-Key": sanitizeKey(localStorage.getItem("gemini_key")),
        "X-Gemini-Model": localStorage.getItem("gemini_model") || "gemini-1.5-pro",
        "X-Groq-Key": sanitizeKey(localStorage.getItem("groq_key")),
        "X-Groq-Model": getGroqModel(),
        "X-OpenAI-Key": sanitizeKey(localStorage.getItem("openai_key")),
        "X-OpenAI-Model": localStorage.getItem("openai_model") || "gpt-4o",
        "X-Ollama-Url": localStorage.getItem("ollama_url") || "http://localhost:11434",
        "X-Ollama-Model": localStorage.getItem("ollama_model") || "llama3",
        "X-RAG-Mode": localStorage.getItem("rag_mode") || "hybrid",
        "X-Chunk-Limit": localStorage.getItem("chunk_limit") || "8",
        "X-LLM-Temperature": localStorage.getItem("llm_temperature") || "0.1",
      },
      body: JSON.stringify(data),
      signal,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Request failed" }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) return

    const decoder = new TextDecoder()
    let buffer = ""

    while (true) {
      const result = await reader.read()
      if (result.done) break

      buffer += decoder.decode(result.value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() || ""

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          let event: Record<string, unknown>
          try {
            event = JSON.parse(line.slice(6))
          } catch {
            // Skip invalid JSON
            continue
          }
          if (event.type === "error") {
            throw new Error(String(event.error || event.data || "LLM provider request failed"))
          }
          onChunk(event)
        }
      }
    }
  },
}

// === DOCUMENTS ===
export const documentsApi = {
  async list(params?: { page?: number; status?: string; search?: string }): Promise<{ documents: Document[]; total: number }> {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set("page", String(params.page))
    if (params?.status) searchParams.set("status", params.status)
    if (params?.search) searchParams.set("search", params.search)

    const query = searchParams.toString()
    return request(`/documents${query ? `?${query}` : ""}`)
  },

  async get(id: string): Promise<Document & { markdown_content: string | null }> {
    return request(`/documents/${id}`)
  },

  async update(id: string, data: Partial<Document>): Promise<Document> {
    return request(`/documents/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    })
  },

  async delete(id: string): Promise<void> {
    return request(`/documents/${id}`, {
      method: "DELETE",
    })
  },
}

// === INGEST ===
export const ingestApi = {
  async submitUrl(url: string, tags?: string[]): Promise<{
    job_id: string
    status: string
    stage?: string | null
    document_id?: string | null
    error_message?: string | null
  }> {
    return request("/ingest/url", {
      method: "POST",
      body: JSON.stringify({ url, tags }),
    })
  },

  async jobs(params?: { page?: number; status?: string }): Promise<{ jobs: IngestJob[]; total: number }> {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set("page", String(params.page))
    if (params?.status) searchParams.set("status", params.status)

    const query = searchParams.toString()
    return request(`/ingest/jobs${query ? `?${query}` : ""}`)
  },

  async getJob(id: string): Promise<IngestJob> {
    return request(`/ingest/jobs/${id}`)
  },

  async submitFile(file: File, tags?: string[]): Promise<{
    job_id: string
    status: string
    stage?: string | null
    document_id?: string | null
    error_message?: string | null
  }> {
    const token = localStorage.getItem("token")
    const form = new FormData()
    form.append("upload", file)
    if (tags?.length) form.append("tags", tags.join(","))

    const response = await fetch(`${API_BASE}/ingest/file`, {
      method: "POST",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: form,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Upload failed" }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
  },

  async retryJob(id: string): Promise<IngestJob> {
    return request(`/ingest/jobs/${id}/retry`, { method: "POST" })
  },

  async deleteJob(id: string): Promise<void> {
    return request(`/ingest/jobs/${id}`, { method: "DELETE" })
  },

  async deleteAllJobs(): Promise<void> {
    return request("/ingest/jobs", { method: "DELETE" })
  },

  async preview(id: string): Promise<{
    markdown_content: string
    metadata: Record<string, unknown>
    quality_score: number
    suggested_tags: string[]
  }> {
    return request(`/ingest/preview/${id}`)
  },
}
