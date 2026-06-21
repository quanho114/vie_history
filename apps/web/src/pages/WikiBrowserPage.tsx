import { useEffect, useState, useCallback, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { wikiApi, projectsApi, draftsApi, type WikiPage, type Project } from "@/lib/api/brain"
import { useAuthStore } from "@/stores/authStore"
import { cn } from "@/lib/utils/cn"
import { useUIStore } from "@/stores/uiStore"
import { MarkdownEditor } from "@/components/UI/MarkdownEditor"

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

// ── Markdown Parser Helper ──────────────────────────────
const parseMarkdownToSections = (markdownText: string) => {
  const sections = {
    background: "",
    causes: "",
    main_events: "",
    results: "",
    significance: "",
    people: "",
    timeline: "",
    references: "",
  };

  const mapping = [
    { key: "background" as const, keywords: ["bối cảnh", "boi canh", "background"] },
    { key: "causes" as const, keywords: ["nguyên nhân", "nguyen nhan", "causes", "cause"] },
    { key: "main_events" as const, keywords: ["diễn biến", "dien bien", "diễn biến chính", "dien bien chinh", "events", "main events"] },
    { key: "results" as const, keywords: ["kết quả", "ket qua", "results", "result"] },
    { key: "significance" as const, keywords: ["ý nghĩa", "y nghia", "ý nghĩa lịch sử", "y nghia lich su", "significance", "historical significance"] },
    { key: "people" as const, keywords: ["nhân vật", "nhan vat", "nhân vật liên quan", "nhan vat lien quan", "people", "figures"] },
    { key: "timeline" as const, keywords: ["mốc thời gian", "moc thoi gian", "timeline", "chronology"] },
    { key: "references" as const, keywords: ["nguồn", "nguon", "nguồn tham khảo", "nguon tham khao", "references", "sources"] },
  ];

  const lines = markdownText.split("\n");
  let currentKey: keyof typeof sections | null = null;
  let currentContent: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const headingMatch = line.match(/^#+\s+(.+)$/);

    if (headingMatch) {
      if (currentKey) {
        sections[currentKey] = currentContent.join("\n").trim();
      }

      const headingText = headingMatch[1].trim().toLowerCase();
      const match = mapping.find((item) =>
        item.keywords.some((kw) => headingText.includes(kw))
      );

      if (match) {
        currentKey = match.key;
      } else {
        currentKey = null;
      }
      currentContent = [];
    } else {
      if (currentKey) {
        currentContent.push(line);
      }
    }
  }

  if (currentKey) {
    sections[currentKey] = currentContent.join("\n").trim();
  }

  const hasContent = Object.values(sections).some((val) => val.trim() !== "");
  if (!hasContent && markdownText.trim()) {
    sections.background = markdownText.trim();
  }

  return sections;
};

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

function IconChevronDown({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="m6 9 6 6 6-6" />
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

function IconUpload({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  )
}

function IconBrain({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" />
      <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" />
      <path d="M12 5v14" />
      <path d="M12 12h6" />
      <path d="M12 12H6" />
    </svg>
  )
}

function IconMessageSquare({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}

function IconExternalLink({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
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
  const showToast = useUIStore((s) => s.showToast)
  const { user } = useAuthStore()
  const [allPages, setAllPages] = useState<WikiPage[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState("")
  const [isProjectDropdownOpen, setIsProjectDropdownOpen] = useState(false)
  const [isModalDropdownOpen, setIsModalDropdownOpen] = useState(false)

  const dropdownRef = useRef<HTMLDivElement>(null)
  const modalDropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsProjectDropdownOpen(false)
      }
      if (modalDropdownRef.current && !modalDropdownRef.current.contains(event.target as Node)) {
        setIsModalDropdownOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

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

  const [selectedWikiPage, setSelectedWikiPage] = useState<WikiPage | null>(null)
  const [isStatsVisible, setIsStatsVisible] = useState(true)
  const [isDraggingFile, setIsDraggingFile] = useState(false)

  const selectedProject = projects.find(p => p.id === selectedProjectId)
  const selectedDraftProject = projects.find(p => p.id === draftProjectId)


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
      showToast("Tạo dự án mới thành công!", "success")
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Không thể tạo dự án", "error")
    } finally {
      setProjectSubmitting(false)
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      const text = event.target?.result as string
      if (!text) return

      // Try to parse H1 header for title
      const h1Match = text.match(/^#\s+(.+)$/m)
      if (h1Match && h1Match[1]) {
        setDraftTitle(h1Match[1].trim())
      }

      const parsed = parseMarkdownToSections(text)
      setDraftSections(parsed)
      showToast("Đã nhập nội dung từ file markdown thành công!", "success")
    }
    reader.readAsText(file)
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
        title: draftTitle.trim(),
        project_id: draftProjectId || undefined,
        summary: draftSummary.trim() || undefined,
        content: Object.keys(content).length > 0 ? content : undefined,
      })

      showToast("Đề xuất bản thảo trang mới thành công! Đang chờ duyệt.", "success")
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
      showToast(err instanceof Error ? err.message : "Không thể tạo bản thảo đề xuất", "error")
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

          <div ref={dropdownRef} className="relative flex-shrink-0">
            <button
              type="button"
              onClick={() => setIsProjectDropdownOpen(!isProjectDropdownOpen)}
              className="flex items-center justify-between gap-3 px-4 py-2.5 bg-white border border-[#e6dfd8] rounded-xl text-sm text-[#6c6a64] hover:border-[#cc785c] hover:text-[#cc785c] focus:border-[#cc785c] transition-all cursor-pointer min-w-[200px] text-left shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
            >
              <span className="truncate font-medium">
                {selectedProject ? selectedProject.name : "Tất cả Dự án"}
              </span>
              <IconChevronDown className={cn("w-4 h-4 text-[#8e8b82] transition-transform duration-200 flex-shrink-0", isProjectDropdownOpen && "rotate-180")} />
            </button>

            {isProjectDropdownOpen && (
              <div className="absolute left-0 mt-1.5 w-64 bg-white border border-[#e6dfd8] rounded-xl shadow-lg py-1.5 z-30 animate-fadeIn max-h-60 overflow-y-auto">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedProjectId("")
                    setIsProjectDropdownOpen(false)
                  }}
                  className={cn(
                    "w-full px-4 py-2 text-left text-sm flex items-center justify-between transition-colors cursor-pointer",
                    selectedProjectId === ""
                      ? "bg-[#f5f0e8] text-[#cc785c] font-semibold"
                      : "text-[#6c6a64] hover:bg-[#fcfbf9] hover:text-[#cc785c]"
                  )}
                >
                  <span>Tất cả Dự án</span>
                  {selectedProjectId === "" && <IconCheck className="w-4 h-4 text-[#cc785c] flex-shrink-0" />}
                </button>
                <div className="h-px bg-[#e6dfd8] my-1" />
                {projects.map((proj) => (
                  <button
                    key={proj.id}
                    type="button"
                    onClick={() => {
                      setSelectedProjectId(proj.id)
                      setIsProjectDropdownOpen(false)
                    }}
                    className={cn(
                      "w-full px-4 py-2 text-left text-sm flex items-center justify-between transition-colors cursor-pointer",
                      selectedProjectId === proj.id
                        ? "bg-[#f5f0e8] text-[#cc785c] font-semibold"
                        : "text-[#6c6a64] hover:bg-[#fcfbf9] hover:text-[#cc785c]"
                    )}
                  >
                    <div className="flex flex-col min-w-0">
                      <span className="truncate">{proj.name}</span>
                      {proj.slug !== proj.name && (
                        <span className="text-[10px] text-[#8e8b82] truncate mt-0.5">
                          {proj.slug}
                        </span>
                      )}
                    </div>
                    {selectedProjectId === proj.id && <IconCheck className="w-4 h-4 text-[#cc785c] flex-shrink-0" />}
                  </button>
                ))}
              </div>
            )}
          </div>


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
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1.5 px-3 py-1.5 border border-[#cc785c]/30 text-[#cc785c] hover:bg-[#cc785c]/5 text-xs font-semibold rounded-xl cursor-pointer transition-all shadow-sm">
                  <IconUpload className="w-3.5 h-3.5" />
                  <span>Nhập file .md</span>
                  <input
                    type="file"
                    accept=".md,.txt"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </label>
                <button 
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="p-1.5 rounded-lg hover:bg-[#f5f0e8] text-[#8e8b82] hover:text-[#141413] transition-colors"
                >
                  <IconClose />
                </button>
              </div>
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
                    <div ref={modalDropdownRef} className="relative">
                      <button
                        type="button"
                        onClick={() => setIsModalDropdownOpen(!isModalDropdownOpen)}
                        className="w-full flex items-center justify-between gap-3 px-3.5 py-2.5 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl text-sm text-[#6c6a64] hover:border-[#cc785c] focus:border-[#cc785c] focus:bg-white transition-all cursor-pointer text-left shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                      >
                        <span className="truncate">
                          {selectedDraftProject ? selectedDraftProject.name : "Không thuộc dự án nào (Chung)"}
                        </span>
                        <IconChevronDown className={cn("w-4 h-4 text-[#8e8b82] transition-transform duration-200 flex-shrink-0", isModalDropdownOpen && "rotate-180")} />
                      </button>

                      {isModalDropdownOpen && (
                        <div className="absolute left-0 mt-1.5 w-full bg-white border border-[#e6dfd8] rounded-xl shadow-lg py-1.5 z-30 animate-fadeIn max-h-48 overflow-y-auto">
                          <button
                            type="button"
                            onClick={() => {
                              setDraftProjectId("")
                              setIsModalDropdownOpen(false)
                            }}
                            className={cn(
                              "w-full px-4 py-2 text-left text-sm flex items-center justify-between transition-colors cursor-pointer",
                              draftProjectId === ""
                                ? "bg-[#f5f0e8] text-[#cc785c] font-semibold"
                                : "text-[#6c6a64] hover:bg-[#fcfbf9] hover:text-[#cc785c]"
                            )}
                          >
                            <span>Không thuộc dự án nào (Chung)</span>
                            {draftProjectId === "" && <IconCheck className="w-4 h-4 text-[#cc785c] flex-shrink-0" />}
                          </button>
                          <div className="h-px bg-[#e6dfd8] my-1" />
                          {projects.map((proj) => (
                            <button
                              key={proj.id}
                              type="button"
                              onClick={() => {
                                setDraftProjectId(proj.id)
                                setIsModalDropdownOpen(false)
                              }}
                              className={cn(
                                "w-full px-4 py-2 text-left text-sm flex items-center justify-between transition-colors cursor-pointer",
                                draftProjectId === proj.id
                                  ? "bg-[#f5f0e8] text-[#cc785c] font-semibold"
                                  : "text-[#6c6a64] hover:bg-[#fcfbf9] hover:text-[#cc785c]"
                              )}
                            >
                              <div className="flex flex-col min-w-0">
                                <span className="truncate">{proj.name}</span>
                                {proj.slug !== proj.name && (
                                  <span className="text-[10px] text-[#8e8b82] truncate mt-0.5">
                                    {proj.slug}
                                  </span>
                                )}
                              </div>
                              {draftProjectId === proj.id && <IconCheck className="w-4 h-4 text-[#cc785c] flex-shrink-0" />}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
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
