import { useEffect, useState, useCallback, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { wikiApi, projectsApi, draftsApi, type WikiPage, type Project } from "@/lib/api/brain"
import { useAuthStore } from "@/stores/authStore"
import { cn } from "@/lib/utils/cn"

// ── Infinite Scroll Hook ─────────────────────────────────
function useInfiniteScroll(fetchMore: () => void, hasMore: boolean) {
  const observerRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore) {
          fetchMore();
        }
      },
      { threshold: 0.1 }
    );
    if (observerRef.current) observer.observe(observerRef.current);
    return () => observer.disconnect();
  }, [hasMore, fetchMore]);
  return observerRef;
}

// ── Icons ──────────────────────────────────────────────
function IconSearch({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
    </svg>
  )
}

function IconBook({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  )
}

function IconChevronRight({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="m9 18 6-6-6-6" />
    </svg>
  )
}

function IconClose({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

// ── Period config ──────────────────────────────────────
const PERIODS = [
  { value: "", label: "Tất cả" },
  { value: "khang-chien-chong-phap", label: "Kháng chiến chống Pháp" },
  { value: "khang-chien-chong-my", label: "Kháng chiến chống Mỹ" },
  { value: "thong-nhat", label: "Thống nhất" },
]

const PERIOD_COLORS: Record<string, string> = {
  "khang-chien-chong-phap": "bg-blue-50 text-blue-700 border-blue-100",
  "khang-chien-chong-my": "bg-red-50 text-red-700 border-red-100",
  "thong-nhat": "bg-emerald-50 text-emerald-700 border-emerald-100",
  default: "bg-[#f5f0e8] text-[#6c6a64] border-[#e6dfd8]",
}

function getPeriodColor(period: string) {
  return PERIOD_COLORS[period] || PERIOD_COLORS.default
}

// ── Skeleton ───────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="bg-white border border-[#e6dfd8] rounded-xl shadow-sm p-5 animate-pulse">
      <div className="flex gap-2 mb-3">
        <div className="h-5 w-24 rounded-full bg-[#e8e0d2]" />
        <div className="h-5 w-16 rounded-full bg-[#e8e0d2]" />
      </div>
      <div className="h-5 w-3/4 rounded bg-[#e8e0d2] mb-2" />
      <div className="h-4 w-full rounded bg-[#ebe6df] mb-1" />
      <div className="h-4 w-5/6 rounded bg-[#ebe6df]" />
    </div>
  )
}

