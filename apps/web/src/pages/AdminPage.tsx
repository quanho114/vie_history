import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { motion, AnimatePresence } from "framer-motion"
import {
  FileText,
  TrendingUp,
  CheckCircle,
  XCircle,
  Loader2,
  Database,
  Activity,
  GitBranch,
  Users,
  Key,
  ShieldAlert,
  Clock,
  ExternalLink,
  RefreshCw,
  Trash2,
  X,
  FileCode,
  Sliders,
  ChevronRight,
  ChevronLeft,
  FileSearch,
  Settings,
  AlertTriangle,
  FolderOpen,
  Cpu,
  BarChart3
} from "lucide-react"

interface Stats {
  documents: {
    total: number
    pending: number
    approved: number
    rejected: number
  }
  jobs: {
    total: number
    queued: number
    running: number
    failed: number
    done: number
  }
}

interface Bm25Stats {
  status: string
  num_chunks: number
}

interface QualityReport {
  average_quality_score: number
  documents_by_quality: {
    high: number
    medium: number
    low: number
  }
  top_documents: Array<{
    id: string
    title: string
    quality_score: number
  }>
}

interface AdminPendingDoc {
  id: string
  title: string
  status: string
  source_url?: string
  source_type?: string
  quality_score?: number
  created_at: string
  [key: string]: unknown
}

interface AdminIngestJob {
  id: string
  status: string
  source_input?: string
  source_type?: string
  stage?: string
  error_message?: string
  created_at: string
  finished_at?: string
  logs?: Array<{ timestamp: string; level: string; message: string }>
  [key: string]: unknown
}

interface AdminUser {
  id: string
  email: string
  username: string
  role: string
  created_at?: string
  [key: string]: unknown
}

interface AdminResetRequest {
  id: string
  user_id?: string
  email?: string
  status: string
  created_at: string
  [key: string]: unknown
}


