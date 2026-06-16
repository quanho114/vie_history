import { useEffect, useState, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useIngestStore, useDocumentStore } from "@/stores/documentStore"
import { formatDate } from "@/lib/utils/format"
import { cn } from "@/lib/utils/cn"
import { 
  PlusCircle, 
  Link as LinkIcon, 
  Loader2, 
  AlertCircle, 
  CheckCircle, 
  Clock, 
  Zap, 
  UploadCloud, 
  FileText, 
  Tag as TagIcon, 
  History, 
  FileUp, 
  Globe,
  Eye,
  X,
  Copy,
  Check,
  Search,
  FolderOpen
} from "lucide-react"
import ReactMarkdown from "react-markdown"

export function IngestPage() {
  const navigate = useNavigate()
  
  // Drawer & Modal control
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [isPreviewOpen, setIsPreviewOpen] = useState(false)
  
  // Form states
  const [url, setUrl] = useState("")
  const [tags, setTags] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [copied, setCopied] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  // Document search state (for the drawer)
  const [docSearch, setDocSearch] = useState("")
  
  // Stores
  const { jobs, loadJobs, submitUrl, submitFile, getPreview, currentPreview, isLoading: isIngestLoading } = useIngestStore()
  const { documents, loadDocuments, isLoading: isDocsLoading } = useDocumentStore()

  useEffect(() => {
    loadJobs()
  }, [loadJobs])

  // Fetch documents when drawer is open
  useEffect(() => {
    if (isDrawerOpen) {
      loadDocuments({ search: docSearch || undefined })
    }
  }, [isDrawerOpen, docSearch, loadDocuments])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    try {
      const jobId = await submitUrl(url.trim(), tags.split(",").map((t) => t.trim()).filter(Boolean))
      await getPreview(jobId)
      setIsPreviewOpen(true) // Tự động mở khung xem nội dung khi nạp xong
      setUrl("")
      setTags("")
    } catch {
      // Error handled by store
    }
  }

  const handleFileSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    try {
      const jobId = await submitFile(file, tags.split(",").map((t) => t.trim()).filter(Boolean))
      await getPreview(jobId)
      setIsPreviewOpen(true) // Tự động mở khung xem nội dung khi nạp xong
      setFile(null)
      setTags("")
    } catch {
      // Error handled by store
    }
  }

  // Handle drag events
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  // Handle drop event
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

  // Mở xem trước nội dung của một job cũ trong lịch sử
  const handleViewPreview = async (jobId: string) => {
    try {
      await getPreview(jobId)
      setIsPreviewOpen(true)
    } catch {
      // Error handled by store
    }
  }

  const handleCopy = () => {
    if (currentPreview) {
      navigator.clipboard.writeText(currentPreview.markdown)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Beautifully decode encoded Vietnamese URLs for readability
  const decodeUrlSafely = (urlStr: string) => {
    try {
      return decodeURIComponent(urlStr)
    } catch {
      return urlStr
    }
  }

  // Pure Vietnamese mapping for stages/status
  const statusConfig = {
    done: { 
      icon: CheckCircle, 
      color: "text-emerald-600 bg-emerald-50 border-emerald-100", 
      label: "Hoàn thành" 
    },
    failed: { 
      icon: AlertCircle, 
      color: "text-rose-600 bg-rose-50 border-rose-100", 
      label: "Thất bại" 
    },
    running: { 
      icon: Loader2, 
      color: "text-amber-600 bg-amber-50 border-amber-100", 
      label: "Đang xử lý" 
    },
    queued: { 
      icon: Clock, 
      color: "text-slate-600 bg-slate-50 border-slate-100", 
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
    <div className="h-full flex flex-col bg-canvas relative overflow-hidden">
      
      {/* Header */}
      <header className="px-8 py-5 border-b border-hairline bg-white shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center shadow-inner">
            <Zap className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <h2 className="text-xl font-display font-semibold text-ink">Nhập dữ liệu nguồn</h2>
            <p className="text-xs text-soft">Cung cấp tư liệu lịch sử cho AI thông qua URL hoặc tập tin số hóa</p>
          </div>
        </div>
        
        {/* Beautiful Header Actions - Viewing Extracted Documents Button */}
        <button
          onClick={() => setIsDrawerOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-primary text-white text-sm font-semibold rounded-xl hover:bg-coral-hover shadow-sm hover:shadow active:scale-[0.98] transition-all"
        >
          <FolderOpen className="w-4 h-4" />
          Xem tài liệu đã trích xuất
        </button>
      </header>

      <div className="flex-1 overflow-y-auto p-8 space-y-8 max-w-6xl mx-auto w-full">
        
        {/* Two Column Input Methods */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Method 1: URL Ingest */}
          <div className="bg-white rounded-2xl p-6 border border-hairline shadow-sm flex flex-col justify-between hover:shadow-md transition-all duration-300">
            <div>
              <h3 className="font-display font-semibold text-lg text-ink mb-2 flex items-center gap-2">
                <Globe className="w-5 h-5 text-primary-500" />
                Trích xuất từ địa chỉ URL
              </h3>
              <p className="text-xs text-soft mb-6">
                Nhập các liên kết tài liệu, bài báo lịch sử (ví dụ: Wikipedia, báo nhân dân, thư viện điện tử...)
              </p>
              
              <form id="url-form" onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-body-strong mb-1.5 uppercase tracking-wider">
                    Đường dẫn liên kết (URL)
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                      <LinkIcon className="h-4 w-4 text-soft" />
                    </div>
                    <input
                      type="url"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      required
                      placeholder="https://vi.wikipedia.org/wiki/..."
                      className="w-full pl-10 pr-4 py-3 bg-surface-50 border border-hairline rounded-xl text-ink placeholder-soft focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-400 transition-all text-sm shadow-inner"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-body-strong mb-1.5 uppercase tracking-wider">
                    Thẻ phân loại <span className="text-soft font-normal">(phân tách bằng dấu phẩy)</span>
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                      <TagIcon className="h-4 w-4 text-soft" />
                    </div>
                    <input
                      type="text"
                      value={tags}
                      onChange={(e) => setTags(e.target.value)}
                      placeholder="chiến tranh, hồ chí minh, 1945..."
                      className="w-full pl-10 pr-4 py-3 bg-surface-50 border border-hairline rounded-xl text-ink placeholder-soft focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-400 transition-all text-sm shadow-inner"
                    />
                  </div>
                  {tags.trim() && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {tags.split(",").map((t) => t.trim()).filter(Boolean).map((tag, idx) => (
                        <span key={idx} className="bg-primary-50 text-primary-700 text-xs px-2 py-0.5 rounded-md font-medium border border-primary-100">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </form>
            </div>
            
            <div className="mt-6 pt-4 border-t border-hairline-soft">
              <button
                type="submit"
                form="url-form"
                disabled={isIngestLoading || !url.trim()}
                className="w-full py-3 bg-primary text-white rounded-xl font-semibold hover:bg-coral-hover disabled:bg-surface-soft disabled:text-soft disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2 shadow-sm active:scale-[0.98]"
              >
                {isIngestLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlusCircle className="w-4 h-4" />}
                Trích xuất ngay
              </button>
            </div>
          </div>

          {/* Method 2: File Upload (Drag and Drop) */}
          <div className="bg-white rounded-2xl p-6 border border-hairline shadow-sm flex flex-col justify-between hover:shadow-md transition-all duration-300">
            <div>
              <h3 className="font-display font-semibold text-lg text-ink mb-2 flex items-center gap-2">
                <FileUp className="w-5 h-5 text-primary-500" />
                Tải lên tập tin số hóa
              </h3>
              <p className="text-xs text-soft mb-6">
                Chấp nhận tài liệu dạng văn bản thô hoặc PDF đã quét nội dung (giới hạn: PDF, Markdown, TXT)
              </p>
              
              <form id="file-form" onSubmit={handleFileSubmit} className="space-y-4">
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
                    "w-full h-[154px] border-2 border-dashed rounded-xl flex flex-col items-center justify-center p-4 text-center cursor-pointer transition-all duration-200",
                    dragActive 
                      ? "border-primary bg-primary-50/50 shadow-inner" 
                      : file 
                        ? "border-emerald-400 bg-emerald-50/20" 
                        : "border-hairline hover:border-primary-300 hover:bg-surface-50"
                  )}
                >
                  {file ? (
                    <div className="space-y-2">
                      <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center mx-auto">
                        <FileText className="w-5 h-5 text-emerald-600" />
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-body-strong truncate max-w-[240px] mx-auto">{file.name}</p>
                        <p className="text-[10px] text-soft mt-0.5">{(file.size / 1024 / 1024).toFixed(2)} MB • Click để đổi file</p>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="w-10 h-10 rounded-full bg-surface-card flex items-center justify-center mx-auto text-soft">
                        <UploadCloud className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-xs font-medium text-body-strong">Kéo thả tệp tin vào đây</p>
                        <p className="text-[10px] text-soft mt-0.5">hoặc nhấp chuột để duyệt file</p>
                      </div>
                    </div>
                  )}
                </div>
              </form>
            </div>
            
            <div className="mt-6 pt-4 border-t border-hairline-soft">
              <button
                type="submit"
                form="file-form"
                disabled={isIngestLoading || !file}
                className="w-full py-3 bg-primary text-white rounded-xl font-semibold hover:bg-coral-hover disabled:bg-surface-soft disabled:text-soft disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2 shadow-sm active:scale-[0.98]"
              >
                {isIngestLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlusCircle className="w-4 h-4" />}
                Tải lên và xử lý
              </button>
            </div>
          </div>

        </div>

        {/* Clean, Simple Ingestion History Card */}
        <div className="bg-white rounded-2xl p-6 border border-hairline shadow-sm">
          <div className="flex items-center justify-between mb-5">
            <h3 className="font-display font-semibold text-lg text-ink flex items-center gap-2">
              <History className="w-5 h-5 text-primary-500" />
              Lịch sử nhập liệu
            </h3>
            <span className="text-[11px] font-medium bg-surface-soft text-muted px-2.5 py-1 rounded-full border border-hairline-soft">
              Tổng số tác vụ: {jobs.length}
            </span>
          </div>
          
          <div className="space-y-3">
            {jobs.map((job) => {
              const config = statusConfig[job.status] || statusConfig.queued
              const Icon = config.icon
              return (
                <div
                  key={job.id}
                  className="rounded-xl p-4 border border-hairline-soft flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-surface-50/50 transition-all duration-200"
                >
                  <div className="flex items-center gap-3.5 min-w-0 flex-1">
                    <div className={cn("w-10 h-10 rounded-xl border flex items-center justify-center flex-shrink-0 shadow-sm", config.color)}>
                      <Icon className={cn("w-5 h-5", job.status === "running" ? "animate-spin" : "")} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p 
                        className="text-sm font-semibold text-ink truncate max-w-lg" 
                        title={decodeUrlSafely(job.source_input)}
                      >
                        {decodeUrlSafely(job.source_input)}
                      </p>
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-soft mt-1">
                        <span className="bg-surface-card text-muted px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider">
                          {job.source_type}
                        </span>
                        <span className="flex items-center gap-1">
                          Trạng thái: 
                          <strong className={cn("font-medium", 
                            job.status === "done" ? "text-emerald-600" : 
                            job.status === "failed" ? "text-rose-600" : 
                            job.status === "running" ? "text-amber-600" : "text-slate-500"
                          )}>
                            {config.label}
                          </strong>
                        </span>
                        {job.stage && (
                          <span className="text-muted/80">
                            • {getStageVietnamese(job.stage)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3 flex-shrink-0 self-end sm:self-center">
                    {job.status === "done" && (
                      <button
                        onClick={() => handleViewPreview(job.id)}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-soft hover:bg-surface-strong text-body-strong text-xs font-semibold rounded-lg border border-hairline-soft transition-all duration-150 active:scale-95 shadow-sm"
                      >
                        <Eye className="w-3.5 h-3.5 text-primary-600" />
                        Xem nội dung
                      </button>
                    )}
                    
                    {job.error_message && (
                      <div className="max-w-xs">
                        <p className="text-[11px] text-rose-500 bg-rose-50 border border-rose-100 rounded-lg px-2.5 py-1.5 inline-block">
                          Lỗi: {job.error_message}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
            
            {jobs.length === 0 && (
              <div className="text-center py-12 bg-surface-50 border border-dashed border-hairline rounded-xl">
                <div className="w-12 h-12 rounded-full bg-white flex items-center justify-center mx-auto text-soft/50 shadow-sm mb-3">
                  <History className="w-6 h-6" />
                </div>
                <p className="text-body-text text-sm font-medium">Chưa có tác vụ nhập liệu nào</p>
                <p className="text-soft text-xs mt-1">Các tư liệu bạn tải lên hoặc trích xuất sẽ được hiển thị tại đây</p>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Slide-over Right Drawer containing Extracted Documents */}
      {isDrawerOpen && (
        <div className="fixed inset-0 z-50 flex justify-end animate-in fade-in duration-200">
          
          {/* Backdrop Overlay */}
          <div 
            onClick={() => setIsDrawerOpen(false)}
            className="absolute inset-0 bg-surface-dark/30 backdrop-blur-[2px]"
          />
          
          {/* Drawer Container */}
          <div className="relative w-full max-w-md h-full bg-white shadow-2xl border-l border-hairline flex flex-col z-10 animate-in slide-in-from-right duration-300 ease-out">
            
            {/* Drawer Header */}
            <div className="px-6 py-5 border-b border-hairline bg-surface-50 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-primary-100 flex items-center justify-center text-primary-700">
                  <FileText className="w-4.5 h-4.5" />
                </div>
                <div>
                  <h3 className="font-display font-semibold text-base text-ink">Tài liệu đã trích xuất</h3>
                  <p className="text-[10px] text-soft">Kho dữ liệu Markdown ({documents.length})</p>
                </div>
              </div>
              
              <button 
                onClick={() => setIsDrawerOpen(false)}
                className="w-7 h-7 rounded-full flex items-center justify-center hover:bg-surface-card text-soft hover:text-ink transition-colors active:scale-90"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            {/* Drawer Search Filter */}
            <div className="p-4 border-b border-hairline-soft bg-white">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-soft" />
                <input
                  type="text"
                  value={docSearch}
                  onChange={(e) => setDocSearch(e.target.value)}
                  placeholder="Tìm kiếm tài liệu..."
                  className="w-full pl-9 pr-4 py-2 bg-surface-50 border border-hairline rounded-xl text-xs text-ink placeholder-soft focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-400 transition-all shadow-inner"
                />
              </div>
            </div>
            
            {/* Drawer Document List */}
            <div className="flex-1 overflow-y-auto p-4 bg-surface-50/50 space-y-3 shadow-inner">
              {isDocsLoading ? (
                <div className="flex items-center justify-center py-24">
                  <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
                </div>
              ) : documents.map((doc) => (
                <div
                  key={doc.id}
                  onClick={() => {
                    setIsDrawerOpen(false)
                    navigate(`/documents/${doc.id}`)
                  }}
                  className="bg-white rounded-xl p-4 border border-hairline-soft hover:border-primary-300 hover:shadow-sm cursor-pointer transition-all duration-150 group"
                >
                  <h4 className="text-xs font-semibold text-ink truncate group-hover:text-primary-600 transition-colors">
                    {doc.title}
                  </h4>
                  
                  <div className="flex items-center gap-2 text-[10px] text-soft mt-1.5">
                    {doc.source_domain && (
                      <span className="bg-surface-card px-1.5 py-0.5 rounded font-bold uppercase tracking-wider text-[8px]">
                        {doc.source_domain}
                      </span>
                    )}
                    <span>{formatDate(doc.created_at)}</span>
                  </div>
                  
                  {doc.tags && doc.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2.5">
                      {doc.tags.slice(0, 3).map((tag) => (
                        <span key={tag} className="text-primary-600 bg-primary-50 px-1.5 py-0.5 rounded text-[8px] border border-primary-50">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              
              {documents.length === 0 && !isDocsLoading && (
                <div className="text-center py-20 bg-white rounded-xl border border-dashed border-hairline-soft p-6">
                  <div className="w-10 h-10 rounded-full bg-surface-50 flex items-center justify-center mx-auto text-soft/50 shadow-inner mb-3">
                    <FileText className="w-5 h-5" />
                  </div>
                  <p className="text-body-strong text-xs font-medium">Không tìm thấy tài liệu nào</p>
                  <p className="text-[10px] text-soft mt-0.5">Nhập tài liệu mới để hiển thị tại đây</p>
                </div>
              )}
            </div>
            
            {/* Drawer Footer */}
            <div className="p-4 border-t border-hairline bg-white flex items-center justify-between">
              <span className="text-[10px] font-semibold text-soft">
                Tài liệu đã duyệt: {documents.filter(d => d.status === "approved").length}
              </span>
              <button
                onClick={() => {
                  setIsDrawerOpen(false)
                  navigate("/documents")
                }}
                className="text-xs font-semibold text-primary-600 hover:text-coral-hover flex items-center gap-0.5 transition-colors"
              >
                Quản lý kho tài liệu →
              </button>
            </div>
            
          </div>
        </div>
      )}

      {/* Modern High-End Overlay Modal Reader */}
      {isPreviewOpen && currentPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-surface-dark/40 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[85vh] flex flex-col shadow-2xl border border-hairline animate-in fade-in zoom-in-95 duration-200">
            
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-hairline flex items-center justify-between bg-surface-50 rounded-t-2xl">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-lg bg-primary-100 flex items-center justify-center flex-shrink-0 text-primary-700">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-primary-700 bg-primary-50 px-2 py-0.5 rounded-md border border-primary-100">
                    Bản trích xuất
                  </span>
                  <h4 className="text-sm font-semibold text-ink truncate mt-0.5 max-w-xl" title={decodeUrlSafely(currentPreview.source_input || "")}>
                    {decodeUrlSafely(currentPreview.source_input || "Tài liệu trích xuất")}
                  </h4>
                </div>
              </div>
              <button 
                onClick={() => setIsPreviewOpen(false)}
                className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-surface-card text-soft hover:text-ink transition-colors active:scale-90"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto bg-surface-50 flex-1 border-b border-hairline shadow-inner">
              <div className="prose prose-sm max-w-none prose-headings:font-display prose-headings:text-ink prose-p:text-body-text prose-strong:text-ink leading-relaxed">
                <ReactMarkdown>
                  {currentPreview.markdown}
                </ReactMarkdown>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 flex items-center justify-between bg-white rounded-b-2xl">
              <button
                onClick={handleCopy}
                className="flex items-center gap-2 px-4 py-2 bg-surface-soft hover:bg-surface-strong text-body-strong text-xs font-semibold rounded-xl border border-hairline-soft transition-all duration-150 active:scale-95"
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4 text-emerald-600 animate-in zoom-in duration-100" />
                    Đã sao chép!
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 text-soft" />
                    Sao chép Markdown
                  </>
                )}
              </button>
              
              <button
                onClick={() => setIsPreviewOpen(false)}
                className="px-5 py-2 bg-primary text-white font-semibold text-xs rounded-xl hover:bg-coral-hover shadow-sm transition-all duration-150 active:scale-95"
              >
                Đóng
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  )
}
