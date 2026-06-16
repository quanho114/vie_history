import { useEffect, useState, useCallback } from "react"
import { useDocumentStore } from "@/stores/documentStore"
import { brainApi, type BrainJob, type BrainPlan } from "@/lib/api/brain"
import { formatDate } from "@/lib/utils/format"
import { cn } from "@/lib/utils/cn"

// ── Icons ──────────────────────────────────────────────
function IconSettings({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

function IconLayers({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <polygon points="12 2 2 7 12 12 22 7 12 2" /><polygon points="2 17 12 22 22 17" /><polygon points="2 12 12 17 22 12" />
    </svg>
  )
}

function IconLoader({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <line x1="12" y1="2" x2="12" y2="6" /><line x1="12" y1="18" x2="12" y2="22" /><line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
      <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" /><line x1="2" y1="12" x2="6" y2="12" /><line x1="18" y1="12" x2="22" y2="12" />
      <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" /><line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
    </svg>
  )
}

function IconCheck({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

function IconX({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

function IconEye({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function IconSparkles({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
    </svg>
  )
}

const renderSummaryOrCoordinates = (summary: string) => {
  if (!summary) return null;
  
  // Detect coordinates by looking for °B, °N, °Đ, °T or semicolons
  const isGeographic = summary.includes("°") || summary.includes(";");
  if (isGeographic) {
    // Try to extract location name inside parenthesis
    const match = summary.match(/\(([^)]+)\)/);
    const locationName = match ? match[1] : null;
    const coordinateText = summary.split("(")[0]?.trim();
    
    return (
      <div className="flex flex-wrap items-center gap-1.5 mt-2">
        {locationName && (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-[#fdf6f0] border border-[#f5e7db] text-[10px] text-[#cc785c] font-medium shadow-sm">
            <svg xmlns="http://www.w3.org/2000/svg" width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="mr-0.5 text-[#cc785c]">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
              <circle cx="12" cy="10" r="3" />
            </svg>
            {locationName}
          </span>
        )}
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-gray-50 border border-gray-200 text-[10px] text-gray-500 font-mono shadow-sm">
          🌐 {coordinateText}
        </span>
      </div>
    );
  }
  
  return <p className="text-[11px] text-[#6c6a64] mt-1.5 line-clamp-2 leading-relaxed">{summary}</p>;
};

function getStatCard(label: string, value: any) {
  const labelLower = label.toLowerCase();
  let icon = null;
  let bgClass = "";
  let textClass = "";
  let borderClass = "";
  
  if (labelLower === "wiki") {
    icon = (
      <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="text-[#cc785c]">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      </svg>
    );
    bgClass = "bg-[#fdf6f0]";
    textClass = "text-[#cc785c]";
    borderClass = "border-[#f5e7db]";
  } else if (labelLower === "timeline") {
    icon = (
      <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-600">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    );
    bgClass = "bg-[#f0f7ff]";
    textClass = "text-blue-600";
    borderClass = "border-[#e0f0ff]";
  } else if (labelLower === "nodes") {
    icon = (
      <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-600">
        <circle cx="12" cy="5" r="3" />
        <circle cx="5" cy="19" r="3" />
        <circle cx="19" cy="19" r="3" />
        <line x1="12" y1="8" x2="6.5" y2="16.5" />
        <line x1="12" y1="8" x2="17.5" y2="16.5" />
      </svg>
    );
    bgClass = "bg-[#f0fdf4]";
    textClass = "text-emerald-600";
    borderClass = "border-[#dcfce7]";
  } else { // edges
    icon = (
      <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="text-purple-600">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    );
    bgClass = "bg-[#faf5ff]";
    textClass = "text-purple-600";
    borderClass = "border-[#f3e8ff]";
  }
  
  return (
    <div key={label} className={cn("rounded-xl border px-3.5 py-1.5 flex items-center justify-between shadow-[0_1px_2px_rgba(0,0,0,0.01)] transition-all hover:scale-[1.015]", bgClass, borderClass)}>
      <div className="space-y-0.5">
        <p className="text-[9px] font-bold uppercase tracking-wider text-[#8e8b82]">{label}</p>
        <p className={cn("text-sm font-bold leading-tight font-mono", textClass)}>{String(value)}</p>
      </div>
      <div className={cn("w-5.5 h-5.5 rounded-lg flex items-center justify-center bg-white border shadow-[0_1px_2px_rgba(0,0,0,0.02)]", borderClass)}>
        {icon}
      </div>
    </div>
  );
}

function formatDocTitle(title: string): string {
  if (!title) return "Tài liệu chưa đặt tên";
  try {
    if (title.startsWith("http://") || title.startsWith("https://")) {
      const decoded = decodeURIComponent(title);
      // Extract Wikipedia page title if possible
      if (decoded.includes("wikipedia.org/wiki/")) {
        const parts = decoded.split("wikipedia.org/wiki/");
        if (parts[1]) {
          return parts[1].replace(/_/g, " ");
        }
      }
      return decoded;
    }
  } catch (e) {
    // Ignore error and fall back
  }
  return title;
}

function getSourceBadge(domain: string) {
  const isWiki = domain?.includes("wikipedia.org");
  return {
    label: isWiki ? "Wikipedia" : (domain || "Tài liệu"),
    isWiki
  };
}

export function BrainBuilderPage() {
  const { documents, loadDocuments } = useDocumentStore()
  
  // Dashboard states
  const [activeTab, setActiveTab] = useState<"build" | "jobs" | "plans">("build")
  const [jobs, setJobs] = useState<BrainJob[]>([])
  const [plans, setPlans] = useState<BrainPlan[]>([])
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([])
  const [docSearch, setDocSearch] = useState("")
  
  const [loading, setLoading] = useState(false)
  const [jobsLoading, setJobsLoading] = useState(false)
  const [plansLoading, setPlansLoading] = useState(false)
  
  // Review Drawer States
  const [selectedPlan, setSelectedPlan] = useState<BrainPlan | null>(null)
  const [adminNotes, setAdminNotes] = useState("")
  const [submittingReview, setSubmittingReview] = useState(false)

  // Fetch document lists
  useEffect(() => {
    loadDocuments({ page: 1, status: "approved" })
  }, [loadDocuments])

  // Fetch Jobs
  const fetchJobs = useCallback(async () => {
    setJobsLoading(true)
    try {
      const res = await brainApi.getJobs()
      setJobs(res.jobs || [])
    } catch (e) {
      console.error("Không thể tải danh sách build jobs", e)
    } finally {
      setJobsLoading(false)
    }
  }, [])

  // Fetch Plans
  const fetchPlans = useCallback(async () => {
    setPlansLoading(true)
    try {
      const res = await brainApi.getPlans()
      setPlans(res.plans || [])
    } catch (e) {
      console.error("Không thể tải kế hoạch đề xuất", e)
    } finally {
      setPlansLoading(false)
    }
  }, [])

  useEffect(() => {
    if (activeTab === "jobs") fetchJobs()
    if (activeTab === "plans") fetchPlans()
  }, [activeTab, fetchJobs, fetchPlans])

  // Auto-poll jobs every 5s when there are running/pending jobs
  useEffect(() => {
    if (activeTab !== "jobs") return
    const hasActive = jobs.some(
      (j) => j.status === "running" || j.status === "pending"
    )
    if (!hasActive) return
    const interval = setInterval(fetchJobs, 5000)
    return () => clearInterval(interval)
  }, [activeTab, jobs, fetchJobs])

  // Select all toggler — guard against empty document list
  const handleToggleSelectAll = () => {
    if (documents.length === 0) return
    if (selectedDocIds.length === documents.length) {
      setSelectedDocIds([])
    } else {
      setSelectedDocIds(documents.map((d) => d.id))
    }
  }

  // Document check toggler
  const handleToggleDoc = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    )
  }

  // Start Job Pipeline
  const handleStartPipeline = async () => {
    if (selectedDocIds.length === 0) return
    setLoading(true)
    try {
      await brainApi.startJob(selectedDocIds)
      alert("Khởi chạy tiến trình thành công! Đang chuyển sang tab Jobs để theo dõi.")
      setSelectedDocIds([])
      setActiveTab("jobs")
    } catch (err) {
      alert(err instanceof Error ? err.message : "Có lỗi xảy ra khi bắt đầu tiến trình.")
    } finally {
      setLoading(false)
    }
  }

  // Review actions (approve / reject)
  const handleReviewPlan = async (approve: boolean) => {
    if (!selectedPlan) return
    setSubmittingReview(true)
    try {
      if (approve) {
        await brainApi.approvePlan(selectedPlan.id, adminNotes)
        alert("Đã phê duyệt kế hoạch thành công! Trang wiki đang được biên dịch ngầm.")
      } else {
        await brainApi.rejectPlan(selectedPlan.id, adminNotes)
        alert("Đã bác bỏ kế hoạch đề xuất.")
      }
      setSelectedPlan(null)
      setAdminNotes("")
      fetchPlans()
    } catch (err) {
      alert(err instanceof Error ? err.message : "Thao tác duyệt kế hoạch thất bại.")
    } finally {
      setSubmittingReview(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#faf9f5]">
      {/* Header */}
      <header className="px-8 py-5 border-b border-[#e6dfd8] bg-white shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#f5f0e8] flex items-center justify-center">
            <IconSettings className="text-[#cc785c]" />
          </div>
          <div>
            <h2 className="text-xl font-display font-semibold text-[#141413]">Trình biên dịch Tri thức</h2>
            <p className="text-xs text-[#8e8b82]">Quản lý tiến trình Map-Reduce-Plan để tổng hợp Wiki lịch sử có cấu trúc</p>
          </div>
        </div>
      </header>

      {/* Tabs list navigation */}
      <div className="px-8 border-b border-[#e6dfd8] bg-white flex-shrink-0 flex items-center gap-4">
        <button
          onClick={() => setActiveTab("build")}
          className={cn(
            "py-3.5 text-xs font-semibold uppercase tracking-wider border-b-2 transition-all",
            activeTab === "build"
              ? "border-[#cc785c] text-[#cc785c]"
              : "border-transparent text-[#8e8b82] hover:text-[#141413]"
          )}
        >
          Khởi chạy Job
        </button>
        <button
          onClick={() => setActiveTab("jobs")}
          className={cn(
            "py-3.5 text-xs font-semibold uppercase tracking-wider border-b-2 transition-all",
            activeTab === "jobs"
              ? "border-[#cc785c] text-[#cc785c]"
              : "border-transparent text-[#8e8b82] hover:text-[#141413]"
          )}
        >
          Tiến trình Jobs ({jobs.length})
        </button>
        <button
          onClick={() => setActiveTab("plans")}
          className={cn(
            "py-3.5 text-xs font-semibold uppercase tracking-wider border-b-2 transition-all",
            activeTab === "plans"
              ? "border-[#cc785c] text-[#cc785c]"
              : "border-transparent text-[#8e8b82] hover:text-[#141413]"
          )}
        >
          Phê duyệt kế hoạch ({plans.length})
        </button>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 overflow-y-auto p-8">
        
        {/* Tab 1: Build launch */}
        {activeTab === "build" && (() => {
          const filteredDocs = documents.filter((doc) => {
            const titleMatch = formatDocTitle(doc.title).toLowerCase().includes(docSearch.toLowerCase());
            const domainMatch = (doc.source_domain || "").toLowerCase().includes(docSearch.toLowerCase());
            const summaryMatch = (doc.summary || "").toLowerCase().includes(docSearch.toLowerCase());
            return titleMatch || domainMatch || summaryMatch;
          });
          return (
            <div className="max-w-4xl mx-auto space-y-6">
              <div className="bg-gradient-to-r from-[#fcfbf9] to-[#f5f0e8] border border-[#e6dfd8] rounded-2xl p-6 shadow-[0_2px_8px_rgba(0,0,0,0.01)] flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                  <h4 className="text-sm font-semibold text-[#141413] flex items-center gap-2">
                    <IconSparkles className="text-[#cc785c]" />
                    Biên dịch tư liệu thô thành Wiki tri thức
                  </h4>
                  <p className="text-xs text-[#6c6a64] leading-relaxed max-w-2xl">
                    Chọn các tài liệu lịch sử đã duyệt bên dưới. Mô hình ngôn ngữ Gemini sẽ tiến hành trích xuất (Map),
                    phân loại chủ đề (Reduce), và đề xuất kế hoạch tạo các trang Wiki liên kết (Plan). Quá trình này sẽ dừng lại để bạn phê duyệt trước khi ghi dữ liệu thật.
                  </p>
                </div>
                <button
                  onClick={handleStartPipeline}
                  disabled={selectedDocIds.length === 0 || loading}
                  className="flex items-center justify-center gap-1.5 px-5 py-2.5 bg-[#cc785c] disabled:bg-[#ebe6df] text-white disabled:text-[#8e8b82] text-xs font-semibold rounded-xl hover:bg-[#a9583e] active:scale-[0.98] transition-all shadow-sm flex-shrink-0"
                >
                  {loading ? <IconLoader className="animate-spin" /> : <IconSparkles />}
                  Biên dịch ({selectedDocIds.length} tài liệu)
                </button>
              </div>

              {/* Ingested Documents List */}
              <div className="bg-white border border-[#e6dfd8] rounded-2xl overflow-hidden shadow-sm">
                {/* Header & Search */}
                <div className="px-5 py-4 border-b border-[#e6dfd8] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-[#faf9f5]">
                  <div className="relative flex-1 max-w-xs">
                    <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <svg className="h-4 w-4 text-[#8e8b82]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </span>
                    <input
                      type="text"
                      value={docSearch}
                      onChange={(e) => setDocSearch(e.target.value)}
                      placeholder="Tìm kiếm tài liệu đã duyệt..."
                      className="w-full pl-9 pr-4 py-1.5 bg-white border border-[#e6dfd8] rounded-xl text-xs outline-none focus:border-[#cc785c] focus:ring-1 focus:ring-[#cc785c] transition-all placeholder:text-[#8e8b82]"
                    />
                  </div>
                  <div className="flex items-center justify-between sm:justify-end gap-4">
                    <span className="text-xs font-semibold text-[#6c6a64]">
                      Đã chọn <span className="text-[#cc785c] font-bold">{selectedDocIds.length}</span>/{documents.length}
                    </span>
                    <div className="w-[1px] h-3.5 bg-[#e6dfd8] hidden sm:block" />
                    <button
                      onClick={handleToggleSelectAll}
                      className="text-xs text-[#cc785c] font-semibold hover:underline"
                    >
                      {selectedDocIds.length === documents.length ? "Bỏ chọn tất cả" : "Chọn tất cả"}
                    </button>
                  </div>
                </div>

                {/* Documents List */}
                <div className="divide-y divide-[#f5f0e8] max-h-[30rem] overflow-y-auto">
                  {filteredDocs.map((doc) => {
                    const isSelected = selectedDocIds.includes(doc.id);
                    const source = getSourceBadge(doc.source_domain || "");
                    return (
                      <label
                        key={doc.id}
                        className={cn(
                          "flex items-start gap-4 p-4 cursor-pointer transition-all border-l-4 select-none",
                          isSelected 
                            ? "bg-[#faf6f0] border-l-[#cc785c]" 
                            : "hover:bg-[#fbfaf7] border-l-transparent"
                        )}
                      >
                        <div className="mt-1 flex-shrink-0">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleToggleDoc(doc.id)}
                            className="w-4 h-4 text-[#cc785c] border-[#e6dfd8] rounded focus:ring-[#cc785c] accent-[#cc785c]"
                          />
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-xs font-semibold text-[#141413] leading-snug">
                              {formatDocTitle(doc.title)}
                            </span>
                            <span className={cn(
                              "inline-flex items-center px-2 py-0.5 rounded text-[9px] font-bold border",
                              source.isWiki
                                ? "bg-blue-50 text-blue-700 border-blue-100"
                                : "bg-[#f5f0e8] text-[#6c6a64] border-[#e6dfd8]"
                            )}>
                              {source.isWiki ? "📚 Wikipedia" : `🌐 ${source.label}`}
                            </span>
                          </div>
                          
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-[10px] text-[#8e8b82]">
                              {formatDate(doc.created_at)}
                            </span>
                          </div>
                          
                          {renderSummaryOrCoordinates(doc.summary)}
                        </div>
                      </label>
                    );
                  })}

                  {filteredDocs.length === 0 && (
                    <div className="text-center py-16 px-4">
                      <svg className="mx-auto h-8 w-8 text-[#8e8b82] opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <p className="text-xs text-[#8e8b82] mt-3 font-medium">
                        {docSearch ? "Không tìm thấy tài liệu phù hợp." : "Chưa có tài liệu đã duyệt để biên dịch."}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })()}

        {/* Tab 2: Jobs list */}
        {activeTab === "jobs" && (
          <div className="max-w-4xl mx-auto">
            {jobsLoading ? (
              <div className="flex items-center justify-center py-16 text-[#8e8b82]">
                <IconLoader className="animate-spin w-6 h-6 mr-2" /> Đang tải tiến trình...
              </div>
            ) : jobs.length === 0 ? (
              <div className="text-center py-16 px-4 bg-white border border-[#e6dfd8] rounded-2xl">
                <svg className="mx-auto h-8 w-8 text-[#8e8b82] opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-xs text-[#8e8b82] mt-3 font-medium">Chưa có job biên dịch nào được khởi chạy.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {jobs.map((job) => {
                  const statusColors = {
                    done: "bg-green-50 text-green-700 border-green-200",
                    partial: "bg-orange-50 text-orange-700 border-orange-200",
                    failed: "bg-red-50 text-red-700 border-red-200",
                    running: "bg-blue-50 text-blue-700 border-blue-200 animate-pulse",
                    pending: "bg-yellow-50 text-yellow-700 border-yellow-200",
                    awaiting_review: "bg-purple-50 text-purple-700 border-purple-200",
                  }[job.status] || "bg-stone-50 text-stone-700 border-stone-200";

                  const statusLabel = {
                    done: "Hoàn thành",
                    partial: "Một phần",
                    failed: "Lỗi",
                    running: "Đang chạy...",
                    pending: "Đang chờ",
                    awaiting_review: "Chờ duyệt kế hoạch",
                  }[job.status] || job.status;

                  return (
                    <div
                      key={job.id}
                      className="bg-white border border-[#e6dfd8] rounded-2xl p-5 hover:border-[#cc785c]/40 hover:shadow-[0_4px_12px_rgba(204,120,92,0.02)] transition-all duration-300"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[#f5f0e8] pb-3.5 mb-4">
                        <div className="flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-[#cc785c]" />
                          <span className="text-[10px] font-bold text-[#8e8b82] uppercase tracking-wider font-mono">
                            Job ID: {job.id.slice(0, 8).toUpperCase()}...
                          </span>
                          <span className={cn("px-2.5 py-0.5 text-[9px] rounded-full font-bold uppercase border", statusColors)}>
                            {statusLabel}
                          </span>
                        </div>
                        <span className="text-[10px] text-[#8e8b82] font-semibold flex items-center gap-1">
                          ⏱️ Khởi chạy: {formatDate(job.created_at)}
                        </span>
                      </div>
                      
                      <div className="space-y-4">
                        <div className="flex items-center gap-2 text-xs text-[#6c6a64] font-semibold">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#cc785c]">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                            <line x1="16" y1="13" x2="8" y2="13" />
                            <line x1="16" y1="17" x2="8" y2="17" />
                          </svg>
                          Tổng hợp từ <span className="font-bold text-[#141413]">{job.source_document_ids?.length ?? job.document_ids?.length ?? 0} tài liệu</span>
                        </div>

                        {job.result_summary && (
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {[
                              ["Wiki", job.result_summary.wiki_pages_created ?? (Array.isArray(job.result_summary.committed_pages) ? job.result_summary.committed_pages.length : 0)],
                              ["Timeline", job.result_summary.timeline_events_created ?? 0],
                              ["Nodes", job.result_summary.graph_nodes_created ?? 0],
                              ["Edges", job.result_summary.graph_edges_created ?? 0],
                            ].map(([label, value]) => getStatCard(label, value))}
                          </div>
                        )}

                        {job.error_message && (
                          <div className={cn(
                            "border rounded-xl p-3 text-[11px] font-mono leading-normal bg-red-50 text-red-700 border-red-100 flex items-start gap-2"
                          )}>
                            ⚠️ <span className="flex-1">{job.error_message}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Pending Plans Review */}
        {activeTab === "plans" && (
          <div className="max-w-4xl mx-auto space-y-4">
            {plansLoading ? (
              <div className="flex items-center justify-center py-16 text-[#8e8b82]">
                <IconLoader className="animate-spin w-6 h-6 mr-2" /> Đang tải kế hoạch...
              </div>
            ) : plans.length === 0 ? (
              <div className="text-center py-16 px-4 bg-white border border-[#e6dfd8] rounded-2xl">
                <svg className="mx-auto h-8 w-8 text-[#8e8b82] opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h.01M12 12h.01M15 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <p className="text-xs text-[#8e8b82] mt-3 font-medium">Hiện không có bản thảo kế hoạch nào.</p>
              </div>
            ) : (
              <div className="grid gap-4">
                {plans.map((plan) => {
                  const statusColors = {
                    approved: "bg-green-50 text-green-700 border-green-200",
                    rejected: "bg-red-50 text-red-700 border-red-200",
                    partial: "bg-orange-50 text-orange-700 border-orange-200",
                    pending: "bg-yellow-50 text-yellow-700 border-yellow-200",
                  }[plan.status] || "bg-stone-50 text-stone-700 border-stone-200";

                  const statusLabel = {
                    approved: "Đã duyệt",
                    rejected: "Đã bác bỏ",
                    partial: "Duyệt một phần",
                    pending: "Chờ duyệt",
                  }[plan.status] || plan.status;

                  return (
                    <div
                      key={plan.id}
                      className="bg-white border border-[#e6dfd8] rounded-2xl p-5 shadow-sm hover:border-[#cc785c]/40 hover:shadow-[0_4px_12px_rgba(204,120,92,0.02)] transition-all duration-300 flex flex-col md:flex-row md:items-center justify-between gap-4"
                    >
                      <div className="space-y-2 flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold text-[#8e8b82] uppercase tracking-wider font-mono">Plan ID: {plan.id.slice(0, 8).toUpperCase()}...</span>
                          <span className={cn("px-2.5 py-0.5 text-[9px] rounded-full font-bold uppercase border", statusColors)}>
                            {statusLabel}
                          </span>
                        </div>
                        
                        <p className="text-xs font-bold text-[#141413]">
                          Kế hoạch biên dịch: <span className="text-[#cc785c]">{plan.proposed_pages?.length || 0} trang đề xuất</span>
                        </p>
                        
                        <p className="text-[10px] text-[#8e8b82] font-semibold">Tạo lúc: {formatDate(plan.created_at)}</p>

                        {/* Preview proposed pages tags */}
                        {Array.isArray(plan.proposed_pages) && plan.proposed_pages.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-2">
                            {plan.proposed_pages.slice(0, 3).map((p: any, idx: number) => (
                              <span key={idx} className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-[#fdfaf5] border border-[#f5ece0] text-[10px] font-semibold text-[#6c6a64]">
                                📖 {p.title}
                              </span>
                            ))}
                            {plan.proposed_pages.length > 3 && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-[#fdf6f0] border border-[#f5e7db] text-[10px] font-bold text-[#cc785c]">
                                + {plan.proposed_pages.length - 3} trang khác
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      <button
                        onClick={() => {
                          setSelectedPlan(plan)
                          setAdminNotes("")
                        }}
                        className={cn(
                          "flex items-center justify-center gap-1.5 px-4 py-2.5 text-xs font-semibold rounded-xl transition-all shadow-sm self-start md:self-center flex-shrink-0",
                          plan.status === "pending"
                            ? "bg-[#cc785c] text-white hover:bg-[#a9583e]"
                            : "bg-[#f5f0e8] hover:bg-[#e6dfd8] text-[#141413]"
                        )}
                      >
                        {plan.status === "pending" ? (
                          <>✍️ Chi tiết & Duyệt</>
                        ) : (
                          <><IconEye /> Xem chi tiết</>
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Plans Review Details Side Drawer / Overlay */}
      {selectedPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/40 backdrop-blur-[1.5px]">
          <div className="w-full max-w-xl h-full bg-[#faf9f5] border-l border-[#e6dfd8] flex flex-col shadow-2xl animate-slide-in">
            {/* Header */}
            <header className="px-6 py-4 border-b border-[#e6dfd8] bg-white flex items-center justify-between flex-shrink-0">
              <h3 className="font-display text-sm font-bold text-[#141413]">Duyệt kế hoạch Wiki đề xuất</h3>
              <button
                onClick={() => setSelectedPlan(null)}
                className="w-7 h-7 rounded-full flex items-center justify-center text-[#8e8b82] hover:bg-[#f5f0e8] transition-colors"
              >
                <IconX />
              </button>
            </header>

            {/* Proposed pages list */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <div className="bg-[#f5f0e8] border border-[#e6dfd8] rounded-xl p-4 text-xs text-[#6c6a64] leading-relaxed">
                <span className="font-bold text-[#141413]">Hệ thống AI đề xuất xây dựng các trang sau:</span>
              </div>

              {/* Proposed pages details loop */}
              {Array.isArray(selectedPlan.proposed_pages) && selectedPlan.proposed_pages.map((p: any, idx: number) => (
                <div key={idx} className="bg-white border border-[#e6dfd8] rounded-xl p-4 shadow-sm space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#141413] text-sm">{p.title}</span>
                    <span className="px-2 py-0.5 bg-[#f5f0e8] text-[#8e8b82] border border-[#e6dfd8] rounded text-[9px] uppercase tracking-wider font-semibold">
                      {p.event_type || "sự kiện"}
                    </span>
                  </div>
                  {p.period && <p className="text-[10px] text-[#cc785c] font-semibold">{p.period.replace(/-/g, " ").toUpperCase()}</p>}
                  <p className="text-[#6c6a64] leading-relaxed">{p.summary}</p>
                  {p.reason && (
                    <div className="mt-2 pt-2 border-t border-[#f5f0e8] text-[10px] italic text-[#8e8b82]">
                      Lý do: {p.reason}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Admin notes input & Actions */}
            {selectedPlan.status === "pending" ? (
              <div className="p-6 border-t border-[#e6dfd8] bg-white flex flex-col gap-4 flex-shrink-0 text-xs">
                <div className="space-y-1">
                  <label className="font-bold text-[#3d3d3a]">Điều chỉnh / Ghi chú (Admin Notes)</label>
                  <textarea
                    value={adminNotes}
                    onChange={(e) => setAdminNotes(e.target.value)}
                    placeholder="Nhập yêu cầu điều chỉnh hoặc phê chuẩn (Tùy chọn)..."
                    rows={2}
                    className="w-full bg-[#fbfaf7] border border-[#e6dfd8] rounded-xl px-3 py-2 outline-none focus:border-[#cc785c]"
                  />
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => handleReviewPlan(false)}
                    disabled={submittingReview}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2.5 border border-[#e6dfd8] text-red-600 hover:bg-red-50 rounded-xl font-bold transition-all"
                  >
                    <IconX /> Bác bỏ (Reject)
                  </button>
                  <button
                    onClick={() => handleReviewPlan(true)}
                    disabled={submittingReview}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2.5 bg-[#cc785c] hover:bg-[#a9583e] text-white rounded-xl font-bold transition-all shadow-sm"
                  >
                    <IconCheck /> Phê duyệt (Approve)
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-6 border-t border-[#e6dfd8] bg-white flex flex-col gap-3 flex-shrink-0 text-xs text-center">
                <p className="text-[#8e8b82] font-semibold">
                  Kế hoạch này đã được xử lý ở trạng thái:{" "}
                  <span className={cn(
                    "font-bold uppercase",
                    selectedPlan.status === "approved" ? "text-green-600" : "text-red-600"
                  )}>
                    {selectedPlan.status === "approved" ? "Đã duyệt" : "Đã bác bỏ"}
                  </span>
                </p>
                <button
                  onClick={() => setSelectedPlan(null)}
                  className="py-2.5 bg-[#f5f0e8] hover:bg-[#e6dfd8] text-[#141413] rounded-xl font-bold transition-all"
                >
                  Đóng
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
