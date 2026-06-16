import { create } from "zustand"
import type { Document, IngestJob } from "@/types"
import { documentsApi, ingestApi } from "@/lib/services/api"

interface DocumentState {
  documents: Document[]
  total: number
  isLoading: boolean
  error: string | null

  loadDocuments: (params?: { page?: number; status?: string; search?: string }) => Promise<void>
  getDocument: (id: string) => Promise<Document & { markdown_content: string | null }>
  deleteDocument: (id: string) => Promise<void>
}

export const useDocumentStore = create<DocumentState>()((set) => ({
  documents: [],
  total: 0,
  isLoading: false,
  error: null,

  loadDocuments: async (params) => {
    set({ isLoading: true })
    try {
      const response = await documentsApi.list(params)
      set({ documents: response.documents, total: response.total, isLoading: false })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to load documents",
        isLoading: false,
      })
    }
  },

  getDocument: async (id) => {
    return documentsApi.get(id)
  },

  deleteDocument: async (id) => {
    // Optimistic update: save snapshot before deletion
    const snapshot = useDocumentStore.getState().documents;
    // Immediately remove from state for optimistic UI
    set((state) => ({
      documents: state.documents.filter((d) => d.id !== id),
      total: Math.max(0, state.total - 1),
    }));
    try {
      await documentsApi.delete(id);
    } catch (error) {
      // Rollback on failure
      set({ documents: snapshot });
      set({
        error: error instanceof Error ? error.message : "Failed to delete document",
      });
      throw error;
    }
  },
}))

interface IngestState {
  jobs: IngestJob[]
  currentPreview: {
    markdown: string
    metadata: Record<string, unknown>
    quality_score: number
    suggested_tags: string[]
  } | null
  isLoading: boolean
  error: string | null

  loadJobs: (params?: { page?: number; status?: string }) => Promise<void>
  submitUrl: (url: string, tags?: string[]) => Promise<string>
  submitFile: (file: File, tags?: string[]) => Promise<string>
  getPreview: (jobId: string) => Promise<void>
  deleteJob: (jobId: string) => Promise<void>
  deleteAllJobs: () => Promise<void>
}

export const useIngestStore = create<IngestState>()((set, get) => ({
  jobs: [],
  currentPreview: null,
  isLoading: false,
  error: null,

  loadJobs: async (params) => {
    set({ isLoading: true })
    try {
      const response = await ingestApi.jobs(params)
      set({ jobs: response.jobs, isLoading: false })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to load jobs",
        isLoading: false,
      })
    }
  },

  submitUrl: async (url, tags) => {
    set({ isLoading: true })
    try {
      const response = await ingestApi.submitUrl(url, tags)
      set({ isLoading: false })
      await get().loadJobs()
      return response.job_id
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to submit URL",
        isLoading: false,
      })
      throw error
    }
  },

  submitFile: async (file, tags) => {
    set({ isLoading: true })
    try {
      const response = await ingestApi.submitFile(file, tags)
      set({ isLoading: false })
      await get().loadJobs()
      return response.job_id
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to submit file",
        isLoading: false,
      })
      throw error
    }
  },

  getPreview: async (jobId) => {
    set({ isLoading: true })
    try {
      const response = await ingestApi.preview(jobId)
      set({
        currentPreview: {
          markdown: response.markdown_content,
          metadata: response.metadata,
          quality_score: response.quality_score,
          suggested_tags: response.suggested_tags,
        },
        isLoading: false,
      })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to get preview",
        isLoading: false,
      })
    }
  },

  deleteJob: async (jobId) => {
    set({ isLoading: true })
    try {
      await ingestApi.deleteJob(jobId)
      set((state) => ({
        jobs: state.jobs.filter((j) => j.id !== jobId),
        isLoading: false,
      }))
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete job",
        isLoading: false,
      })
      throw error
    }
  },

  deleteAllJobs: async () => {
    set({ isLoading: true })
    try {
      await ingestApi.deleteAllJobs()
      set({ jobs: [], isLoading: false })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete all jobs",
        isLoading: false,
      })
      throw error
    }
  },
}))