// ── Main component ─────────────────────────────────────
export function WikiBrowserPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [allPages, setAllPages] = useState<WikiPage[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState("")
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [period, setPeriod] = useState("")
  const [error, setError] = useState<string | null>(null)

  // Pagination state
  const [page, setPage] = useState(0)
  const pageSize = 20
  const [hasMore, setHasMore] = useState(true)

  // Reset pagination when filters change
  useEffect(() => {
    setPage(0)
    setAllPages([])
    setHasMore(true)
  }, [debouncedSearch, period, selectedProjectId])

  // Modals state
  const [isCreateProjectModalOpen, setIsCreateProjectModalOpen] = useState(false)
  const [newProjectName, setNewProjectName] = useState("")
  const [newProjectDesc, setNewProjectDesc] = useState("")
  const [projectSubmitting, setProjectSubmitting] = useState(false)

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [draftTitle, setDraftTitle] = useState("")
  const [draftProjectId, setDraftProjectId] = useState("")
  const [draftSummary, setDraftSummary] = useState("")
  const [draftSections, setDraftSections] = useState({
    background: "",
    causes: "",
    main_events: "",
    results: "",
    significance: "",
    people: "",
    timeline: "",
    references: "",
  })
  const [draftSubmitting, setDraftSubmitting] = useState(false)

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 350)
    return () => clearTimeout(timer)
  }, [search])

  // Fetch projects on mount
  useEffect(() => {
    projectsApi.list()
      .then((res) => setProjects(res.projects || []))
      .catch((e) => console.error("Không thể tải danh sách dự án", e))
  }, [])

  const fetchPages = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await wikiApi.getPages({
        search: debouncedSearch || undefined,
        period: period || undefined,
        project_id: selectedProjectId || undefined,
        offset: page * pageSize,
        limit: pageSize,
      })
      const newPages = res.pages || []
      if (page === 0) {
        setAllPages(newPages)
      } else {
        setAllPages(prev => [...prev, ...newPages])
      }
      setHasMore(newPages.length === pageSize)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không thể tải danh sách wiki")
      setAllPages([])
    } finally {
      setLoading(false)
    }
  }, [debouncedSearch, period, selectedProjectId, page, pageSize])

  const fetchMore = useCallback(() => {
    if (!loading && hasMore) {
      setPage(prev => prev + 1)
    }
  }, [loading, hasMore])

  const scrollRef = useInfiniteScroll(fetchMore, hasMore && !loading)

  useEffect(() => {
    fetchPages()
  }, [fetchPages])

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newProjectName.trim()) return
    setProjectSubmitting(true)
    try {
      const created = await projectsApi.create({
        name: newProjectName.trim(),
        description: newProjectDesc.trim() || undefined,
      })
      setProjects((prev) => [created, ...prev])
      setSelectedProjectId(created.id)
      setNewProjectName("")
      setNewProjectDesc("")
      setIsCreateProjectModalOpen(false)
    } catch (err) {
      alert(err instanceof Error ? err.message : "Không thể tạo dự án")
    } finally {
      setProjectSubmitting(false)
    }
  }

  const handleCreateDraft = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!draftTitle.trim()) {
      alert("Vui lòng điền tiêu đề trang")
      return
    }
    setDraftSubmitting(true)
    try {
      const content: Record<string, string> = {}
      Object.entries(draftSections).forEach(([k, v]) => {
        if (v.trim()) {
          content[k] = v.trim()
        }
      })

      await draftsApi.propose({
        title: draftTitle.trim(),
        project_id: draftProjectId || undefined,
        summary: draftSummary.trim() || undefined,
        content: Object.keys(content).length > 0 ? content : undefined,
      })

      alert("Đề xuất bản thảo trang mới thành công! Đang chờ duyệt.")
      setDraftTitle("")
      setDraftProjectId("")
      setDraftSummary("")
      setDraftSections({
        background: "",
        causes: "",
        main_events: "",
        results: "",
        significance: "",
        people: "",
        timeline: "",
        references: "",
      })
      setIsCreateModalOpen(false)
    } catch (err) {
      alert(err instanceof Error ? err.message : "Không thể tạo bản thảo đề xuất")
    } finally {
      setDraftSubmitting(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#faf9f5]">
      {/* Header */}
      <header className="px-8 py-5 border-b border-[#e6dfd8] bg-white shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#f5f0e8] flex items-center justify-center">
            <IconBook className="text-[#cc785c]" />
          </div>
          <div>
            <h2 className="text-xl font-display font-semibold text-[#141413]">Kho Wiki Lịch Sử</h2>
            <p className="text-xs text-[#8e8b82]">Tra cứu các sự kiện và nhân vật lịch sử Việt Nam</p>
          </div>
        </div>
        <div className="flex gap-2">
          {(user?.role === "admin" || user?.role === "editor") && (
            <button
              onClick={() => navigate("/wiki/drafts/review")}
              className="flex items-center gap-2 px-4 py-2 border border-[#e6dfd8] text-[#6c6a64] hover:text-[#cc785c] hover:border-[#cc785c]/40 text-sm font-medium rounded-xl transition-all bg-white"
            >
              Duyệt bản thảo
            </button>
          )}
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-[#cc785c] text-white text-sm font-medium rounded-xl hover:bg-[#a9583e] transition-all shadow-sm"
          >
            Đề xuất trang mới
          </button>
        </div>
      </header>

      {/* Search + Filters */}
      <div className="px-8 pt-6 pb-4 flex-shrink-0 space-y-3">
        <div className="flex gap-3 max-w-4xl">
          <div className="relative flex-1">
            <IconSearch className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#8e8b82]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm kiếm sự kiện, nhân vật, địa danh..."
              className="w-full pl-10 pr-4 py-2.5 bg-white border border-[#e6dfd8] rounded-xl text-sm text-[#141413] placeholder-[#8e8b82] outline-none focus:border-[#cc785c] focus:shadow-[0_0_0_3px_rgba(204,120,92,0.1)] transition-all"
            />
          </div>

          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
            className="px-4 py-2.5 bg-white border border-[#e6dfd8] rounded-xl text-sm text-[#6c6a64] outline-none focus:border-[#cc785c] transition-all cursor-pointer"
          >
            <option value="">Tất cả Dự án</option>
            {projects.map((proj) => (
              <option key={proj.id} value={proj.id}>
                {proj.name} {proj.slug !== proj.name && `(${proj.slug})`}
              </option>
            ))}
          </select>

          <button
            onClick={() => setIsCreateProjectModalOpen(true)}
            className="px-4 py-2.5 border border-[#e6dfd8] text-sm font-medium text-[#6c6a64] rounded-xl bg-white hover:border-[#cc785c] hover:text-[#cc785c] transition-all cursor-pointer"
          >
            + Dự án mới
          </button>
        </div>

        {/* Period pills */}
        <div className="flex flex-wrap gap-2">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={cn(
                "px-3.5 py-1.5 rounded-full text-xs font-medium border transition-all duration-150 cursor-pointer",
                period === p.value
                  ? "bg-[#cc785c] text-white border-[#cc785c] shadow-sm"
                  : "bg-white text-[#6c6a64] border-[#e6dfd8] hover:border-[#cc785c] hover:text-[#cc785c]"
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-y-auto px-8 pb-8">
        {error && (
          <div className="bg-red-50 border border-red-100 rounded-xl px-4 py-3 text-sm text-red-600 mb-6">
            {error}
          </div>
        )}

        {loading && page === 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : allPages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-16 h-16 rounded-2xl bg-[#f5f0e8] flex items-center justify-center mb-4">
              <IconBook className="w-8 h-8 text-[#8e8b82]" />
            </div>
            <p className="text-[#3d3d3a] font-medium text-base">Chưa có wiki page nào</p>
            <p className="text-[#8e8b82] text-sm mt-1">
              {debouncedSearch || period
                ? "Thử thay đổi bộ lọc hoặc từ khóa tìm kiếm"
                : "Các trang wiki sẽ xuất hiện ở đây sau khi xây dựng"}
            </p>
          </div>
        ) : (
          <>
            <p className="text-xs text-[#8e8b82] mb-4">
              {allPages.length} trang wiki{debouncedSearch ? ` cho "${debouncedSearch}"` : ""}
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {allPages.map((page) => (
                <WikiCard key={page.id} page={page} onClick={() => navigate(`/wiki/${page.slug}`)} />
              ))}
            </div>
            {hasMore && !loading && <div ref={scrollRef} className="h-4" aria-hidden="true" />}
            {loading && page > 0 && (
              <div className="flex justify-center py-4">
                <div className="w-6 h-6 border-2 border-[#cc785c] border-t-transparent rounded-full animate-spin" />
              </div>
            )}
          </>
        )}
      </div>

      {/* Modal: Create Project */}
      {isCreateProjectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white border border-[#e6dfd8] rounded-2xl w-full max-w-md p-6 shadow-xl animate-fade-in mx-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-display font-semibold text-[#141413]">Tạo Dự án Mới</h3>
              <button 
                onClick={() => setIsCreateProjectModalOpen(false)}
                className="p-1.5 rounded-lg hover:bg-[#f5f0e8] text-[#8e8b82] hover:text-[#141413] transition-colors"
              >
                <IconClose />
              </button>
            </div>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[#6c6a64] uppercase tracking-wider mb-1">
                  Tên dự án <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="Ví dụ: Chiến dịch Điện Biên Phủ"
                  className="w-full px-3.5 py-2 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#141413] outline-none focus:border-[#cc785c] focus:bg-white transition-all"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#6c6a64] uppercase tracking-wider mb-1">
                  Mô tả dự án
                </label>
                <textarea
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  placeholder="Mô tả tóm tắt về mục tiêu hoặc phạm vi nghiên cứu..."
                  rows={4}
                  className="w-full px-3.5 py-2 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#141413] outline-none focus:border-[#cc785c] focus:bg-white transition-all resize-none"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateProjectModalOpen(false)}
                  className="px-4 py-2 border border-[#e6dfd8] text-sm font-medium text-[#6c6a64] rounded-xl bg-white hover:bg-[#f5f0e8] transition-all"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={projectSubmitting}
                  className="px-4 py-2 bg-[#cc785c] text-white text-sm font-medium rounded-xl hover:bg-[#a9583e] transition-all disabled:opacity-50"
                >
                  {projectSubmitting ? "Đang tạo..." : "Tạo dự án"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Propose New Page Draft */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white border border-[#e6dfd8] rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-xl animate-fade-in mx-4">
            <div className="flex justify-between items-center p-6 border-b border-[#e6dfd8] flex-shrink-0">
              <div>
                <h3 className="text-lg font-display font-semibold text-[#141413]">Đề xuất trang wiki mới</h3>
                <p className="text-xs text-[#8e8b82] mt-0.5">Bản thảo của bạn sẽ được gửi tới Admin/Biên tập viên phê duyệt trước khi xuất bản</p>
              </div>
              <button 
                onClick={() => setIsCreateModalOpen(false)}
                className="p-1.5 rounded-lg hover:bg-[#f5f0e8] text-[#8e8b82] hover:text-[#141413] transition-colors"
              >
                <IconClose />
              </button>
            </div>
            
            <form onSubmit={handleCreateDraft} className="flex-1 flex flex-col overflow-hidden">
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-[#6c6a64] uppercase tracking-wider mb-1">
                      Tiêu đề trang <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={draftTitle}
                      onChange={(e) => setDraftTitle(e.target.value)}
                      placeholder="Ví dụ: Chiến dịch Tây Bắc"
                      className="w-full px-3.5 py-2 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#141413] outline-none focus:border-[#cc785c] focus:bg-white transition-all"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[#6c6a64] uppercase tracking-wider mb-1">
                      Dự án / Không gian làm việc
                    </label>
                    <select
                      value={draftProjectId}
                      onChange={(e) => setDraftProjectId(e.target.value)}
                      className="w-full px-3.5 py-2.5 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#6c6a64] outline-none focus:border-[#cc785c] focus:bg-white transition-all cursor-pointer"
                    >
                      <option value="">Không thuộc dự án nào (Chung)</option>
                      {projects.map((proj) => (
                        <option key={proj.id} value={proj.id}>
                          {proj.name} {proj.slug !== proj.name && `(${proj.slug})`}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#6c6a64] uppercase tracking-wider mb-1">
                    Tóm tắt ngắn gọn
                  </label>
                  <textarea
                    value={draftSummary}
                    onChange={(e) => setDraftSummary(e.target.value)}
                    placeholder="Tóm tắt chung của sự kiện, nhân vật..."
                    rows={2}
                    className="w-full px-3.5 py-2 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#141413] outline-none focus:border-[#cc785c] focus:bg-white transition-all resize-none"
                  />
                </div>

                <div className="border-t border-[#e6dfd8] pt-4">
                  <h4 className="text-xs font-semibold text-[#141413] uppercase tracking-wider mb-3">Nội dung chi tiết từng mục</h4>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1">Bối cảnh</label>
                      <textarea
                        value={draftSections.background}
                        onChange={(e) => setDraftSections({ ...draftSections, background: e.target.value })}
                        placeholder="Tình hình lịch sử trước khi sự kiện diễn ra..."
                        rows={3}
                        className="w-full px-3.5 py-2 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#141413] outline-none focus:border-[#cc785c] focus:bg-white transition-all resize-none"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1">Nguyên nhân</label>
                      <textarea
                        value={draftSections.causes}
                        onChange={(e) => setDraftSections({ ...draftSections, causes: e.target.value })}
                        placeholder="Tại sao sự kiện này xảy ra?"
                        rows={3}
                        className="w-full px-3.5 py-2 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#141413] outline-none focus:border-[#cc785c] focus:bg-white transition-all resize-none"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1">Diễn biến chính</label>
                      <textarea
                        value={draftSections.main_events}
                        onChange={(e) => setDraftSections({ ...draftSections, main_events: e.target.value })}
                        placeholder="Các mốc tiến trình và sự kiện quan trọng xảy ra..."
                        rows={4}
                        className="w-full px-3.5 py-2 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#141413] outline-none focus:border-[#cc785c] focus:bg-white transition-all resize-none"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1">Kết quả</label>
                      <textarea
                        value={draftSections.results}
                        onChange={(e) => setDraftSections({ ...draftSections, results: e.target.value })}
                        placeholder="Kết cục của sự kiện, chiến thắng, tổn thất..."
                        rows={3}
                        className="w-full px-3.5 py-2 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#141413] outline-none focus:border-[#cc785c] focus:bg-white transition-all resize-none"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1">Ý nghĩa lịch sử</label>
                      <textarea
                        value={draftSections.significance}
                        onChange={(e) => setDraftSections({ ...draftSections, significance: e.target.value })}
                        placeholder="Tầm ảnh hưởng, bài học lịch sử..."
                        rows={3}
                        className="w-full px-3.5 py-2 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#141413] outline-none focus:border-[#cc785c] focus:bg-white transition-all resize-none"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1">Nhân vật liên quan</label>
                      <textarea
                        value={draftSections.people}
                        onChange={(e) => setDraftSections({ ...draftSections, people: e.target.value })}
                        placeholder="Các tướng lĩnh, nhà lãnh đạo, anh hùng..."
                        rows={2}
                        className="w-full px-3.5 py-2 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#141413] outline-none focus:border-[#cc785c] focus:bg-white transition-all resize-none"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1">Mốc thời gian</label>
                      <textarea
                        value={draftSections.timeline}
                        onChange={(e) => setDraftSections({ ...draftSections, timeline: e.target.value })}
                        placeholder="Liệt kê các mốc ngày tháng quan trọng..."
                        rows={2}
                        className="w-full px-3.5 py-2 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#141413] outline-none focus:border-[#cc785c] focus:bg-white transition-all resize-none"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1">Nguồn tham khảo</label>
                      <textarea
                        value={draftSections.references}
                        onChange={(e) => setDraftSections({ ...draftSections, references: e.target.value })}
                        placeholder="Các tài liệu sách báo, nguồn dẫn..."
                        rows={2}
                        className="w-full px-3.5 py-2 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#141413] outline-none focus:border-[#cc785c] focus:bg-white transition-all resize-none"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-6 border-t border-[#e6dfd8] flex justify-end gap-2 flex-shrink-0 bg-[#faf9f5]">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 border border-[#e6dfd8] text-sm font-medium text-[#6c6a64] rounded-xl bg-white hover:bg-[#f5f0e8] transition-all"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={draftSubmitting}
                  className="px-4 py-2 bg-[#cc785c] text-white text-sm font-medium rounded-xl hover:bg-[#a9583e] transition-all disabled:opacity-50"
                >
                  {draftSubmitting ? "Đang gửi..." : "Gửi đề xuất"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Card subcomponent ──────────────────────────────────
function WikiCard({ page, onClick }: { page: WikiPage; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="group bg-white border border-[#e6dfd8] rounded-xl shadow-sm p-5 text-left hover:shadow-md hover:border-[#cc785c]/40 transition-all duration-200 animate-fade-in"
    >
      {/* Badges */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {page.period && (
          <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-full border", getPeriodColor(page.period))}>
            {page.period.replace(/-/g, " ")}
          </span>
        )}
        {page.event_type && (
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#f5f0e8] text-[#6c6a64] border border-[#e6dfd8]">
            {page.event_type}
          </span>
        )}
      </div>

      {/* Title */}
      <h3 className="font-display text-[15px] text-[#141413] mb-2 group-hover:text-[#cc785c] transition-colors line-clamp-2 leading-snug">
        {page.title}
      </h3>

      {/* Summary preview */}
      <p className="text-xs text-[#6c6a64] line-clamp-3 leading-relaxed">
        {page.summary || "Chưa có tóm tắt."}
      </p>

      {/* Read more */}
      <div className="mt-3 flex items-center gap-1 text-[#cc785c] text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity">
        Xem chi tiết <IconChevronRight />
      </div>
    </button>
  )
}
