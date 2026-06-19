// Reuse the same request helper pattern as existing api.ts
const API_BASE = "/api/v1";

const DEFAULT_TIMEOUT_MS = 30000;

function sanitizeKey(key: string | null): string {
  if (!key) return ""
  if (key === "••••••••" || key === "********") return "********"
  return key
}

async function fetchWithTimeout(url: string, options: RequestInit, timeoutMs: number = DEFAULT_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timeoutId);
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("token");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Active-Provider": localStorage.getItem("active_provider") || "gemini",
    "X-Gemini-Key": sanitizeKey(localStorage.getItem("gemini_key")),
    "X-Gemini-Model": localStorage.getItem("gemini_model") || "gemini-1.5-pro",
    "X-Groq-Key": sanitizeKey(localStorage.getItem("groq_key")),
    "X-Groq-Model": localStorage.getItem("groq_model") || "llama-3.3-70b-versatile",
    "X-OpenAI-Key": sanitizeKey(localStorage.getItem("openai_key")),
    "X-OpenAI-Model": localStorage.getItem("openai_model") || "gpt-4o",
    "X-Ollama-Url": localStorage.getItem("ollama_url") || "http://localhost:11434",
    "X-Ollama-Model": localStorage.getItem("ollama_model") || "llama3",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetchWithTimeout(`${API_BASE}${endpoint}`, { ...options, headers });

    if (response.status === 401) {
      localStorage.removeItem("token");
      window.dispatchEvent(new CustomEvent("auth:expired"));
      throw new Error("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error(`Yêu cầu bị timeout sau ${timeoutMs / 1000}s. Vui lòng thử lại.`);
    }
    throw err;
  }
}

function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") {
      sp.set(k, String(v));
    }
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

// ========================
// Wiki API
// ========================
export interface WikiPage {
  id: string;
  slug: string;
  title: string;
  period: string;
  event_type: string;
  summary: string;
  content?: string;
  sections?: WikiSection[];
  related_pages?: RelatedPage[];
  sources?: WikiSource[];
  created_at: string;
  updated_at?: string;
}

export interface WikiSection {
  title: string;
  content: string;
}

export interface RelatedPage {
  slug: string;
  title: string;
  period?: string;
}

export interface WikiSource {
  title: string;
  url?: string;
  author?: string;
  year?: number;
}

// Map Vietnamese section keys from backend content dict to frontend section titles
const CONTENT_KEY_TO_TITLE: Record<string, string> = {
  background: "Bối cảnh",
  causes: "Nguyên nhân",
  main_events: "Diễn biến chính",
  results: "Kết quả",
  significance: "Ý nghĩa lịch sử",
  people: "Nhân vật liên quan",
  timeline: "Mốc thời gian",
  references: "Nguồn tham khảo",
};

interface RawWikiPage {
  id: string;
  slug: string;
  title: string;
  period?: string;
  event_type?: string;
  summary?: string;
  content?: string | Record<string, unknown>;
  related_pages?: RelatedPage[];
  sources?: WikiSource[];
  created_at: string;
  updated_at?: string;
}

interface RawTimelineEvent {
  id: string;
  slug?: string;
  event_name?: string;
  title?: string;
  start_year?: number;
  year?: number;
  start_date?: string;
  period?: string;
  summary?: string;
  causes?: string[];
  effects?: string[];
  wiki_page_id?: string;
  wiki_page_slug?: string;
  created_at?: string;
}

interface RawBrainJob {
  id: string;
  status: string;
  source_document_ids?: string[];
  created_at: string;
  updated_at?: string;
  error_message?: string | null;
  result_summary?: Record<string, unknown> | null;
}

interface RawBrainPlan {
  id: string;
  job_id: string;
  status: string;
  proposed_pages?: unknown[];
  created_at: string;
  admin_notes?: string | null;
}

interface RawWikiPagesResponse {
  pages: RawWikiPage[];
  total: number;
}

interface RawTimelineResponse {
  events: RawTimelineEvent[];
  total: number;
  page: number;
  page_size: number;
}

interface RawBrainJobsResponse {
  jobs: RawBrainJob[];
  total: number;
}

interface RawBrainPlansResponse {
  plans: RawBrainPlan[];
  total: number;
}

