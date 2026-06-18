import { useEffect, useState } from "react"
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

export function TimelinePage() {
  const navigate = useNavigate()
  
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  const [selectedPeriod, setSelectedPeriod] = useState<string>("all")
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")

  // Knowledge Graph connections from active wiki page
  const [wikiContext, setWikiContext] = useState<any>(null)
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

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#faf8f3] relative">
      
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
        <div className="relative w-full md:w-96">
          <div className="relative p-0.5 rounded-sm bg-white border border-[#e8ddd0] focus-within:border-[#cc785c] transition-colors">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-[#8c8275] pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm kiếm sự kiện hoặc bối cảnh..."
              className="w-full pl-9 pr-8 py-2 bg-transparent text-sm text-[#1c1a17] placeholder-[#a69c8f] focus:outline-none border-none"
            />
            {searchQuery && (
              <button 
                onClick={() => setSearchQuery("")}
                className="absolute right-2 top-2 p-1 text-[#8c8275] hover:text-[#1c1a17] bg-transparent border-none cursor-pointer"
              >
                <X size={14} />
              </button>
            )}
          </div>
          
          {/* Quick search hints */}
          {!searchQuery && (
            <div className="hidden md:flex items-center gap-1.5 mt-2 overflow-x-auto text-[10px] text-[#8c8275]">
              <span className="font-semibold shrink-0">Gợi ý:</span>
              {suggestions.map((sug, i) => (
                <button
                  key={i}
                  onClick={() => setSearchQuery(sug)}
                  className="bg-[#f0eae1] hover:bg-[#e6dfd4] px-2 py-0.5 rounded-sm text-[#5c544a] border-none transition-colors cursor-pointer"
                >
                  {sug}
                </button>
              ))}
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
      <div className="flex-1 overflow-y-auto bg-[#faf8f3] px-8 py-8 relative">
        
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
          <div className="relative pl-6 sm:pl-20 border-l border-[#e8ddd0]/80 ml-4 sm:ml-16 space-y-12 max-w-4xl mx-auto text-left">
            
            {uniqueYears.map((year) => {
              const yearEvents = eventsByYear[year]
              
              return (
                <div key={year} className="relative">
                  
                  {/* Floating Timeline Year Badge */}
                  <div className="absolute -left-[31px] sm:-left-[105px] top-0 flex items-center">
                    <div className="w-4 h-4 rounded-full border-2 border-[#cc785c] bg-[#faf8f3] z-10 shadow-sm" />
                    <div className="w-[15px] sm:w-[50px] h-[1px] bg-[#e8ddd0]" />
                    <div className="font-serif text-xl sm:text-2xl font-bold text-[#cc785c] tracking-tight bg-[#faf8f3] px-2 rounded-sm">
                      {year < 0 ? `TCN ${Math.abs(year)}` : year}
                    </div>
                  </div>

                  {/* Events list under this year */}
                  <div className="pt-8 sm:pt-0 pl-2 space-y-5">
                    {yearEvents.map((ev) => {
                      const isSelected = expandedEvent === ev.id
                      const cat = getEventCategory(ev.title)
                      
                      return (
                        <div
                          key={ev.id}
                          onClick={() => setExpandedEvent(isSelected ? null : ev.id)}
                          className={cn(
                            "relative p-6 bg-white border border-[#e8ddd0] transition-all duration-300 cursor-pointer text-left rounded-sm pl-7",
                            isSelected 
                              ? "border-[#cc785c] shadow-[0_4px_20px_rgba(204,120,92,0.04)] translate-x-1" 
                              : "hover:border-[#cc785c]/60"
                          )}
                        >
                          <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#cc785c]" />
                          
                          <div className="flex items-center justify-between gap-3 mb-2">
                            <span className={cn("text-[9px] font-bold tracking-wider uppercase px-2 py-0.5 border border-transparent rounded-sm", cat.color)}>
                              {cat.icon} {cat.label}
                            </span>
                            <span className="font-mono text-xs text-[#8c8275] bg-[#f0eae1] px-1.5 py-0.5 rounded-sm">
                              {formatEventDate(ev)}
                            </span>
                          </div>

                          <h3 className="font-serif text-[17px] font-bold text-[#1c1a17] leading-snug group-hover:text-[#cc785c] transition-colors mt-1">
                            {ev.title}
                          </h3>

                          {ev.summary && (
                            <p className="text-[12.5px] text-[#5c544a] mt-2.5 leading-relaxed font-serif italic text-justify opacity-95">
                              "{ev.summary}"
                            </p>
                          )}

                          <div className="mt-4 pt-3.5 border-t border-[#f0eae1]/50 flex items-center justify-between text-[10px] text-[#cc785c] font-bold">
                            <span className="flex items-center gap-1">
                              👤 {ev.wiki_page_slug ? "Xem liên kết & phân tích →" : "Xem chi tiết →"}
                            </span>
                          </div>
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
          className="fixed inset-0 bg-black/10 backdrop-blur-xs z-40 transition-opacity duration-300"
          onClick={() => setExpandedEvent(null)}
        />
      )}

      {/* ── DRAWER PANEL CONTAINER (Slide-over RAG explorer) ── */}
      <div className={cn(
        "fixed top-0 right-0 h-full w-[400px] max-w-[90vw] bg-[#faf8f3] border-l border-[#e8ddd0] shadow-[-8px_0_24px_rgba(28,26,23,0.08)] z-50 transition-transform duration-300 transform flex flex-col",
        expandedEvent ? "translate-x-0" : "translate-x-full"
      )}>
        {expandedData && (
          <div className="flex-1 flex flex-col overflow-hidden text-left">
            
            {/* Context Panel Header */}
            <div className="px-6 py-4 bg-[#f4ece1] border-b border-[#e8ddd0] flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-2.5">
                <span className="text-xl bg-white w-8 h-8 rounded-sm flex items-center justify-center border border-[#e8ddd0] shadow-sm">
                  {getEventCategory(expandedData.title).icon}
                </span>
                <div className="text-left">
                  <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-[#8c8275]">
                    AI Context Panel
                  </span>
                  <div className="text-xs font-bold text-[#cc785c] mt-0.5">
                    {formatEventDate(expandedData)}
                  </div>
                </div>
              </div>
              <button
                onClick={() => setExpandedEvent(null)}
                className="w-7 h-7 rounded-full flex items-center justify-center text-[#8c8275] hover:bg-white hover:text-[#1c1a17] border border-transparent hover:border-[#e8ddd0] transition-all cursor-pointer bg-white/50"
              >
                <X size={14} />
              </button>
            </div>

            {/* Context Panel Content */}
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
              
              {/* Header title */}
              <div className="text-left space-y-1">
                <div className="inline-block px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider rounded-sm bg-[#f0eae1] text-[#5c544a]">
                  {getEraLabel(expandedData.period) || "Sự kiện lịch sử"}
                </div>
                <h3 className="font-serif text-lg font-bold text-[#1c1a17] leading-snug">
                  {expandedData.title}
                </h3>
              </div>

              {/* Importance Summary */}
              {expandedData.summary && (
                <div className="text-left space-y-2">
                  <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#8c8275]">
                    Tại sao quan trọng?
                  </h4>
                  <div className="p-4 rounded-sm bg-white border border-[#e8ddd0] shadow-xs">
                    <p className="text-[12.5px] text-[#1c1a17]/90 leading-relaxed font-serif italic">
                      "{expandedData.summary}"
                    </p>
                  </div>
                </div>
              )}

              {/* Sơ đồ Liên kết Tri thức */}
              <div className="text-left space-y-2">
                <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#8c8275] flex items-center gap-1">
                  <span>🕸️</span> Sơ đồ Liên kết Tri thức
                </h4>
                
                <div className="p-4 rounded-sm bg-white border border-[#e8ddd0] flex flex-col items-center justify-center min-h-[220px] relative overflow-hidden">
                  
                  {/* Background Grid */}
                  <div className="absolute inset-0 opacity-[0.02] pointer-events-none" 
                       style={{ backgroundImage: "radial-gradient(#cc785c 1px, transparent 1px)", backgroundSize: "16px 16px" }} />
                  
                  {loadingContext ? (
                    <div className="flex flex-col items-center gap-2 text-[#8c8275]">
                      <div className="w-5 h-5 rounded-full border-2 border-[#cc785c] border-t-transparent animate-spin" />
                      <span className="text-xs">Đang lập sơ đồ kết nối...</span>
                    </div>
                  ) : wikiContext?.context?.entities && wikiContext.context.entities.length > 0 ? (
                    <div className="relative w-full h-48 flex items-center justify-center">
                      
                      {/* Center Node */}
                      <div className="absolute z-20 w-16 h-16 rounded-full bg-[#cc785c] text-white flex items-center justify-center text-center p-1.5 shadow-md border-2 border-white scale-100 hover:scale-105 transition-transform">
                        <span className="text-[8px] font-serif font-bold leading-tight line-clamp-3">
                          {expandedData.title}
                        </span>
                      </div>

                      {/* Satellite Nodes */}
                      {wikiContext.context.entities.slice(0, 5).map((entity: string, idx: number) => {
                        const angle = (idx * 2 * Math.PI) / Math.min(wikiContext.context.entities.slice(0, 5).length, 5)
                        const radius = 68
                        const x = Math.round(radius * Math.cos(angle))
                        const y = Math.round(radius * Math.sin(angle))
                        const icon = getEntityIcon(entity)
                        
                        return (
                          <div key={idx} className="absolute z-10" style={{ transform: `translate(${x}px, ${y}px)` }}>
                            
                            {/* Connector link line */}
                            <svg className="absolute top-1/2 left-1/2 w-48 h-48 -translate-x-1/2 -translate-y-1/2 pointer-events-none z-0" style={{ overflow: "visible" }}>
                              <line 
                                x1="0" 
                                y1="0" 
                                x2={-x} 
                                y2={-y} 
                                stroke="#e8ddd0" 
                                strokeWidth="1.5" 
                                strokeDasharray="3 3"
                              />
                            </svg>

                            <button
                              onClick={() => navigate(`/chat?q=${encodeURIComponent(`Hãy kể cho tôi nghe về ${entity}`)}`)}
                              title={`Hỏi AI về ${entity}`}
                              className="w-10 h-10 rounded-full bg-white hover:bg-[#faf8f3] border border-[#e8ddd0] hover:border-[#cc785c] shadow-sm flex items-center justify-center text-base transition-all cursor-pointer relative group"
                            >
                              <span>{icon}</span>
                              <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 bg-stone-900 text-white text-[8px] px-1 rounded opacity-0 group-hover:opacity-100 whitespace-nowrap pointer-events-none z-30 transition-opacity">
                                {entity}
                              </span>
                            </button>
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    <div className="text-xs text-[#8c8275] italic">
                      Không tìm thấy thực thể liên quan trực tiếp.
                    </div>
                  )}
                </div>
              </div>

              {/* Connected Entity Buttons */}
              {wikiContext?.context?.entities && wikiContext.context.entities.length > 0 && (
                <div className="text-left space-y-2">
                  <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#8c8275]">
                    Thực thể Lịch sử liên kết
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {wikiContext.context.entities.map((entity: string, idx: number) => {
                      const icon = getEntityIcon(entity)
                      return (
                        <button
                          key={idx}
                          onClick={() => navigate(`/chat?q=${encodeURIComponent(`Hãy phân tích mối liên hệ của nhân vật/sự kiện "${entity}" đối với sự kiện "${expandedData.title}"`)}`)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-[#f0eae1] border border-[#e8ddd0] hover:border-[#cc785c] rounded-sm text-xs font-semibold text-[#1c1a17] transition-all cursor-pointer"
                        >
                          <span>{icon}</span>
                          <span>{entity}</span>
                          <ArrowUpRight size={10} className="text-[#8c8275]" />
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* RAG Quick Ask suggestions */}
              <div className="p-4 bg-[#cc785c]/5 border border-[#cc785c]/10 rounded-sm text-left space-y-3">
                <div className="text-[10px] font-bold text-[#cc785c] uppercase tracking-[0.1em] flex items-center gap-1.5">
                  <Sparkles size={13} />
                  Trợ lý Lịch sử AI RAG
                </div>
                
                <div className="space-y-2">
                  <button
                    onClick={() => {
                      navigate(`/chat?q=${encodeURIComponent(`Giải thích bối cảnh lịch sử và nguyên nhân chính dẫn đến sự kiện "${expandedData.title}"?`)}&context_type=wiki&context_id=${expandedData.wiki_page_slug || ""}`)
                    }}
                    className="w-full p-3 bg-white hover:bg-stone-50 border border-[#e8ddd0] hover:border-[#cc785c] rounded-sm text-left text-xs font-medium text-[#1c1a17] flex items-center justify-between group transition-all cursor-pointer"
                  >
                    <span className="line-clamp-1">Giải thích nguyên nhân &amp; bối cảnh chính?</span>
                    <ArrowRight size={13} className="text-[#8c8275] group-hover:translate-x-0.5 transition-transform shrink-0 ml-2" />
                  </button>

                  <button
                    onClick={() => {
                      navigate(`/chat?q=${encodeURIComponent(`Phân tích ảnh hưởng lâu dài và tầm quan trọng lịch sử của sự kiện "${expandedData.title}"?`)}&context_type=wiki&context_id=${expandedData.wiki_page_slug || ""}`)
                    }}
                    className="w-full p-3 bg-white hover:bg-stone-50 border border-[#e8ddd0] hover:border-[#cc785c] rounded-sm text-left text-xs font-medium text-[#1c1a17] flex items-center justify-between group transition-all cursor-pointer"
                  >
                    <span className="line-clamp-1">Ảnh hưởng lâu dài đến lịch sử Việt Nam?</span>
                    <ArrowRight size={13} className="text-[#8c8275] group-hover:translate-x-0.5 transition-transform shrink-0 ml-2" />
                  </button>
                </div>
              </div>

            </div>

            {/* Context Panel Footer Actions */}
            <div className="p-4 border-t border-[#e8ddd0] bg-[#f4ece1] flex gap-2.5 flex-shrink-0">
              {expandedData.wiki_page_slug && (
                <button
                  onClick={() => navigate(`/wiki/${expandedData.wiki_page_slug}`)}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 bg-white hover:bg-stone-50 text-[#1c1a17] text-xs font-bold rounded-sm border border-[#e8ddd0] transition-all cursor-pointer shadow-xs"
                >
                  📖 Đọc tài liệu Wiki
                </button>
              )}
              <button
                onClick={() => navigate(`/chat?q=${encodeURIComponent(`Hãy kể cho tôi nghe chi tiết về ${expandedData.title}`)}&context_type=wiki&context_id=${expandedData.wiki_page_slug || ""}`)}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 bg-[#cc785c] hover:bg-[#b0674c] text-white text-xs font-bold rounded-sm transition-all shadow-sm cursor-pointer border-none"
              >
                💬 Hỏi AI Assistant
              </button>
            </div>

          </div>
        )}
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
