import { useEffect, useState, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { timelineApi, wikiApi, type TimelineEvent } from "@/lib/api/brain"
import { cn } from "@/lib/utils/cn"
import {
  Search,
  Sparkles,
  ArrowRight,
  Info,
  BookOpen,
  MessageSquare,
  X,
  Compass,
  ArrowUpRight,
  HelpCircle,
  FileText,
  User,
  MapPin,
  Calendar,
  Layers,
  Link2
} from "lucide-react"

// ── Period filters config ──────────────────────────────────
interface PeriodFilter {
  value: string
  label: string
  icon: string
  color: string
  startYear?: number
  endYear?: number
}

const PERIOD_FILTERS: PeriodFilter[] = [
  { value: "all", label: "Toàn bộ lịch sử", icon: "◉", color: "text-[#cc785c]" },
  { value: "chong-phap", label: "Kháng chiến chống Pháp", icon: "🟦", color: "text-sky-500", startYear: 1945, endYear: 1954 },
  { value: "chong-my", label: "Kháng chiến chống Mỹ", icon: "🟥", color: "text-rose-500", startYear: 1954, endYear: 1975 },
  { value: "thong-nhat", label: "Đổi mới & Hiện đại", icon: "🟩", color: "text-emerald-500", startYear: 1975 },
]

const PERIOD_LABELS: Record<string, string> = {
  "khang-chien-chong-phap": "Kháng chiến chống Pháp (1945–1954)",
  "khang-chien-chong-my": "Kháng chiến chống Mỹ (1954–1975)",
  "thong-nhat": "Kỷ nguyên Thống nhất (1975–Nay)",
}

function getPeriodColorClass(period: string) {
  if (period === "khang-chien-chong-phap") return "sky"
  if (period === "khang-chien-chong-my") return "rose"
  if (period === "thong-nhat") return "emerald"
  return "amber"
}

function formatEventDate(ev: TimelineEvent) {
  if (ev.day && ev.month) return `${ev.day}/${ev.month}/${ev.year}`
  if (ev.month) return `${ev.month}/${ev.year}`
  return ev.year < 0 ? `TCN ${Math.abs(ev.year)}` : String(ev.year)
}

function getEventCategory(title: string) {
  const t = title.toLowerCase()
  if (t.includes("chiến dịch") || t.includes("trận") || t.includes("kháng chiến") || t.includes("chiến đấu") || t.includes("quân sự") || t.includes("tấn công") || t.includes("đánh chiếm")) {
    return { label: "Quân sự", icon: "⚔️", color: "bg-red-50 text-red-600 border-red-100" }
  }
  if (t.includes("hiệp định") || t.includes("hội nghị") || t.includes("hiệp ước") || t.includes("ký kết") || t.includes("đàm phán") || t.includes("ngoại giao")) {
    return { label: "Ngoại giao", icon: "🤝", color: "bg-sky-50 text-sky-600 border-sky-100" }
  }
  if (t.includes("thành lập") || t.includes("đại hội") || t.includes("chính phủ") || t.includes("ban chấp hành") || t.includes("hiến pháp") || t.includes("quốc hội") || t.includes("độc lập")) {
    return { label: "Chính trị", icon: "🏛️", color: "bg-amber-50 text-amber-700 border-amber-100" }
  }
  if (t.includes("văn hóa") || t.includes("xã hội") || t.includes("giáo dục") || t.includes("phong trào") || t.includes("học tập")) {
    return { label: "Văn hóa", icon: "📜", color: "bg-emerald-50 text-emerald-600 border-emerald-100" }
  }
  return { label: "Lịch sử", icon: "📅", color: "bg-stone-50 text-stone-600 border-stone-200" }
}

function getEntityIcon(name: string) {
  const lowercase = name.toLowerCase()
  const locationKeywords = ["sông", "núi", "đèo", "ải", "vịnh", "biển", "quốc gia", "tỉnh", "thành phố", "quận", "huyện", "thị xã", "hà nội", "sài gòn", "huế", "điện biên", "quảng trị", "bạch đằng"]
  if (locationKeywords.some(kw => lowercase.includes(kw))) return "📍"

  const docKeywords = ["hiệp định", "hội nghị", "hiệp ước", "tuyên ngôn", "sắc lệnh", "hiến pháp", "chỉ thị", "nghị quyết"]
  if (docKeywords.some(kw => lowercase.includes(kw))) return "📄"

  const orgKeywords = ["đảng", "mặt trận", "quân đội", "chính phủ", "quốc hội", "trung ương"]
  if (orgKeywords.some(kw => lowercase.includes(kw))) return "🏛️"

  const personKeywords = ["vua", "chúa", "tướng", "đại tướng", "hoàng đế", "bác", "ông", "bà", "nguyễn", "trần", "lê", "phạm", "phan", "võ", "hồ"]
  if (personKeywords.some(kw => lowercase.startsWith(kw) || lowercase.includes(" " + kw))) return "👤"

  return "🏷️"
}

interface WikiContextData {
  context?: {
    entities?: string[];
  };
}

export function TimelinePage() {
  const navigate = useNavigate()

  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [selectedPeriod, setSelectedPeriod] = useState<string>("all")
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [showSuggestions, setShowSuggestions] = useState(false)
  const suggestionsRef = useRef<HTMLDivElement>(null)

  // Click outside to close search suggestions
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  // Knowledge Graph connections from active wiki page
  const [wikiContext, setWikiContext] = useState<WikiContextData | null>(null)
  const [loadingContext, setLoadingContext] = useState(false)

  // Fetch events based on selected period
  useEffect(() => {
    setLoading(true)
    setError(null)
    const pf = PERIOD_FILTERS.find((p) => p.value === selectedPeriod)
    timelineApi.getEvents({
      start_year: pf?.startYear,
      end_year: pf?.endYear,
    })
      .then((res) => {
        setEvents(res.events || [])
        setExpandedEvent(null)
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Không thể tải dữ liệu dòng lịch sử")
        setEvents([])
      })
      .finally(() => setLoading(false))
  }, [selectedPeriod])

  // Filter events based on Search Query
  const sortedEvents = [...events].sort((a, b) => a.year - b.year)
  const filteredEvents = sortedEvents.filter(ev =>
    ev.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (ev.summary && ev.summary.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  // Fetch context for details view
  const expandedData = expandedEvent ? events.find((e) => e.id === expandedEvent) : null

  useEffect(() => {
    if (expandedData?.wiki_page_slug) {
      setLoadingContext(true)
      setWikiContext(null)
      wikiApi.getContext(expandedData.wiki_page_slug)
        .then(res => {
          setWikiContext(res)
        })
        .catch(err => {
          console.error("Failed to load wiki context:", err)
          setWikiContext(null)
        })
        .finally(() => {
          setLoadingContext(false)
        })
    } else {
      setWikiContext(null)
      setLoadingContext(false)
    }
  }, [expandedEvent])

  // Group events by year
  const eventsByYear: Record<number, TimelineEvent[]> = {}
  filteredEvents.forEach(ev => {
    if (!eventsByYear[ev.year]) {
      eventsByYear[ev.year] = []
    }
    eventsByYear[ev.year].push(ev)
  })

  // Sorted unique years
  const uniqueYears = Object.keys(eventsByYear).map(Number).sort((a, b) => a - b)

  // Popular search suggestions helper
  const suggestions = [
    "Cách mạng tháng Tám",
    "Trận Điện Biên Phủ",
    "Hiệp định Genève",
    "Chiến dịch Hồ Chí Minh",
    "Đổi mới năm 1986"
  ]

  // Compute stats for current period
  const stats = { total: filteredEvents.length, military: 0, diplomacy: 0, politics: 0, culture: 0, general: 0 }
  filteredEvents.forEach(ev => {
    const cat = getEventCategory(ev.title).label
    if (cat === "Quân sự") stats.military++
    else if (cat === "Ngoại giao") stats.diplomacy++
    else if (cat === "Chính trị") stats.politics++
    else if (cat === "Văn hóa") stats.culture++
    else stats.general++
  })
  const maxStat = Math.max(stats.military, stats.diplomacy, stats.politics, stats.culture, stats.general) || 1

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#faf8f3] relative">
      {/* Noise Texture Overlay for Physical Material Vibe */}
      <div className="absolute inset-0 opacity-[0.015] pointer-events-none z-40 mix-blend-overlay"
        style={{
          backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")"
        }}
      />

      <style>{`
        @keyframes dash {
          to {
            stroke-dashoffset: -20;
          }
        }
        .animate-dash-line {
          stroke-dasharray: 4, 4;
          animation: dash 1s linear infinite;
        }
        @keyframes float-1 {
          0%, 100% { transform: translateY(0px) translateX(0px); }
          50% { transform: translateY(-5px) translateX(2px); }
        }
        @keyframes float-2 {
          0%, 100% { transform: translateY(0px) translateX(0px); }
          50% { transform: translateY(4px) translateX(-3px); }
        }
        @keyframes float-3 {
          0%, 100% { transform: translateY(0px) translateX(0px); }
          50% { transform: translateY(-3px) translateX(-4px); }
        }
        .animate-float-1 {
          animation: float-1 5s ease-in-out infinite;
        }
        .animate-float-2 {
          animation: float-2 6s ease-in-out infinite;
        }
        .animate-float-3 {
          animation: float-3 7s ease-in-out infinite;
        }
        @keyframes center-pulse {
          0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(204,120,92,0.15), 0 4px 12px rgba(0,0,0,0.05); }
          50% { transform: scale(1.03); box-shadow: 0 0 16px 6px rgba(204,120,92,0.25), 0 8px 24px rgba(0,0,0,0.08); }
        }
        .animate-center-pulse {
          animation: center-pulse 4s ease-in-out infinite;
        }
      `}</style>

      {/* ── HEADER REDESIGN ── */}
      <header className="px-8 pt-8 pb-5 bg-[#faf8f3] border-b border-[#e8ddd0]/45 flex flex-col md:flex-row md:items-center justify-between gap-6 flex-shrink-0">
        <div className="text-left">
          <span className="text-[10px] font-bold tracking-[0.25em] text-[#cc785c] uppercase">
            Học viện Tri thức Số hóa
          </span>
          <h2 className="text-3xl font-serif font-semibold text-[#1c1a17] tracking-tight mt-1">
            LỊCH SỬ VIỆT NAM
          </h2>
          <p className="text-xs text-[#7c756b] mt-1 font-medium">
            Khám phá dòng chảy lịch sử Việt Nam bằng Trí tuệ Nhân tạo (RAG)
          </p>
        </div>

        {/* Global Search Interface */}
        <div className="relative w-full md:w-96" ref={suggestionsRef}>
          <div className="relative p-0.5 rounded-full bg-white border border-[#e8ddd0] focus-within:border-[#cc785c] transition-colors flex items-center">
            <Search className="absolute left-3.5 top-3 w-4 h-4 text-[#8c8275] pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setShowSuggestions(true)}
              placeholder="Tìm kiếm sự kiện hoặc bối cảnh..."
              className="w-full pl-10 pr-9 py-2 bg-transparent text-sm text-[#1c1a17] placeholder-[#a69c8f] focus:outline-none border-none rounded-full"
            />
            {searchQuery && (
              <button
                onClick={() => {
                  setSearchQuery("")
                  setShowSuggestions(false)
                }}
                className="absolute right-3 top-2.5 p-1 text-[#8c8275] hover:text-[#1c1a17] bg-transparent hover:bg-[#faf8f3] rounded-full border-none cursor-pointer flex items-center justify-center transition-colors"
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Search Suggestions Dropdown Popover */}
          {showSuggestions && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-[#faf8f3] border border-[#e8ddd0]/80 shadow-[0_8px_30px_rgba(28,26,23,0.08)] rounded-xl z-30 p-3 space-y-1.5 transition-all">
              <div className="px-2 py-1 text-[9px] font-bold uppercase tracking-[0.15em] text-[#8c8275] border-b border-[#e8ddd0]/45 pb-1.5 mb-1.5">
                💡 Gợi ý tìm kiếm phổ biến
              </div>
              <div className="flex flex-col gap-0.5">
                {suggestions.map((sug, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setSearchQuery(sug)
                      setShowSuggestions(false)
                    }}
                    className="w-full text-left px-2.5 py-2 text-xs font-semibold text-[#1c1a17] hover:bg-[#f0eae1] rounded-lg transition-colors flex items-center gap-2.5 group cursor-pointer border-none bg-transparent"
                  >
                    <span className="text-[#cc785c] group-hover:scale-110 transition-transform">◉</span>
                    <span className="line-clamp-1">{sug}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </header>

      {/* ── FILTER REDESIGN (Custom Chips) ── */}
      <div className="px-8 py-3 bg-[#faf8f3] border-b border-[#e8ddd0]/45 flex-shrink-0 flex items-center justify-between">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
          {PERIOD_FILTERS.map((pf) => (
            <button
              key={pf.value}
              onClick={() => setSelectedPeriod(pf.value)}
              className={cn(
                "px-4 py-1.5 rounded-full text-xs font-semibold transition-all duration-200 border cursor-pointer flex items-center gap-1.5 shrink-0",
                selectedPeriod === pf.value
                  ? "bg-[#cc785c] text-white border-[#cc785c]"
                  : "bg-white text-[#5c544a] border-[#e8ddd0] hover:border-[#cc785c] hover:bg-[#faf8f3]"
              )}
            >
              <span>{pf.icon}</span>
              <span>{pf.label}</span>
            </button>
          ))}
        </div>

        <div className="hidden lg:flex items-center gap-1.5 text-xs text-[#8c8275] font-semibold">
          <Layers size={13} className="text-[#cc785c]" />
          <span>{filteredEvents.length} mốc lịch sử</span>
        </div>
      </div>

      {/* ── MAIN WORKSPACE: Vertical Historical Stream ── */}
      <div className="flex-1 bg-[#faf8f3] p-6 overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-10 gap-6 h-full overflow-hidden">

          {/* Left Column: Timeline List */}
          <div className="col-span-1 lg:col-span-6 h-full overflow-y-auto pr-2 scrollbar-thin text-left flex flex-col">

            {loading ? (
              <div className="h-full flex items-center justify-center">
                <div className="flex flex-col items-center gap-2 text-[#8c8275] animate-pulse">
                  <div className="w-8 h-8 rounded-full border-2 border-[#cc785c] border-t-transparent animate-spin" />
                  <span className="text-xs font-semibold uppercase tracking-wider">Đang tải biên niên sử...</span>
                </div>
              </div>
            ) : error ? (
              <div className="max-w-md mx-auto mt-8 bg-red-50 border border-red-100 rounded-sm p-5 text-red-600 text-sm flex items-center gap-2.5">
                <Info size={16} />
                <span>{error}</span>
              </div>
            ) : filteredEvents.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center max-w-sm mx-auto">
                <div className="w-14 h-14 rounded-sm bg-white border border-[#e8ddd0] flex items-center justify-center mb-4 text-[#8c8275] shadow-sm">
                  <Compass size={24} />
                </div>
                <h4 className="text-sm font-semibold text-[#1c1a17]">Không tìm thấy mốc lịch sử nào</h4>
                <p className="text-xs text-[#8c8275] mt-1 leading-relaxed">
                  Thử đổi từ khóa hoặc bộ lọc thời kỳ để tiếp tục khám phá kho tàng lịch sử Việt Nam.
                </p>
              </div>
            ) : (
              <div className="relative pl-6 border-l-2 border-[#e8ddd0] ml-4 space-y-8 max-w-full text-left py-2">

                {uniqueYears.map((year) => {
                  const yearEvents = eventsByYear[year]

                  return (
                    <div key={year} className="relative">

                      {/* Year Section Header */}
                      <div className="flex items-center gap-2 mb-3 -ml-6">
                        <div className="w-3 h-3 rounded-full border-2 border-[#cc785c] bg-[#faf8f3] flex-shrink-0 z-10" />
                        <span className="font-mono text-[11px] font-bold text-[#cc785c] tracking-[0.1em] uppercase">
                          {year < 0 ? `TCN ${Math.abs(year)}` : year}
                        </span>
                        <div className="flex-1 h-px bg-[#e8ddd0]" />
                      </div>

                      {/* Events list */}
                      <div className="space-y-2">
                        {yearEvents.map((ev) => {
                          const isSelected = expandedEvent === ev.id
                          const cat = getEventCategory(ev.title)

                          return (
                            <div
                              key={ev.id}
                              onClick={() => setExpandedEvent(isSelected ? null : ev.id)}
                              className={cn(
                                "relative p-2.5 pl-3.5 pr-2.5 bg-white border border-[#e8ddd0] transition-all duration-200 cursor-pointer text-left rounded-sm group",
                                isSelected
                                  ? "border-[#cc785c] bg-[#cc785c]/5 shadow-[0_2px_12px_rgba(204,120,92,0.05)] translate-x-0.5"
                                  : "hover:bg-[#faf8f3] hover:border-[#cc785c]/45 hover:translate-x-0.5"
                              )}
                            >
                              <div className={cn(
                                "absolute left-0 top-0 bottom-0 w-[3px] rounded-l-sm transition-colors",
                                isSelected ? "bg-[#cc785c]" : "bg-transparent group-hover:bg-[#cc785c]/45"
                              )} />

                              <div className="flex items-center justify-between gap-2 mb-1">
                                <span className={cn("text-[9px] font-bold tracking-wider uppercase px-1.5 py-0.5 rounded-sm", cat.color)}>
                                  {cat.icon} {cat.label}
                                </span>
                                <span className="font-mono text-[9px] text-[#a09589]">
                                  {formatEventDate(ev)}
                                </span>
                              </div>

                              <h3 className={cn(
                                "font-serif text-[13px] font-bold leading-snug transition-colors",
                                isSelected ? "text-[#cc785c]" : "text-[#1c1a17] group-hover:text-[#cc785c]"
                              )}>
                                {ev.title}
                              </h3>
                            </div>
                          )
                        })}
                      </div>

                    </div>
                  )
                })}

              </div>
            )}
          </div>

          {/* ── DRAWER BACKDROP OVERLAY ── */}
          {expandedEvent && (
            <div
              className="fixed inset-0 bg-black/10 backdrop-blur-xs z-40 transition-opacity duration-300 lg:hidden"
              onClick={() => setExpandedEvent(null)}
            />
          )}

          {/* ── RIGHT COLUMN: AI Insights Panel ── */}
          <div className={cn(
            "fixed top-0 right-0 h-full w-[400px] max-w-[90vw] z-50 transition-transform duration-300 transform shadow-[-8px_0_24px_rgba(28,26,23,0.08)] border-l border-[#e8ddd0] flex flex-col bg-[#faf8f3]",
            expandedEvent ? "translate-x-0" : "translate-x-full",
            "lg:static lg:col-span-4 lg:h-full lg:w-full lg:max-w-none lg:shadow-none lg:translate-x-0 lg:z-0 lg:overflow-hidden lg:flex"
          )}>
            {expandedData ? (
              // DETAILED VIEW: Active selection state
              <div className="flex-1 flex flex-col overflow-hidden text-left h-full bg-[#FAF9F5]">
                {/* Context Panel Header */}
                <div className="px-6 py-5 bg-[#FAF9F5]/90 backdrop-blur-md border-b border-stone-200/50 flex items-center justify-between flex-shrink-0">
                  <div className="flex items-center gap-3">
                    <span className="text-xl bg-white w-9 h-9 rounded-xl flex items-center justify-center border border-stone-200/80 shadow-[0_2px_8px_rgba(0,0,0,0.02)]">
                      {getEventCategory(expandedData.title).icon}
                    </span>
                    <div className="text-left">
                      <span className="text-[9px] font-bold uppercase tracking-[0.25em] text-stone-400">
                        AI CONTEXT PANEL
                      </span>
                      <div className="text-xs font-bold text-[#cc785c] mt-0.5 font-mono">
                        {formatEventDate(expandedData)}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => setExpandedEvent(null)}
                    className="w-7 h-7 rounded-full flex items-center justify-center text-stone-400 hover:bg-white hover:text-stone-900 border border-transparent hover:border-stone-200 transition-all cursor-pointer bg-white/50"
                  >
                    <X size={14} />
                  </button>
                </div>

                {/* Context Panel Content */}
                <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 scrollbar-thin">

                  {/* Header title */}
                  <div className="text-left space-y-2">
                    <div className="inline-block px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-[0.15em] rounded-md bg-stone-100 text-stone-600 border border-stone-200/30">
                      {getEraLabel(expandedData.period) || "Sự kiện lịch sử"}
                    </div>
                    <h3 className="font-serif text-xl font-bold text-stone-900 leading-snug tracking-tight">
                      {expandedData.title}
                    </h3>
                  </div>

                  {/* Importance Summary - Styled as Museum Quote Block */}
                  {expandedData.summary && (
                    <div className="text-left space-y-2.5">
                      <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-stone-400">
                        Ý NGHĨA LỊCH SỬ
                      </h4>
                      <div className="p-1 rounded-[20px] bg-stone-900/5 ring-1 ring-stone-900/10 shadow-[0_4px_20px_rgba(0,0,0,0.01)]">
                        <div className="p-5 rounded-[calc(20px-4px)] bg-white border border-stone-200/40 relative overflow-hidden">
                          {/* Large quotes watermark */}
                          <span className="absolute left-2 -top-4 text-7xl font-serif text-stone-100 pointer-events-none select-none">“</span>
                          <p className="text-[12.5px] text-stone-850 leading-relaxed font-serif italic relative z-10 pl-4">
                            {expandedData.summary}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Sơ đồ Liên kết Tri thức (Knowledge Graph) */}
                  <div className="text-left space-y-2.5">
                    <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-stone-400 flex items-center gap-1.5">
                      <span>🕸️</span> SƠ ĐỒ LIÊN KẾT TRI THỨC
                    </h4>

                    <div className="p-1 rounded-[24px] bg-stone-900/5 ring-1 ring-stone-900/10 shadow-[0_4px_20px_rgba(0,0,0,0.01)]">
                      <div className="p-5 rounded-[calc(24px-4px)] bg-white border border-stone-200/40 flex flex-col items-center justify-center min-h-[290px] relative overflow-hidden">

                        {/* Background Grid */}
                        <div className="absolute inset-0 opacity-[0.02] pointer-events-none"
                          style={{ backgroundImage: "radial-gradient(#cc785c 1px, transparent 1px)", backgroundSize: "16px 16px" }} />

                        {loadingContext ? (
                          <div className="flex flex-col items-center gap-2 text-stone-400">
                            <div className="w-5 h-5 rounded-full border-2 border-[#cc785c] border-t-transparent animate-spin" />
                            <span className="text-xs">Đang truy vấn liên kết...</span>
                          </div>
                        ) : wikiContext?.context?.entities && wikiContext.context.entities.length > 0 ? (
                          <div className="relative w-full h-64 flex items-center justify-center">

                            {/* SVG Connector lines canvas covering entire container */}
                            <svg className="absolute inset-0 w-full h-full pointer-events-none z-0" style={{ overflow: "visible" }}>
                              {wikiContext.context.entities.slice(0, 5).map((entity: string, idx: number) => {
                                const angle = (idx * 2 * Math.PI) / Math.min(wikiContext.context.entities.slice(0, 5).length, 5)
                                const radius = 95
                                // Relative coordinates from center of canvas (which is at 50%, 50%)
                                return (
                                  <g key={idx}>
                                    {/* Glowing base line */}
                                    <line
                                      x1="50%"
                                      y1="50%"
                                      x2={`calc(50% + ${radius * Math.cos(angle)}px)`}
                                      y2={`calc(50% + ${radius * Math.sin(angle)}px)`}
                                      stroke="#cc785c"
                                      strokeWidth="1"
                                      className="opacity-15"
                                    />
                                    {/* Animated dashing connector line */}
                                    <line
                                      x1="50%"
                                      y1="50%"
                                      x2={`calc(50% + ${radius * Math.cos(angle)}px)`}
                                      y2={`calc(50% + ${radius * Math.sin(angle)}px)`}
                                      stroke="#cc785c"
                                      strokeWidth="1.2"
                                      className="animate-dash-line opacity-40"
                                    />
                                  </g>
                                )
                              })}
                            </svg>

                            {/* Center Node */}
                            <div className="absolute z-20 w-24 h-24 rounded-full bg-stone-900 text-white flex flex-col items-center justify-center text-center p-3 border-2 border-stone-800 animate-center-pulse select-none">
                              <span className="text-[7.5px] font-bold uppercase tracking-[0.1em] text-stone-400 mb-0.5">
                                ĐANG XEM
                              </span>
                              <span className="text-[9.5px] font-serif font-bold leading-tight line-clamp-3">
                                {expandedData.title}
                              </span>
                            </div>

                            {/* Satellite Nodes */}
                            {wikiContext.context.entities.slice(0, 5).map((entity: string, idx: number) => {
                              const angle = (idx * 2 * Math.PI) / Math.min(wikiContext.context.entities.slice(0, 5).length, 5)
                              const radius = 95
                              const x = Math.round(radius * Math.cos(angle))
                              const y = Math.round(radius * Math.sin(angle))
                              const icon = getEntityIcon(entity)

                              return (
                                <div
                                  key={idx}
                                  className="absolute z-10"
                                  style={{ transform: `translate(${x}px, ${y}px)` }}
                                >
                                  <button
                                    onClick={() => navigate(`/chat?q=${encodeURIComponent(`Hãy kể cho tôi nghe về ${entity}`)}`)}
                                    title={`Hỏi AI về ${entity}`}
                                    className={`px-3 py-1.5 bg-white hover:bg-stone-50 border border-stone-200/80 hover:border-[#cc785c] rounded-full shadow-[0_2px_8px_rgba(0,0,0,0.02)] hover:shadow-[0_8px_16px_rgba(204,120,92,0.1)] flex items-center gap-1.5 transition-all duration-300 cursor-pointer scale-100 hover:scale-105 active:scale-[0.97] animate-float-${(idx % 3) + 1} select-none`}
                                    style={{ animationDelay: `${idx * 0.4}s` }}
                                  >
                                    <span className="text-xs shrink-0">{icon}</span>
                                    <span className="text-[9px] font-bold uppercase tracking-wider text-stone-700 max-w-[85px] truncate">
                                      {entity}
                                    </span>
                                  </button>
                                </div>
                              )
                            })}
                          </div>
                        ) : (
                          <div className="text-xs text-stone-400 italic">
                            Không tìm thấy thực thể liên quan trực tiếp.
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Connected Entity Buttons */}
                  {wikiContext?.context?.entities && wikiContext.context.entities.length > 0 && (
                    <div className="text-left space-y-2.5">
                      <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-stone-400">
                        THỰC THỂ KẾT NỐI
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {wikiContext.context.entities.map((entity: string, idx: number) => {
                          const icon = getEntityIcon(entity)
                          return (
                            <button
                              key={idx}
                              onClick={() => navigate(`/chat?q=${encodeURIComponent(`Hãy phân tích mối liên hệ của nhân vật/sự kiện "${entity}" đối với sự kiện "${expandedData.title}"`)}`)}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-stone-50 border border-stone-200/60 hover:border-stone-400 rounded-full text-xs font-semibold text-stone-700 transition-all duration-200 cursor-pointer shadow-[0_1px_3px_rgba(0,0,0,0.01)] hover:shadow-sm"
                            >
                              <span>{icon}</span>
                              <span className="text-stone-850 font-semibold">{entity}</span>
                              <ArrowUpRight size={10} className="text-stone-400" />
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {/* Trợ lý Lịch sử AI RAG (Prompt cards) */}
                  <div className="space-y-3.5 text-left">
                    <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-stone-400 flex items-center gap-1.5">
                      <Sparkles size={12} className="text-[#cc785c] animate-pulse" />
                      TRỢ LÝ AI RAG
                    </h4>

                    <div className="space-y-2">
                      {[
                        {
                          text: "Giải thích nguyên nhân & bối cảnh chính?",
                          query: `Giải thích bối cảnh lịch sử và nguyên nhân chính dẫn đến sự kiện "${expandedData.title}"?`
                        },
                        {
                          text: "Ảnh hưởng lâu dài đến lịch sử Việt Nam?",
                          query: `Phân tích ảnh hưởng lâu dài và tầm quan trọng lịch sử của sự kiện "${expandedData.title}"?`
                        }
                      ].map((prompt, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            navigate(`/chat?q=${encodeURIComponent(prompt.query)}&context_type=wiki&context_id=${expandedData.wiki_page_slug || ""}`)
                          }}
                          className="w-full text-left p-3.5 bg-white/80 hover:bg-white border border-stone-200/60 hover:border-stone-400 rounded-xl transition-all duration-300 group cursor-pointer shadow-[0_2px_8px_rgba(0,0,0,0.01)] hover:shadow-[0_8px_20px_rgba(204,120,92,0.04)] flex items-center justify-between gap-3 text-stone-700"
                        >
                          <span className="text-xs font-semibold text-stone-850 group-hover:text-[#cc785c] transition-colors line-clamp-1">
                            {prompt.text}
                          </span>
                          <span className="w-5 h-5 rounded-full bg-stone-50 group-hover:bg-[#cc785c]/10 flex items-center justify-center transition-colors shrink-0">
                            <ArrowRight size={10} className="text-stone-400 group-hover:text-[#cc785c] transition-colors" />
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                </div>

                {/* Context Panel Footer Actions */}
                <div className="p-4 border-t border-stone-200/50 bg-[#FAF9F5]/95 backdrop-blur-md flex gap-3 flex-shrink-0">
                  {expandedData.wiki_page_slug && (
                    <button
                      onClick={() => navigate(`/wiki/${expandedData.wiki_page_slug}`)}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 bg-white hover:bg-stone-50 text-stone-750 text-xs font-bold rounded-lg border border-stone-200 transition-all cursor-pointer shadow-2xs hover:border-stone-400 active:scale-[0.98]"
                    >
                      📖 Đọc tài liệu Wiki
                    </button>
                  )}
                  <button
                    onClick={() => navigate(`/chat?q=${encodeURIComponent(`Hãy kể cho tôi nghe chi tiết về ${expandedData.title}`)}&context_type=wiki&context_id=${expandedData.wiki_page_slug || ""}`)}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 bg-stone-900 hover:bg-stone-850 text-white text-xs font-bold rounded-lg transition-all shadow-xs cursor-pointer border-none active:scale-[0.98]"
                  >
                    💬 Hỏi AI Assistant
                  </button>
                </div>
              </div>
            ) : (
              // DEFAULT VIEW: Stats & Period Overview dashboard
              <div className="flex-1 flex flex-col overflow-hidden text-left h-full bg-[#FAF9F5]">
                {/* Header */}
                <div className="px-6 py-5 bg-[#FAF9F5]/90 backdrop-blur-md border-b border-stone-200/50 flex items-center justify-between flex-shrink-0">
                  <div className="flex items-center gap-3">
                    <span className="text-xl bg-white w-9 h-9 rounded-xl flex items-center justify-center border border-stone-200/80 shadow-[0_2px_8px_rgba(0,0,0,0.02)]">
                      📊
                    </span>
                    <div className="text-left">
                      <span className="text-[10px] font-bold uppercase tracking-[0.25em] text-stone-400">
                        BÁO CÁO THỜI KỲ
                      </span>
                      <div className="text-xs font-bold text-[#cc785c] mt-0.5 font-serif">
                        {PERIOD_FILTERS.find(p => p.value === selectedPeriod)?.label || "Toàn bộ lịch sử"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 scrollbar-thin">
                  {/* Total events card - Double-Bezel structure */}
                  <div className="p-1 rounded-[20px] bg-stone-900/5 ring-1 ring-stone-900/10 shadow-[0_4px_20px_rgba(0,0,0,0.01)]">
                    <div className="p-5 rounded-[calc(20px-4px)] bg-white border border-stone-200/40 text-left relative overflow-hidden">
                      {/* Decorative drum glow background */}
                      <div className="absolute -right-16 -bottom-16 w-36 h-36 opacity-[0.03] pointer-events-none">
                        <img src="/trong_dong.svg" alt="" className="w-full h-full object-contain animate-spin-slow" />
                      </div>
                      <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-stone-450 block mb-1">
                        SỐ LƯỢNG SỰ KIỆN GHI NHẬN
                      </span>
                      <div className="text-5xl font-serif font-semibold text-[#cc785c] tracking-tight">
                        {stats.total}
                      </div>
                      <p className="text-[11px] text-stone-400 mt-2 leading-relaxed">
                        Tổng số mốc sự kiện quan trọng trong dòng chảy lịch sử Việt Nam đang được lựa chọn.
                      </p>
                    </div>
                  </div>

                  {/* Category distribution Breakdown */}
                  <div className="space-y-3.5 text-left">
                    <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-stone-400">
                      PHÂN LOẠI SỰ KIỆN
                    </h4>

                    <div className="p-1 rounded-[24px] bg-stone-900/5 ring-1 ring-stone-900/10 shadow-[0_4px_20px_rgba(0,0,0,0.01)]">
                      <div className="p-5 rounded-[calc(24px-4px)] bg-white border border-stone-200/40 space-y-5">
                        
                        {/* Segmented Distribution Bar */}
                        <div className="space-y-1.5">
                          <div className="h-2.5 w-full bg-stone-100 rounded-full overflow-hidden flex shadow-[inset_0_1px_2px_rgba(0,0,0,0.05)]">
                            {stats.military > 0 && (
                              <div className="h-full bg-[#cc785c] transition-all duration-500" style={{ width: `${(stats.military / stats.total) * 100}%` }} title={`Quân sự: ${stats.military}`} />
                            )}
                            {stats.politics > 0 && (
                              <div className="h-full bg-[#d69e2e] transition-all duration-500" style={{ width: `${(stats.politics / stats.total) * 100}%` }} title={`Chính trị: ${stats.politics}`} />
                            )}
                            {stats.diplomacy > 0 && (
                              <div className="h-full bg-[#3182ce] transition-all duration-500" style={{ width: `${(stats.diplomacy / stats.total) * 100}%` }} title={`Ngoại giao: ${stats.diplomacy}`} />
                            )}
                            {stats.culture > 0 && (
                              <div className="h-full bg-[#38a169] transition-all duration-500" style={{ width: `${(stats.culture / stats.total) * 100}%` }} title={`Văn hóa: ${stats.culture}`} />
                            )}
                            {stats.general > 0 && (
                              <div className="h-full bg-[#718096] transition-all duration-500" style={{ width: `${(stats.general / stats.total) * 100}%` }} title={`Khác: ${stats.general}`} />
                            )}
                          </div>
                          <div className="flex flex-wrap gap-x-3 gap-y-1.5 pt-1 text-[10px] text-stone-500 font-semibold">
                            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#cc785c]" /> Quân sự</span>
                            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#d69e2e]" /> Chính trị</span>
                            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#3182ce]" /> Ngoại giao</span>
                            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#38a169]" /> Văn hóa</span>
                            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#718096]" /> Khác</span>
                          </div>
                        </div>

                        <div className="h-px bg-stone-100" />

                        {/* Detail Stats Meters */}
                        <div className="space-y-4">
                          {/* Military */}
                          <div className="space-y-1.5 group">
                            <div className="flex justify-between items-center text-xs font-semibold text-stone-700">
                              <span className="flex items-center gap-2 text-stone-600 transition-colors group-hover:text-[#cc785c]">⚔️ Quân sự</span>
                              <div className="flex items-center gap-1.5 font-mono">
                                <span className="text-stone-850 font-bold">{stats.military}</span>
                                <span className="text-[10px] text-stone-400">({Math.round((stats.military / (stats.total || 1)) * 100)}%)</span>
                              </div>
                            </div>
                            <div className="h-1.5 w-full bg-stone-100 rounded-full overflow-hidden">
                              <div className="h-full bg-[#cc785c] rounded-full transition-all duration-500" style={{ width: `${(stats.military / maxStat) * 100}%` }} />
                            </div>
                          </div>

                          {/* Politics */}
                          <div className="space-y-1.5 group">
                            <div className="flex justify-between items-center text-xs font-semibold text-stone-700">
                              <span className="flex items-center gap-2 text-stone-600 transition-colors group-hover:text-[#d69e2e]">🏛️ Chính trị</span>
                              <div className="flex items-center gap-1.5 font-mono">
                                <span className="text-stone-850 font-bold">{stats.politics}</span>
                                <span className="text-[10px] text-stone-400">({Math.round((stats.politics / (stats.total || 1)) * 100)}%)</span>
                              </div>
                            </div>
                            <div className="h-1.5 w-full bg-stone-100 rounded-full overflow-hidden">
                              <div className="h-full bg-[#d69e2e] rounded-full transition-all duration-500" style={{ width: `${(stats.politics / maxStat) * 100}%` }} />
                            </div>
                          </div>

                          {/* Diplomacy */}
                          <div className="space-y-1.5 group">
                            <div className="flex justify-between items-center text-xs font-semibold text-stone-700">
                              <span className="flex items-center gap-2 text-stone-600 transition-colors group-hover:text-[#3182ce]">🤝 Ngoại giao</span>
                              <div className="flex items-center gap-1.5 font-mono">
                                <span className="text-stone-850 font-bold">{stats.diplomacy}</span>
                                <span className="text-[10px] text-stone-400">({Math.round((stats.diplomacy / (stats.total || 1)) * 100)}%)</span>
                              </div>
                            </div>
                            <div className="h-1.5 w-full bg-stone-100 rounded-full overflow-hidden">
                              <div className="h-full bg-[#3182ce] rounded-full transition-all duration-500" style={{ width: `${(stats.diplomacy / maxStat) * 100}%` }} />
                            </div>
                          </div>

                          {/* Culture */}
                          <div className="space-y-1.5 group">
                            <div className="flex justify-between items-center text-xs font-semibold text-stone-700">
                              <span className="flex items-center gap-2 text-stone-600 transition-colors group-hover:text-[#38a169]">📜 Văn hóa</span>
                              <div className="flex items-center gap-1.5 font-mono">
                                <span className="text-stone-850 font-bold">{stats.culture}</span>
                                <span className="text-[10px] text-stone-400">({Math.round((stats.culture / (stats.total || 1)) * 100)}%)</span>
                              </div>
                            </div>
                            <div className="h-1.5 w-full bg-stone-100 rounded-full overflow-hidden">
                              <div className="h-full bg-[#38a169] rounded-full transition-all duration-500" style={{ width: `${(stats.culture / maxStat) * 100}%` }} />
                            </div>
                          </div>

                          {/* General */}
                          <div className="space-y-1.5 group">
                            <div className="flex justify-between items-center text-xs font-semibold text-stone-700">
                              <span className="flex items-center gap-2 text-stone-600 transition-colors group-hover:text-[#718096]">📅 Khác</span>
                              <div className="flex items-center gap-1.5 font-mono">
                                <span className="text-stone-850 font-bold">{stats.general}</span>
                                <span className="text-[10px] text-stone-400">({Math.round((stats.general / (stats.total || 1)) * 100)}%)</span>
                              </div>
                            </div>
                            <div className="h-1.5 w-full bg-stone-100 rounded-full overflow-hidden">
                              <div className="h-full bg-[#718096] rounded-full transition-all duration-500" style={{ width: `${(stats.general / maxStat) * 100}%` }} />
                            </div>
                          </div>
                        </div>

                      </div>
                    </div>
                  </div>

                  {/* AI suggestion prompt launcher */}
                  <div className="space-y-3.5 text-left">
                    <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-stone-400 flex items-center gap-1.5">
                      <Sparkles size={12} className="text-[#cc785c] animate-pulse" />
                      GỢI Ý HỎI ĐÁP AI RAG
                    </h4>

                    <div className="space-y-2.5">
                      {[
                        {
                          text: "Giới thiệu khái quát thời kỳ này?",
                          desc: "Phân tích bối cảnh chung, động lực lịch sử và đặc điểm tiêu biểu."
                        },
                        {
                          text: "Sự kiện bước ngoặt và bài học lớn?",
                          desc: "Rút ra các sự kiện làm thay đổi tiến trình và bài học quý giá cho mai sau."
                        }
                      ].map((prompt, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            const label = PERIOD_FILTERS.find(p => p.value === selectedPeriod)?.label || "toàn bộ lịch sử"
                            const query = idx === 0 
                              ? `Hãy khái quát các đặc điểm nổi bật và dấu ấn lịch sử chính của "${label}"?`
                              : `Các mốc sự kiện mang tính bước ngoặt và bài học lịch sử rút ra trong giai đoạn "${label}"?`
                            navigate(`/chat?q=${encodeURIComponent(query)}`)
                          }}
                          className="w-full text-left p-4 bg-white/80 hover:bg-white border border-stone-200/60 hover:border-stone-400 rounded-xl transition-all duration-300 group cursor-pointer shadow-[0_2px_8px_rgba(0,0,0,0.01)] hover:shadow-[0_8px_20px_rgba(204,120,92,0.05)] flex items-start justify-between gap-3 text-stone-700"
                        >
                          <div className="space-y-0.5">
                            <div className="text-xs font-semibold text-stone-850 group-hover:text-[#cc785c] transition-colors">
                              {prompt.text}
                            </div>
                            <div className="text-[10px] text-stone-450 leading-normal">
                              {prompt.desc}
                            </div>
                          </div>
                          <span className="w-6 h-6 rounded-full bg-stone-50 group-hover:bg-[#cc785c]/10 flex items-center justify-center transition-colors shrink-0">
                            <ArrowRight size={12} className="text-stone-400 group-hover:text-[#cc785c] transition-colors" />
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

        </div>
      </div>

    </div>
  )
}

function getEraLabel(period?: string): string {
  if (!period) return ""
  return PERIOD_LABELS[period] || period
    .split("-")
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}