interface RawGraphNodesResponse {
  nodes: Record<string, unknown>[];
  total: number;
}

interface RawGraphEdgesResponse {
  edges: Record<string, unknown>[];
  total: number;
}

/**
 * Transform a raw backend WikiPage response (where content is a JSONB dict)
 * into the frontend WikiPage shape (with sections[] array).
 */
function transformWikiPage(raw: RawWikiPage): WikiPage {
  const sections: WikiSection[] = [];
  if (raw.content && typeof raw.content === "object" && !Array.isArray(raw.content)) {
    for (const [key, value] of Object.entries(raw.content)) {
      if (value && typeof value === "string" && value.trim()) {
        const sectionTitle = CONTENT_KEY_TO_TITLE[key] || key;
        sections.push({ title: sectionTitle, content: value.trim() });
      } else if (Array.isArray(value) && value.length > 0) {
        const sectionTitle = CONTENT_KEY_TO_TITLE[key] || key;
        sections.push({ title: sectionTitle, content: (value as string[]).join("\n") });
      }
    }
  }

  return {
    id: raw.id,
    slug: raw.slug,
    title: raw.title,
    period: raw.period || "",
    event_type: raw.event_type || "",
    summary: raw.summary || "",
    content: typeof raw.content === "string" ? raw.content : undefined,
    sections: sections.length > 0 ? sections : undefined,
    related_pages: raw.related_pages,
    sources: raw.sources,
    created_at: raw.created_at,
    updated_at: raw.updated_at,
  };
}

export const wikiApi = {
  getPages: async (params?: { search?: string; period?: string; project_id?: string }) => {
    const raw = await request<RawWikiPagesResponse>(
      `/wiki/pages${buildQuery(params || {})}`
    );
    return {
      total: raw.total,
      pages: (raw.pages || []).map(transformWikiPage),
    };
  },

  getPage: async (slug: string) => {
    const raw = await request<RawWikiPage>(`/wiki/pages/${slug}`);
    return transformWikiPage(raw);
  },

  getContext: async (slug: string) => {
    return request<{
      context: {
        title: string;
        summary: string;
        entities: string[];
      };
      sources: Array<{ title: string; page?: number }>;
    }>(`/wiki/pages/${slug}/context`);
  },
};

