// API response types
export interface User {
  id: string
  email: string
  username: string
  role: "user" | "admin"
  settings?: Record<string, unknown>
}

export interface Document {
  id: string
  title: string
  source_url: string | null
  source_domain: string | null
  source_type: string | null
  author: string | null
  published_at: string | null
  language: string
  summary: string | null
  tags: string[] | null
  detected_years: number[] | null
  entity_persons: string[] | null
  entity_places: string[] | null
  entity_organizations: string[] | null
  entity_events: string[] | null
  status: "pending" | "approved" | "rejected" | "archived"
  quality_score: number
  created_at: string
}

export interface DocumentChunk {
  id: string
  document_id: string
  chunk_index: number
  section_title: string | null
  content: string
  token_count: number | null
}

export interface Session {
  id: string
  user_id: string | null
  title: string | null
  created_at: string
  updated_at: string
  message_count: number
}

export interface Message {
  id: string
  session_id: string
  role: "user" | "assistant" | "system"
  content: string
  mode: string | null
  citations: Citation[] | null
  trace: ResponseTrace | null
  created_at: string
}

export interface Citation {
  document_id: string
  document_title: string
  source_url: string | null
  chunk_id: string
  section_title: string | null
  excerpt: string
  score: number
}

export interface ResponseTrace {
  intent: string
  workflow: string
  tools_used: string[]
  retrieval_ms: number
  generation_ms: number
  cache_hit: boolean
  verification: {
    sufficient_evidence: boolean
    evidence_count: number
    duplicate_ratio: number
    conflict_detected: boolean
  }
  agent_trace?: {
    agent: string
    action: string
    status: string
  }[]
}

export interface IngestJob {
  id: string
  source_input: string
  source_type: "url" | "file" | "batch"
  status: "queued" | "running" | "done" | "failed"
  stage: string | null
  error_message: string | null
  logs: { timestamp: string; level: string; message: string }[]
  document_id: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
}

export interface QueryRequest {
  query: string
  session_id?: string
  filters?: QueryFilters
  mode?: string
}

export interface QueryFilters {
  year_from?: number
  year_to?: number
  person?: string
  event?: string
  topic?: string
}

export interface QueryResponse {
  session_id: string
  message_id: string
  mode: string
  answer: string
  citations: Citation[]
  trace: ResponseTrace
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

// ─── Chat Types (localStorage-based) ───────────────────────────────────────

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  tags?: string[]
  attachedDocs?: string[]
}

export interface ChatConversation {
  id: string
  title: string
  createdAt: number
  updatedAt: number
  messages: ChatMessage[]
}

export interface ChatDocument {
  id: string
  name: string
  size: number
  type: string
  content: string
  uploadedAt: number
}

export type MessageTag = 'factual' | 'phân tích' | 'so sánh' | 'nhân vật' | 'sự kiện' | 'niên đại'