export function AdminPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<"stats" | "pending_docs" | "jobs" | "users" | "reset_requests">("stats")

  // BM25 states
  const [bm25Stats, setBm25Stats] = useState<Bm25Stats | null>(null)
  const [isRebuildingBm25, setIsRebuildingBm25] = useState(false)
  const [bm25Message, setBm25Message] = useState("")

  // Quality Report states
  const [qualityReport, setQualityReport] = useState<QualityReport | null>(null)
  const [qualityLoading, setQualityLoading] = useState(false)

  // Pending Documents states
  const [pendingDocs, setPendingDocs] = useState<AdminPendingDoc[]>([])
  const [pendingTotal, setPendingTotal] = useState(0)
  const [pendingPage, setPendingPage] = useState(1)
  const [docsLoading, setDocsLoading] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState<AdminPendingDoc | null>(null)
  const [selectedDocMarkdown, setSelectedDocMarkdown] = useState<string | null>(null)
  const [loadingMarkdown, setLoadingMarkdown] = useState(false)
  const [actioningDocId, setActioningDocId] = useState<string | null>(null)

  // Ingestion Jobs states
  const [ingestJobs, setIngestJobs] = useState<AdminIngestJob[]>([])
  const [jobsLoading, setJobsLoading] = useState(false)
  const [jobFilterStatus, setJobFilterStatus] = useState<string>("")
  const [selectedJob, setSelectedJob] = useState<AdminIngestJob | null>(null)
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null)
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null)
  const [isDeletingAllJobs, setIsDeletingAllJobs] = useState(false)
  const [jobsPage, setJobsPage] = useState(1)
  const [jobsTotal, setJobsTotal] = useState(0)
  const jobsPageSize = 10

  // User management states
  const [users, setUsers] = useState<AdminUser[]>([])
  const [usersLoading, setUsersLoading] = useState(false)
  const [resettingUser, setResettingUser] = useState<AdminUser | null>(null)
  const [newPassword, setNewPassword] = useState("")
  const [resetMessage, setResetMessage] = useState("")
  const [resetError, setResetError] = useState("")

  // Reset requests states
  const [resetRequests, setResetRequests] = useState<AdminResetRequest[]>([])
  const [requestsLoading, setRequestsLoading] = useState(false)
  const [approvingRequest, setApprovingRequest] = useState<AdminResetRequest | null>(null)
  const [approvePassword, setApprovePassword] = useState("")
  const [approveMessage, setApproveMessage] = useState("")
  const [approveError, setApproveError] = useState("")

  const fetchStats = () => {
    fetch("/api/v1/admin/stats", {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error()
        return res.json()
      })
      .then(setStats)
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }

  const fetchBm25Stats = () => {
    fetch("/api/v1/admin/bm25/stats", {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error()
        return res.json()
      })
      .then(setBm25Stats)
      .catch(() => {})
  }

  const fetchQualityReport = () => {
    setQualityLoading(true)
    fetch("/api/v1/admin/quality-report", {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error()
        return res.json()
      })
      .then(setQualityReport)
      .catch(() => {})
      .finally(() => setQualityLoading(false))
  }

  const handleRebuildBm25 = () => {
    if (!confirm("Bạn có chắc chắn muốn xây dựng lại toàn bộ chỉ mục BM25?")) return
    setIsRebuildingBm25(true)
    setBm25Message("")
    fetch("/api/v1/admin/bm25/rebuild", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error("Thất bại")
        return res.json()
      })
      .then((data) => {
        setBm25Message(`Thành công! Đã lập chỉ mục lại ${data.num_chunks} phân đoạn.`)
        fetchBm25Stats()
        setTimeout(() => setBm25Message(""), 4000)
      })
      .catch((err) => {
        setBm25Message("Yêu cầu thất bại: " + err.message)
      })
      .finally(() => setIsRebuildingBm25(false))
  }

  const fetchUsers = () => {
    setUsersLoading(true)
    fetch("/api/v1/admin/users", {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) setUsers(data)
        else setUsers([])
      })
      .catch(() => setUsers([]))
      .finally(() => setUsersLoading(false))
  }

  const fetchResetRequests = () => {
    setRequestsLoading(true)
    fetch("/api/v1/admin/reset-requests", {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) setResetRequests(data)
        else setResetRequests([])
      })
      .catch(() => setResetRequests([]))
      .finally(() => setRequestsLoading(false))
  }

  const fetchPendingDocs = (page = 1) => {
    setDocsLoading(true)
    fetch(`/api/v1/documents?status=pending&page=${page}&page_size=10`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data && Array.isArray(data.documents)) {
          setPendingDocs(data.documents)
          setPendingTotal(data.total || 0)
        } else {
          setPendingDocs([])
          setPendingTotal(0)
        }
      })
      .catch(() => {
        setPendingDocs([])
        setPendingTotal(0)
      })
      .finally(() => setDocsLoading(false))
  }

  const fetchDocMarkdown = (docId: string) => {
    setLoadingMarkdown(true)
    setSelectedDocMarkdown(null)
    fetch(`/api/v1/documents/${docId}/markdown`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        setSelectedDocMarkdown(data.markdown)
      })
      .catch(() => {})
      .finally(() => setLoadingMarkdown(false))
  }

  const handleApproveDoc = (docId: string) => {
    setActioningDocId(docId)
    fetch(`/api/v1/admin/documents/${docId}/approve`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error()
        fetchPendingDocs(pendingPage)
        fetchStats()
        if (selectedDoc?.id === docId) {
          setSelectedDoc(null)
        }
      })
      .catch(() => alert("Duyệt tài liệu thất bại"))
      .finally(() => setActioningDocId(null))
  }

  const handleRejectDoc = (docId: string) => {
    if (!confirm("Bạn có chắc chắn muốn từ chối tài liệu này không?")) return
    setActioningDocId(docId)
    fetch(`/api/v1/admin/documents/${docId}/reject`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error()
        fetchPendingDocs(pendingPage)
        fetchStats()
        if (selectedDoc?.id === docId) {
          setSelectedDoc(null)
        }
      })
      .catch(() => alert("Từ chối tài liệu thất bại"))
      .finally(() => setActioningDocId(null))
  }

  const fetchIngestJobs = (page = 1, filter = "") => {
    setJobsLoading(true)
    const statusParam = filter ? `&status=${filter}` : ""
    fetch(`/api/v1/ingest/jobs?page=${page}&page_size=${jobsPageSize}${statusParam}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data && Array.isArray(data.jobs)) {
          setIngestJobs(data.jobs)
          setJobsTotal(data.total || 0)
        } else {
          setIngestJobs([])
          setJobsTotal(0)
        }
      })
      .catch(() => {
        setIngestJobs([])
        setJobsTotal(0)
      })
      .finally(() => setJobsLoading(false))
  }

  const handleRetryJob = (jobId: string) => {
    setRetryingJobId(jobId)
    fetch(`/api/v1/ingest/jobs/${jobId}/retry`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error()
        fetchIngestJobs(jobsPage, jobFilterStatus)
        fetchStats()
      })
      .catch(() => alert("Thao tác chạy lại thất bại"))
      .finally(() => setRetryingJobId(null))
  }

  const handleDeleteJob = (jobId: string) => {
    if (!confirm("Xóa lịch sử tiến trình này?")) return
    setDeletingJobId(jobId)
    fetch(`/api/v1/ingest/jobs/${jobId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error()
        fetchIngestJobs(jobsPage, jobFilterStatus)
        fetchStats()
        if (selectedJob?.id === jobId) setSelectedJob(null)
      })
      .catch(() => alert("Xóa thất bại"))
      .finally(() => setDeletingJobId(null))
  }

  const handleDeleteAllJobs = () => {
    if (!confirm("Hành động này sẽ xóa toàn bộ lịch sử. Xác nhận?")) return
    setIsDeletingAllJobs(true)
    fetch("/api/v1/ingest/jobs", {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error()
        setJobsPage(1)
        fetchIngestJobs(1, jobFilterStatus)
        fetchStats()
      })
      .catch(() => alert("Xóa toàn bộ thất bại"))
      .finally(() => setIsDeletingAllJobs(false))
  }

  const handleApproveRequest = (e: React.FormEvent) => {
    e.preventDefault()
    if (!approvingRequest || approvePassword.length < 8) return

    setApproveError("")
    setApproveMessage("")

    fetch(`/api/v1/admin/reset-requests/${approvingRequest.id}/approve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
      body: JSON.stringify({ new_password: approvePassword }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json()
          throw new Error(data.detail || "Phê duyệt thất bại")
        }
        return res.json()
      })
      .then((data) => {
        setApproveMessage(data.message || "Đặt lại mật khẩu thành công!")
        setApprovePassword("")
        fetchResetRequests()
        setTimeout(() => {
          setApprovingRequest(null)
          setApproveMessage("")
        }, 1500)
      })
      .catch((err) => {
        setApproveError(err.message)
      })
  }

  const handleRejectRequest = (requestId: string) => {
    if (!confirm("Từ chối yêu cầu khôi phục này?")) return

    fetch(`/api/v1/admin/reset-requests/${requestId}/reject`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json()
          throw new Error(data.detail || "Từ chối thất bại")
        }
        return res.json()
      })
      .then(() => {
        fetchResetRequests()
      })
      .catch((err) => {
        alert(err.message)
      })
  }

  const handleResetPassword = (e: React.FormEvent) => {
    e.preventDefault()
    if (!resettingUser || newPassword.length < 8) return

    setResetError("")
    setResetMessage("")

    fetch(`/api/v1/admin/users/${resettingUser.id}/reset-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
      body: JSON.stringify({ new_password: newPassword }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json()
          throw new Error(data.detail || "Đặt lại mật khẩu thất bại")
        }
        return res.json()
      })
      .then(() => {
        setResetMessage(`Đặt lại mật khẩu thành công cho ${resettingUser.username}!`);
        setNewPassword("")
        setTimeout(() => {
          setResettingUser(null)
          setResetMessage("")
        }, 1500)
      })
      .catch((err) => {
        setResetError(err.message)
      })
  }

  useEffect(() => {
    fetchStats()
    fetchResetRequests()
  }, [])

  useEffect(() => {
    if (activeTab === "stats") {
      fetchStats()
      fetchBm25Stats()
      fetchQualityReport()
    } else if (activeTab === "users") {
      fetchUsers()
    } else if (activeTab === "reset_requests") {
      fetchResetRequests()
    } else if (activeTab === "pending_docs") {
      setPendingPage(1)
      fetchPendingDocs(1)
    } else if (activeTab === "jobs") {
      setJobsPage(1)
      fetchIngestJobs(1, jobFilterStatus)
    }
  }, [activeTab])

  useEffect(() => {
    if (activeTab === "pending_docs") {
      fetchPendingDocs(pendingPage)
    }
  }, [pendingPage])

  useEffect(() => {
    if (activeTab === "jobs") {
      fetchIngestJobs(jobsPage, jobFilterStatus)
    }
  }, [jobsPage, jobFilterStatus])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-[#faf8f4]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-[#cc785c]" />
          <p className="text-xs text-[#8e8b82] font-serif italic">Đang tải cấu hình quản trị...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-[#faf8f4] selection:bg-[#cc785c]/10 selection:text-[#cc785c] p-6 font-sans">
      
      <div className="flex-1 flex flex-col min-h-0 bg-transparent">
        
        {/* Editorial Header */}
        <header className="pb-6 border-b border-[#e6dfd8] flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-1">
            <h2 className="text-2xl font-serif font-bold text-[#141413] tracking-wide flex items-center gap-2">
              Ban Quản Trị
            </h2>
            <p className="text-[10px] text-[#8e8b82] tracking-[0.25em] uppercase font-bold">
              HỆ THỐNG TRI THỨC LỊCH SỬ
            </p>
          </div>

          {/* Minimalist Bottom-border Active Tab Switcher */}
          <div className="flex items-center gap-6 overflow-x-auto scrollbar-none">
            <button
              onClick={() => setActiveTab("stats")}
              className={`pb-2 text-xs font-semibold tracking-wide transition-all duration-200 cursor-pointer border-0 border-b-2 bg-transparent ${
                activeTab === "stats"
                  ? "border-[#cc785c] text-[#cc785c] font-serif italic"
                  : "border-transparent text-[#6c6a64] hover:text-[#141413]"
              }`}
            >
              Tổng quan
            </button>
            
            <button
              onClick={() => setActiveTab("pending_docs")}
              className={`pb-2 text-xs font-semibold tracking-wide transition-all duration-200 cursor-pointer border-0 border-b-2 bg-transparent flex items-center gap-1.5 ${
                activeTab === "pending_docs"
                  ? "border-[#cc785c] text-[#cc785c] font-serif italic"
                  : "border-transparent text-[#6c6a64] hover:text-[#141413]"
              }`}
            >
              <span>Chờ duyệt</span>
              {stats?.documents && stats.documents.pending > 0 && (
                <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-[#cc785c] px-1 text-[8px] font-bold text-white">
                  {stats.documents.pending}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab("jobs")}
              className={`pb-2 text-xs font-semibold tracking-wide transition-all duration-200 cursor-pointer border-0 border-b-2 bg-transparent flex items-center gap-1.5 ${
                activeTab === "jobs"
                  ? "border-[#cc785c] text-[#cc785c] font-serif italic"
                  : "border-transparent text-[#6c6a64] hover:text-[#141413]"
              }`}
            >
              <span>Tiến trình Ingest</span>
              {stats?.jobs && stats.jobs.running > 0 && (
                <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-[#4a7b9c] px-1 text-[8px] font-bold text-white animate-pulse">
                  {stats.jobs.running}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab("users")}
              className={`pb-2 text-xs font-semibold tracking-wide transition-all duration-200 cursor-pointer border-0 border-b-2 bg-transparent ${
                activeTab === "users"
                  ? "border-[#cc785c] text-[#cc785c] font-serif italic"
                  : "border-transparent text-[#6c6a64] hover:text-[#141413]"
              }`}
            >
              Thành viên
            </button>

            <button
              onClick={() => setActiveTab("reset_requests")}
              className={`pb-2 text-xs font-semibold tracking-wide transition-all duration-200 cursor-pointer border-0 border-b-2 bg-transparent flex items-center gap-1.5 ${
                activeTab === "reset_requests"
                  ? "border-[#cc785c] text-[#cc785c] font-serif italic"
                  : "border-transparent text-[#6c6a64] hover:text-[#141413]"
              }`}
            >
              <span>Yêu cầu MK</span>
              {resetRequests.filter((r) => r.status === "pending").length > 0 && (
                <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-[#cc785c] px-1 text-[8px] font-bold text-white">
                  {resetRequests.filter((r) => r.status === "pending").length}
                </span>
              )}
            </button>
          </div>

          <Link
            to="/graph/drafts/review"
            className="flex items-center gap-1.5 px-4 py-2 border border-[#cc785c]/35 text-[#cc785c] hover:bg-[#cc785c]/5 text-xs font-semibold rounded-xl transition-all cursor-pointer bg-white active:scale-[0.98] flex-shrink-0"
          >
            <GitBranch className="w-3.5 h-3.5" /> Bảng Tiến hóa Tri thức (HITL)
          </Link>
        </header>

        {/* Workspace Body */}
        <div className="flex-1 overflow-y-auto pt-6 min-h-0">
          
          {/* TAB 1: SYSTEM GENERAL STATS (BENTO-STYLE GRID) */}
          {activeTab === "stats" && (
            <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 items-start pb-8">
              
              {/* LEFT COLUMN: Stat Modules & BM25 Management (7/12 width) */}
              <div className="lg:col-span-7 space-y-8">
                
                {/* Module A: Knowledge Archive Stats (Borderless column layout) */}
                <div className="bg-white border border-[#e6dfd8] rounded-2xl p-6 shadow-[0_2px_12px_rgba(20,20,19,0.015)]">
                  <div className="flex items-center gap-2 border-b border-[#e6dfd8]/40 pb-3.5 mb-5">
                    <FolderOpen className="w-4 h-4 text-[#cc785c]" />
                    <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-[#6c6a64]">
                      KHO LƯU TRỮ TRI THỨC
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-4 divide-x divide-[#e6dfd8]/50">
                    <div className="px-3 first:pl-0">
                      <span className="text-3xl font-serif font-bold text-[#141413] block tracking-tight">
                        {stats?.documents.total || 0}
                      </span>
                      <span className="text-[9px] uppercase tracking-wider text-[#8e8b82] font-semibold mt-1 block">
                        Tổng số
                      </span>
                    </div>
                    <div className="px-3">
                      <span className="text-3xl font-serif font-bold text-[#4c7a5c] block tracking-tight">
                        {stats?.documents.approved || 0}
                      </span>
                      <span className="text-[9px] uppercase tracking-wider text-[#8e8b82] font-semibold mt-1 block">
                        Đã duyệt
                      </span>
                    </div>
                    <div className="px-3">
                      <span className="text-3xl font-serif font-bold text-[#b88a44] block tracking-tight">
                        {stats?.documents.pending || 0}
                      </span>
                      <span className="text-[9px] uppercase tracking-wider text-[#8e8b82] font-semibold mt-1 block">
                        Đang chờ
                      </span>
                    </div>
                    <div className="px-3 last:pr-0">
                      <span className="text-3xl font-serif font-bold text-[#b55a4c] block tracking-tight">
                        {stats?.documents.rejected || 0}
                      </span>
                      <span className="text-[9px] uppercase tracking-wider text-[#8e8b82] font-semibold mt-1 block">
                        Từ chối
                      </span>
                    </div>
                  </div>
                </div>

                {/* Module B: Ingestion Pipeline Queue Stats (Borderless column layout) */}
                <div className="bg-white border border-[#e6dfd8] rounded-2xl p-6 shadow-[0_2px_12px_rgba(20,20,19,0.015)]">
                  <div className="flex items-center gap-2 border-b border-[#e6dfd8]/40 pb-3.5 mb-5">
                    <Cpu className="w-4 h-4 text-[#4a7b9c]" />
                    <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-[#6c6a64]">
                      TIẾN TRÌNH THU THẬP & INGESTION
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-5 divide-x divide-[#e6dfd8]/50">
                    <div className="px-2 first:pl-0">
                      <span className="text-2xl md:text-3xl font-serif font-bold text-[#141413] block tracking-tight">
                        {stats?.jobs.total || 0}
                      </span>
                      <span className="text-[9px] uppercase tracking-wider text-[#8e8b82] font-semibold mt-1 block">
                        Tổng số
                      </span>
                    </div>
                    <div className="px-2">
                      <span className="text-2xl md:text-3xl font-serif font-bold text-[#4c7a5c] block tracking-tight">
                        {stats?.jobs.done || 0}
                      </span>
                      <span className="text-[9px] uppercase tracking-wider text-[#8e8b82] font-semibold mt-1 block">
                        Hoàn thành
                      </span>
                    </div>
                    <div className="px-2">
                      <span className="text-2xl md:text-3xl font-serif font-bold text-[#4a7b9c] block tracking-tight">
                        {stats?.jobs.running || 0}
                      </span>
                      <span className="text-[9px] uppercase tracking-wider text-[#8e8b82] font-semibold mt-1 block">
                        Đang chạy
                      </span>
                    </div>
                    <div className="px-2">
                      <span className="text-2xl md:text-3xl font-serif font-bold text-[#b88a44] block tracking-tight">
                        {stats?.jobs.queued || 0}
                      </span>
                      <span className="text-[9px] uppercase tracking-wider text-[#8e8b82] font-semibold mt-1 block">
                        Đang đợi
                      </span>
                    </div>
                    <div className="px-2 last:pr-0">
                      <span className="text-2xl md:text-3xl font-serif font-bold text-[#b55a4c] block tracking-tight">
                        {stats?.jobs.failed || 0}
                      </span>
                      <span className="text-[9px] uppercase tracking-wider text-[#8e8b82] font-semibold mt-1 block">
                        Gặp lỗi
                      </span>
                    </div>
                  </div>
                </div>

                {/* Module C: BM25 Search Index Control */}
                <div className="bg-white border border-[#e6dfd8] rounded-2xl p-6 shadow-[0_2px_12px_rgba(20,20,19,0.015)]">
                  <div className="flex items-center justify-between border-b border-[#e6dfd8]/40 pb-3.5 mb-4">
                    <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-[#141413] flex items-center gap-2">
                      <Sliders className="w-4 h-4 text-[#cc785c]" />
                      BỘ CHỈ MỤC TÌM KIẾM BM25
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[8px] font-bold uppercase tracking-widest ${
                      bm25Stats?.status === "ready" 
                        ? "bg-[#4c7a5c]/10 text-[#4c7a5c] border border-[#4c7a5c]/20" 
                        : "bg-[#b88a44]/10 text-[#b88a44] border border-[#b88a44]/20"
                    }`}>
                      {bm25Stats?.status === "ready" ? "Sẵn sàng" : "Chưa lập"}
                    </span>
                  </div>

                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mt-4">
                    <div className="space-y-1.5 max-w-md">
                      <p className="text-xs text-[#6c6a64] leading-relaxed">
                        Chỉ mục từ khóa BM25 lưu trữ cục bộ. Hãy xây dựng lại chỉ mục khi nạp tài liệu mới để đồng bộ kết quả tìm kiếm chính xác nhất.
                      </p>
                      <div className="text-[10px] text-[#8e8b82]">
                        Tổng số phân đoạn (Chunks): <b className="font-mono text-neutral-800">{bm25Stats?.num_chunks ?? 0}</b>
                      </div>
                    </div>

                    <button
                      onClick={handleRebuildBm25}
                      disabled={isRebuildingBm25}
                      className="px-4 py-2.5 border border-[#cc785c] text-[#cc785c] hover:bg-[#cc785c]/5 text-xs font-semibold rounded-xl disabled:opacity-50 transition-all cursor-pointer bg-white flex items-center justify-center gap-2 flex-shrink-0"
                    >
                      {isRebuildingBm25 ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          Đang xử lý...
                        </>
                      ) : (
                        <>
                          <RefreshCw className="w-3.5 h-3.5" />
                          Xây dựng lại chỉ mục
                        </>
                      )}
                    </button>
                  </div>

                  {bm25Message && (
                    <p className="text-[10px] text-center font-medium mt-3 text-[#cc785c] animate-pulse">
                      {bm25Message}
                    </p>
                  )}
                </div>

              </div>

              {/* RIGHT COLUMN: Quality Diagnostics Report & Top Docs (5/12 width) */}
              <div className="lg:col-span-5">
                <div className="bg-white border border-[#e6dfd8] rounded-2xl p-6 shadow-[0_2px_12px_rgba(20,20,19,0.015)]">
                  
                  <div className="flex items-center justify-between border-b border-[#e6dfd8]/40 pb-3.5 mb-5">
                    <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-[#141413] flex items-center gap-2">
                      <BarChart3 className="w-4 h-4 text-[#4c7a5c]" />
                      PHÂN TÍCH CHẤT LƯỢNG DỮ LIỆU
                    </span>
                    <button 
                      onClick={fetchQualityReport} 
                      disabled={qualityLoading}
                      className="text-[#6c6a64] hover:text-[#cc785c] cursor-pointer bg-transparent border-0 outline-none transition-colors"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${qualityLoading ? "animate-spin" : ""}`} />
                    </button>
                  </div>

                  {qualityReport ? (
                    <div className="space-y-6">
                      
                      {/* Premium score display card */}
                      <div className="flex items-center gap-6 bg-[#faf8f4] p-5 border border-[#e8e4dc] rounded-2xl">
                        <div className="text-center flex-shrink-0">
                          <span className="text-4xl font-serif font-bold text-[#141413] block">
                            {qualityReport.average_quality_score.toFixed(2)}
                          </span>
                          <span className="text-[8px] uppercase tracking-widest text-[#8e8b82] font-bold mt-1 block">
                            Điểm TB
                          </span>
                        </div>

                        <div className="h-10 w-[1px] bg-[#e6dfd8] flex-shrink-0" />

                        <div className="space-y-2 flex-1">
                          <span className="block text-[8px] uppercase tracking-wider text-[#8e8b82] font-bold">
                            PHÂN PHỐI CHẤT LƯỢNG (MẪU {qualityReport.documents_by_quality.high + qualityReport.documents_by_quality.medium + qualityReport.documents_by_quality.low} BẢN DUYỆT)
                          </span>
                          
                          <div className="space-y-1">
                            <div className="h-2 rounded-full overflow-hidden flex bg-[#e6dfd8]/50">
                              {(() => {
                                const total = qualityReport.documents_by_quality.high + qualityReport.documents_by_quality.medium + qualityReport.documents_by_quality.low || 1
                                const highPct = (qualityReport.documents_by_quality.high / total) * 100
                                const medPct = (qualityReport.documents_by_quality.medium / total) * 100
                                const lowPct = (qualityReport.documents_by_quality.low / total) * 100
                                return (
                                  <>
                                    <div style={{ width: `${highPct}%` }} className="bg-[#4c7a5c]" title="Tốt (>= 0.8)" />
                                    <div style={{ width: `${medPct}%` }} className="bg-[#b88a44]" title="Đạt (0.5 - 0.8)" />
                                    <div style={{ width: `${lowPct}%` }} className="bg-[#b55a4c]" title="Kém (< 0.5)" />
                                  </>
                                )
                              })()}
                            </div>
                            
                            <div className="flex items-center justify-between text-[8px] text-[#6c6a64] font-semibold font-mono">
                              <span className="flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-[#4c7a5c]" />
                                Tốt: {qualityReport.documents_by_quality.high}
                              </span>
                              <span className="flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-[#b88a44]" />
                                Đạt: {qualityReport.documents_by_quality.medium}
                              </span>
                              <span className="flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-[#b55a4c]" />
                                Kém: {qualityReport.documents_by_quality.low}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Top Documents List */}
                      <div className="space-y-4">
                        <span className="text-[9px] uppercase font-bold text-[#8e8b82] tracking-widest block border-b border-[#e6dfd8]/40 pb-2">
                          TOP 5 TÀI LIỆU UY TÍN CAO NHẤT
                        </span>

                        <div className="divide-y divide-[#e6dfd8]/30">
                          {qualityReport.top_documents && qualityReport.top_documents.length > 0 ? (
                            qualityReport.top_documents.slice(0, 5).map((doc, idx) => (
                              <div key={doc.id} className="flex items-center justify-between gap-4 py-2.5 text-xs first:pt-0 last:pb-0">
                                <span className="truncate font-serif italic text-[#141413] hover:text-[#cc785c] transition-colors flex-1">
                                  {idx + 1}. {doc.title}
                                </span>
                                <span className="font-mono bg-[#4c7a5c]/5 text-[#4c7a5c] px-2 py-0.5 rounded border border-[#4c7a5c]/10 text-[9px] font-bold">
                                  {doc.quality_score.toFixed(2)}
                                </span>
                              </div>
                            ))
                          ) : (
                            <p className="text-xs text-[#8e8b82] italic py-4">Không có tài liệu nào.</p>
                          )}
                        </div>
                      </div>

                    </div>
                  ) : (
                    <div className="py-16 text-center text-[#8e8b82] font-serif italic text-xs">
                      Không tải được dữ liệu phân tích.
                    </div>
                  )}

                </div>
              </div>

            </div>
          )}

          {/* TAB 2: PENDING DOCUMENTS LIST */}
          {activeTab === "pending_docs" && (
            <div className="space-y-4 max-w-6xl mx-auto">
              <div className="flex items-center justify-between border-b border-[#e6dfd8] pb-4">
                <h3 className="font-serif text-base font-semibold text-[#141413] flex items-center gap-2">
                  <span className="text-[#cc785c] text-sm">✦</span>
                  Phê duyệt tài liệu lịch sử nạp mới ({pendingTotal})
                </h3>
                <button 
                  onClick={() => fetchPendingDocs(pendingPage)}
                  className="flex items-center gap-2 text-xs text-[#6c6a64] hover:text-[#141413] border border-[#e6dfd8] px-3.5 py-2 rounded-xl bg-white cursor-pointer transition-colors shadow-xs"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Tải lại
                </button>
              </div>

              {docsLoading ? (
                <div className="flex items-center justify-center py-20">
                  <Loader2 className="w-6 h-6 animate-spin text-[#cc785c]" />
                </div>
              ) : (
                <div className="bg-white border border-[#e6dfd8] rounded-2xl overflow-hidden shadow-xs">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-[#e6dfd8] bg-[#efe9de]/20 text-[9px] font-bold uppercase tracking-widest text-[#6c6a64]">
                          <th className="py-4 px-6">Tên tài liệu</th>
                          <th className="py-4 px-6">Nguồn / Loại</th>
                          <th className="py-4 px-6">Độ uy tín</th>
                          <th className="py-4 px-6">Ngày gửi</th>
                          <th className="py-4 px-6 text-right">Hành động</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#e6dfd8]/40 text-xs text-[#141413]">
                        {pendingDocs.map((doc) => (
                          <tr key={doc.id} className="hover:bg-[#efe9de]/10 transition-colors group">
                            <td className="py-4 px-6 max-w-sm">
                              <button
                                onClick={() => {
                                  setSelectedDoc(doc)
                                  fetchDocMarkdown(doc.id)
                                }}
                                className="font-medium text-[#141413] hover:text-[#cc785c] hover:underline text-left block truncate w-full outline-none border-0 bg-transparent cursor-pointer font-serif italic text-base"
                              >
                                {doc.title}
                              </button>
                            </td>
                            <td className="py-4 px-6 text-[#6c6a64]">
                              <div className="flex items-center gap-1.5">
                                <span className="truncate max-w-[120px] font-medium">{doc.source_domain || "-"}</span>
                                <span className="bg-[#cc785c]/5 text-[#cc785c] text-[8px] px-1.5 py-0.5 rounded-md uppercase font-bold tracking-widest border border-[#cc785c]/10">
                                  {doc.source_type}
                                </span>
                              </div>
                            </td>
                            <td className="py-4 px-6">
                              <span className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded-md ${
                                doc.quality_score >= 0.8 
                                  ? "bg-[#4c7a5c]/5 text-[#4c7a5c] border border-[#4c7a5c]/10" 
                                  : doc.quality_score >= 0.5
                                  ? "bg-[#b88a44]/5 text-[#b88a44] border border-[#b88a44]/10"
                                  : "bg-[#b55a4c]/5 text-[#b55a4c] border border-[#b55a4c]/10"
                              }`}>
                                {doc.quality_score.toFixed(2)}
                              </span>
                            </td>
                            <td className="py-4 px-6 text-[#8e8b82] font-serif italic">
                              {new Date(doc.created_at).toLocaleDateString("vi-VN")}
                            </td>
                            <td className="py-4 px-6 text-right space-x-2">
                              <button
                                onClick={() => {
                                  setSelectedDoc(doc)
                                  fetchDocMarkdown(doc.id)
                                }}
                                className="inline-flex items-center gap-1 px-3 py-2 border border-[#e6dfd8] text-[#6c6a64] hover:bg-[#efe9de]/30 rounded-xl text-xs font-semibold cursor-pointer bg-white transition-colors"
                              >
                                <FileSearch size={12} /> Xem
                              </button>
                              <button
                                onClick={() => handleApproveDoc(doc.id)}
                                disabled={actioningDocId === doc.id}
                                className="inline-flex items-center gap-1 px-3.5 py-2 bg-[#4c7a5c] text-white hover:bg-[#3d624a] rounded-xl text-xs font-semibold cursor-pointer border-0 transition-colors shadow-xs"
                              >
                                {actioningDocId === doc.id ? (
                                  <Loader2 size={12} className="animate-spin" />
                                ) : (
                                  "Duyệt"
                                )}
                              </button>
                              <button
                                onClick={() => handleRejectDoc(doc.id)}
                                disabled={actioningDocId === doc.id}
                                className="inline-flex items-center gap-1 px-3 py-2 border border-[#e6dfd8] text-[#b55a4c] hover:border-[#b55a4c] hover:bg-[#b55a4c]/5 rounded-xl text-xs font-semibold cursor-pointer bg-white transition-colors"
                              >
                                Từ chối
                              </button>
                            </td>
                          </tr>
                        ))}
                        {pendingDocs.length === 0 && (
                          <tr>
                            <td colSpan={5} className="py-16 text-center text-[#8e8b82] font-serif italic text-sm">
                              Không có tài liệu nào đang chờ duyệt.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  {pendingTotal > 10 && (
                    <div className="flex items-center justify-between border-t border-[#e6dfd8] px-6 py-4 bg-[#efe9de]/10">
                      <span className="text-xs text-[#6c6a64]">
                        Hiển thị trang {pendingPage} trên {Math.ceil(pendingTotal / 10)}
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          disabled={pendingPage === 1}
                          onClick={() => setPendingPage((p) => Math.max(1, p - 1))}
                          className="p-1.5 rounded-lg border border-[#e6dfd8] hover:bg-neutral-50 disabled:opacity-30 cursor-pointer bg-white"
                        >
                          <ChevronLeft className="w-4 h-4" />
                        </button>
                        <button
                          disabled={pendingPage >= Math.ceil(pendingTotal / 10)}
                          onClick={() => setPendingPage((p) => p + 1)}
                          className="p-1.5 rounded-lg border border-[#e6dfd8] hover:bg-neutral-50 disabled:opacity-30 cursor-pointer bg-white"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: INGESTION JOBS LIST */}
          {activeTab === "jobs" && (
            <div className="space-y-4 max-w-6xl mx-auto">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#e6dfd8] pb-4">
                <div className="flex flex-wrap items-center gap-3">
                  <h3 className="font-serif text-base font-semibold text-[#141413] flex items-center gap-2">
                    <span className="text-[#cc785c] text-sm">✦</span>
                    Tiến trình Ingestion nạp tự động ({jobsTotal})
                  </h3>
                  
                  <select
                    value={jobFilterStatus}
                    onChange={(e) => {
                      setJobFilterStatus(e.target.value)
                      setJobsPage(1)
                    }}
                    className="bg-white border border-[#e6dfd8] text-xs font-semibold rounded-xl py-2 px-3 text-[#6c6a64] focus:border-[#cc785c] outline-none transition-colors shadow-xs"
                  >
                    <option value="">Tất cả trạng thái</option>
                    <option value="queued">Đang chờ (Queued)</option>
                    <option value="running">Đang chạy (Running)</option>
                    <option value="done">Hoàn thành (Done)</option>
                    <option value="failed">Thất bại (Failed)</option>
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <button 
                    onClick={() => fetchIngestJobs(jobsPage, jobFilterStatus)}
                    className="flex items-center gap-2 text-xs text-[#6c6a64] hover:text-[#141413] border border-[#e6dfd8] px-3.5 py-2 rounded-xl bg-white cursor-pointer transition-colors shadow-xs"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Tải lại
                  </button>
                  <button
                    onClick={handleDeleteAllJobs}
                    disabled={isDeletingAllJobs}
                    className="flex items-center gap-2 text-xs text-[#b55a4c] hover:bg-[#b55a4c]/5 border border-[#b55a4c]/20 px-3.5 py-2 rounded-xl bg-white cursor-pointer transition-colors shadow-xs"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Xóa tất cả lịch sử
                  </button>
                </div>
              </div>

              {jobsLoading ? (
                <div className="flex items-center justify-center py-20">
                  <Loader2 className="w-6 h-6 animate-spin text-[#cc785c]" />
                </div>
              ) : (
                <div className="bg-white border border-[#e6dfd8] rounded-2xl overflow-hidden shadow-xs">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-[#e6dfd8] bg-[#efe9de]/20 text-[9px] font-bold uppercase tracking-widest text-[#6c6a64]">
                          <th className="py-4 px-6">Nguồn Ingest (URL / Tên tệp)</th>
                          <th className="py-4 px-6">Loại</th>
                          <th className="py-4 px-6">Trạng thái</th>
                          <th className="py-4 px-6">Giai đoạn</th>
                          <th className="py-4 px-6">Ngày khởi tạo</th>
                          <th className="py-4 px-6 text-right">Thao tác</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#e6dfd8]/40 text-xs text-[#141413]">
                        {ingestJobs.map((job) => (
                          <tr key={job.id} className="hover:bg-[#efe9de]/10 transition-colors">
                            <td className="py-4 px-6 max-w-sm truncate" title={job.source_input}>
                              {job.source_type === "url" ? (
                                <a 
                                  href={job.source_input} 
                                  target="_blank" 
                                  rel="noreferrer" 
                                  className="text-[#cc785c] hover:underline font-medium inline-flex items-center gap-1"
                                >
                                  {job.source_input}
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              ) : (
                                <span className="font-medium font-serif italic text-base text-neutral-800">{job.source_input}</span>
                              )}
                            </td>
                            <td className="py-4 px-6 text-[#6c6a64]">
                              <span className="uppercase tracking-wider text-[8px] font-bold bg-[#efe9de] px-1.5 py-0.5 rounded-md text-[#6c6a64] border border-[#e6dfd8]/40">
                                {job.source_type}
                              </span>
                            </td>
                            <td className="py-4 px-6">
                              <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wide border ${
                                job.status === "done" 
                                  ? "bg-[#4c7a5c]/5 text-[#4c7a5c] border-[#4c7a5c]/20" 
                                  : job.status === "failed" 
                                  ? "bg-[#b55a4c]/5 text-[#b55a4c] border-[#b55a4c]/20"
                                  : job.status === "running"
                                  ? "bg-[#4a7b9c]/5 text-[#4a7b9c] border-[#4a7b9c]/20"
                                  : "bg-[#b88a44]/5 text-[#b88a44] border-[#b88a44]/20"
                              }`}>
                                {job.status === "running" && <Loader2 className="w-2.5 h-2.5 animate-spin" />}
                                {job.status}
                              </span>
                            </td>
                            <td className="py-4 px-6 font-mono text-[#8e8b82] text-[10px]">
                              {job.stage}
                            </td>
                            <td className="py-4 px-6 text-[#8e8b82] font-serif italic">
                              {new Date(job.created_at).toLocaleString("vi-VN", {
                                hour: "2-digit",
                                minute: "2-digit",
                                day: "2-digit",
                                month: "2-digit"
                              })}
                            </td>
                            <td className="py-4 px-6 text-right space-x-2">
                              <button
                                onClick={() => setSelectedJob(job)}
                                className="inline-flex items-center gap-1 px-3 py-2 border border-[#e6dfd8] text-[#6c6a64] hover:bg-neutral-50 rounded-xl text-xs font-semibold cursor-pointer bg-white transition-colors"
                              >
                                Logs
                              </button>
                              
                              {(job.status === "failed" || job.status === "done") && (
                                <button
                                  onClick={() => handleRetryJob(job.id)}
                                  disabled={retryingJobId === job.id}
                                  className="inline-flex items-center gap-1 px-3.5 py-2 bg-[#cc785c] text-white hover:bg-[#b8694d] rounded-xl text-xs font-semibold cursor-pointer border-0 transition-colors shadow-xs"
                                >
                                  {retryingJobId === job.id ? (
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                  ) : (
                                    "Chạy lại"
                                  )}
                                </button>
                              )}

                              <button
                                onClick={() => handleDeleteJob(job.id)}
                                disabled={deletingJobId === job.id}
                                className="inline-flex items-center justify-center p-2 border border-[#e6dfd8] text-[#b55a4c] hover:border-red-300 hover:bg-red-50 rounded-xl cursor-pointer bg-white transition-colors"
                              >
                                {deletingJobId === job.id ? (
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                  <Trash2 size={13} />
                                )}
                              </button>
                            </td>
                          </tr>
                        ))}
                        {ingestJobs.length === 0 && (
                          <tr>
                            <td colSpan={6} className="py-16 text-center text-[#8e8b82] font-serif italic text-sm">
                              Không tìm thấy tiến trình ingest nào.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  {jobsTotal > jobsPageSize && (
                    <div className="flex items-center justify-between border-t border-[#e6dfd8] px-6 py-4 bg-[#efe9de]/10">
                      <span className="text-xs text-[#6c6a64]">
                        Hiển thị trang {jobsPage} trên {Math.ceil(jobsTotal / jobsPageSize)}
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          disabled={jobsPage === 1}
                          onClick={() => setJobsPage((p) => Math.max(1, p - 1))}
                          className="p-1.5 rounded-lg border border-[#e6dfd8] hover:bg-neutral-50 disabled:opacity-30 cursor-pointer bg-white"
                        >
                          <ChevronLeft className="w-4 h-4" />
                        </button>
                        <button
                          disabled={jobsPage >= Math.ceil(jobsTotal / jobsPageSize)}
                          onClick={() => setJobsPage((p) => p + 1)}
                          className="p-1.5 rounded-lg border border-[#e6dfd8] hover:bg-neutral-50 disabled:opacity-30 cursor-pointer bg-white"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: MEMBER USER ACCOUNTS MANAGEMENT */}
          {activeTab === "users" && (
            <div className="max-w-5xl mx-auto space-y-6">
              <div className="flex items-center justify-between border-b border-[#e6dfd8] pb-4">
                <h3 className="font-serif text-base font-semibold text-[#141413] flex items-center gap-2">
                  <span className="text-[#cc785c] text-sm">✦</span>
                  Danh sách thành viên hệ thống
                </h3>
                <button 
                  onClick={fetchUsers} 
                  className="flex items-center gap-2 text-xs text-[#6c6a64] hover:text-[#141413] border border-[#e6dfd8] px-3.5 py-2 rounded-xl bg-white cursor-pointer transition-colors shadow-xs"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Tải lại
                </button>
              </div>

              {usersLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="w-6 h-6 animate-spin text-[#cc785c]" />
                </div>
              ) : (
                <div className="bg-white border border-[#e6dfd8] rounded-2xl overflow-hidden shadow-xs">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-[#e6dfd8] bg-[#efe9de]/20 text-[9px] font-bold uppercase tracking-widest text-[#6c6a64]">
                          <th className="py-4 px-6">Tên người dùng</th>
                          <th className="py-4 px-6">Email</th>
                          <th className="py-4 px-6">Vai trò</th>
                          <th className="py-4 px-6">Ngày tạo</th>
                          <th className="py-4 px-6 text-right">Thao tác</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#e6dfd8]/40 text-xs text-[#141413]">
                        {users.map((u) => (
                          <tr key={u.id} className="hover:bg-[#efe9de]/10 transition-colors">
                            <td className="py-4 px-6 font-serif italic text-base text-[#141413]">{u.username}</td>
                            <td className="py-4 px-6 text-[#6c6a64] font-mono text-[11px]">{u.email}</td>
                            <td className="py-4 px-6">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-widest border ${
                                u.role === "admin"
                                  ? "bg-[#b55a4c]/5 text-[#b55a4c] border-[#b55a4c]/20"
                                  : "bg-[#4a7b9c]/5 text-[#4a7b9c] border-[#4a7b9c]/20"
                              }`}>
                                {u.role}
                              </span>
                            </td>
                            <td className="py-4 px-6 text-[#8e8b82] font-serif italic">
                              {new Date(u.created_at).toLocaleDateString("vi-VN", {
                                year: "numeric",
                                month: "long",
                                day: "numeric",
                              })}
                            </td>
                            <td className="py-4 px-6 text-right">
                              <button
                                onClick={() => setResettingUser(u)}
                                className="inline-flex items-center gap-1.5 px-3 py-2 border border-[#e6dfd8] text-[#cc785c] hover:border-[#cc785c] hover:bg-[#cc785c]/5 rounded-xl text-xs font-semibold transition-all cursor-pointer bg-white active:scale-95 shadow-sm"
                              >
                                <Key size={12} />
                                Đặt lại mật khẩu
                              </button>
                            </td>
                          </tr>
                        ))}
                        {users.length === 0 && (
                          <tr>
                            <td colSpan={5} className="py-12 text-center text-[#8e8b82] font-serif italic text-sm">
                              Không tìm thấy tài khoản người dùng nào.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 5: PASSWORD RESET REQUESTS */}
          {activeTab === "reset_requests" && (
            <div className="max-w-5xl mx-auto space-y-6">
              <div className="flex items-center justify-between border-b border-[#e6dfd8] pb-4">
                <h3 className="font-serif text-base font-semibold text-[#141413] flex items-center gap-2">
                  <span className="text-[#cc785c] text-sm">✦</span>
                  Yêu cầu khôi phục mật khẩu chờ duyệt
                </h3>
                <button 
                  onClick={fetchResetRequests} 
                  className="flex items-center gap-2 text-xs text-[#6c6a64] hover:text-[#141413] border border-[#e6dfd8] px-3.5 py-2 rounded-xl bg-white cursor-pointer transition-colors shadow-xs"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Tải lại
                </button>
              </div>

              {requestsLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="w-6 h-6 animate-spin text-[#cc785c]" />
                </div>
              ) : (
                <div className="bg-white border border-[#e6dfd8] rounded-2xl overflow-hidden shadow-xs">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-[#e6dfd8] bg-[#efe9de]/20 text-[9px] font-bold uppercase tracking-widest text-[#6c6a64]">
                          <th className="py-4 px-6">Email</th>
                          <th className="py-4 px-6">Tên người dùng</th>
                          <th className="py-4 px-6">Lý do</th>
                          <th className="py-4 px-6">Trạng thái</th>
                          <th className="py-4 px-6">Ngày gửi</th>
                          <th className="py-4 px-6 text-right">Thao tác</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#e6dfd8]/40 text-xs text-[#141413]">
                        {resetRequests.map((r) => (
                          <tr key={r.id} className="hover:bg-[#efe9de]/10 transition-colors">
                            <td className="py-4 px-6 font-mono text-[11px] text-[#141413]">{r.email}</td>
                            <td className="py-4 px-6 text-[#6c6a64] font-serif italic text-base">{r.username || "-"}</td>
                            <td className="py-4 px-6 text-[#6c6a64] max-w-xs truncate" title={r.reason || ""}>
                              {r.reason || "-"}
                            </td>
                            <td className="py-4 px-6">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-widest border ${
                                r.status === "pending"
                                  ? "bg-[#b88a44]/5 text-[#b88a44] border-[#b88a44]/20"
                                  : r.status === "approved"
                                  ? "bg-[#4c7a5c]/5 text-[#4c7a5c] border-[#4c7a5c]/20"
                                  : r.status === "rejected"
                                  ? "bg-[#b55a4c]/5 text-[#b55a4c] border-[#b55a4c]/20"
                                  : "bg-[#6c6a64]/5 text-[#6c6a64] border-[#6c6a64]/20"
                              }`}>
                                {r.status === "pending" ? "Đang chờ" : r.status === "approved" ? "Đã duyệt" : r.status === "rejected" ? "Từ chối" : r.status}
                              </span>
                            </td>
                            <td className="py-4 px-6 text-[#8e8b82] font-serif italic">
                              {new Date(r.created_at).toLocaleString("vi-VN", {
                                year: "numeric",
                                month: "long",
                                day: "numeric",
                                hour: "2-digit",
                                minute: "2-digit"
                              })}
                            </td>
                            <td className="py-4 px-6 text-right space-x-2">
                              {r.status === "pending" ? (
                                <>
                                  <button
                                    onClick={() => setApprovingRequest(r)}
                                    className="inline-flex items-center gap-1.5 px-3 py-2 bg-[#4c7a5c] text-white hover:bg-[#3d624a] rounded-xl text-xs font-semibold transition-all border-0 cursor-pointer shadow-xs active:scale-95"
                                  >
                                    <Key size={12} />
                                    Cấp lại MK
                                  </button>
                                  <button
                                    onClick={() => handleRejectRequest(r.id)}
                                    className="inline-flex items-center gap-1.5 px-3 py-2 border border-[#e6dfd8] text-[#b55a4c] hover:border-[#b55a4c] hover:bg-[#b55a4c]/5 rounded-xl text-xs font-semibold transition-all cursor-pointer bg-white active:scale-95"
                                  >
                                    Từ chối
                                  </button>
                                </>
                              ) : (
                                <span className="text-[#8e8b82] text-xs italic">Đã xử lý</span>
                              )}
                            </td>
                          </tr>
                        ))}
                        {resetRequests.length === 0 && (
                          <tr>
                            <td colSpan={6} className="py-12 text-center text-[#8e8b82] font-serif italic text-sm">
                              Không tìm thấy yêu cầu khôi phục mật khẩu nào.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      </div>

      {/* DRAWERS & MODALS */}
      <AnimatePresence>
        
        {/* MODAL 1: RESET PASSWORD DIRECTLY */}
        {resettingUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#141413]/30 backdrop-blur-xs">
            <motion.form
              initial={{ scale: 0.96, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.96, opacity: 0 }}
              onSubmit={handleResetPassword}
              className="bg-[#faf8f4] border border-[#e6dfd8] rounded-2xl p-6.5 max-w-[390px] w-full shadow-2xl space-y-4 text-left relative overflow-hidden font-sans"
            >
              <div className="absolute inset-2 border border-[#e6dfd8]/40 pointer-events-none rounded-xl" />

              <div className="flex items-center gap-3 border-b border-[#e6dfd8] pb-3 text-[#cc785c] relative z-10">
                <div className="w-8 h-8 rounded-lg bg-[#cc785c]/5 flex items-center justify-center text-[#cc785c] border border-[#cc785c]/10">
                  <ShieldAlert size={16} />
                </div>
                <h3 className="font-serif text-base font-semibold text-[#141413]">Đặt lại mật khẩu</h3>
              </div>

              <div className="space-y-1 relative z-10">
                <span className="text-[9px] text-[#6c6a64] uppercase font-bold tracking-widest">Tài khoản</span>
                <p className="text-xs font-semibold text-[#141413] bg-white py-2 px-3.5 rounded-xl border border-[#e6dfd8]">
                  {resettingUser.username} ({resettingUser.email})
                </p>
              </div>

              <div className="space-y-1.5 relative z-10">
                <label className="text-[9px] text-[#6c6a64] uppercase font-bold tracking-widest block">Mật khẩu mới</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Nhập tối thiểu 8 ký tự"
                  className="w-full bg-white border border-[#e6dfd8] rounded-xl py-2.5 px-3.5 text-xs text-[#141413] outline-none placeholder:text-[#8e8b82]/40 focus:border-[#cc785c] transition-all box-border"
                />
              </div>

              {resetMessage && (
                <p className="text-xs font-semibold text-green-700 bg-green-50 border border-green-200 py-2 px-3 rounded-lg relative z-10">
                  {resetMessage}
                </p>
              )}

              {resetError && (
                <p className="text-xs font-semibold text-red-700 bg-red-50 border border-red-200 py-2 px-3 rounded-lg relative z-10">
                  {resetError}
                </p>
              )}

              <div className="flex items-center justify-end gap-2 pt-2 relative z-10">
                <button
                  type="button"
                  onClick={() => {
                    setResettingUser(null)
                    setNewPassword("")
                    setResetError("")
                    setResetMessage("")
                  }}
                  className="px-4 py-2 border border-[#e6dfd8] bg-white hover:bg-[#efe9de]/30 text-[#6c6a64] rounded-xl text-xs font-semibold cursor-pointer transition-colors"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#cc785c] hover:bg-[#b8694d] text-white rounded-xl text-xs font-semibold cursor-pointer transition-colors border-0 shadow-sm"
                >
                  Xác nhận
                </button>
              </div>
            </motion.form>
          </div>
        )}

        {/* MODAL 2: APPROVE PASSWORD RESET REQUEST */}
        {approvingRequest && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#141413]/30 backdrop-blur-xs">
            <motion.form
              initial={{ scale: 0.96, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.96, opacity: 0 }}
              onSubmit={handleApproveRequest}
              className="bg-[#faf8f4] border border-[#e6dfd8] rounded-2xl p-6.5 max-w-[390px] w-full shadow-2xl space-y-4 text-left relative overflow-hidden font-sans"
            >
              <div className="absolute inset-2 border border-[#e6dfd8]/40 pointer-events-none rounded-xl" />

              <div className="flex items-center gap-3 border-b border-[#e6dfd8] pb-3 text-[#4c7a5c] relative z-10">
                <div className="w-8 h-8 rounded-lg bg-[#4c7a5c]/5 flex items-center justify-center text-[#4c7a5c] border border-[#4c7a5c]/10">
                  <ShieldAlert size={16} />
                </div>
                <h3 className="font-serif text-base font-semibold text-[#141413]">Phê duyệt & Cấp mật khẩu</h3>
              </div>

              <div className="space-y-1 relative z-10">
                <span className="text-[9px] text-[#6c6a64] uppercase font-bold tracking-widest">Yêu cầu từ</span>
                <p className="text-xs font-semibold text-[#141413] bg-white py-2 px-3.5 rounded-xl border border-[#e6dfd8]">
                  {approvingRequest.email} {approvingRequest.username ? `(${approvingRequest.username})` : ""}
                </p>
                {approvingRequest.reason && (
                  <div className="text-[11px] text-[#8a6d3b] mt-2 bg-[#fcf8e3] p-2.5 rounded-lg border border-[#faebcc] leading-relaxed">
                    <span className="font-bold block text-[10px] uppercase tracking-wider mb-0.5">Lý do khôi phục:</span>
                    "{approvingRequest.reason}"
                  </div>
                )}
              </div>

              <div className="space-y-1.5 relative z-10">
                <label className="text-[9px] text-[#6c6a64] uppercase font-bold tracking-widest block">Mật khẩu mới cấp</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={approvePassword}
                  onChange={(e) => setApprovePassword(e.target.value)}
                  placeholder="Nhập tối thiểu 8 ký tự"
                  className="w-full bg-white border border-[#e6dfd8] rounded-xl py-2.5 px-3.5 text-xs text-[#141413] outline-none placeholder:text-[#8e8b82]/40 focus:border-[#cc785c] transition-all box-border"
                />
              </div>

              {approveMessage && (
                <p className="text-xs font-semibold text-green-700 bg-green-50 border border-green-200 py-2 px-3 rounded-lg relative z-10">
                  {approveMessage}
                </p>
              )}

              {approveError && (
                <p className="text-xs font-semibold text-red-700 bg-red-50 border border-red-200 py-2 px-3 rounded-lg relative z-10">
                  {approveError}
                </p>
              )}

              <div className="flex items-center justify-end gap-2 pt-2 relative z-10">
                <button
                  type="button"
                  onClick={() => {
                    setApprovingRequest(null)
                    setApprovePassword("")
                    setApproveError("")
                    setApproveMessage("")
                  }}
                  className="px-4 py-2 border border-[#e6dfd8] bg-white hover:bg-[#efe9de]/30 text-[#6c6a64] rounded-xl text-xs font-semibold cursor-pointer transition-colors"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#4c7a5c] hover:bg-[#3d624a] text-white rounded-xl text-xs font-semibold cursor-pointer transition-colors border-0 shadow-sm"
                >
                  Xác nhận & Cấp
                </button>
              </div>
            </motion.form>
          </div>
        )}

        {/* SLIDE-OVER DRAWER: PENDING DOCUMENT DETAILS */}
        {selectedDoc && (
          <div className="fixed inset-0 z-50 flex justify-end bg-[#141413]/20 backdrop-blur-xs">
            <div className="absolute inset-0 cursor-default" onClick={() => setSelectedDoc(null)} />

            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 26, stiffness: 220 }}
              className="bg-[#faf8f4] w-full max-w-2xl h-full shadow-2xl border-l border-[#e6dfd8] flex flex-col relative z-10 font-sans"
            >
              <div className="absolute inset-2 border border-[#e6dfd8]/40 pointer-events-none rounded-xl z-20" />

              <div className="px-8 py-4.5 border-b border-[#e6dfd8] bg-white flex items-center justify-between relative z-10">
                <div className="flex items-center gap-2 text-[#cc785c]">
                  <FileText className="w-5 h-5" />
                  <span className="text-[9px] uppercase font-bold tracking-widest text-[#8e8b82]">
                    Chi tiết tài liệu chờ duyệt
                  </span>
                </div>
                <button 
                  onClick={() => setSelectedDoc(null)}
                  className="p-1 rounded-lg border border-[#e6dfd8] hover:bg-neutral-50 cursor-pointer bg-white"
                >
                  <X className="w-4 h-4 text-[#6c6a64]" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-8 space-y-6 relative z-10">
                <div>
                  <h4 className="text-2xl font-serif font-semibold text-[#141413] leading-relaxed">
                    {selectedDoc.title}
                  </h4>
                  {selectedDoc.author && (
                    <p className="text-xs text-[#8e8b82] mt-1.5 italic font-serif">Tác giả: {selectedDoc.author}</p>
                  )}
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-white p-3 border border-[#e6dfd8]/70 rounded-xl text-center shadow-xs">
                    <span className="block text-[8px] uppercase tracking-widest text-[#8e8b82] font-semibold mb-0.5">
                      Điểm chất lượng
                    </span>
                    <span className="font-serif text-base font-bold text-[#cc785c]">
                      {selectedDoc.quality_score.toFixed(2)}
                    </span>
                  </div>

                  <div className="bg-white p-3 border border-[#e6dfd8]/70 rounded-xl text-center shadow-xs">
                    <span className="block text-[8px] uppercase tracking-widest text-[#8e8b82] font-semibold mb-0.5">
                      Nguồn / Loại
                    </span>
                    <span className="text-xs font-bold text-[#6c6a64] uppercase tracking-wider">
                      {selectedDoc.source_type}
                    </span>
                  </div>

                  <div className="bg-white p-3 border border-[#e6dfd8]/70 rounded-xl text-center shadow-xs">
                    <span className="block text-[8px] uppercase tracking-widest text-[#8e8b82] font-semibold mb-0.5">
                      Ngôn ngữ
                    </span>
                    <span className="text-xs font-bold text-neutral-800 uppercase">
                      {selectedDoc.language || "vi"}
                    </span>
                  </div>

                  <div className="bg-white p-3 border border-[#e6dfd8]/70 rounded-xl text-center shadow-xs">
                    <span className="block text-[8px] uppercase tracking-widest text-[#8e8b82] font-semibold mb-0.5">
                      Thời đại nạp
                    </span>
                    <span className="text-xs font-bold text-neutral-800">
                      {selectedDoc.detected_years ? selectedDoc.detected_years.join(", ") : "-"}
                    </span>
                  </div>
                </div>

                {selectedDoc.summary && (
                  <div className="bg-white p-4 border border-[#e6dfd8]/70 rounded-xl space-y-1.5 shadow-xs">
                    <span className="text-[9px] uppercase font-bold text-[#8e8b82] tracking-wider block">
                      Tóm tắt nội dung
                    </span>
                    <p className="text-xs text-[#6c6a64] leading-relaxed">
                      {selectedDoc.summary}
                    </p>
                  </div>
                )}

                <div className="space-y-3">
                  <span className="text-[9px] uppercase font-bold text-[#8e8b82] tracking-wider block border-b border-[#e6dfd8]/30 pb-2">
                    Thực thể Lịch sử phát hiện
                  </span>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="space-y-1.5">
                      <span className="text-[10px] text-[#8e8b82] block">Nhân vật (Persons):</span>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedDoc.entity_persons && selectedDoc.entity_persons.length > 0 ? (
                          selectedDoc.entity_persons.map((p: string) => (
                            <span key={p} className="bg-[#cc785c]/5 text-[#cc785c] border border-[#cc785c]/10 px-2 py-0.5 rounded-lg text-[10px]">
                              {p}
                            </span>
                          ))
                        ) : (
                          <span className="text-neutral-400 italic text-[11px]">-</span>
                        )}
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <span className="text-[10px] text-[#8e8b82] block">Địa danh (Places):</span>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedDoc.entity_places && selectedDoc.entity_places.length > 0 ? (
                          selectedDoc.entity_places.map((pl: string) => (
                            <span key={pl} className="bg-[#4c7a5c]/5 text-[#4c7a5c] border border-[#4c7a5c]/10 px-2 py-0.5 rounded-lg text-[10px]">
                              {pl}
                            </span>
                          ))
                        ) : (
                          <span className="text-neutral-400 italic text-[11px]">-</span>
                        )}
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <span className="text-[10px] text-[#8e8b82] block">Sự kiện (Events):</span>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedDoc.entity_events && selectedDoc.entity_events.length > 0 ? (
                          selectedDoc.entity_events.map((ev: string) => (
                            <span key={ev} className="bg-[#b88a44]/5 text-[#b88a44] border border-[#b88a44]/10 px-2 py-0.5 rounded-lg text-[10px]">
                              {ev}
                            </span>
                          ))
                        ) : (
                          <span className="text-neutral-400 italic text-[11px]">-</span>
                        )}
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <span className="text-[10px] text-[#8e8b82] block">Tổ chức (Organizations):</span>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedDoc.entity_organizations && selectedDoc.entity_organizations.length > 0 ? (
                          selectedDoc.entity_organizations.map((org: string) => (
                            <span key={org} className="bg-[#4a7b9c]/5 text-[#4a7b9c] border border-[#4a7b9c]/10 px-2 py-0.5 rounded-lg text-[10px]">
                              {org}
                            </span>
                          ))
                        ) : (
                          <span className="text-neutral-400 italic text-[11px]">-</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <span className="text-[9px] uppercase font-bold text-[#8e8b82] tracking-wider block border-b border-[#e6dfd8]/30 pb-2">
                    Bản thảo Nội dung (Markdown)
                  </span>

                  {loadingMarkdown ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="w-5 h-5 animate-spin text-[#cc785c]" />
                    </div>
                  ) : selectedDocMarkdown ? (
                    <div className="bg-white p-6 border border-[#e6dfd8] rounded-2xl max-h-80 overflow-y-auto font-serif text-sm leading-relaxed text-neutral-800 shadow-inner">
                      <div className="prose max-w-none whitespace-pre-wrap">
                        {selectedDocMarkdown}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-neutral-50 border border-[#e6dfd8]/60 p-4 rounded-xl text-center text-xs text-[#8e8b82] italic">
                      Không có hoặc không thể nạp bản thảo nội dung văn bản.
                    </div>
                  )}
                </div>
              </div>

              <div className="px-8 py-5 border-t border-[#e6dfd8] bg-white flex items-center justify-between gap-3 relative z-10">
                <div className="flex items-center gap-1.5">
                  {selectedDoc.source_url && (
                    <a 
                      href={selectedDoc.source_url} 
                      target="_blank" 
                      rel="noreferrer"
                      className="text-xs text-[#cc785c] hover:underline inline-flex items-center gap-1 font-semibold"
                    >
                      Mở liên kết gốc
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedDoc(null)}
                    className="px-4 py-2.5 border border-[#e6dfd8] hover:bg-neutral-50 text-neutral-700 rounded-xl text-xs font-semibold cursor-pointer bg-white"
                  >
                    Đóng
                  </button>
                  <button
                    onClick={() => handleRejectDoc(selectedDoc.id)}
                    disabled={actioningDocId === selectedDoc.id}
                    className="px-4 py-2.5 border border-[#e6dfd8] text-[#b55a4c] hover:bg-[#b55a4c]/5 rounded-xl text-xs font-semibold cursor-pointer bg-white"
                  >
                    Từ chối
                  </button>
                  <button
                    onClick={() => handleApproveDoc(selectedDoc.id)}
                    disabled={actioningDocId === selectedDoc.id}
                    className="px-4 py-2.5 bg-[#4c7a5c] text-white hover:bg-[#3d624a] rounded-xl text-xs font-semibold cursor-pointer border-0 shadow-sm"
                  >
                    {actioningDocId === selectedDoc.id ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      "Duyệt tài liệu"
                    )}
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}

        {/* MODAL 3: INGESTION JOB LOGS */}
        {selectedJob && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#141413]/30 backdrop-blur-xs">
            <motion.div
              initial={{ scale: 0.96, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.96, opacity: 0 }}
              className="bg-[#faf8f4] border border-[#e6dfd8] rounded-2xl p-6.5 max-w-2xl w-full shadow-2xl space-y-4 text-left relative overflow-hidden font-sans"
            >
              <div className="absolute inset-2 border border-[#e6dfd8]/40 pointer-events-none rounded-xl" />

              <div className="flex items-center justify-between border-b border-[#e6dfd8] pb-3 relative z-10">
                <div className="flex items-center gap-2">
                  <FileCode className="w-5 h-5 text-[#cc785c]" />
                  <h3 className="font-serif text-base font-semibold text-[#141413]">Nhật ký tiến trình</h3>
                </div>
                <button 
                  onClick={() => setSelectedJob(null)}
                  className="p-1 rounded-lg border border-[#e6dfd8] hover:bg-neutral-50 cursor-pointer bg-white"
                >
                  <X className="w-4 h-4 text-[#6c6a64]" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs relative z-10 bg-white p-4 rounded-xl border border-[#e6dfd8]/50 shadow-xs">
                <div>
                  <span className="text-[#8e8b82] block text-[8px] uppercase font-bold tracking-widest mb-0.5">Mã Job (ID)</span>
                  <span className="font-mono text-neutral-800">{selectedJob.id}</span>
                </div>
                <div>
                  <span className="text-[#8e8b82] block text-[8px] uppercase font-bold tracking-widest mb-0.5">Nguồn tải (Source)</span>
                  <span className="truncate block font-medium max-w-[240px] text-neutral-800" title={selectedJob.source_input}>
                    {selectedJob.source_input}
                  </span>
                </div>
                <div>
                  <span className="text-[#8e8b82] block text-[8px] uppercase font-bold tracking-widest mb-0.5">Trạng thái (Status)</span>
                  <span className="font-bold uppercase text-[10px] text-[#cc785c]">{selectedJob.status}</span>
                </div>
                <div>
                  <span className="text-[#8e8b82] block text-[8px] uppercase font-bold tracking-widest mb-0.5">Phân đoạn xử lý (Stage)</span>
                  <span className="font-mono text-neutral-800 text-[10px]">{selectedJob.stage}</span>
                </div>
              </div>

              {selectedJob.error_message && (
                <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-xs font-semibold relative z-10 flex items-start gap-2 leading-relaxed">
                  <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold block text-[10px] uppercase tracking-wider mb-0.5">Thông báo lỗi:</span>
                    {selectedJob.error_message}
                  </div>
                </div>
              )}

              <div className="space-y-2 relative z-10">
                <span className="text-[9px] text-[#6c6a64] uppercase font-bold tracking-widest block">
                  Console Output Logs
                </span>
                
                <div className="bg-neutral-900 text-neutral-100 font-mono text-[10px] p-4.5 rounded-xl max-h-60 overflow-y-auto space-y-1.5 shadow-inner">
                  {selectedJob.logs && selectedJob.logs.length > 0 ? (
                    selectedJob.logs.map((log: string, idx: number) => {
                      const isError = log.toLowerCase().includes("err") || log.toLowerCase().includes("fail")
                      const isSuccess = log.toLowerCase().includes("success") || log.toLowerCase().includes("ok")
                      let colorClass = "text-neutral-300"
                      if (isError) colorClass = "text-red-400"
                      else if (isSuccess) colorClass = "text-emerald-400"
                      
                      return (
                        <div key={idx} className={`leading-relaxed border-l-2 border-neutral-700/50 pl-2 ${colorClass}`}>
                          <span className="text-neutral-500 mr-2">[{idx + 1}]</span>
                          {log}
                        </div>
                      )
                    })
                  ) : (
                    <p className="text-neutral-500 italic">Không có nhật ký chi tiết nào được ghi nhận.</p>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 relative z-10 border-t border-[#e6dfd8]/60">
                <button
                  type="button"
                  onClick={() => setSelectedJob(null)}
                  className="px-4 py-2.5 border border-[#e6dfd8] bg-white hover:bg-neutral-50 text-[#6c6a64] rounded-xl text-xs font-semibold cursor-pointer transition-colors"
                >
                  Đóng
                </button>
                {(selectedJob.status === "failed" || selectedJob.status === "done") && (
                  <button
                    onClick={() => {
                      handleRetryJob(selectedJob.id)
                      setSelectedJob(null)
                    }}
                    className="px-4 py-2.5 bg-[#cc785c] text-white hover:bg-[#b8694d] rounded-xl text-xs font-semibold cursor-pointer transition-colors border-0 shadow-sm"
                  >
                    Chạy lại ngay
                  </button>
                )}
              </div>
            </motion.div>
          </div>
        )}

      </AnimatePresence>
    </div>
  )
}