// ========================
// Projects API
// ========================
export interface Project {
  id: string;
  slug: string;
  name: string;
  description?: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export const projectsApi = {
  list: async (params?: { page?: number; page_size?: number }) => {
    return request<{ projects: Project[]; total: number }>("/projects" + buildQuery(params || {}));
  },
  get: async (slug: string) => {
    return request<Project>(`/projects/${slug}`);
  },
  create: async (data: { name: string; description?: string; slug?: string }) => {
    return request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
};

// ========================
// Wiki Page Drafts API
// ========================
export interface WikiPageDraft {
  id: string;
  wiki_page_id?: string;
  project_id?: string;
  slug: string;
  title: string;
  summary?: string;
  content?: Record<string, any>;
  status: string; // pending | approved | rejected
  admin_notes?: string;
  proposed_by?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  created_at: string;
}

export const draftsApi = {
  propose: async (data: {
    wiki_page_id?: string;
    project_id?: string;
    title: string;
    slug?: string;
    summary?: string;
    content?: Record<string, any>;
  }) => {
    return request<WikiPageDraft>("/wiki/drafts", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
  list: async (params?: { status?: string; project_id?: string; page?: number; page_size?: number }) => {
    return request<WikiPageDraft[]>("/wiki/drafts" + buildQuery(params || {}));
  },
  get: async (id: string) => {
    return request<WikiPageDraft>(`/wiki/drafts/${id}`);
  },
  review: async (id: string, action: { status: "approved" | "rejected"; admin_notes?: string }) => {
    return request<WikiPageDraft>(`/wiki/drafts/${id}/review`, {
      method: "POST",
      body: JSON.stringify(action),
    });
  },
};

// ========================
// Timeline API
// ========================
export interface TimelineEvent {
  id: string;
  slug?: string;
  // Frontend-normalised alias: backend field is event_name
  title: string;
  // Frontend-normalised alias: backend field is start_year
  year: number;
  month?: number;
  day?: number;
  period: string;
  summary?: string;
  causes?: string[];
  effects?: string[];
  // wiki_page_id from backend; slug requires a separate lookup but we pass it through
  wiki_page_id?: string;
  wiki_page_slug?: string;
  created_at?: string;
}

/**
 * Transform a backend HistoricalEventResponse to the frontend TimelineEvent shape.
 * Backend uses event_name/start_year; frontend expects title/year.
 */
function transformTimelineEvent(raw: RawTimelineEvent): TimelineEvent {
  // Derive month/day from start_date if present
  let month: number | undefined;
  let day: number | undefined;
  if (raw.start_date) {
    const d = new Date(raw.start_date);
    if (!isNaN(d.getTime())) {
      month = d.getMonth() + 1;
      day = d.getDate();
    }
  }

  return {
    id: raw.id,
    slug: raw.slug,
    title: raw.event_name || raw.title || "(Không có tên)",
    year: raw.start_year ?? raw.year ?? 0,
    month,
    day,
    period: raw.period || "default",
    summary: raw.summary,
    causes: raw.causes,
    effects: raw.effects,
    wiki_page_id: raw.wiki_page_id,
    wiki_page_slug: raw.wiki_page_slug,
    created_at: raw.created_at,
  };
}

export const timelineApi = {
  getEvents: async (params?: { period?: string; start_year?: number; end_year?: number }) => {
    const raw = await request<RawTimelineResponse>(
      `/timeline/events${buildQuery(params || {})}`
    );
    return {
      events: (raw.events || []).map(transformTimelineEvent),
    };
  },
};

// ========================
// Graph API
// ========================
export interface GraphNode {
  id: string;
  slug: string;
  name: string;
  type: string; // Primary field (frontend convention)
  node_type?: string; // Backend alias
  description?: string;
}

export interface GraphEdge {
  id: string;
  source_id: string;
  target_id: string;
  edge_type: string;
  description?: string;
}

export interface GraphNeighborEntry {
  node_id: string;
  node_slug: string | null;
  node_name: string;
  node_type: string;
  edge_type: string;
  direction: "outgoing" | "incoming";
  depth: number;
}

export interface NeighborsResponse {
  center_node: GraphNode;
  neighbors: GraphNeighborEntry[];
  total_neighbors: number;
}

export interface GraphPathStep {
  node_id: string;
  node_slug: string | null;
  node_name: string;
  node_type: string;
  edge_type: string | null;
}

export interface PathResponse {
  source_slug: string;
  target_slug: string;
  path_length: number;
  path: GraphPathStep[];
}

export const graphApi = {
  getNodes: async (search?: string) => {
    const res = await request<RawGraphNodesResponse>(
      `/graph/nodes${search ? `?search=${encodeURIComponent(search)}` : ""}`
    );
    return {
      total: res.total,
      nodes: (res.nodes || []).map((n) => ({
        ...n,
        type: (n.type as string) || (n.node_type as string) || "",
      })) as GraphNode[],
    };
  },

  getNeighbors: async (slug: string, depth: number = 1) => {
    const res = await request<{ center_node: Record<string, unknown>; neighbors: Record<string, unknown>[]; total_neighbors: number }>(
      `/graph/neighbors/${slug}?depth=${depth}`
    );
    const centerNode = res.center_node;
    return {
      center_node: {
        ...centerNode,
        type: (centerNode.type as string) || (centerNode.node_type as string) || "",
      } as GraphNode,
      neighbors: (res.neighbors || []).map((n) => ({
        node_id: n.node_id,
        node_slug: (n.node_slug as string) || (n.slug as string) || "",
        node_name: n.node_name,
        node_type: (n.node_type as string) || (n.type as string) || "",
        edge_type: (n.edge_type as string) || "",
        direction: (n.direction as "outgoing" | "incoming") || "outgoing",
        weight: n.weight,
      })),
      total_neighbors: res.total_neighbors || 0,
    };
  },

  findPath: (source: string, target: string) =>
    request<PathResponse>(
      `/graph/path?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`
    ),

  createNode: (node: { node_type: string; name: string; description?: string }) =>
    request<GraphNode>("/graph/nodes", {
      method: "POST",
      body: JSON.stringify(node),
    }),

  createEdge: (edge: { source_id: string; target_id: string; edge_type: string; weight?: number; description?: string }) =>
    request<GraphEdge>("/graph/edges", {
      method: "POST",
      body: JSON.stringify(edge),
    }),

  getEdges: async (page: number = 1, pageSize: number = 500) =>
    request<RawGraphEdgesResponse>(
      `/graph/edges?page=${page}&page_size=${pageSize}`
    ),
};

// ========================
// Brain Builder API
// ========================

// Backend BrainBuildJob statuses: pending | running | awaiting_review | done | failed
export type BrainJobStatus = "pending" | "running" | "awaiting_review" | "done" | "partial" | "failed";

export interface BrainJob {
  id: string;
  status: BrainJobStatus;
  source_document_ids: string[] | null;
  // Alias: backend uses source_document_ids, kept for compatibility
  document_ids?: string[];
  created_at: string;
  updated_at?: string;
  error_message?: string | null;
  result_summary?: Record<string, unknown> | null;
}

// Backend BrainReviewPlan statuses: pending | approved | rejected | partial
export type BrainPlanStatus = "pending" | "approved" | "rejected" | "partial";

export interface BrainPlan {
  id: string;
  job_id: string;
  status: BrainPlanStatus;
  proposed_pages: unknown[];
  created_at: string;
  notes?: string;
  admin_notes?: string | null;
}

/**
 * Transform a raw BrainBuildJobResponse from backend to BrainJob shape.
 * Backend uses source_document_ids; maintain document_ids alias for compatibility.
 */
function transformBrainJob(raw: RawBrainJob): BrainJob {
  return {
    id: raw.id,
    status: raw.status as BrainJobStatus,
    source_document_ids: raw.source_document_ids,
    document_ids: raw.source_document_ids,
    created_at: raw.created_at,
    updated_at: raw.updated_at,
    error_message: raw.error_message,
    result_summary: raw.result_summary,
  };
}

/**
 * Transform a raw BrainReviewPlanResponse to BrainPlan shape.
 */
function transformBrainPlan(raw: RawBrainPlan): BrainPlan {
  return {
    id: raw.id,
    job_id: raw.job_id,
    status: raw.status as BrainPlanStatus,
    proposed_pages: raw.proposed_pages || [],
    created_at: raw.created_at,
    notes: raw.admin_notes,
    admin_notes: raw.admin_notes,
  };
}

export const brainApi = {
  startJob: async (document_ids: string[]) => {
    const raw = await request<RawBrainJob>("/brain/jobs", {
      method: "POST",
      body: JSON.stringify({ document_ids }),
    });
    return transformBrainJob(raw);
  },

  getJobs: async () => {
    const raw = await request<RawBrainJobsResponse>("/brain/jobs");
    return {
      jobs: (raw.jobs || []).map(transformBrainJob),
    };
  },

  getPlans: async () => {
    const raw = await request<RawBrainPlansResponse>("/brain/plans");
    return {
      plans: (raw.plans || []).map(transformBrainPlan),
    };
  },

  approvePlan: async (id: string, notes?: string) => {
    const raw = await request<RawBrainPlan>(`/brain/plans/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    });
    return transformBrainPlan(raw);
  },

  rejectPlan: async (id: string, notes?: string) => {
    const raw = await request<RawBrainPlan>(`/brain/plans/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    });
    return transformBrainPlan(raw);
  },
};

// ========================
// HITL Graph Drafts API
// ========================
export interface KnowledgeDraft {
  id: string;
  change_type: "add_node" | "add_edge" | "update_node" | "contradiction";
  status: "pending" | "approved" | "rejected";
  draft_data: Record<string, any>;
  source_info?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export const graphDraftsApi = {
  list: async (params?: { status?: string }) => {
    return request<KnowledgeDraft[]>("/graph/drafts" + buildQuery(params || {}));
  },
  review: async (id: string, action: { status: "approved" | "rejected"; comment?: string }) => {
    return request<KnowledgeDraft>(`/graph/drafts/${id}/review`, {
      method: "POST",
      body: JSON.stringify(action),
    });
  },
};
