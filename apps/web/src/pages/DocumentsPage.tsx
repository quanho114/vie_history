import { useEffect, useState, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useDocumentStore, useIngestStore } from "@/stores/documentStore"
import { formatDate } from "@/lib/utils/format"
import { cn } from "@/lib/utils/cn"
import {
  FileText,
  Search,
  Loader2,
  FileBadge,
  Globe,
  FileUp,
  Sparkles,
  BookOpen,
  Layers,
  ArrowRight,
  Trash2,
  Link as LinkIcon,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap,
  UploadCloud,
  Tag as TagIcon,
  History,
  Eye,
  X,
  Copy,
  Check,
  PlusCircle,
  ChevronDown,
} from "lucide-react"
import ReactMarkdown from "react-markdown"

// Decode URL-encoded titles and clean Wikipedia strings
function decodeTitle(title: string): string {
  try {
    let decoded = decodeURIComponent(title)
    if (decoded.startsWith("https://")) {
      const parts = decoded.split("/")
      let lastPart = parts[parts.length - 1]
      lastPart = lastPart.split("#")[0]
      decoded = lastPart.replace(/_/g, " ")
    }
    return decoded
  } catch (e) {
    return title.replace(/_/g, " ")
  }
}

// Clean messy markdown table structures and pipes
function cleanSummary(summary: string): string {
  if (!summary) return ""
  let cleaned = summary
  cleaned = cleaned.replace(/Chú\s*ý/g, "")
  cleaned = cleaned.replace(/\s*\(en\)/gi, "")
  cleaned = cleaned.replace(/[|\-]+([|:\-]+[|:\-]+)+/g, " ")
  cleaned = cleaned.replace(/\|+/g, " ")
  cleaned = cleaned.replace(/--+/g, " ")
  cleaned = cleaned.replace(/-{2,}/g, " ")
  cleaned = cleaned.replace(/(?<=\s|[,.:;!?])\d{2,}(?=\s|$)/g, (match) => {
    const n = parseInt(match, 10)
    return n >= 1000 && n <= 2100 ? match : ""
  })
  cleaned = cleaned.replace(/([a-zA-ZáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ])\s+(\d+)(?=\s|$)/g, "$1")
  cleaned = cleaned.replace(/\s+/g, " ").trim()
  return cleaned
}

// Dynamic icon based on source domain/type
function getDocumentIcon(doc: any) {
  if (doc.source_domain?.includes("wikipedia") || doc.title?.includes("wikipedia")) {
    return <Globe className="w-4 h-4 text-sky-600" />
  }
  if (doc.tags?.includes("chat-upload") || doc.source_type === "upload") {
    return <FileUp className="w-4 h-4 text-orange-600" />
  }
  if (doc.source_type === "book" || doc.tags?.includes("thư viện")) {
    return <BookOpen className="w-4 h-4 text-emerald-600" />
  }
  return <FileText className="w-4 h-4 text-[#8a8175]" />
}

// Elegant color-coding for historical entities and categories
function getTagClass(tag: string): string {
  if (/^\d{4}/.test(tag) || tag.endsWith("s")) {
    return "bg-[#fdf6e2] text-[#b28b2a] border-[#f5ebcd]"
  }
  const keyLeaders = ["Hồ Chí Minh", "Võ Nguyên Giáp", "Lê Duẩn", "Trần Phú", "Trường Chinh"]
  if (keyLeaders.some(leader => tag.includes(leader))) {
    return "bg-[#eefcf7] text-[#0f7652] border-[#d2f3e8]"
  }
  if (tag === "chat-upload") {
    return "bg-orange-50 text-[var(--coral)] border-orange-200/50"
  }
  return "bg-[#f5f1ea] text-[#6f675d] border-[#e7e1d8]"
}

