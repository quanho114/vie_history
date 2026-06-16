import { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { draftsApi, projectsApi, type WikiPageDraft, type Project } from "@/lib/api/brain"
import { useAuthStore } from "@/stores/authStore"
import { cn } from "@/lib/utils/cn"

// ── Icons ──────────────────────────────────────────────
function IconArrowLeft({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="m12 19-7-7 7-7" /><path d="M19 12H5" />
    </svg>
  )
}

function IconCheck({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

function IconX({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  )
}

function IconAlert({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  )
}

function IconClock({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
    </svg>
  )
}

const SECTION_LABELS: Record<string, string> = {
  background: "Bối cảnh",
  causes: "Nguyên nhân",
  main_events: "Diễn biến chính",
  results: "Kết quả",
  significance: "Ý nghĩa lịch sử",
  people: "Nhân vật liên quan",
  timeline: "Mốc thời gian",
  references: "Nguồn tham khảo",
}

export function DraftsReviewPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const isAdminOrEditor = user?.role === "admin" || user?.role === "editor"

  const [drafts, setDrafts] = useState<WikiPageDraft[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedDraft, setSelectedDraft] = useState<WikiPageDraft | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>("pending")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [adminNotes, setAdminNotes] = useState("")
  const [submitting, setSubmitting] = useState(false)

  // Fetch projects maps
  useEffect(() => {
    if (!isAdminOrEditor) return
    projectsApi.list()
      .then((res) => setProjects(res.projects || []))
      .catch((e) => console.error("Không thể tải danh sách dự án", e))
  }, [isAdminOrEditor])

  const fetchDrafts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await draftsApi.list({ status: statusFilter })
      setDrafts(res || [])
      setSelectedDraft(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không thể tải danh sách bản thảo")
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    if (isAdminOrEditor) {
      fetchDrafts()
    }
  }, [fetchDrafts, isAdminOrEditor])

  const handleReview = async (status: "approved" | "rejected") => {
    if (!selectedDraft) return
    setSubmitting(true)
    try {
      await draftsApi.review(selectedDraft.id, {
        status,
        admin_notes: adminNotes.trim() || undefined,
      })
      alert(status === "approved" ? "Đã phê duyệt bản thảo thành công!" : "Đã từ chối bản thảo.")
      setAdminNotes("")
      fetchDrafts()
    } catch (err) {
      alert(err instanceof Error ? err.message : "Thao tác phê duyệt thất bại")
    } finally {
      setSubmitting(false)
    }
  }

  // Permission Check Block
  if (!isAdminOrEditor) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-[#faf9f5] p-6 text-center">
        <div className="w-16 h-16 rounded-2xl bg-red-50 flex items-center justify-center mb-4 text-red-600 border border-red-100">
          <IconAlert />
        </div>
        <h2 className="text-xl font-display font-semibold text-[#141413]">Không có quyền truy cập</h2>
        <p className="text-sm text-[#8e8b82] max-w-sm mt-1">
          Chỉ có Quản trị viên hoặc Biên tập viên mới có quyền xem và xét duyệt các bản thảo đề xuất wiki.
        </p>
        <button
          onClick={() => navigate("/wiki")}
          className="mt-6 px-4 py-2 bg-[#cc785c] text-white text-sm font-medium rounded-xl hover:bg-[#a9583e] transition-all"
        >
          Quay lại Wiki
        </button>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#faf9f5]">
      {/* Header */}
      <header className="px-8 py-5 border-b border-[#e6dfd8] bg-white shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/wiki")}
            className="w-8 h-8 rounded-lg hover:bg-[#f5f0e8] flex items-center justify-center text-[#6c6a64] hover:text-[#141413] transition-colors"
          >
            <IconArrowLeft />
          </button>
          <div>
            <h2 className="text-xl font-display font-semibold text-[#141413]">Xét duyệt Đề xuất Wiki</h2>
            <p className="text-xs text-[#8e8b82]">Xem và duyệt các thay đổi do cộng đồng hoặc trợ lý đề xuất</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-1.5 bg-[#f5f0e8] p-1 rounded-xl border border-[#e6dfd8]">
          {[
            { id: "pending", label: "Đang chờ" },
            { id: "approved", label: "Đã duyệt" },
            { id: "rejected", label: "Bị từ chối" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setStatusFilter(t.id)}
              className={cn(
                "px-3 py-1.5 text-xs font-semibold rounded-lg transition-all",
                statusFilter === t.id
                  ? "bg-white text-[#cc785c] shadow-sm"
                  : "text-[#6c6a64] hover:text-[#cc785c]"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </header>

      {/* Main Review Dashboard Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column: Drafts List */}
        <div className="w-80 border-r border-[#e6dfd8] bg-white flex flex-col flex-shrink-0">
          {loading ? (
            <div className="p-4 space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="animate-pulse bg-[#faf9f5] border border-[#e6dfd8] rounded-xl p-4 space-y-2">
                  <div className="h-4 w-3/4 rounded bg-[#e8e0d2]" />
                  <div className="h-3 w-1/2 rounded bg-[#ebe6df]" />
                </div>
              ))}
            </div>
          ) : drafts.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-[#8e8b82]">
              <IconClock className="w-8 h-8 mb-2 opacity-50" />
              <p className="text-xs">Không có bản thảo nào ({statusFilter})</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {drafts.map((d) => (
                <button
                  key={d.id}
                  onClick={() => {
                    setSelectedDraft(d)
                    setAdminNotes(d.admin_notes || "")
                  }}
                  className={cn(
                    "w-full text-left p-4 rounded-xl border transition-all text-xs flex flex-col gap-1.5 cursor-pointer",
                    selectedDraft?.id === d.id
                      ? "bg-[#faf9f5] border-[#cc785c] shadow-sm"
                      : "bg-white border-[#e6dfd8] hover:border-[#cc785c]/40"
                  )}
                >
                  <div className="flex justify-between items-start gap-1">
                    <span className="font-semibold text-[#141413] text-sm line-clamp-1 flex-1">
                      {d.title}
                    </span>
                    {d.wiki_page_id ? (
                      <span className="bg-amber-50 text-amber-700 border border-amber-100 text-[9px] px-1 rounded font-medium">Chỉnh sửa</span>
                    ) : (
                      <span className="bg-emerald-50 text-emerald-700 border border-emerald-100 text-[9px] px-1 rounded font-medium">Tạo mới</span>
                    )}
                  </div>
                  {d.summary && (
                    <p className="text-[#6c6a64] line-clamp-2 leading-normal">{d.summary}</p>
                  )}
                  <div className="flex items-center justify-between text-[10px] text-[#8e8b82] mt-1 border-t border-[#f5f0e8] pt-1.5">
                    <span>Dự án: {projects.find(p => p.id === d.project_id)?.name || "Chung"}</span>
                    <span>{new Date(d.created_at).toLocaleDateString("vi-VN")}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Draft Detail View & Review Panel */}
        <div className="flex-1 bg-[#faf9f5] overflow-y-auto p-8">
          {selectedDraft ? (
            <div className="max-w-3xl mx-auto space-y-6">
              {/* Draft Info Header Card */}
              <div className="bg-white border border-[#e6dfd8] rounded-2xl p-6 shadow-sm space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-[10px] font-semibold text-[#cc785c] uppercase tracking-wider">
                      Chi tiết bản thảo đề xuất
                    </span>
                    <h3 className="text-xl font-display font-semibold text-[#141413] mt-1">
                      {selectedDraft.title}
                    </h3>
                  </div>
                  <div className="text-xs text-[#8e8b82] text-right">
                    <p>Ngày đề xuất: {new Date(selectedDraft.created_at).toLocaleString("vi-VN")}</p>
                    {selectedDraft.reviewed_at && (
                      <p className="mt-1">Ngày duyệt: {new Date(selectedDraft.reviewed_at).toLocaleString("vi-VN")}</p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 border-t border-[#f5f0e8] pt-4 text-xs">
                  <div>
                    <span className="text-[#8e8b82]">Dự án áp dụng:</span>
                    <p className="font-semibold text-[#3d3d3a] mt-0.5">
                      {projects.find((p) => p.id === selectedDraft.project_id)?.name || "Chung"}
                    </p>
                  </div>
                  <div>
                    <span className="text-[#8e8b82]">Trang gốc:</span>
                    <p className="font-semibold text-[#3d3d3a] mt-0.5">
                      {selectedDraft.wiki_page_id ? `ID: ${selectedDraft.wiki_page_id} (Đang cập nhật)` : "Không có (Trang wiki mới)"}
                    </p>
                  </div>
                </div>

                {selectedDraft.summary && (
                  <div className="bg-[#faf9f5] border border-[#e6dfd8] rounded-xl p-4">
                    <span className="text-[10px] font-bold text-[#8e8b82] uppercase tracking-wider block mb-1">
                      Mô tả tóm tắt
                    </span>
                    <p className="text-sm text-[#3d3d3a] leading-relaxed">{selectedDraft.summary}</p>
                  </div>
                )}
              </div>

              {/* Draft Sections Content Detail */}
              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-[#141413] uppercase tracking-wider">Nội dung đề xuất</h4>
                {selectedDraft.content && Object.keys(selectedDraft.content).length > 0 ? (
                  Object.entries(selectedDraft.content).map(([key, val]) => {
                    if (!val || typeof val !== "string" || !val.trim()) return null
                    return (
                      <div key={key} className="bg-white border border-[#e6dfd8] rounded-xl p-5 shadow-sm">
                        <h5 className="font-display font-medium text-sm text-[#141413] border-b border-[#f5f0e8] pb-2 mb-3">
                          {SECTION_LABELS[key] || key}
                        </h5>
                        <p className="text-sm text-[#3d3d3a] leading-relaxed whitespace-pre-line">
                          {val.trim()}
                        </p>
                      </div>
                    )
                  }).filter(Boolean)
                ) : (
                  <div className="bg-white border border-[#e6dfd8] rounded-xl p-5 shadow-sm text-center text-xs text-[#8e8b82] italic">
                    Bản thảo này không có nội dung phần mục.
                  </div>
                )}
              </div>

              {/* Review Panel Area */}
              <div className="bg-white border border-[#e6dfd8] rounded-2xl p-6 shadow-md space-y-4">
                <h4 className="text-sm font-semibold text-[#141413] uppercase tracking-wider">Ghi chú & Duyệt bản thảo</h4>
                
                <div>
                  <label className="block text-xs font-semibold text-[#6c6a64] uppercase tracking-wider mb-1.5">
                    Ghi chú của Biên tập viên / Admin
                  </label>
                  <textarea
                    value={adminNotes}
                    onChange={(e) => setAdminNotes(e.target.value)}
                    placeholder="Ghi lý do phê duyệt/từ chối, góp ý sửa đổi..."
                    disabled={selectedDraft.status !== "pending" || submitting}
                    rows={3}
                    className="w-full px-3.5 py-2.5 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#141413] outline-none focus:border-[#cc785c] focus:bg-white transition-all disabled:opacity-75 disabled:bg-gray-50 resize-none"
                  />
                </div>

                {selectedDraft.status === "pending" ? (
                  <div className="flex justify-end gap-3 pt-2">
                    <button
                      onClick={() => handleReview("rejected")}
                      disabled={submitting}
                      className="flex items-center gap-1.5 px-4 py-2 border border-red-200 text-red-600 font-medium text-sm rounded-xl hover:bg-red-50 hover:border-red-300 transition-all cursor-pointer disabled:opacity-50"
                    >
                      <IconX /> Từ chối
                    </button>
                    <button
                      onClick={() => handleReview("approved")}
                      disabled={submitting}
                      className="flex items-center gap-1.5 px-5 py-2 bg-[#cc785c] text-white font-medium text-sm rounded-xl hover:bg-[#a9583e] transition-all cursor-pointer shadow-sm disabled:opacity-50"
                    >
                      <IconCheck /> Phê duyệt & Cập nhật Wiki
                    </button>
                  </div>
                ) : (
                  <div className="pt-2 border-t border-[#f5f0e8] flex justify-between items-center text-xs">
                    <span className="text-[#8e8b82]">Trạng thái bản thảo:</span>
                    <span className={cn(
                      "font-semibold px-2.5 py-1 rounded-full text-[10px] border uppercase",
                      selectedDraft.status === "approved" 
                        ? "bg-emerald-50 text-emerald-700 border-emerald-100" 
                        : "bg-red-50 text-red-700 border-red-100"
                    )}>
                      {selectedDraft.status === "approved" ? "Đã duyệt" : "Đã từ chối"}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center text-[#8e8b82] py-24">
              <div className="w-16 h-16 rounded-2xl bg-white border border-[#e6dfd8] flex items-center justify-center mb-4 shadow-sm">
                <IconClock className="w-8 h-8 text-[#8e8b82] opacity-60" />
              </div>
              <h4 className="font-display font-semibold text-[#141413] text-sm">Chưa chọn bản thảo</h4>
              <p className="text-xs mt-1">Chọn một bản thảo ở danh sách bên trái để kiểm tra và phê duyệt.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
