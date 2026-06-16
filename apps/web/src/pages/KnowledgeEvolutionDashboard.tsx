import { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { graphDraftsApi, type KnowledgeDraft } from "@/lib/api/brain"
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

function IconGraph({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="12" cy="12" r="3" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="6" r="3" />
      <line x1="9" y1="15" x2="12" y2="12" />
      <line x1="12" y1="12" x2="15" y2="9" />
    </svg>
  )
}

function IconBook({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
      <path d="M6 6h10" />
      <path d="M6 10h10" />
    </svg>
  )
}

const CHANGE_TYPE_LABELS: Record<string, { label: string; color: string; bg: string; border: string }> = {
  add_node: { label: "Thêm Thực thể", color: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-100" },
  add_edge: { label: "Thêm Quan hệ", color: "text-blue-700", bg: "bg-blue-50", border: "border-blue-100" },
  update_node: { label: "Cập nhật Thực thể", color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-100" },
  contradiction: { label: "Phát hiện Mâu thuẫn", color: "text-red-700", bg: "bg-red-50", border: "border-red-100" },
}

export function KnowledgeEvolutionDashboard() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const isAdminOrEditor = user?.role === "admin" || user?.role === "editor"

  const [drafts, setDrafts] = useState<KnowledgeDraft[]>([])
  const [selectedDraft, setSelectedDraft] = useState<KnowledgeDraft | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>("pending")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [adminNotes, setAdminNotes] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const fetchDrafts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await graphDraftsApi.list({ status: statusFilter })
      setDrafts(res || [])
      setSelectedDraft(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không thể tải danh sách bản thảo đồ thị")
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
      await graphDraftsApi.review(selectedDraft.id, {
        status,
        comment: adminNotes.trim() || undefined,
      })
      alert(status === "approved" ? "Đã phê duyệt và đồng bộ vào Neo4j + PostgreSQL thành công!" : "Đã từ chối bản thảo tri thức.")
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
        <div className="w-16 h-16 rounded-2xl bg-red-50 flex items-center justify-center mb-4 text-red-600 border border-red-100 animate-bounce">
          <IconAlert />
        </div>
        <h2 className="text-xl font-display font-semibold text-[#141413]">Không có quyền truy cập</h2>
        <p className="text-sm text-[#8e8b82] max-w-sm mt-1">
          Chỉ có Quản trị viên mới có quyền truy cập bảng điều khiển tiến hóa tri thức lịch sử (HITL Pipeline).
        </p>
        <button
          onClick={() => navigate("/wiki")}
          className="mt-6 px-4 py-2 bg-[#cc785c] text-white text-sm font-medium rounded-xl hover:bg-[#a9583e] transition-all cursor-pointer"
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
            className="w-8 h-8 rounded-lg hover:bg-[#f5f0e8] flex items-center justify-center text-[#6c6a64] hover:text-[#141413] transition-colors cursor-pointer"
          >
            <IconArrowLeft />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <IconGraph className="text-[#cc785c]" />
              <h2 className="text-xl font-display font-semibold text-[#141413]">Bảng điều khiển Tiến hóa Tri thức</h2>
            </div>
            <p className="text-xs text-[#8e8b82]">Duyệt các phát hiện thực thể & quan hệ mới từ mô hình suy luận đa tác nhân (HITL)</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-1.5 bg-[#f5f0e8] p-1 rounded-xl border border-[#e6dfd8]">
          {[
            { id: "pending", label: "Đang chờ duyệt" },
            { id: "approved", label: "Đã duyệt" },
            { id: "rejected", label: "Bị từ chối" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setStatusFilter(t.id)}
              className={cn(
                "px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer",
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

      {/* Main Content Area */}
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
              <p className="text-xs">Không có đề xuất tri thức nào ({statusFilter === "pending" ? "chờ duyệt" : statusFilter})</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {drafts.map((d) => {
                const labelMeta = CHANGE_TYPE_LABELS[d.change_type] || { label: d.change_type, color: "text-gray-700", bg: "bg-gray-50", border: "border-gray-100" }
                const title = d.change_type.includes("edge") 
                  ? `${d.draft_data.source_slug} ➔ ${d.draft_data.target_slug}`
                  : d.draft_data.name || d.draft_data.slug || "Thực thể không tên"

                return (
                  <button
                    key={d.id}
                    onClick={() => {
                      setSelectedDraft(d)
                      setAdminNotes("")
                    }}
                    className={cn(
                      "w-full text-left p-4 rounded-xl border transition-all text-xs flex flex-col gap-2 cursor-pointer",
                      selectedDraft?.id === d.id
                        ? "bg-[#faf9f5] border-[#cc785c] shadow-sm"
                        : "bg-white border-[#e6dfd8] hover:border-[#cc785c]/40"
                    )}
                  >
                    <div className="flex justify-between items-start gap-1">
                      <span className="font-semibold text-[#141413] text-sm line-clamp-1 flex-1">
                        {title}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span className={cn("text-[9px] px-1.5 py-0.5 rounded font-medium border", labelMeta.bg, labelMeta.color, labelMeta.border)}>
                        {labelMeta.label}
                      </span>
                    </div>

                    {d.draft_data.description && (
                      <p className="text-[#6c6a64] line-clamp-2 leading-normal mt-0.5">{d.draft_data.description}</p>
                    )}

                    <div className="flex items-center justify-between text-[10px] text-[#8e8b82] mt-1 border-t border-[#f5f0e8] pt-1.5">
                      <span>ID: {d.id.substring(0, 8)}...</span>
                      <span>{new Date(d.created_at).toLocaleDateString("vi-VN")}</span>
                    </div>
                  </button>
                )
              })}
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
                      CHI TIẾT PHÁT HIỆN TRI THỨC MỚI
                    </span>
                    <h3 className="text-xl font-display font-semibold text-[#141413] mt-1">
                      {selectedDraft.change_type.includes("edge")
                        ? `Liên kết quan hệ: ${selectedDraft.draft_data.edge_type}`
                        : `Thực thể đồ thị: ${selectedDraft.draft_data.name}`}
                    </h3>
                  </div>
                  <div className="text-xs text-[#8e8b82] text-right">
                    <p>Ngày đề xuất: {new Date(selectedDraft.created_at).toLocaleString("vi-VN")}</p>
                    {selectedDraft.updated_at && (
                      <p className="mt-1">Ngày cập nhật: {new Date(selectedDraft.updated_at).toLocaleString("vi-VN")}</p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 border-t border-[#f5f0e8] pt-4 text-xs">
                  <div>
                    <span className="text-[#8e8b82]">Loại thay đổi:</span>
                    <p className="font-semibold text-[#3d3d3a] mt-0.5 uppercase tracking-wider text-[#cc785c]">
                      {CHANGE_TYPE_LABELS[selectedDraft.change_type]?.label}
                    </p>
                  </div>
                  <div>
                    <span className="text-[#8e8b82]">Nguồn trích xuất:</span>
                    <p className="font-semibold text-[#3d3d3a] mt-0.5">
                      {selectedDraft.source_info?.source_page ? (
                        <span className="flex items-center gap-1">
                          <IconBook className="w-3.5 h-3.5 text-[#6c6a64]" />
                          Trang Wiki: "{selectedDraft.source_info.source_page}"
                        </span>
                      ) : "Trực tiếp từ Phiên chat nghiên cứu (Multi-agent Consolidation)"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Visualization Card based on type */}
              <div className="bg-white border border-[#e6dfd8] rounded-2xl p-6 shadow-sm space-y-4">
                <h4 className="text-xs font-semibold text-[#141413] uppercase tracking-wider border-b border-[#f5f0e8] pb-2">
                  Dữ liệu kỹ thuật (Draft Data Payload)
                </h4>

                {selectedDraft.change_type === "add_node" || selectedDraft.change_type === "update_node" ? (
                  <div className="space-y-4">
                    {/* Visual Node Representation */}
                    <div className="flex items-center gap-4 bg-[#faf9f5] border border-[#e6dfd8] rounded-2xl p-4">
                      <div className="w-14 h-14 rounded-full bg-[#cc785c]/10 text-[#cc785c] flex items-center justify-center font-display font-bold text-lg border-2 border-[#cc785c]/20 shadow-inner">
                        {selectedDraft.draft_data.node_type?.substring(0, 2).toUpperCase() || "NO"}
                      </div>
                      <div>
                        <h4 className="text-base font-semibold text-[#141413]">{selectedDraft.draft_data.name}</h4>
                        <span className="text-xs text-[#8e8b82] font-mono">slug: {selectedDraft.draft_data.slug}</span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-xs">
                      <div className="bg-[#faf9f5] border border-[#e6dfd8] p-3 rounded-xl">
                        <span className="text-[#8e8b82] block mb-1">Loại thực thể (Node Type)</span>
                        <strong className="text-sm text-[#141413]">{selectedDraft.draft_data.node_type || "Concept"}</strong>
                      </div>
                      <div className="bg-[#faf9f5] border border-[#e6dfd8] p-3 rounded-xl">
                        <span className="text-[#8e8b82] block mb-1">ID hệ thống đề xuất</span>
                        <strong className="text-[10px] font-mono text-[#141413] block truncate">{selectedDraft.id}</strong>
                      </div>
                    </div>

                    {selectedDraft.draft_data.description && (
                      <div className="bg-[#faf9f5] border border-[#e6dfd8] p-4 rounded-xl">
                        <span className="text-[#8e8b82] text-xs block mb-1">Mô tả thực thể</span>
                        <p className="text-sm text-[#3d3d3a] leading-relaxed">{selectedDraft.draft_data.description}</p>
                      </div>
                    )}
                  </div>
                ) : selectedDraft.change_type === "add_edge" ? (
                  <div className="space-y-4">
                    {/* Visual Connector Representation */}
                    <div className="flex items-center justify-between gap-4 bg-[#faf9f5] border border-[#e6dfd8] rounded-2xl p-6 relative overflow-hidden">
                      {/* Source */}
                      <div className="flex flex-col items-center gap-1 z-10">
                        <div className="w-12 h-12 rounded-full bg-white border border-[#e6dfd8] text-[#141413] flex items-center justify-center font-semibold text-xs shadow-sm">
                          SRC
                        </div>
                        <span className="text-[10px] font-semibold text-[#141413] max-w-[100px] truncate" title={selectedDraft.draft_data.source_slug}>
                          {selectedDraft.draft_data.source_slug}
                        </span>
                      </div>

                      {/* Connection Line */}
                      <div className="flex-1 flex flex-col items-center justify-center relative">
                        <div className="w-full h-0.5 bg-dashed bg-[#cc785c] opacity-60 border-t border-dashed border-[#cc785c]"></div>
                        <span className="absolute -top-4 bg-white px-2 py-0.5 border border-[#e6dfd8] text-[9px] font-bold text-[#cc785c] rounded-full uppercase tracking-wider shadow-sm">
                          {selectedDraft.draft_data.edge_type}
                        </span>
                        <span className="text-[8px] text-[#8e8b82] mt-1">Trọng số (weight): {selectedDraft.draft_data.weight || 1.0}</span>
                      </div>

                      {/* Target */}
                      <div className="flex flex-col items-center gap-1 z-10">
                        <div className="w-12 h-12 rounded-full bg-white border border-[#e6dfd8] text-[#141413] flex items-center justify-center font-semibold text-xs shadow-sm">
                          TGT
                        </div>
                        <span className="text-[10px] font-semibold text-[#141413] max-w-[100px] truncate" title={selectedDraft.draft_data.target_slug}>
                          {selectedDraft.draft_data.target_slug}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-xs">
                      <div className="bg-[#faf9f5] border border-[#e6dfd8] p-3 rounded-xl">
                        <span className="text-[#8e8b82] block mb-1">Mối quan hệ (Relationship Edge)</span>
                        <strong className="text-sm text-[#141413] uppercase">{selectedDraft.draft_data.edge_type || "RELATED_TO"}</strong>
                      </div>
                      <div className="bg-[#faf9f5] border border-[#e6dfd8] p-3 rounded-xl">
                        <span className="text-[#8e8b82] block mb-1">Trọng số liên kết</span>
                        <strong className="text-sm text-[#141413]">{selectedDraft.draft_data.weight || "1.0"}</strong>
                      </div>
                    </div>

                    {selectedDraft.draft_data.description && (
                      <div className="bg-[#faf9f5] border border-[#e6dfd8] p-4 rounded-xl">
                        <span className="text-[#8e8b82] text-xs block mb-1">Mô tả bối cảnh quan hệ</span>
                        <p className="text-sm text-[#3d3d3a] leading-relaxed">{selectedDraft.draft_data.description}</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Contradiction visual */}
                    <div className="bg-red-50 border border-red-100 rounded-2xl p-5 text-red-800 space-y-2">
                      <div className="flex items-center gap-2">
                        <IconAlert className="w-5 h-5 text-red-600" />
                        <h4 className="font-semibold text-sm">Phát hiện Tri thức Lịch sử xung đột</h4>
                      </div>
                      <p className="text-xs text-red-700 leading-relaxed">
                        Hệ thống Multi-agent trong quá trình suy luận và phản tư đã phát hiện thông tin mới mâu thuẫn trực tiếp với đồ thị tri thức hiện tại.
                      </p>
                    </div>

                    <div className="bg-[#faf9f5] border border-[#e6dfd8] p-4 rounded-xl space-y-3">
                      <div>
                        <span className="text-[#8e8b82] text-[10px] font-bold block uppercase">Chi tiết xung đột</span>
                        <p className="text-sm text-[#3d3d3a] leading-relaxed whitespace-pre-line mt-1">
                          {selectedDraft.draft_data.conflict_description || "Xung đột tri thức giữa thông tin mới trích xuất và cơ sở dữ liệu."}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Source/Citation Context */}
              {selectedDraft.source_info && Object.keys(selectedDraft.source_info).length > 0 && (
                <div className="bg-white border border-[#e6dfd8] rounded-2xl p-6 shadow-sm space-y-3">
                  <h4 className="text-xs font-semibold text-[#141413] uppercase tracking-wider border-b border-[#f5f0e8] pb-2">
                    Bằng chứng & Nguồn dẫn (Grounding Sources)
                  </h4>
                  <div className="space-y-3.5">
                    {selectedDraft.source_info.excerpt && (
                      <div className="bg-[#faf9f5] border-l-4 border-[#cc785c] rounded-r-xl p-4 italic text-sm text-[#6c6a64] leading-relaxed">
                        "{selectedDraft.source_info.excerpt}"
                      </div>
                    )}
                    <div className="text-xs text-[#8e8b82] flex flex-wrap gap-x-6 gap-y-2">
                      {selectedDraft.source_info.page_id && (
                        <span>ID nguồn: <strong className="text-[#6c6a64]">{selectedDraft.source_info.page_id}</strong></span>
                      )}
                      {selectedDraft.source_info.confidence && (
                        <span>Độ tin cậy trích xuất: <strong className="text-emerald-600">{Math.round(selectedDraft.source_info.confidence * 100)}%</strong></span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Review Panel Area */}
              <div className="bg-white border border-[#e6dfd8] rounded-2xl p-6 shadow-md space-y-4">
                <h4 className="text-sm font-semibold text-[#141413] uppercase tracking-wider">Hành động Phê duyệt (HITL Gatekeeper)</h4>
                
                <div>
                  <label className="block text-xs font-semibold text-[#6c6a64] uppercase tracking-wider mb-1.5">
                    Ý kiến nhận xét của Quản trị viên
                  </label>
                  <textarea
                    value={adminNotes}
                    onChange={(e) => setAdminNotes(e.target.value)}
                    placeholder="Lưu ý phê duyệt, lý do từ chối thực thể hoặc ghi chú hiệu chỉnh..."
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
                      <IconX /> Từ chối đề xuất
                    </button>
                    <button
                      onClick={() => handleReview("approved")}
                      disabled={submitting}
                      className="flex items-center gap-1.5 px-5 py-2 bg-[#cc785c] text-white font-medium text-sm rounded-xl hover:bg-[#a9583e] transition-all cursor-pointer shadow-sm disabled:opacity-50"
                    >
                      <IconCheck /> Duyệt & Đồng bộ Neo4j + Postgres
                    </button>
                  </div>
                ) : (
                  <div className="pt-2 border-t border-[#f5f0e8] flex justify-between items-center text-xs">
                    <span className="text-[#8e8b82]">Trạng thái bản thảo tri thức:</span>
                    <span className={cn(
                      "font-semibold px-2.5 py-1 rounded-full text-[10px] border uppercase",
                      selectedDraft.status === "approved" 
                        ? "bg-emerald-50 text-emerald-700 border-emerald-100" 
                        : "bg-red-50 text-red-700 border-red-100"
                    )}>
                      {selectedDraft.status === "approved" ? "Đã duyệt & Ghi đồ thị" : "Đã từ chối"}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center text-[#8e8b82] py-24">
              <div className="w-16 h-16 rounded-2xl bg-white border border-[#e6dfd8] flex items-center justify-center mb-4 shadow-sm animate-pulse">
                <IconGraph className="w-8 h-8 text-[#8e8b82] opacity-60" />
              </div>
              <h4 className="font-display font-semibold text-[#141413] text-sm">Chưa chọn bản thảo tri thức</h4>
              <p className="text-xs mt-1">Chọn một đề xuất phát hiện thực thể / quan hệ ở danh sách bên trái để kiểm tra và xét duyệt.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