export function DocumentsPage() {
  const navigate = useNavigate()
  const { documents, loadDocuments, isLoading, total, deleteDocument } = useDocumentStore()
  const [search, setSearch] = useState("")
  const [status, setStatus] = useState<string>("")
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [confirmDeleteTitle, setConfirmDeleteTitle] = useState<string>("")
  const [confirmDeleteJobId, setConfirmDeleteJobId] = useState<string | null>(null)
  const [confirmDeleteJobInput, setConfirmDeleteJobInput] = useState<string>("")

  // Tab and Drawers
  const [activeTab, setActiveTab] = useState<"library" | "jobs">("library")
  const [isIngestOpen, setIsIngestOpen] = useState(false)
  const [ingestTab, setIngestTab] = useState<"url" | "file">("url")
  const [isPreviewOpen, setIsPreviewOpen] = useState(false)

  // Ingest states
  const [url, setUrl] = useState("")
  const [tags, setTags] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [copied, setCopied] = useState(false)
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null)
  const [confirmDeleteAllJobs, setConfirmDeleteAllJobs] = useState(false)
  const [isDeletingAllJobs, setIsDeletingAllJobs] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Store ingest
  const { jobs, loadJobs, submitUrl, submitFile, getPreview, currentPreview, deleteJob, deleteAllJobs, isLoading: isIngestLoading } = useIngestStore()

  // Dropdown states
  const [isOpenStatus, setIsOpenStatus] = useState(false)
  const statusRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (statusRef.current && !statusRef.current.contains(event.target as Node)) {
        setIsOpenStatus(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [])

  useEffect(() => {
    if (activeTab === "library") {
      loadDocuments({ search: search || undefined, status: status || undefined })
    }
  }, [search, status, activeTab])

  useEffect(() => {
    loadJobs()
  }, [loadJobs])

  const prevJobStatusesRef = useRef<Record<string, string>>({})
  useEffect(() => {
    const hasRunning = jobs.some((j) => j.status === "running" || j.status === "queued")
    if (!hasRunning) return
    const interval = setInterval(async () => {
      await loadJobs()
      jobs.forEach((j) => {
        const prev = prevJobStatusesRef.current[j.id]
        if (prev && prev !== "done" && j.status === "done") {
          loadDocuments({ search: search || undefined, status: status || undefined })
        }
        prevJobStatusesRef.current[j.id] = j.status
      })
    }, 4000)
    return () => clearInterval(interval)
  }, [jobs, loadJobs, loadDocuments, search, status])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    try {
      const jobId = await submitUrl(url.trim(), tags.split(",").map((t) => t.trim()).filter(Boolean))
      await getPreview(jobId)
      setIsPreviewOpen(true)
      setUrl("")
      setTags("")
      setIsIngestOpen(false)
      setActiveTab("jobs")
    } catch {
      // handled
    }
  }

  const handleFileSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    try {
      const jobId = await submitFile(file, tags.split(",").map((t) => t.trim()).filter(Boolean))
      await getPreview(jobId)
      setIsPreviewOpen(true)
      setFile(null)
      setTags("")
      setIsIngestOpen(false)
      setActiveTab("jobs")
    } catch {
      // handled
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      const fileExtension = droppedFile.name.split(".").pop()?.toLowerCase()
      if (fileExtension && ["pdf", "md", "txt"].includes(fileExtension)) {
        setFile(droppedFile)
      }
    }
  }

  const triggerFileInput = () => {
    fileInputRef.current?.click()
  }

  const handleViewPreview = async (jobId: string) => {
    try {
      await getPreview(jobId)
      setIsPreviewOpen(true)
    } catch {
      // handled
    }
  }

  const handleCopy = () => {
    if (currentPreview) {
      navigator.clipboard.writeText(currentPreview.markdown)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const decodeUrlSafely = (urlStr: string) => {
    try {
      return decodeURIComponent(urlStr)
    } catch {
      return urlStr
    }
  }

  const statusConfig = {
    done: {
      icon: CheckCircle,
      color: "text-emerald-600 bg-emerald-50 border-emerald-200/60",
      label: "Hoàn thành"
    },
    failed: {
      icon: AlertCircle,
      color: "text-rose-600 bg-rose-50 border-rose-200/60",
      label: "Thất bại"
    },
    running: {
      icon: Loader2,
      color: "text-orange-600 bg-orange-50 border-orange-200/60",
      label: "Đang xử lý"
    },
    queued: {
      icon: Clock,
      color: "text-stone-500 bg-stone-50 border-stone-200/60",
      label: "Đang chờ"
    },
  } as const

  const getStageVietnamese = (stage: string) => {
    const stages: Record<string, string> = {
      "done": "Thành công",
      "failed": "Thất bại",
      "downloading": "Đang tải trang",
      "extracting": "Đang trích xuất nội dung",
      "cleaning": "Đang làm sạch văn bản",
      "indexing": "Đang lập chỉ mục Vector/Lexical",
      "queued": "Đang xếp hàng",
    }
    return stages[stage.toLowerCase()] || stage
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-[#FAF9F5] transition-all">
      
      {/* Executive Page Header Dashboard - Beautifully integrated with brand clay-orange colors */}
      <header className="px-6 py-6 md:py-8 border-b border-[#e7e1d8] bg-white shadow-[0_2px_12px_rgba(20,20,19,0.01)] flex-shrink-0">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#fdfaf5] to-[#f5f0e8] flex items-center justify-center border border-orange-100/60 shadow-[inset_0_1px_2px_rgba(255,255,255,0.6),0_4px_12px_rgba(204,120,92,0.05)] text-[var(--coral)] relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-tr from-orange-500/5 to-transparent" />
              <FileBadge className="w-6 h-6 relative z-10" />
            </div>
            <div className="text-left">
              <div className="flex flex-wrap items-center gap-2.5">
                <h2 className="text-2xl font-display font-bold text-[#2d2a26] tracking-tight leading-none">Kho tư liệu lịch sử</h2>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-100 rounded-full shadow-[0_1px_2px_rgba(0,0,0,0.01)]">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_4px_rgba(16,185,129,0.5)]" />
                  RAG Linked
                </span>
              </div>
              <p className="text-xs text-[#8a8175] mt-1 font-sans">
                Quản lý các tài liệu nghiên cứu đã được nhúng vector tri thức ngầm ({total} tài liệu)
              </p>
            </div>
          </div>

          <button
            onClick={() => setIsIngestOpen(true)}
            className="group flex items-center justify-center gap-2 px-5 py-2.5 bg-[var(--coral)] hover:bg-[#b85b40] text-white text-xs font-bold rounded-xl transition-all shadow-[0_4px_12px_rgba(204,120,92,0.2)] hover:shadow-[0_6px_20px_rgba(204,120,92,0.35)] active:scale-[0.97] self-start md:self-center font-sans"
          >
            <PlusCircle className="w-4 h-4 transition-transform group-hover:rotate-90 duration-300" />
            Nhập tài liệu mới
          </button>
        </div>

        {/* Tab & Filter bar row */}
        <div className="max-w-5xl mx-auto flex flex-col lg:flex-row lg:items-center justify-between gap-4 mt-6 pt-4 border-t border-[#f5f1ea]">
          {/* Custom Warm Clay-themed Segmented Tab Bar */}
          <div className="flex p-1 bg-[#f5f0e8] rounded-xl max-w-md border border-[#e7e1d8] self-start shadow-inner">
            <button
              onClick={() => setActiveTab("library")}
              className={cn(
                "px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-2",
                activeTab === "library"
                  ? "bg-white text-[var(--coral)] shadow-sm font-semibold"
                  : "text-[#8a8175] hover:text-[#2d2a26]"
              )}
            >
              <BookOpen size={13} />
              Thư viện tri thức
            </button>
            <button
              onClick={() => setActiveTab("jobs")}
              className={cn(
                "px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-2 relative",
                activeTab === "jobs"
                  ? "bg-white text-[var(--coral)] shadow-sm font-semibold"
                  : "text-[#8a8175] hover:text-[#2d2a26]"
              )}
            >
              <History size={13} />
              Tiến trình & Jobs
              {jobs.filter(j => j.status === "running").length > 0 && (
                <span className="w-1.5 h-1.5 bg-orange-500 rounded-full animate-ping ml-0.5" />
              )}
            </button>
          </div>

          {/* Inline filters for Library Tab */}
          {activeTab === "library" && (
            <div className="flex flex-col sm:flex-row gap-2.5 w-full lg:w-auto">
              <div className="relative flex-1 sm:w-80 group">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#aaa39a] group-focus-within:text-[var(--coral)] transition-colors duration-250" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Tìm kiếm tiêu đề, thẻ tài liệu..."
                  className="w-full pl-10 pr-4 py-2 bg-[#FAF9F5]/80 border border-[#e7e1d8] rounded-xl text-xs text-[#2d2a26] placeholder-[#aaa39a] focus:outline-none focus:bg-white focus:ring-4 focus:ring-orange-100/30 focus:border-[var(--coral)] transition-all shadow-sm"
                />
              </div>

              {(() => {
                const statusOptions = [
                  { value: "", label: "Tất cả trạng thái", dotColor: "bg-[#8e8b82]" },
                  { value: "approved", label: "Đã duyệt (Index)", dotColor: "bg-[#5db872]" },
                  { value: "pending", label: "Chờ duyệt", dotColor: "bg-[#e8a55a]" },
                  { value: "rejected", label: "Từ chối", dotColor: "bg-[#c64545]" },
                ]
                const currentOption = statusOptions.find(opt => opt.value === status) || statusOptions[0]

                return (
                  <div ref={statusRef} className="relative">
                    <button
                      type="button"
                      onClick={() => setIsOpenStatus(!isOpenStatus)}
                      className="w-full sm:w-52 px-4 py-2 bg-white border border-[#e7e1d8] rounded-xl text-xs text-[#6f675d] hover:bg-[#FAF9F5] focus:outline-none focus:ring-4 focus:ring-orange-100/30 focus:border-[var(--coral)] transition-all flex items-center justify-between gap-3 shadow-sm font-bold active:scale-[0.98]"
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span className={cn("w-1.5 h-1.5 rounded-full", currentOption.dotColor)} />
                        <span className="truncate">{currentOption.label}</span>
                      </div>
                      <ChevronDown className={cn("w-3.5 h-3.5 text-[#aaa39a] transition-transform duration-250", isOpenStatus && "rotate-180")} />
                    </button>

                    {isOpenStatus && (
                      <div className="absolute right-0 mt-1.5 w-full sm:w-52 z-30 bg-white border border-[#e7e1d8] rounded-xl shadow-lg py-1 overflow-hidden animate-fade-in origin-top-right">
                        {statusOptions.map((option) => (
                          <button
                            key={option.value}
                            type="button"
                            onClick={() => {
                              setStatus(option.value)
                              setIsOpenStatus(false)
                            }}
                            className={cn(
                              "w-full text-left px-4 py-2 text-[11px] text-[#6f675d] hover:text-[#2d2a26] hover:bg-[#FAF9F5] transition-colors flex items-center gap-2 font-medium",
                              status === option.value && "bg-[#FAF9F5] text-[var(--coral)] font-extrabold"
                            )}
                          >
                            <span className={cn("w-1.5 h-1.5 rounded-full", option.dotColor)} />
                            <span>{option.label}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })()}
            </div>
          )}
        </div>
      </header>

      {/* Main Body content area */}
      <div className="flex-1 overflow-y-auto p-6 md:p-8">
        {activeTab === "library" ? (
          isLoading ? (
            <div className="flex flex-col items-center justify-center h-64 gap-3 animate-fade-in">
              <Loader2 className="w-6 h-6 animate-spin text-[var(--coral)]" />
              <span className="text-xs font-bold text-[#8a8175]">Đang tải thư viện tri thức...</span>
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-20 bg-white rounded-3xl border border-[#e7e1d8] max-w-4xl mx-auto shadow-sm animate-fade-in">
              <div className="w-14 h-14 rounded-2xl bg-orange-50/50 border border-orange-100 flex items-center justify-center mx-auto mb-4 text-[#8a8175]">
                <FileText className="w-6 h-6 text-[var(--coral)] opacity-80" />
              </div>
              <p className="text-[#2d2a26] font-extrabold text-base">Không tìm thấy tài liệu</p>
              <p className="text-[#8a8175] text-xs mt-1.5 max-w-sm mx-auto px-4 leading-relaxed">
                Tài liệu sẽ xuất hiện sau khi được nhập từ mục "Nhập liệu" và được duyệt hệ thống.
              </p>
            </div>
          ) : (
            <div className="grid gap-5 max-w-5xl mx-auto animate-fade-in font-sans">
              {documents.map((doc) => {
                const prettyTitle = decodeTitle(doc.title)
                const cleanSummaryText = cleanSummary(doc.summary || "")
                
                // Color accent matches document source icon
                const isWiki = doc.source_domain?.includes("wikipedia") || doc.title?.includes("wikipedia")
                const isBook = doc.source_type === "book" || doc.tags?.includes("thư viện")
                const leftAccentColor = isWiki ? "bg-sky-400" : isBook ? "bg-emerald-400" : "bg-[var(--coral)]"

                return (
                  <div
                    key={doc.id}
                    onClick={() => navigate(`/documents/${doc.id}`)}
                    className="text-left bg-white rounded-2xl p-6 border border-[#e7e1d8] hover:border-[var(--coral)]/80 hover:shadow-[0_8px_30px_rgba(204,120,92,0.06),0_1px_2px_rgba(204,120,92,0.02)] hover:-translate-y-0.5 transition-all duration-300 ease-out group cursor-pointer relative overflow-hidden"
                  >
                    {/* Left Accent Color bar */}
                    <div className={cn("absolute left-0 top-0 bottom-0 w-[4px] opacity-75 group-hover:opacity-100 transition-opacity", leftAccentColor)} />

                    <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 pl-1">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2.5">
                          <div className="w-9 h-9 rounded-xl bg-stone-50 border border-[#e7e1d8] flex items-center justify-center group-hover:bg-orange-50/50 group-hover:border-orange-150 transition-colors duration-250 flex-shrink-0">
                            {getDocumentIcon(doc)}
                          </div>
                          <h3 className="font-display text-lg font-bold text-[#2d2a26] leading-tight tracking-tight group-hover:text-[var(--coral)] transition-colors duration-200 truncate pr-4">
                            {prettyTitle}
                          </h3>
                        </div>

                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-[#aaa39a] font-bold mb-3 pl-0.5">
                          {doc.source_domain && (
                            <>
                              <span className="text-[#8a8175]/90">{doc.source_domain}</span>
                              <span className="text-stone-300">•</span>
                            </>
                          )}
                          <span>{formatDate(doc.created_at)}</span>
                          {doc.quality_score > 0 && (
                            <>
                              <span className="text-stone-300">•</span>
                              <span className="inline-flex items-center gap-1 text-emerald-800 font-bold bg-emerald-50/50 border border-emerald-100/60 px-2 py-0.5 rounded shadow-[0_1px_2px_rgba(0,0,0,0.01)]">
                                <Sparkles className="w-3 h-3 text-emerald-600 animate-pulse" />
                                Chất lượng: {(doc.quality_score * 100).toFixed(0)}%
                              </span>
                            </>
                          )}
                        </div>

                        {cleanSummaryText && (
                          <p className="text-xs text-[#6c6a64] leading-relaxed line-clamp-2 pl-0.5 group-hover:text-[#3d3d3a] transition-colors text-wrap-pretty mt-1 max-w-[75ch]">
                            {cleanSummaryText}
                          </p>
                        )}
                      </div>

                      <div className="flex md:flex-col items-center md:items-end justify-between md:justify-start gap-4 md:gap-3.5 flex-shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-[#f5f1ea] mt-3 md:mt-0" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setConfirmDeleteId(doc.id)
                              setConfirmDeleteTitle(prettyTitle)
                            }}
                            disabled={deletingId !== null}
                            className="p-2 rounded-xl text-stone-300 hover:text-red-600 hover:bg-red-50 border border-transparent hover:border-red-100 transition-all disabled:opacity-40 active:scale-90"
                            title="Xóa tài liệu"
                          >
                            {deletingId === doc.id ? (
                              <Loader2 size={14} className="animate-spin text-red-600" />
                            ) : (
                              <Trash2 size={14} />
                            )}
                          </button>
                          
                          <span
                            className={cn(
                              "px-3 py-1 text-[10px] rounded-xl font-bold border flex-shrink-0 shadow-sm",
                              doc.status === "approved" && "bg-emerald-50 text-emerald-700 border-emerald-100/70",
                              doc.status === "pending" && "bg-amber-50 text-amber-700 border-amber-100/70",
                              doc.status === "rejected" && "bg-rose-50 text-rose-700 border-rose-100/70",
                              doc.status === "archived" && "bg-[#f5f1ea] text-[#6f675d] border-[#e7e1d8]"
                            )}
                          >
                            {doc.status === "approved" && "✓ Đã duyệt"}
                            {doc.status === "pending" && "⏳ Chờ duyệt"}
                            {doc.status === "rejected" && "✕ Từ chối"}
                            {doc.status === "archived" && "Lưu trữ"}
                          </span>
                        </div>

                        <div className="hidden md:flex w-7 h-7 rounded-full bg-stone-50 border border-[#e7e1d8] items-center justify-center text-stone-400 group-hover:text-white group-hover:bg-[var(--coral)] group-hover:border-transparent group-hover:translate-x-0.5 transition-all duration-300 active:scale-95 shadow-sm">
                          <ArrowRight size={14} />
                        </div>
                      </div>
                    </div>

                    {/* Metadata tags */}
                    {doc.tags && doc.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-4 pt-4 border-t border-[#f5f1ea] pl-1">
                        {doc.tags.slice(0, 8).map((tag) => (
                          <span
                            key={tag}
                            className={cn(
                              "px-2.5 py-0.5 text-[10px] rounded-md font-bold transition-colors border shadow-sm hover:scale-[1.03] transition-transform duration-200",
                              getTagClass(tag)
                            )}
                          >
                            {tag}
                          </span>
                        ))}
                        {doc.tags.length > 8 && (
                          <span className="px-2 py-0.5 text-[10px] text-stone-400 font-extrabold self-center">
                            +{doc.tags.length - 8}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )
        ) : (
          /* Extraction Jobs Tab */
          <div className="max-w-4xl mx-auto space-y-4 animate-fade-in">
            <div className="flex items-center justify-between px-2">
              <div className="text-left">
                <h3 className="font-extrabold text-[#2d2a26] text-sm flex items-center gap-2">
                  Tiến trình trích xuất RAG
                </h3>
                <p className="text-[10px] text-[#8a8175] font-bold mt-0.5">
                  Theo dõi trạng thái tải xuống, trích xuất thực thể lịch sử ngầm
                </p>
              </div>
              <div className="flex items-center gap-2">
                {jobs.length > 0 && (
                  <button
                    onClick={() => setConfirmDeleteAllJobs(true)}
                    className="flex items-center gap-1 px-3 py-1.5 text-[10px] font-bold border border-red-100 text-red-600 hover:text-white bg-red-50/30 hover:bg-red-600 rounded-xl transition-all duration-150 active:scale-95 shadow-sm"
                  >
                    <Trash2 className="w-3 h-3" />
                    Xóa tất cả
                  </button>
                )}
                <span className="text-[10px] font-bold bg-[#f5f1ea] border border-[#e7e1d8] text-[#6f675d] px-3 py-1.5 rounded-xl shadow-sm">
                  Tác vụ: {jobs.length}
                </span>
              </div>
            </div>

            {/* Ingestion Table/List */}
            {jobs.length > 0 ? (
              <div className="bg-white rounded-3xl border border-[#e7e1d8] overflow-hidden shadow-sm divide-y divide-[#f5f1ea]">
                {jobs.map((job) => {
                  const config = statusConfig[job.status] || statusConfig.queued
                  const Icon = config.icon
                  return (
                    <div
                      key={job.id}
                      className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-[#FAF9F5]/40 transition-colors duration-150"
                    >
                      <div className="flex items-center gap-3.5 min-w-0 flex-1">
                        <div className={cn(
                          "w-8 h-8 rounded-lg border flex items-center justify-center flex-shrink-0 shadow-inner", 
                          config.color
                        )}>
                          <Icon className={cn("w-4 h-4", job.status === "running" ? "animate-spin" : "")} />
                        </div>
                        
                        <div className="min-w-0 flex-1 text-left">
                          <div className="flex items-center gap-2">
                            <span className="bg-[#f5f1ea] text-[#6f675d] px-1.5 py-0.5 rounded text-[8px] font-extrabold uppercase border border-[#e7e1d8] flex-shrink-0">
                              {job.source_type}
                            </span>
                            <p 
                              className="text-xs font-bold text-[#2d2a26] truncate max-w-md sm:max-w-xl" 
                              title={decodeUrlSafely(job.source_input)}
                            >
                              {decodeUrlSafely(job.source_input)}
                            </p>
                          </div>
                          
                          <div className="flex items-center gap-x-2 text-[10px] text-[#aaa39a] font-bold mt-1">
                            <span className={cn("font-extrabold", 
                              job.status === "done" ? "text-emerald-600" : 
                              job.status === "failed" ? "text-rose-600" : 
                              job.status === "running" ? "text-orange-600" : "text-slate-500"
                            )}>
                              {config.label}
                            </span>
                            {job.stage && (
                              <span className="text-stone-300">
                                • {getStageVietnamese(job.stage)}
                              </span>
                            )}
                            {job.error_message && (
                              <span className="text-rose-500 italic font-medium truncate max-w-sm" title={job.error_message}>
                                • Lỗi: {job.error_message}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 flex-shrink-0 self-end sm:self-center">
                        {job.status === "done" && (
                          <button
                            onClick={() => handleViewPreview(job.id)}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-stone-50 text-stone-750 text-[10px] font-bold rounded-xl border border-[#e7e1d8] transition-all duration-150 active:scale-95 shadow-sm"
                          >
                            <Eye className="w-3.5 h-3.5 text-[var(--coral)]" />
                            Xem nội dung
                          </button>
                        )}
                        
                        <button
                          disabled={deletingJobId !== null}
                          onClick={(e) => {
                            e.stopPropagation()
                            setConfirmDeleteJobId(job.id)
                            setConfirmDeleteJobInput(decodeUrlSafely(job.source_input))
                          }}
                          className="w-8 h-8 rounded-xl flex items-center justify-center border border-[#e7e1d8] hover:border-red-200 bg-white text-stone-400 hover:text-red-500 hover:bg-red-50/20 transition-all duration-150 active:scale-90 shadow-sm disabled:opacity-50"
                          title="Xóa tác vụ"
                        >
                          {deletingJobId === job.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin text-red-500" />
                          ) : (
                            <Trash2 className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-center py-16 bg-white rounded-3xl border border-[#e7e1d8] shadow-sm">
                <div className="w-12 h-12 rounded-2xl bg-stone-50 border border-[#e7e1d8] flex items-center justify-center mx-auto text-[#8a8175] shadow-sm mb-3">
                  <History className="w-5 h-5 text-[var(--coral)] opacity-80" />
                </div>
                <p className="text-[#2d2a26] text-xs font-bold">Chưa có tác vụ nào</p>
                <p className="text-[#8a8175] text-[10px] mt-1">Các tư liệu được trích xuất sẽ hiển thị tại đây</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Confirmation Modal - Delete Document */}
      {confirmDeleteId !== null && (
        <div 
          className="fixed inset-0 bg-stone-900/40 backdrop-blur-md z-[9999] flex items-center justify-center p-4 animate-fade-in"
          onClick={() => {
            if (deletingId === null) {
              setConfirmDeleteId(null)
            }
          }}
        >
          <div 
            className="bg-white rounded-3xl border border-[#e7e1d8] p-7 max-w-md w-full shadow-2xl text-center relative overflow-hidden animate-zoom-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="absolute top-0 left-0 right-0 h-[5px] bg-red-600" />
            
            <div className="w-12 h-12 rounded-2xl bg-red-50 border border-red-100 flex items-center justify-center text-red-600 mb-4 mx-auto shadow-sm">
              <Trash2 className="w-5 h-5 animate-pulse" />
            </div>

            <h3 className="text-base font-extrabold text-[#2d2a26] mb-2 leading-snug">
              Xóa tài liệu khỏi hệ thống?
            </h3>
            
            <p className="text-xs text-[#8a8175] font-semibold px-1 mb-5 leading-relaxed">
              Hành động này sẽ dọn sạch hoàn toàn các vector nhúng (Qdrant), chỉ mục BM25 (Elasticsearch), tệp vật lý và cơ sở dữ liệu:
              <span className="block font-bold text-red-600 my-2.5 text-[12px] bg-red-50 border border-red-100 py-2 px-3 rounded-xl italic break-words">
                "{confirmDeleteTitle}"
              </span>
              Hành động này không thể khôi phục!
            </p>

            <div className="flex gap-3 justify-center">
              <button
                disabled={deletingId !== null}
                onClick={() => setConfirmDeleteId(null)}
                className="flex-1 px-4 py-2 bg-stone-50 hover:bg-stone-100 border border-[#e7e1d8] text-xs font-bold text-[#6f675d] rounded-xl transition-all disabled:opacity-50"
              >
                Hủy bỏ
              </button>
              <button
                disabled={deletingId !== null}
                onClick={async () => {
                  setDeletingId(confirmDeleteId)
                  try {
                    await deleteDocument(confirmDeleteId)
                    setConfirmDeleteId(null)
                  } catch (err) {
                    alert("Lỗi xóa tài liệu: " + (err instanceof Error ? err.message : String(err)))
                  } finally {
                    setDeletingId(null)
                  }
                }}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-1.5 shadow-md shadow-red-200/50 disabled:opacity-50"
              >
                {deletingId !== null ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    Đang xóa...
                  </>
                ) : (
                  "Xác nhận xóa"
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal - Delete Job */}
      {confirmDeleteJobId && (
        <div 
          className="fixed inset-0 bg-stone-900/40 backdrop-blur-md z-[9999] flex items-center justify-center p-4 animate-fade-in"
          onClick={() => setConfirmDeleteJobId(null)}
        >
          <div 
            className="bg-white rounded-3xl border border-[#e7e1d8] p-7 max-w-md w-full shadow-2xl text-center relative overflow-hidden animate-zoom-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="absolute top-0 left-0 right-0 h-[5px] bg-red-600" />
            
            <div className="w-12 h-12 rounded-2xl bg-red-50 border border-red-100 flex items-center justify-center text-red-600 mb-4 mx-auto shadow-sm">
              <Trash2 className="w-5 h-5 animate-pulse" />
            </div>

            <h3 className="text-base font-extrabold text-[#2d2a26] mb-2 leading-snug">
              Xóa lịch sử tác vụ?
            </h3>
            
            <p className="text-xs text-[#8a8175] font-semibold px-1 mb-5">
              Xóa bản ghi tiến trình ra khỏi danh sách theo dõi:
              <span className="block font-bold text-red-600 my-2.5 text-[12px] bg-red-50 border border-red-100 py-2 px-3 rounded-xl italic break-words">
                "{confirmDeleteJobInput}"
              </span>
            </p>

            <div className="flex gap-3 justify-center">
              <button
                disabled={deletingJobId !== null}
                onClick={() => setConfirmDeleteJobId(null)}
                className="flex-1 px-4 py-2 bg-stone-50 hover:bg-stone-100 border border-[#e7e1d8] text-xs font-bold text-[#6f675d] rounded-xl transition-all disabled:opacity-50"
              >
                Hủy
              </button>
              <button
                disabled={deletingJobId !== null}
                onClick={async () => {
                  setDeletingJobId(confirmDeleteJobId)
                  try {
                    await deleteJob(confirmDeleteJobId)
                    setConfirmDeleteJobId(null)
                  } catch (err) {
                    alert("Lỗi xóa: " + (err instanceof Error ? err.message : String(err)))
                  } finally {
                    setDeletingJobId(null)
                  }
                }}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-1.5 shadow-md shadow-red-200/50 disabled:opacity-50"
              >
                {deletingJobId !== null ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    Đang xóa...
                  </>
                ) : (
                  "Xác nhận xóa"
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal - Delete All Jobs */}
      {confirmDeleteAllJobs && (
        <div 
          className="fixed inset-0 bg-stone-900/40 backdrop-blur-md z-[9999] flex items-center justify-center p-4 animate-fade-in"
          onClick={() => setConfirmDeleteAllJobs(false)}
        >
          <div 
            className="bg-white rounded-3xl border border-[#e7e1d8] p-7 max-w-md w-full shadow-2xl text-center relative overflow-hidden animate-zoom-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="absolute top-0 left-0 right-0 h-[5px] bg-red-600" />
            
            <div className="w-12 h-12 rounded-2xl bg-red-50 border border-red-100 flex items-center justify-center text-red-600 mb-4 mx-auto shadow-sm">
              <Trash2 className="w-5 h-5 animate-pulse" />
            </div>

            <h3 className="text-base font-extrabold text-[#2d2a26] mb-2 leading-snug">
              Xóa sạch lịch sử tác vụ?
            </h3>
            
            <p className="text-xs text-[#8a8175] font-semibold px-1 mb-5">
              Dọn dẹp sạch sẽ toàn bộ các bản ghi trong danh sách lịch sử tác vụ RAG.
              <span className="block font-bold text-red-600 my-2.5 text-[11px] bg-red-50 border border-red-100 py-2 px-3 rounded-xl italic">
                Cảnh báo: Hành động này không thể hoàn tác!
              </span>
              Tất cả {jobs.length} tiến trình sẽ bị xóa khỏi lịch sử theo dõi.
            </p>

            <div className="flex gap-3 justify-center">
              <button
                disabled={isDeletingAllJobs}
                onClick={() => setConfirmDeleteAllJobs(false)}
                className="flex-1 px-4 py-2 bg-stone-50 hover:bg-stone-100 border border-[#e7e1d8] text-xs font-bold text-[#6f675d] rounded-xl transition-all disabled:opacity-50"
              >
                Hủy
              </button>
              <button
                disabled={isDeletingAllJobs}
                onClick={async () => {
                  setIsDeletingAllJobs(true)
                  try {
                    await deleteAllJobs()
                    setConfirmDeleteAllJobs(false)
                  } catch (err) {
                    alert("Lỗi: " + (err instanceof Error ? err.message : String(err)))
                  } finally {
                    setIsDeletingAllJobs(false)
                  }
                }}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-1.5 shadow-md shadow-red-200/50 disabled:opacity-50"
              >
                {isDeletingAllJobs ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    Đang xóa...
                  </>
                ) : (
                  "Xác nhận xóa tất cả"
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Slide-over Right Drawer containing Ingest forms */}
      {isIngestOpen && (
        <div className="fixed inset-0 z-[50] flex justify-end animate-fade-in">
          <div 
            onClick={() => setIsIngestOpen(false)}
            className="absolute inset-0 bg-stone-900/40 backdrop-blur-sm z-45"
          />
          
          <div className="relative w-full max-w-md h-full bg-[#FAF9F5] shadow-2xl border-l border-[#e7e1d8] flex flex-col z-50 animate-slide-in-right">
            {/* Drawer Header */}
            <div className="px-6 py-5 border-b border-[#e7e1d8] bg-white flex items-center justify-between shadow-sm">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-orange-50 flex items-center justify-center border border-orange-100 text-[var(--coral)] shadow-inner">
                  <Zap className="w-4 h-4" />
                </div>
                <div className="text-left">
                  <h3 className="font-extrabold text-[#2d2a26] text-sm">Nhập dữ liệu tri thức mới</h3>
                  <p className="text-[10px] text-[#8a8175] font-bold mt-0.5">Nạp dữ liệu vào cơ sở tri thức RAG</p>
                </div>
              </div>
              
              <button 
                onClick={() => setIsIngestOpen(false)}
                className="w-7 h-7 rounded-full flex items-center justify-center hover:bg-stone-100 text-stone-400 hover:text-[#2d2a26] transition-all"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Ingestion Type Tabs inside Drawer */}
            <div className="px-6 pt-4 bg-white border-b border-[#f5f1ea] flex gap-2">
              <button
                onClick={() => setIngestTab("url")}
                className={cn(
                  "flex-1 pb-3 text-xs font-bold transition-all border-b-2 -mb-[2px] flex items-center justify-center gap-1.5",
                  ingestTab === "url"
                    ? "border-[var(--coral)] text-[var(--coral)]"
                    : "border-transparent text-[#8a8175] hover:text-[#2d2a26]"
                )}
              >
                <Globe size={13} />
                Trích xuất URL
              </button>
              <button
                onClick={() => setIngestTab("file")}
                className={cn(
                  "flex-1 pb-3 text-xs font-bold transition-all border-b-2 -mb-[2px] flex items-center justify-center gap-1.5",
                  ingestTab === "file"
                    ? "border-[var(--coral)] text-[var(--coral)]"
                    : "border-transparent text-[#8a8175] hover:text-[#2d2a26]"
                )}
              >
                <FileUp size={13} />
                Tải lên tệp tin
              </button>
            </div>

            {/* Drawer Content Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-5 text-left">
              {ingestTab === "url" ? (
                /* URL Extraction Form */
                <form id="drawer-url-form" onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-[10px] font-extrabold text-[#6f675d] mb-1.5 uppercase tracking-wider">
                      Địa chỉ liên kết (URL)
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                        <LinkIcon className="h-4 w-4 text-stone-400" />
                      </div>
                      <input
                        type="url"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        required
                        placeholder="https://vi.wikipedia.org/wiki/..."
                        className="w-full pl-10 pr-4 py-2.5 bg-white border border-[#e7e1d8] rounded-xl text-xs text-[#2d2a26] placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-orange-100 focus:border-[var(--coral)] transition-all shadow-sm"
                      />
                    </div>
                    <p className="text-[9px] text-[#aaa39a] font-bold mt-1.5 leading-relaxed">
                      Hỗ trợ Wikipedia tiếng Việt, các trang báo điện tử hoặc blog nghiên cứu lịch sử.
                    </p>
                  </div>
                  
                  <div>
                    <label className="block text-[10px] font-extrabold text-[#6f675d] mb-1.5 uppercase tracking-wider">
                      Thẻ phân loại <span className="text-[#aaa39a] font-normal">(ngăn cách bởi dấu phẩy)</span>
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                        <TagIcon className="h-4 w-4 text-stone-400" />
                      </div>
                      <input
                        type="text"
                        value={tags}
                        onChange={(e) => setTags(e.target.value)}
                        placeholder="hồ chí minh, 1945, cách mạng..."
                        className="w-full pl-10 pr-4 py-2.5 bg-white border border-[#e7e1d8] rounded-xl text-xs text-[#2d2a26] placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-orange-100 focus:border-[var(--coral)] transition-all shadow-sm"
                      />
                    </div>
                    {tags.trim() && (
                      <div className="flex flex-wrap gap-1 mt-2.5">
                        {tags.split(",").map((t) => t.trim()).filter(Boolean).map((tag, idx) => (
                          <span key={idx} className="bg-[#FAF9F5] text-[var(--coral)] text-[9px] px-2 py-0.5 rounded border border-[#e7e1d8] font-bold shadow-sm">
                            #{tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </form>
              ) : (
                /* File Upload Form */
                <form id="drawer-file-form" onSubmit={handleFileSubmit} className="space-y-4">
                  <input
                    type="file"
                    ref={fileInputRef}
                    accept=".pdf,.md,.txt,text/plain,application/pdf"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    className="hidden"
                  />
                  
                  <div 
                    onDragEnter={handleDrag}
                    onDragOver={handleDrag}
                    onDragLeave={handleDrag}
                    onDrop={handleDrop}
                    onClick={triggerFileInput}
                    className={cn(
                      "w-full h-[160px] border-2 border-dashed rounded-2xl flex flex-col items-center justify-center p-4 text-center cursor-pointer transition-all duration-200 bg-white",
                      dragActive 
                        ? "border-[var(--coral)] bg-orange-50/15 shadow-inner" 
                        : file 
                          ? "border-emerald-400 bg-emerald-50/10" 
                          : "border-[#e7e1d8] hover:border-[var(--coral)] hover:bg-stone-50"
                    )}
                  >
                    {file ? (
                      <div className="space-y-2">
                        <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mx-auto text-emerald-600">
                          <FileText className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="text-xs font-bold text-[#2d2a26] truncate max-w-[200px] mx-auto">{file.name}</p>
                          <p className="text-[9px] text-[#8a8175] mt-0.5 font-bold">
                            {(file.size / 1024 / 1024).toFixed(2)} MB • Click để đổi tệp
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <div className="w-10 h-10 rounded-xl bg-stone-50 border border-[#e7e1d8] flex items-center justify-center mx-auto text-[#8a8175]">
                          <UploadCloud className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="text-xs font-bold text-slate-700">Kéo thả tệp tin vào đây</p>
                          <p className="text-[9px] text-[#8a8175] mt-1 font-bold">hoặc click để duyệt file (.pdf, .md, .txt)</p>
                        </div>
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-[10px] font-extrabold text-[#6f675d] mb-1.5 uppercase tracking-wider">
                      Thẻ phân loại <span className="text-[#aaa39a] font-normal">(ngăn cách bởi dấu phẩy)</span>
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                        <TagIcon className="h-4 w-4 text-stone-400" />
                      </div>
                      <input
                        type="text"
                        value={tags}
                        onChange={(e) => setTags(e.target.value)}
                        placeholder="hồ chí minh, 1945, cách mạng..."
                        className="w-full pl-10 pr-4 py-2.5 bg-white border border-[#e7e1d8] rounded-xl text-xs text-[#2d2a26] placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-orange-100 focus:border-[var(--coral)] transition-all shadow-sm"
                      />
                    </div>
                    {tags.trim() && (
                      <div className="flex flex-wrap gap-1 mt-2.5">
                        {tags.split(",").map((t) => t.trim()).filter(Boolean).map((tag, idx) => (
                          <span key={idx} className="bg-[#FAF9F5] text-[var(--coral)] text-[9px] px-2 py-0.5 rounded border border-[#e7e1d8] font-bold shadow-sm">
                            #{tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </form>
              )}
            </div>

            {/* Drawer Footer Actions */}
            <div className="p-4 border-t border-[#e7e1d8] bg-white flex gap-3">
              <button
                type="button"
                disabled={isIngestLoading}
                onClick={() => setIsIngestOpen(false)}
                className="flex-1 py-2.5 bg-stone-50 hover:bg-stone-100 border border-[#e7e1d8] text-xs font-bold text-[#6f675d] rounded-xl transition-all shadow-sm disabled:opacity-50"
              >
                Hủy bỏ
              </button>
              
              {ingestTab === "url" ? (
                <button
                  type="submit"
                  form="drawer-url-form"
                  disabled={isIngestLoading || !url.trim()}
                  className="flex-1 py-2.5 bg-[var(--coral)] hover:bg-orange-655 text-white rounded-xl text-xs font-bold disabled:bg-[#f5f1ea] disabled:text-[#8a8175] disabled:cursor-not-allowed transition-all flex items-center justify-center gap-1.5 shadow-md shadow-orange-200/50"
                >
                  {isIngestLoading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Đang trích xuất...
                    </>
                  ) : (
                    <>
                      <PlusCircle className="w-3.5 h-3.5" />
                      Trích xuất ngay
                    </>
                  )}
                </button>
              ) : (
                <button
                  type="submit"
                  form="drawer-file-form"
                  disabled={isIngestLoading || !file}
                  className="flex-1 py-2.5 bg-[var(--coral)] hover:bg-orange-655 text-white rounded-xl text-xs font-bold disabled:bg-[#f5f1ea] disabled:text-[#8a8175] disabled:cursor-not-allowed transition-all flex items-center justify-center gap-1.5 shadow-md shadow-orange-200/50"
                >
                  {isIngestLoading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Đang xử lý...
                    </>
                  ) : (
                    <>
                      <PlusCircle className="w-3.5 h-3.5" />
                      Tải lên & Xử lý
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Integrated Extractions Preview Modal */}
      {isPreviewOpen && currentPreview && (
        <div className="fixed inset-0 z-[99999] flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-md animate-fade-in"
          onClick={() => setIsPreviewOpen(false)}
        >
          <div className="bg-white rounded-3xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl border border-[#e7e1d8] animate-zoom-in overflow-hidden text-left relative"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="absolute top-0 left-0 right-0 h-[5px] bg-[var(--coral)]" />
            
            {/* Modal Header */}
            <div className="px-6 py-5 border-b border-[#f5f1ea] flex items-center justify-between bg-stone-50 pt-6">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-orange-50 border border-orange-100 flex items-center justify-center flex-shrink-0 text-[var(--coral)] shadow-sm">
                  <FileText className="w-4.5 h-4.5" />
                </div>
                <div className="min-w-0">
                  <span className="text-[9px] font-extrabold uppercase tracking-wider text-[#b28b2a] bg-[#fdf6e2] border border-[#f5ebcd] px-2.5 py-0.5 rounded-full">
                    Bản xem trước RAG Markdown
                  </span>
                  <h4 className="text-sm font-bold text-[#2d2a26] truncate mt-1 max-w-lg" title={decodeUrlSafely(currentPreview.source_input || "")}>
                    {decodeUrlSafely(currentPreview.source_input || "Tài liệu trích xuất")}
                  </h4>
                </div>
              </div>
              <button 
                onClick={() => setIsPreviewOpen(false)}
                className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-stone-200 text-[#8a8175] hover:text-[#2d2a26] transition-all"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto bg-[#FAF9F5] flex-1 border-b border-[#e7e1d8] shadow-inner">
              <div className="prose prose-stone prose-sm max-w-none prose-headings:font-extrabold prose-p:text-[#6f675d] leading-relaxed text-slate-700 text-xs">
                <ReactMarkdown>
                  {currentPreview.markdown}
                </ReactMarkdown>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 flex items-center justify-between bg-white rounded-b-3xl">
              <button
                onClick={handleCopy}
                className="flex items-center gap-2 px-4 py-2 bg-stone-50 hover:bg-stone-100 text-[#2d2a26] text-xs font-bold rounded-xl border border-[#e7e1d8] transition-all shadow-sm active:scale-95"
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4 text-emerald-600" />
                    Đã sao chép!
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 text-stone-450" />
                    Sao chép Markdown
                  </>
                )}
              </button>
              
              <button
                onClick={() => setIsPreviewOpen(false)}
                className="px-5 py-2 bg-[var(--coral)] hover:bg-orange-600 text-white font-bold text-xs rounded-xl shadow-md transition-all active:scale-95"
              >
                Đóng đầu đọc
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
