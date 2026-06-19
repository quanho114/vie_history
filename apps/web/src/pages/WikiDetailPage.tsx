import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { wikiApi, projectsApi, draftsApi, graphApi, type WikiPage, type Project } from "@/lib/api/brain"
import { cn } from "@/lib/utils/cn"
import { useUIStore } from "@/stores/uiStore"
import { MarkdownRenderer } from "@/components/UI/MarkdownRenderer"
import { MarkdownEditor } from "@/components/UI/MarkdownEditor"

// ── Icons ──────────────────────────────────────────────
function IconArrowLeft({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="m12 19-7-7 7-7" /><path d="M19 12H5" />
    </svg>
  )
}

function IconEdit({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
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

function IconChevronDown({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="m6 9 6 6 6-6" />
    </svg>
  )
}

function IconMessageSquare({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}

function IconExternalLink({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15,3 21,3 21,9" /><line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  )
}

// ── Period badge color helper ──────────────────────────
const PERIOD_COLORS: Record<string, string> = {
  "khang-chien-chong-phap": "bg-blue-50 text-blue-700 border-blue-100",
  "khang-chien-chong-my": "bg-red-50 text-red-700 border-red-100",
  "thong-nhat": "bg-emerald-50 text-emerald-700 border-emerald-100",
  default: "bg-[#f5f0e8] text-[#6c6a64] border-[#e6dfd8]",
}

function getPeriodColor(period: string) {
  return PERIOD_COLORS[period] || PERIOD_COLORS.default
}

// ── Expandable Section ─────────────────────────────────
function ExpandableSection({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="border border-[#e6dfd8] rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3.5 bg-[#faf9f5] hover:bg-[#f5f0e8] transition-colors text-left"
      >
        <span className="font-display text-[15px] text-[#141413]">{title}</span>
        <IconChevronDown className={cn("text-[#8e8b82] transition-transform duration-200", open ? "rotate-180" : "")} />
      </button>
      {open && (
        <div className="px-5 py-4 bg-white text-sm text-[#3d3d3a] leading-relaxed">
          {children}
        </div>
      )}
    </div>
  )
}

// ── Skeleton ───────────────────────────────────────────
function Skeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="flex gap-2">
        <div className="h-5 w-28 rounded-full bg-[#e8e0d2]" />
        <div className="h-5 w-20 rounded-full bg-[#e8e0d2]" />
      </div>
      <div className="h-8 w-2/3 rounded bg-[#e8e0d2]" />
      <div className="h-4 w-full rounded bg-[#ebe6df]" />
      <div className="h-4 w-5/6 rounded bg-[#ebe6df]" />
      <div className="h-4 w-4/5 rounded bg-[#ebe6df]" />
      <div className="space-y-3 mt-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="border border-[#e6dfd8] rounded-xl p-4">
            <div className="h-4 w-1/3 rounded bg-[#e8e0d2] mb-3" />
            <div className="h-3 w-full rounded bg-[#ebe6df]" />
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Section definitions ────────────────────────────────
const SECTION_KEYS = [
  "Bối cảnh",
  "Nguyên nhân",
  "Diễn biến chính",
  "Kết quả",
  "Ý nghĩa lịch sử",
  "Nhân vật liên quan",
  "Mốc thời gian",
  "Nguồn tham khảo",
]

// ── Main component ─────────────────────────────────────
export function WikiDetailPage() {
  const showToast = useUIStore((s) => s.showToast)
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const [page, setPage] = useState<WikiPage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Projects & Drafts
  const [projects, setProjects] = useState<Project[]>([])
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
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

  // Graph links
  const [neighbors, setNeighbors] = useState<any[]>([])
  const [loadingLinks, setLoadingLinks] = useState(false)

  useEffect(() => {
    if (!slug) return
    setLoading(true)
    setError(null)

    // Load wiki page
    wikiApi.getPage(slug)
      .then((p) => {
        setPage(p)
        // Pre-populate draft edit fields
        setDraftTitle(p.title)
        setDraftSummary(p.summary || "")
        setDraftSections({
          background: p.sections?.find(s => s.title === "Bối cảnh")?.content || "",
          causes: p.sections?.find(s => s.title === "Nguyên nhân")?.content || "",
          main_events: p.sections?.find(s => s.title === "Diễn biến chính")?.content || "",
          results: p.sections?.find(s => s.title === "Kết quả")?.content || "",
          significance: p.sections?.find(s => s.title === "Ý nghĩa lịch sử")?.content || "",
          people: p.sections?.find(s => s.title === "Nhân vật liên quan")?.content || "",
          timeline: p.sections?.find(s => s.title === "Mốc thời gian")?.content || "",
          references: p.sections?.find(s => s.title === "Nguồn tham khảo")?.content || "",
        })
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Không thể tải trang"))
      .finally(() => setLoading(false))

    // Load neighbors/backlinks
    setLoadingLinks(true)
    graphApi.getNeighbors(slug)
      .then((res) => {
        setNeighbors(res.neighbors || [])
      })
      .catch((e) => console.error("Không thể tải các liên kết liên quan", e))
      .finally(() => setLoadingLinks(false))
  }, [slug])

  // Load projects
  useEffect(() => {
    projectsApi.list()
      .then((res) => setProjects(res.projects || []))
      .catch((e) => console.error("Không thể tải danh sách dự án", e))
  }, [])

  const handleAskChatbot = () => {
    if (!slug) return
    navigate(`/chat?context_type=wiki&context_id=${slug}`)
  }

  const handleCreateDraft = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!draftTitle.trim()) {
      showToast("Vui lòng điền tiêu đề trang", "error")
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
        wiki_page_id: page?.id,
        title: draftTitle.trim(),
        project_id: draftProjectId || undefined,
        summary: draftSummary.trim() || undefined,
        content: Object.keys(content).length > 0 ? content : undefined,
      })

      showToast("Đề xuất chỉnh sửa trang thành công! Đang chờ duyệt.", "success")
      setIsEditModalOpen(false)
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Không thể tạo bản thảo đề xuất", "error")
    } finally {
      setDraftSubmitting(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#faf9f5]">
      {/* Top bar */}
      <header className="px-8 py-4 border-b border-[#e6dfd8] bg-white flex items-center justify-between flex-shrink-0">
        <button
          onClick={() => navigate("/wiki")}
          className="flex items-center gap-2 text-sm text-[#6c6a64] hover:text-[#141413] transition-colors"
        >
          <IconArrowLeft /> Quay lại Wiki
        </button>

        <div className="flex gap-2">
          {page && (
            <button
              onClick={() => setIsEditModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 border border-[#e6dfd8] text-[#6c6a64] hover:text-[#cc785c] hover:border-[#cc785c]/40 text-sm font-medium rounded-xl transition-all bg-white"
            >
              <IconEdit />
              Đề xuất chỉnh sửa
            </button>
          )}
          <button
            onClick={handleAskChatbot}
            className="flex items-center gap-2 px-4 py-2 bg-[#cc785c] text-white text-sm font-medium rounded-xl hover:bg-[#a9583e] transition-all shadow-sm"
          >
            <IconMessageSquare />
            Hỏi chatbot về trang này
          </button>
        </div>
      </header>

      {/* Split Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Main content area */}
        <div className="flex-1 overflow-y-auto px-8 py-6">
          <div className="max-w-3xl mx-auto">
            {loading ? (
              <Skeleton />
            ) : error ? (
              <div className="bg-red-50 border border-red-100 rounded-xl px-5 py-4 text-red-600 text-sm">
                {error}
              </div>
            ) : page ? (
              <div className="space-y-6 animate-fade-in">
                {/* Badges */}
                <div className="flex flex-wrap gap-2">
                  {page.period && (
                    <span className={cn("text-[11px] font-semibold px-2.5 py-1 rounded-full border", getPeriodColor(page.period))}>
                      {page.period.replace(/-/g, " ")}
                    </span>
                  )}
                  {page.event_type && (
                    <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-[#f5f0e8] text-[#6c6a64] border border-[#e6dfd8]">
                      {page.event_type}
                    </span>
                  )}
                </div>

                {/* Title */}
                <h1 className="font-display text-3xl text-[#141413] leading-tight">
                  {page.title}
                </h1>

                {/* Summary card */}
                {page.summary && (
                  <div className="bg-[#f5f0e8] border border-[#e6dfd8] rounded-xl px-5 py-4">
                    <p className="text-xs font-semibold text-[#8e8b82] uppercase tracking-wider mb-2">Tóm tắt</p>
                    <p className="text-sm text-[#3d3d3a] leading-relaxed">{page.summary}</p>
                  </div>
                )}

                {/* Expandable sections */}
                {page.sections && page.sections.length > 0 ? (
                  <div className="space-y-2">
                    {page.sections.map((section, i) => (
                      <ExpandableSection key={i} title={section.title}>
                        <MarkdownRenderer content={section.content} />
                      </ExpandableSection>
                    ))}
                  </div>
                ) : (
                  // Fallback: show content field as sections if no structured sections
                  page.content && (
                    <div className="space-y-2">
                      {SECTION_KEYS.map((title) => {
                        const regex = new RegExp(`(?:^|\\n)#+\\s*${title}[^\\n]*\\n([\\s\\S]*?)(?=\\n#+|$)`, "i")
                        const match = page.content!.match(regex)
                        if (!match) return null
                        return (
                          <ExpandableSection key={title} title={title}>
                            <MarkdownRenderer content={match[1].trim()} />
                          </ExpandableSection>
                        )
                      }).filter(Boolean)}
                      {/* Full content fallback */}
                      {!SECTION_KEYS.some((t) => page.content!.match(new RegExp(`#+\\s*${t}`, "i"))) && (
                        <ExpandableSection title="Nội dung">
                          <MarkdownRenderer content={page.content} />
                        </ExpandableSection>
                      )}
                    </div>
                  )
                )}

                {/* Related pages */}
                {page.related_pages && page.related_pages.length > 0 && (
                  <div className="bg-white border border-[#e6dfd8] rounded-xl p-5">
                    <p className="text-xs font-semibold text-[#8e8b82] uppercase tracking-wider mb-3">Trang liên quan</p>
                    <div className="flex flex-wrap gap-2">
                      {page.related_pages.map((rel) => (
                        <button
                          key={rel.slug}
                          onClick={() => navigate(`/wiki/${rel.slug}`)}
                          className="flex items-center gap-1 px-3 py-1.5 bg-[#f5f0e8] hover:bg-[#ebe6df] text-[#3d3d3a] text-xs rounded-lg border border-[#e6dfd8] transition-colors"
                        >
                          {rel.title}
                          <IconExternalLink className="text-[#8e8b82]" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Sources */}
                {page.sources && page.sources.length > 0 && (
                  <div className="bg-white border border-[#e6dfd8] rounded-xl p-5">
                    <p className="text-xs font-semibold text-[#8e8b82] uppercase tracking-wider mb-3">Nguồn tham khảo</p>
                    <ul className="space-y-2">
                      {page.sources.map((src, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-[#3d3d3a]">
                          <span className="text-[#cc785c] font-bold text-xs mt-0.5">[{i + 1}]</span>
                          <span>
                            {src.author && <span className="font-medium">{src.author}. </span>}
                            {src.url ? (
                              <a href={src.url} target="_blank" rel="noopener noreferrer"
                                className="text-[#cc785c] hover:underline">
                                {src.title}
                              </a>
                            ) : (
                              <span>{src.title}</span>
                            )}
                            {src.year && <span className="text-[#8e8b82]"> ({src.year})</span>}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>

        {/* Knowledge Link Sidebar */}
        {!loading && !error && page && (
          <div className="w-80 border-l border-[#e6dfd8] bg-white overflow-y-auto p-6 hidden lg:block flex-shrink-0">
            <h3 className="font-display font-semibold text-[#141413] text-sm mb-4">
              Mạng Liên Kết Tri Thức
            </h3>

            {/* Backlinks */}
            <div className="mb-6">
              <h4 className="text-xs font-semibold text-[#8e8b82] uppercase tracking-wider mb-2.5 flex items-center justify-between">
                <span>Liên kết đến đây (Backlinks)</span>
                <span className="bg-[#f5f0e8] text-[#6c6a64] px-1.5 py-0.5 rounded text-[10px]">
                  {neighbors.filter((n) => n.direction === "incoming").length}
                </span>
              </h4>
              {neighbors.filter((n) => n.direction === "incoming").length === 0 ? (
                <p className="text-xs text-[#8e8b82] italic">Chưa có liên kết đến.</p>
              ) : (
                <ul className="space-y-2">
                  {neighbors
                    .filter((n) => n.direction === "incoming")
                    .map((n) => (
                      <li key={n.node_id}>
                        {n.node_slug ? (
                          <button
                            onClick={() => navigate(`/wiki/${n.node_slug}`)}
                            className="w-full text-left text-xs text-[#6c6a64] hover:text-[#cc785c] hover:underline font-medium break-words transition-colors p-1.5 hover:bg-[#faf9f5] rounded-lg border border-transparent hover:border-[#e6dfd8]"
                          >
                            {n.node_name} <span className="text-[10px] text-[#8e8b82] font-normal font-sans">({n.edge_type})</span>
                          </button>
                        ) : (
                          <span className="text-xs text-[#6c6a64] italic break-words p-1.5 block">
                            {n.node_name} <span className="text-[10px] text-[#8e8b82] font-normal font-sans">({n.edge_type})</span>
                          </span>
                        )}
                      </li>
                    ))}
                </ul>
              )}
            </div>

            {/* Outlinks */}
            <div>
              <h4 className="text-xs font-semibold text-[#8e8b82] uppercase tracking-wider mb-2.5 flex items-center justify-between">
                <span>Liên kết đi (Outlinks)</span>
                <span className="bg-[#f5f0e8] text-[#6c6a64] px-1.5 py-0.5 rounded text-[10px]">
                  {neighbors.filter((n) => n.direction === "outgoing").length}
                </span>
              </h4>
              {neighbors.filter((n) => n.direction === "outgoing").length === 0 ? (
                <p className="text-xs text-[#8e8b82] italic">Chưa có liên kết đi.</p>
              ) : (
                <ul className="space-y-2">
                  {neighbors
                    .filter((n) => n.direction === "outgoing")
                    .map((n) => (
                      <li key={n.node_id}>
                        {n.node_slug ? (
                          <button
                            onClick={() => navigate(`/wiki/${n.node_slug}`)}
                            className="w-full text-left text-xs text-[#6c6a64] hover:text-[#cc785c] hover:underline font-medium break-words transition-colors p-1.5 hover:bg-[#faf9f5] rounded-lg border border-transparent hover:border-[#e6dfd8]"
                          >
                            {n.node_name} <span className="text-[10px] text-[#8e8b82] font-normal font-sans">({n.edge_type})</span>
                          </button>
                        ) : (
                          <span className="text-xs text-[#6c6a64] italic break-words p-1.5 block">
                            {n.node_name} <span className="text-[10px] text-[#8e8b82] font-normal font-sans">({n.edge_type})</span>
                          </span>
                        )}
                      </li>
                    ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Modal: Propose Edit */}
      {isEditModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white border border-[#e6dfd8] rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-xl animate-fade-in mx-4">
            <div className="flex justify-between items-center p-6 border-b border-[#e6dfd8] flex-shrink-0">
              <div>
                <h3 className="text-lg font-display font-semibold text-[#141413]">Đề xuất chỉnh sửa trang</h3>
                <p className="text-xs text-[#8e8b82] mt-0.5">Bản thảo chỉnh sửa sẽ được gửi tới Admin/Biên tập viên phê duyệt trước khi cập nhật</p>
              </div>
              <button
                onClick={() => setIsEditModalOpen(false)}
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
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1.5">Bối cảnh</label>
                      <MarkdownEditor
                        value={draftSections.background}
                        onChange={(val) => setDraftSections({ ...draftSections, background: val })}
                        placeholder="Tình hình lịch sử trước khi sự kiện diễn ra..."
                        minHeight="140px"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1.5">Nguyên nhân</label>
                      <MarkdownEditor
                        value={draftSections.causes}
                        onChange={(val) => setDraftSections({ ...draftSections, causes: val })}
                        placeholder="Tại sao sự kiện này xảy ra?"
                        minHeight="140px"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1.5">Diễn biến chính</label>
                      <MarkdownEditor
                        value={draftSections.main_events}
                        onChange={(val) => setDraftSections({ ...draftSections, main_events: val })}
                        placeholder="Các mốc tiến trình và sự kiện quan trọng xảy ra..."
                        minHeight="180px"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1.5">Kết quả</label>
                      <MarkdownEditor
                        value={draftSections.results}
                        onChange={(val) => setDraftSections({ ...draftSections, results: val })}
                        placeholder="Kết cục của sự kiện, chiến thắng, tổn thất..."
                        minHeight="140px"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1.5">Ý nghĩa lịch sử</label>
                      <MarkdownEditor
                        value={draftSections.significance}
                        onChange={(val) => setDraftSections({ ...draftSections, significance: val })}
                        placeholder="Tầm ảnh hưởng, bài học lịch sử..."
                        minHeight="140px"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1.5">Nhân vật liên quan</label>
                      <MarkdownEditor
                        value={draftSections.people}
                        onChange={(val) => setDraftSections({ ...draftSections, people: val })}
                        placeholder="Các tướng lĩnh, nhà lãnh đạo, anh hùng..."
                        minHeight="120px"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1.5">Mốc thời gian</label>
                      <MarkdownEditor
                        value={draftSections.timeline}
                        onChange={(val) => setDraftSections({ ...draftSections, timeline: val })}
                        placeholder="Liệt kê các mốc ngày tháng quan trọng..."
                        minHeight="120px"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#6c6a64] mb-1.5">Nguồn tham khảo</label>
                      <MarkdownEditor
                        value={draftSections.references}
                        onChange={(val) => setDraftSections({ ...draftSections, references: val })}
                        placeholder="Các tài liệu sách báo, nguồn dẫn..."
                        minHeight="120px"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-6 border-t border-[#e6dfd8] flex justify-end gap-2 flex-shrink-0 bg-[#faf9f5]">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
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
