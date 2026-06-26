import { create } from "zustand"
import type { Session, Message } from "@/types"
import { sessionsApi, queryApi } from "@/lib/services/api"

interface ChatState {
  sessions: Session[]
  activeSessionId: string | null
  messages: Record<string, Message[]>
  isStreaming: boolean
  streamingContent: string
  currentStage: string | null
  liveTrace: Array<{ agent: string; action: string; status: string }> | null
  error: string | null
  abortController: AbortController | null

  loadSessions: () => Promise<void>
  createSession: (title?: string) => Promise<Session>
  setActiveSession: (id: string | null) => void
  loadMessages: (sessionId: string) => Promise<void>
  sendMessage: (query: string, filters?: Record<string, unknown>) => Promise<void>
  abortStreaming: () => void
  clearError: () => void
  renameSession: (id: string, title: string) => Promise<void>
  deleteSession: (id: string) => Promise<void>
  deleteAllSessions: () => Promise<void>
}

export const useChatStore = create<ChatState>()((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: {},
  isStreaming: false,
  streamingContent: "",
  currentStage: null,
  liveTrace: null,
  error: null,
  abortController: null,

  loadSessions: async () => {
    try {
      const response = await sessionsApi.list()
      set({ sessions: response.sessions })
      // Restore last active session after page reload
      const lastId = localStorage.getItem("last_active_session_id")
      if (lastId && response.sessions.find((s) => s.id === lastId)) {
        get().setActiveSession(lastId)
      } else if (response.sessions.length > 0 && !get().activeSessionId) {
        get().setActiveSession(response.sessions[0].id)
      }
    } catch (error) {
      console.error("Failed to load sessions:", error)
    }
  },

  createSession: async (title?: string) => {
    const session = await sessionsApi.create(title)
    const sessionWithClientTime = {
      ...session,
      client_created_at: Date.now(),
    }
    set((state) => ({
      sessions: [sessionWithClientTime, ...state.sessions],
    }))
    return sessionWithClientTime
  },

  setActiveSession: (id: string | null) => {
    set({ activeSessionId: id })
    if (id) {
      localStorage.setItem("last_active_session_id", id)
      get().loadMessages(id)
    } else {
      localStorage.removeItem("last_active_session_id")
    }
  },

  loadMessages: async (sessionId: string) => {
    try {
      const response = await sessionsApi.messages(sessionId)
      set((state) => ({
        messages: {
          ...state.messages,
          [sessionId]: response.messages,
        },
      }))
    } catch (error) {
      console.error("Failed to load messages:", error)
    }
  },

  sendMessage: async (query: string, filters?: Record<string, unknown>) => {
    const { activeSessionId, sessions } = get()

    // Create session if none selected
    let sessionId = activeSessionId
    if (!sessionId) {
      const session = await get().createSession(query.trim().slice(0, 80) || "Cuộc trò chuyện mới")
      sessionId = session.id
      set({ activeSessionId: sessionId })
    }

    // Add user and assistant messages optimistically.
    const userMessage: Message = {
      id: crypto.randomUUID(),
      session_id: sessionId,
      role: "user",
      content: query,
      created_at: new Date().toISOString(),
    }

    const assistantMessageId = crypto.randomUUID()
    const assistantMessage: Message = {
      id: assistantMessageId,
      session_id: sessionId,
      role: "assistant",
      content: "",
      mode: null,
      citations: [],
      trace: null,
      created_at: new Date().toISOString(),
    }
    const controller = new AbortController()

    set((state) => ({
      messages: {
        ...state.messages,
        [sessionId!]: [...(state.messages[sessionId!] || []), userMessage, assistantMessage],
      },
      sessions: state.sessions.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              message_count: Math.max(session.message_count ?? 0, 1),
              title:
                !session.title || session.title === "Cuộc trò chuyện mới" || session.title === "Session"
                  ? query.trim().slice(0, 80) || session.title
                  : session.title,
              updated_at: new Date().toISOString(),
            }
          : session
      ),
      isStreaming: true,
      streamingContent: "",
      currentStage: "classifying",
      liveTrace: null,
      abortController: controller,
      error: null,
    }))

    try {
      await queryApi.streamQuery(
        { query, session_id: sessionId, filters },
        (data) => {
          if (data.type === "stage") {
            set({ currentStage: (data.stage ?? data.data ?? null) as string | null })
          } else if (data.type === "token") {
            const token = (data.token ?? data.data ?? "") as string
            set((state) => ({
              streamingContent: state.streamingContent + token,
              messages: {
                ...state.messages,
                [sessionId!]: (state.messages[sessionId!] || []).map((message) =>
                  message.id === assistantMessageId
                    ? { ...message, content: message.content + token }
                    : message
                ),
              },
            }))
          } else if (data.type === "message") {
            const messageId = data.message_id as string | undefined
            if (messageId) {
              set((state) => ({
                messages: {
                  ...state.messages,
                  [sessionId!]: (state.messages[sessionId!] || []).map((message) =>
                    message.id === assistantMessageId ? { ...message, id: messageId } : message
                  ),
                },
              }))
            }
          } else if (data.type === "citations") {
            const citations = (data.citations ?? data.data ?? []) as Message["citations"]
            set((state) => ({
              messages: {
                ...state.messages,
                [sessionId!]: (() => {
                  const list = state.messages[sessionId!] || []
                  const lastAssistant = [...list].reverse().find((item) => item.role === "assistant")
                  return list.map((message) =>
                    message.id === assistantMessageId || message.id === lastAssistant?.id
                    ? { ...message, citations }
                    : message
                  )
                })(),
              },
            }))
          } else if (data.type === "trace_step") {
            // Incremental step: append or update this single step
            const step = data.step as { agent: string; action: string; status: string }
            if (step?.agent) {
              set((state) => {
                const current = state.liveTrace || []
                const last = current[current.length - 1]
                
                // If the last step was pending and is for the same agent (roughly), replace it
                if (last && last.status === "pending" && (last.agent === step.agent || step.agent.includes(last.agent))) {
                  return { liveTrace: [...current.slice(0, -1), step] }
                }
                
                return { liveTrace: [...current, step] }
              })
            }
          } else if (data.type === "trace") {
            const trace = (data.trace ?? data.data ?? null) as Message["trace"]
            // Sync full cumulative trace to keep liveTrace in order
            if (trace?.agent_trace) {
              set({ liveTrace: trace.agent_trace as Array<{ agent: string; action: string; status: string }> })
            }
            set((state) => ({
              messages: {
                ...state.messages,
                [sessionId!]: (() => {
                  const list = state.messages[sessionId!] || []
                  const lastAssistant = [...list].reverse().find((item) => item.role === "assistant")
                  return list.map((message) =>
                    message.id === assistantMessageId || message.id === lastAssistant?.id
                    ? { ...message, mode: trace?.intent || message.mode, trace }
                    : message
                  )
                })(),
              },
            }))
          } else if (data.type === "error") {
            throw new Error(String(data.error || data.data || "LLM provider request failed"))
          }
        },
        controller.signal
      )

      set({
        isStreaming: false,
        streamingContent: "",
        currentStage: null,
        liveTrace: null,
        abortController: null,
      })
    } catch (error) {
      const aborted = error instanceof DOMException && error.name === "AbortError"
      set((state) => ({
        error: aborted ? null : error instanceof Error ? error.message : "Query failed",
        isStreaming: false,
        streamingContent: "",
        currentStage: null,
        liveTrace: null,
        abortController: null,
        messages: {
          ...state.messages,
          [sessionId!]: (state.messages[sessionId!] || []).filter(
            (message) => message.id !== assistantMessageId
          ),
        },
      }))
    }
  },

  abortStreaming: () => {
    const controller = get().abortController
    if (controller) {
      controller.abort()
    }
    set({
      isStreaming: false,
      streamingContent: "",
      currentStage: null,
      liveTrace: null,
      abortController: null,
    })
  },

  clearError: () => set({ error: null }),

  renameSession: async (id: string, title: string) => {
    try {
      const updated = await sessionsApi.update(id, title)
      set((state) => ({
        sessions: state.sessions.map((s) => (s.id === id ? updated : s)),
      }))
    } catch (error) {
      console.error("Failed to rename session:", error)
      throw error
    }
  },

  deleteSession: async (id: string) => {
    const previousState = get()
    try {
      set((state) => {
        const nextSessions = state.sessions.filter((s) => s.id !== id)
        let nextActiveId = state.activeSessionId
        if (state.activeSessionId === id) {
          nextActiveId = nextSessions.length > 0 ? nextSessions[0].id : null
        }
        return {
          sessions: nextSessions,
          activeSessionId: nextActiveId,
        }
      })
      await sessionsApi.delete(id)
      const { activeSessionId } = get()
      if (activeSessionId) {
        get().loadMessages(activeSessionId)
      }
    } catch (error) {
      const isNotFoundError = error instanceof Error && (
        error.message.includes("404") ||
        error.message.toLowerCase().includes("not found")
      )
      if (isNotFoundError) {
        console.warn("Session was already deleted or not found on server:", id)
        return
      }
      console.error("Failed to delete session:", error)
      set({
        sessions: previousState.sessions,
        activeSessionId: previousState.activeSessionId,
      })
      throw error
    }
  },

  deleteAllSessions: async () => {
    const previousState = get()
    try {
      set({
        sessions: [],
        activeSessionId: null,
      })
      await sessionsApi.deleteAll()
    } catch (error) {
      console.error("Failed to delete all sessions:", error)
      set({
        sessions: previousState.sessions,
        activeSessionId: previousState.activeSessionId,
      })
      throw error
    }
  },
}))

