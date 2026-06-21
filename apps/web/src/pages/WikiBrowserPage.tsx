import { useEffect, useState, useCallback, useRef, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { wikiApi, projectsApi, draftsApi, type WikiPage, type Project } from "@/lib/api/brain"
import { useAuthStore } from "@/stores/authStore"
import { cn } from "@/lib/utils/cn"
import { useUIStore } from "@/stores/uiStore"
import { MarkdownEditor } from "@/components/UI/MarkdownEditor"
import { MarkdownRenderer } from "@/components/UI/MarkdownRenderer"

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

function IconTrash({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6M14 11v6" />
      <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
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

// Dynamic palette — all colors via inline hex styles (avoids Tailwind JIT purge)
const PALETTE: { bg: string; text: string; border: string; bar: string }[] = [
  { bg: "#eff6ff", text: "#1d4ed8", border: "#bfdbfe", bar: "#3b82f6" }, // blue
  { bg: "#fef2f2", text: "#b91c1c", border: "#fecaca", bar: "#ef4444" }, // red
  { bg: "#ecfdf5", text: "#047857", border: "#a7f3d0", bar: "#10b981" }, // emerald
  { bg: "#fffbeb", text: "#b45309", border: "#fde68a", bar: "#f59e0b" }, // amber
  { bg: "#f5f3ff", text: "#6d28d9", border: "#ddd6fe", bar: "#8b5cf6" }, // violet
  { bg: "#ecfeff", text: "#0e7490", border: "#a5f3fc", bar: "#06b6d4" }, // cyan
  { bg: "#fff1f2", text: "#be123c", border: "#fecdd3", bar: "#f43f5e" }, // rose
  { bg: "#f0fdfa", text: "#0f766e", border: "#99f6e4", bar: "#14b8a6" }, // teal
  { bg: "#fff7ed", text: "#c2410c", border: "#fed7aa", bar: "#f97316" }, // orange
  { bg: "#f7fee7", text: "#3f6212", border: "#d9f99d", bar: "#84cc16" }, // lime
]

const _periodColorCache: Record<string, number> = {}
let _paletteIdx = 0

function getPeriodPaletteIndex(period: string): number {
  if (!(period in _periodColorCache)) {
    _periodColorCache[period] = _paletteIdx % PALETTE.length
    _paletteIdx++
  }
  return _periodColorCache[period]
}

/** Returns inline React style object for period badge (bg, text, border). */
function getPeriodBadgeStyle(period: string): React.CSSProperties {
  if (!period) return { backgroundColor: "#f5f0e8", color: "#6c6a64", borderColor: "#e6dfd8" }
  const p = PALETTE[getPeriodPaletteIndex(period)]
  return { backgroundColor: p.bg, color: p.text, borderColor: p.border }
}

/** Returns hex bar color for the ratio chart. */
function getPeriodBarColor(period: string): string {
  if (!period) return "#c0bab4"
  return PALETTE[getPeriodPaletteIndex(period)].bar
}

// ── Skeleton row ───────────────────────────────────────
function SkeletonRow() {
  return (
    <tr className="border-b border-[#f5f0e8] animate-pulse">
      <td className="px-4 py-3"><div className="h-3 w-5 rounded bg-[#e8e0d2]" /></td>
      <td className="px-4 py-3"><div className="h-4 w-40 rounded bg-[#e8e0d2]" /></td>
      <td className="px-4 py-3 hidden lg:table-cell"><div className="h-3 w-64 rounded bg-[#ebe6df]" /></td>
      <td className="px-4 py-3 hidden md:table-cell"><div className="h-5 w-20 rounded-full bg-[#e8e0d2]" /></td>
      <td className="px-4 py-3 hidden md:table-cell"><div className="h-5 w-24 rounded-full bg-[#e8e0d2]" /></td>
      <td className="px-4 py-3"><div className="h-4 w-16 rounded bg-[#e8e0d2] ml-auto" /></td>
    </tr>
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
  const [selectedWikiPageDetails, setSelectedWikiPageDetails] = useState<WikiPage | null>(null)
  const drawerContentRef = useRef<HTMLDivElement>(null)

  const processedDrawerSections = useMemo(() => {
    if (!selectedWikiPageDetails) return []
    if (selectedWikiPageDetails.sections && selectedWikiPageDetails.sections.length > 0) {
      return selectedWikiPageDetails.sections
    }
    const content = selectedWikiPageDetails.content || ""
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
    const extracted: { title: string; content: string }[] = []
    SECTION_KEYS.forEach((title) => {
      const regex = new RegExp(`(?:^|\\n)#+\\s*${title}[^\\n]*\\n([\\s\\S]*?)(?=\\n#+|$)`, "i")
      const match = content.match(regex)
      if (match && match[1].trim()) {
        extracted.push({ title, content: match[1].trim() })
      }
    })
    if (extracted.length > 0) return extracted
    if (content.trim()) {
      return [{ title: "Nội dung", content: content.trim() }]
    }
    return []
  }, [selectedWikiPageDetails])

  const scrollToDrawerSection = (title: string) => {
    const id = `drawer-sec-${title.toLowerCase().replace(/[^a-z0-9]/g, "-")}`
    const el = document.getElementById(id)
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }
  const [isStatsVisible, setIsStatsVisible] = useState(true)
  const [isDraggingFile, setIsDraggingFile] = useState(false)

  // Fetch full wiki page details when selected wiki page changes
  useEffect(() => {
    if (!selectedWikiPage?.slug) {
      setSelectedWikiPageDetails(null)
      return
    }
    wikiApi.getPage(selectedWikiPage.slug)
      .then((fullPage) => {
        setSelectedWikiPageDetails(fullPage)
      })
      .catch((e) => {
        console.error("Không thể tải chi tiết trang wiki", e)
        setSelectedWikiPageDetails(selectedWikiPage)
      })
  }, [selectedWikiPage?.slug])

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

  const handleModalDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDraggingFile(false)
    const file = e.dataTransfer.files?.[0]
    if (!file) return
    if (!file.name.endsWith(".md") && !file.name.endsWith(".txt")) {
      showToast("Chỉ hỗ trợ file .md hoặc .txt", "error")
      return
    }
    const reader = new FileReader()
    reader.onload = (event) => {
      const text = event.target?.result as string
      if (!text) return
      const h1Match = text.match(/^#\s+(.+)$/m)
      if (h1Match && h1Match[1]) setDraftTitle(h1Match[1].trim())
      const parsed = parseMarkdownToSections(text)
      setDraftSections(parsed)
      showToast(`Đã nhập "${file.name}" thành công!`, "success")
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

  const stats = useMemo(() => {
    const totalPages = allPages.length
    const totalProjects = projects.length
    const periodCounts = allPages.reduce((acc, p) => {
      if (p.period) {
        acc[p.period] = (acc[p.period] || 0) + 1
      }
      return acc
    }, {} as Record<string, number>)
    
    return { totalPages, totalProjects, periodCounts }
  }, [allPages, projects])

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
          <button
            onClick={() => setIsStatsVisible(!isStatsVisible)}
            className="flex items-center gap-2 px-4 py-2 border border-[#e6dfd8] text-[#6c6a64] hover:text-[#cc785c] hover:border-[#cc785c]/40 text-sm font-medium rounded-xl transition-all bg-white"
          >
            {isStatsVisible ? "Ẩn Thống kê" : "Hiện Thống kê"}
          </button>
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

      {isStatsVisible && (
        <div className="px-8 py-5 grid grid-cols-1 md:grid-cols-3 gap-5 bg-[#fcfbf9] border-b border-[#e6dfd8] flex-shrink-0 animate-fade-in">
          <div className="bg-white border border-[#e6dfd8] rounded-xl p-4 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-[10px] text-[#8e8b82] uppercase tracking-wider font-semibold">Tập tài liệu</p>
              <h4 className="text-xl font-display font-semibold text-[#141413] mt-1">{stats.totalPages} Trang tài liệu</h4>
            </div>
            <div className="w-10 h-10 bg-[#f5f0e8] text-[#cc785c] rounded-xl flex items-center justify-center">
              <IconBook className="w-5 h-5" />
            </div>
          </div>
          <div className="bg-white border border-[#e6dfd8] rounded-xl p-4 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-[10px] text-[#8e8b82] uppercase tracking-wider font-semibold">Chủ đề chính</p>
              <h4 className="text-xl font-display font-semibold text-[#141413] mt-1">{stats.totalProjects} Dự án lịch sử</h4>
            </div>
            <div className="w-10 h-10 bg-[#f5f0e8] text-[#cc785c] rounded-xl flex items-center justify-center">
              <IconBrain className="w-5 h-5" />
            </div>
          </div>
          <div className="bg-white border border-[#e6dfd8] rounded-xl p-4 shadow-sm flex flex-col gap-3">
            <p className="text-[10px] text-[#8e8b82] uppercase tracking-wider font-semibold">Tỷ lệ theo Thời kỳ lịch sử</p>
            {/* Ratio bar */}
            <div className="flex h-2.5 bg-[#f5f0e8] rounded-full overflow-hidden gap-px">
              {Object.entries(stats.periodCounts).map(([periodKey, count]) => (
                <div
                  key={periodKey}
                  style={{ 
                    width: `${(count / (stats.totalPages || 1)) * 100}%`,
                    backgroundColor: getPeriodBarColor(periodKey),
                  }}
                  className="h-full transition-all duration-500 first:rounded-l-full last:rounded-r-full"
                  title={`${periodKey.replace(/-/g, ' ')}: ${count} trang`}
                />
              ))}
              {stats.totalPages === 0 && <div className="h-full w-full bg-[#e6dfd8] rounded-full" />}
            </div>
            {/* Legend */}
            <div className="flex flex-wrap gap-x-3 gap-y-1.5">
              {Object.entries(stats.periodCounts).map(([periodKey, count]) => (
                <button
                  key={periodKey}
                  onClick={() => setPeriod(period === periodKey ? "" : periodKey)}
                  className={cn(
                    "flex items-center gap-1.5 text-[10px] font-medium transition-opacity cursor-pointer",
                    period && period !== periodKey ? "opacity-40" : "opacity-100"
                  )}
                >
                  <span
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: getPeriodBarColor(periodKey) }}
                  />
                  <span className="text-[#6c6a64] capitalize">
                    {periodKey.replace(/-/g, " ")}
                  </span>
                  <span className="text-[#8e8b82]">({count})</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

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
              className="w-full pl-10 pr-12 py-2.5 bg-white border border-[#e6dfd8] rounded-xl text-sm text-[#141413] placeholder-[#8e8b82] outline-none focus:border-[#cc785c] focus:shadow-[0_0_0_3px_rgba(204,120,92,0.1)] transition-all"
            />
            {!search && (
              <kbd className="absolute right-3.5 top-1/2 -translate-y-1/2 px-1.5 py-0.5 text-[10px] font-sans font-medium text-[#8e8b82] bg-[#f5f0e8] border border-[#e6dfd8] rounded pointer-events-none">
                /
              </kbd>
            )}
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
        <div className="flex flex-wrap items-center gap-2">
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

          {(search || selectedProjectId || period) && (
            <button
              onClick={() => {
                setSearch("")
                setSelectedProjectId("")
                setPeriod("")
              }}
              className="text-xs font-semibold text-[#cc785c] hover:text-[#a9583e] flex items-center gap-1 transition-colors ml-2 bg-transparent border-0 cursor-pointer"
            >
              Xóa tất cả bộ lọc <IconClose className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Main Grid Section */}
        <div className="flex-1 overflow-y-auto px-8 pb-8">
          {error && (
            <div className="bg-red-50 border border-red-100 rounded-xl px-4 py-3 text-sm text-red-600 mb-6">
              {error}
            </div>
          )}

          {loading && page === 0 ? (
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} />)}
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
              <p className="text-xs text-[#8e8b82] mb-3">
                {allPages.length} trang wiki{debouncedSearch ? ` cho "${debouncedSearch}"` : ""}
              </p>

              {/* Table */}
              <div className="rounded-xl border border-[#e6dfd8] overflow-hidden">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="bg-[#f5f0e8] border-b border-[#e6dfd8]">
                      <th className="text-left px-4 py-3 text-[10px] font-semibold text-[#8e8b82] uppercase tracking-wider w-10">#</th>
                      <th className="text-left px-4 py-3 text-[10px] font-semibold text-[#8e8b82] uppercase tracking-wider">Tên trang</th>
                      <th className="text-left px-4 py-3 text-[10px] font-semibold text-[#8e8b82] uppercase tracking-wider hidden lg:table-cell">Mô tả</th>
                      <th className="text-left px-4 py-3 text-[10px] font-semibold text-[#8e8b82] uppercase tracking-wider hidden md:table-cell w-36">Phân loại</th>
                      <th className="text-left px-4 py-3 text-[10px] font-semibold text-[#8e8b82] uppercase tracking-wider hidden md:table-cell w-28">Giai đoạn</th>
                      <th className="text-right px-4 py-3 text-[10px] font-semibold text-[#8e8b82] uppercase tracking-wider w-28">Thao tác</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allPages.map((p, idx) => (
                      <WikiTableRow
                        key={p.id}
                        index={idx + 1}
                        page={p}
                        isSelected={selectedWikiPage?.id === p.id}
                        canDelete={user?.role === "admin" || user?.role === "editor"}
                        onClick={() => setSelectedWikiPage(p)}
                        onAskAI={(e) => {
                          e.stopPropagation()
                          navigate(`/chat?q=Hãy tóm tắt sự kiện lịch sử: ${p.title}`)
                        }}
                        onDelete={async () => {
                          if (!confirm(`Xóa trang "${p.title}"? Hành động này không thể hoàn tác.`)) return
                          try {
                            await wikiApi.deletePage(p.slug)
                            setAllPages(prev => prev.filter(x => x.id !== p.id))
                            if (selectedWikiPage?.id === p.id) setSelectedWikiPage(null)
                            showToast("Đã xóa trang wiki.", "success")
                          } catch (err) {
                            showToast(err instanceof Error ? err.message : "Không thể xóa trang", "error")
                          }
                        }}
                      />
                    ))}
                  </tbody>
                </table>
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

        {/* Slide-out Preview Drawer */}
        {selectedWikiPage && (
          <div className="w-[320px] sm:w-[400px] md:w-[480px] lg:w-[560px] border-l border-[#e6dfd8] bg-white flex flex-col h-full overflow-hidden flex-shrink-0 animate-fade-in relative shadow-[-4px_0_12px_rgba(0,0,0,0.03)]">
            {/* Drawer Header */}
            <div className="p-5 border-b border-[#e6dfd8] flex justify-between items-start gap-4">
              <div>
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {selectedWikiPage.period && (
                    <span
                      className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full border"
                      style={getPeriodBadgeStyle(selectedWikiPage.period)}
                    >
                      {selectedWikiPage.period.replace(/-/g, " ")}
                    </span>
                  )}
                  {selectedWikiPage.event_type && (
                    <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-[#f5f0e8] text-[#6c6a64] border border-[#e6dfd8]">
                      {selectedWikiPage.event_type}
                    </span>
                  )}
                </div>
                <h3 className="font-display font-semibold text-base text-[#141413] leading-snug">
                  {selectedWikiPage.title}
                </h3>
              </div>
              <button 
                onClick={() => setSelectedWikiPage(null)}
                className="p-1.5 rounded-lg hover:bg-[#f5f0e8] text-[#8e8b82] hover:text-[#141413] transition-colors cursor-pointer flex-shrink-0"
              >
                <IconClose className="w-4 h-4" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="flex-1 flex overflow-hidden">
              {/* ToC Sidebar */}
              <div className="w-36 border-r border-[#f5f0e8] p-4 text-[10px] space-y-1 select-none hidden md:block overflow-y-auto">
                <p className="font-semibold text-[#8e8b82] uppercase tracking-wider mb-2">Mục lục</p>
                {processedDrawerSections.map((sec) => (
                  <button
                    key={sec.title}
                    onClick={() => scrollToDrawerSection(sec.title)}
                    className="w-full text-left font-medium text-[#6c6a64] hover:text-[#cc785c] hover:bg-[#f5f0e8] p-1.5 rounded transition-all truncate block cursor-pointer"
                  >
                    {sec.title}
                  </button>
                ))}
              </div>

              {/* Main Content Area */}
              <div ref={drawerContentRef} className="flex-1 p-5 space-y-6 overflow-y-auto scroll-smooth">
                {selectedWikiPage.summary && (
                  <div className="bg-[#faf9f5] border border-[#e6dfd8] rounded-xl p-4 text-xs text-[#3d3d3a] leading-relaxed">
                    <p className="font-semibold text-[#8e8b82] uppercase tracking-wider mb-1">Tóm tắt</p>
                    <p>{selectedWikiPage.summary}</p>
                  </div>
                )}

                {processedDrawerSections.length > 0 ? (
                  <div className="space-y-6">
                    {processedDrawerSections.map((sec) => (
                      <div 
                        key={sec.title} 
                        id={`drawer-sec-${sec.title.toLowerCase().replace(/[^a-z0-9]/g, "-")}`}
                        className="scroll-mt-4"
                      >
                        <h4 className="font-display font-semibold text-xs text-[#141413] border-b border-[#f5f0e8] pb-1.5 mb-2">
                          {sec.title}
                        </h4>
                        <div className="text-xs text-[#3d3d3a] leading-relaxed prose prose-sm max-w-none">
                          <MarkdownRenderer content={sec.content} />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-[#8e8b82] italic text-center py-8">
                    Đang tải nội dung chi tiết...
                  </div>
                )}
              </div>
            </div>

            {/* Drawer Footer */}
            <div className="p-4 border-t border-[#e6dfd8] bg-[#faf9f5] flex items-center justify-between gap-2">
              <button
                onClick={() => navigate(`/chat?context_type=wiki&context_id=${selectedWikiPage.slug}`)}
                className="flex items-center justify-center gap-1.5 px-3.5 py-2 border border-[#e6dfd8] text-xs font-semibold text-[#6c6a64] hover:text-[#cc785c] hover:border-[#cc785c]/40 rounded-xl transition-all bg-white flex-1 cursor-pointer"
              >
                <IconMessageSquare className="w-3.5 h-3.5" />
                Hỏi AI
              </button>
              <button
                onClick={() => navigate(`/wiki/${selectedWikiPage.slug}`)}
                className="flex items-center justify-center gap-1.5 px-3.5 py-2 bg-[#cc785c] text-white text-xs font-semibold rounded-xl hover:bg-[#a9583e] transition-all flex-1 cursor-pointer"
              >
                Xem chi tiết
                <IconExternalLink className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
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
          <div
            className="bg-white border border-[#e6dfd8] rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-xl animate-fade-in mx-4 relative overflow-hidden"
            onDragOver={(e) => { e.preventDefault(); setIsDraggingFile(true) }}
            onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setIsDraggingFile(false) }}
            onDrop={handleModalDrop}
          >
            {/* Drag overlay */}
            {isDraggingFile && (
              <div className="absolute inset-0 z-20 bg-[#cc785c]/5 border-2 border-dashed border-[#cc785c] rounded-2xl flex flex-col items-center justify-center pointer-events-none">
                <IconUpload className="w-10 h-10 text-[#cc785c] mb-3" />
                <p className="text-[#cc785c] font-semibold text-base">Thả file .md vào đây</p>
                <p className="text-[#cc785c]/70 text-xs mt-1">Nội dung sẽ được tự động điền vào form</p>
              </div>
            )}
            <div className="flex justify-between items-center p-6 border-b border-[#e6dfd8] flex-shrink-0">
              <div>
                <h3 className="text-lg font-display font-semibold text-[#141413]">Đề xuất trang wiki mới</h3>
                <p className="text-xs text-[#8e8b82] mt-0.5">
                  Bản thảo sẽ được gửi duyệt · Kéo thả file <kbd className="px-1 py-0.5 bg-[#f5f0e8] border border-[#e6dfd8] rounded text-[9px]">.md</kbd> vào đây để tự động điền
                </p>
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

// ── Table Row subcomponent ─────────────────────────────
function WikiTableRow({ 
  index,
  page, 
  isSelected,
  canDelete,
  onClick, 
  onAskAI,
  onDelete,
}: { 
  index: number
  page: WikiPage 
  isSelected: boolean
  canDelete: boolean
  onClick: () => void 
  onAskAI: (e: React.MouseEvent) => void 
  onDelete: () => void
}) {
  return (
    <tr
      onClick={onClick}
      className={cn(
        "border-b border-[#f5f0e8] group cursor-pointer transition-colors duration-100",
        isSelected
          ? "bg-[#cc785c]/5"
          : "hover:bg-[#faf9f5] even:bg-[#fcfbf9]"
      )}
    >
      {/* # */}
      <td className="px-4 py-3 text-[11px] text-[#c0bab4] font-mono select-none">
        {index}
      </td>

      {/* Tên */}
      <td className="px-4 py-3">
        <p className={cn(
          "font-display font-semibold text-sm leading-snug line-clamp-1 transition-colors",
          isSelected ? "text-[#cc785c]" : "text-[#141413] group-hover:text-[#cc785c]"
        )}>
          {page.title}
        </p>
      </td>

      {/* Mô tả */}
      <td className="px-4 py-3 hidden lg:table-cell">
        <p className="text-xs text-[#6c6a64] line-clamp-1 leading-relaxed max-w-sm">
          {page.summary || <span className="text-[#c0bab4] italic">Chưa có mô tả</span>}
        </p>
      </td>

      {/* Phân loại */}
      <td className="px-4 py-3 hidden md:table-cell">
        {page.event_type ? (
          <span className="inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#f5f0e8] text-[#6c6a64] border border-[#e6dfd8] truncate max-w-[120px]">
            {page.event_type}
          </span>
        ) : (
          <span className="text-[#c0bab4] text-[11px]">—</span>
        )}
      </td>

      {/* Giai đoạn (màu) */}
      <td className="px-4 py-3 hidden md:table-cell">
        {page.period ? (
          <span
            className="inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full border truncate max-w-[110px]"
            style={getPeriodBadgeStyle(page.period)}
          >
            {page.period.replace(/-/g, " ")}
          </span>
        ) : (
          <span className="text-[#c0bab4] text-[11px]">—</span>
        )}
      </td>

      {/* Thao tác */}
      <td className="px-4 py-3">
        <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={onAskAI}
            title="Hỏi AI"
            className="p-1.5 rounded-lg text-[#8e8b82] hover:text-[#cc785c] hover:bg-[#f5f0e8] transition-colors cursor-pointer"
          >
            <IconMessageSquare className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onClick() }}
            title="Xem nhanh"
            className="p-1.5 rounded-lg text-[#8e8b82] hover:text-[#cc785c] hover:bg-[#f5f0e8] transition-colors cursor-pointer"
          >
            <IconChevronRight className="w-3.5 h-3.5" />
          </button>
          {canDelete && (
            <button
              onClick={(e) => { e.stopPropagation(); onDelete() }}
              title="Xóa trang"
              className="p-1.5 rounded-lg text-[#8e8b82] hover:text-red-500 hover:bg-red-50 transition-colors cursor-pointer"
            >
              <IconTrash className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </td>
    </tr>
  )
}
