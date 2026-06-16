import { useEffect, useState, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { timelineApi, type TimelineEvent } from "@/lib/api/brain"
import { cn } from "@/lib/utils/cn"

// ── Icons ──────────────────────────────────────────────
function IconClock({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="12" cy="12" r="10" />
      <polyline points="12,6 12,12 16,14" />
    </svg>
  )
}

function IconMessageSquare({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}

function IconBook({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  )
}

function IconX({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

// ── Period config ──────────────────────────────────────
interface PeriodFilter {
  value: string
  label: string
  startYear?: number
  endYear?: number
}

const PERIOD_FILTERS: PeriodFilter[] = [
  { value: "all", label: "Tất cả" },
  { value: "chong-phap", label: "1945–1954", startYear: 1945, endYear: 1954 },
  { value: "chong-my", label: "1954–1975", startYear: 1954, endYear: 1975 },
  { value: "thong-nhat", label: "1975–nay", startYear: 1975 },
]

const PERIOD_COLORS: Record<string, { dot: string; card: string; text: string; border: string }> = {
  "khang-chien-chong-phap": {
    dot: "bg-blue-500",
    card: "bg-blue-50 border-blue-200",
    text: "text-blue-700",
    border: "border-l-blue-500",
  },
  "khang-chien-chong-my": {
    dot: "bg-red-500",
    card: "bg-red-50 border-red-200",
    text: "text-red-700",
    border: "border-l-red-500",
  },
  "thong-nhat": {
    dot: "bg-emerald-500",
    card: "bg-emerald-50 border-emerald-200",
    text: "text-emerald-700",
    border: "border-l-emerald-500",
  },
  default: {
    dot: "bg-[#cc785c]",
    card: "bg-[#f5f0e8] border-[#e6dfd8]",
    text: "text-[#cc785c]",
    border: "border-l-[#cc785c]",
  },
}

function getPeriodStyle(period: string) {
  return PERIOD_COLORS[period] || PERIOD_COLORS.default
}

function formatEventDate(ev: TimelineEvent) {
  if (ev.day && ev.month) return `${ev.day}/${ev.month}/${ev.year}`
  if (ev.month) return `${ev.month}/${ev.year}`
  return String(ev.year)
}

// ── Main component ─────────────────────────────────────
export function TimelinePage() {
  const navigate = useNavigate()
  const timelineRef = useRef<HTMLDivElement>(null)
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedPeriod, setSelectedPeriod] = useState<string>("all")
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null)

  // Floating scroll navigation buttons state
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)

  const checkScroll = () => {
    const el = timelineRef.current
    if (!el) return
    setCanScrollLeft(el.scrollLeft > 2)
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 5)
  }

  // Handle smooth scroll clicks
  const scrollTimeline = (direction: "left" | "right") => {
    const el = timelineRef.current
    if (!el) return
    const scrollAmount = 400
    el.scrollBy({
      left: direction === "left" ? -scrollAmount : scrollAmount,
      behavior: "smooth"
    })
  }

  // Fetch events on selectedPeriod change
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
        // Reset expanded event
        setExpandedEvent(null)
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Không thể tải dữ liệu timeline")
        setEvents([])
      })
      .finally(() => setLoading(false))
  }, [selectedPeriod])

  // Mouse wheel vertical -> horizontal scroll translation hook
  useEffect(() => {
    const el = timelineRef.current
    if (!el) return

    const handleWheel = (e: WheelEvent) => {
      if (e.deltaY !== 0) {
        e.preventDefault()
        el.scrollLeft += e.deltaY * 1.1
      }
    }

    el.addEventListener("wheel", handleWheel, { passive: false })
    return () => el.removeEventListener("wheel", handleWheel)
  }, [events])

  // Monitor scroll bounds to show/hide floating slide arrows
  useEffect(() => {
    const el = timelineRef.current
    if (!el) return
    
    // Initial check
    setTimeout(checkScroll, 100)
    
    el.addEventListener("scroll", checkScroll)
    window.addEventListener("resize", checkScroll)
    return () => {
      el.removeEventListener("scroll", checkScroll)
      window.removeEventListener("resize", checkScroll)
    }
  }, [events])

  const handleEventClick = (id: string) => {
    setExpandedEvent(expandedEvent === id ? null : id)
  }

  const expandedData = expandedEvent ? events.find((e) => e.id === expandedEvent) : null

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#faf9f5]">
      {/* Header */}
      <header className="px-8 py-5 border-b border-[#e6dfd8] bg-white shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex items-center gap-3 flex-shrink-0">
        <div className="w-10 h-10 rounded-xl bg-[#f5f0e8] flex items-center justify-center">
          <IconClock className="text-[#cc785c]" />
        </div>
        <div>
          <h2 className="text-xl font-display font-semibold text-[#141413]">Dòng thời gian lịch sử</h2>
          <p className="text-xs text-[#8e8b82]">Khám phá các sự kiện lịch sử Việt Nam theo trục thời gian</p>
        </div>
      </header>

      {/* Period Filter Tabs */}
      <div className="px-8 pt-4 pb-3 border-b border-[#e6dfd8] bg-white flex-shrink-0">
        <div className="flex items-center gap-1">
          {PERIOD_FILTERS.map((pf) => (
            <button
              key={pf.value}
              onClick={() => setSelectedPeriod(pf.value)}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150",
                selectedPeriod === pf.value
                  ? "bg-[#cc785c] text-white shadow-sm"
                  : "text-[#6c6a64] hover:text-[#141413] hover:bg-[#f5f0e8]"
              )}
            >
              {pf.label}
            </button>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="px-8 py-2.5 border-b border-[#e6dfd8] bg-[#faf9f5] flex items-center gap-5 flex-shrink-0">
        <span className="text-[10px] font-semibold text-[#8e8b82] uppercase tracking-wider">Chú thích:</span>
        {Object.entries(PERIOD_COLORS).filter(([k]) => k !== "default").map(([period, style]) => {
          const labels: Record<string, string> = {
            "khang-chien-chong-phap": "Kháng chiến chống Pháp",
            "khang-chien-chong-my": "Kháng chiến chống Mỹ",
            "thong-nhat": "Thống nhất",
          }
          return (
            <div key={period} className="flex items-center gap-1.5">
              <div className={cn("w-2.5 h-2.5 rounded-full", style.dot)} />
              <span className="text-[11px] text-[#6c6a64]">{labels[period]}</span>
            </div>
          )
        })}
      </div>

      {/* Timeline Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex flex-col items-center gap-3 text-[#8e8b82]">
              <div className="w-8 h-8 rounded-full border-2 border-[#cc785c] border-t-transparent animate-spin" />
              <p className="text-sm">Đang tải dữ liệu...</p>
            </div>
          </div>
        ) : error ? (
          <div className="p-8">
            <div className="bg-red-50 border border-red-100 rounded-xl px-5 py-4 text-red-600 text-sm">
              {error}
            </div>
          </div>
        ) : events.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
            <div className="w-16 h-16 rounded-2xl bg-[#f5f0e8] flex items-center justify-center mb-4">
              <IconClock className="w-8 h-8 text-[#8e8b82]" />
            </div>
            <p className="text-[#3d3d3a] font-medium text-base">Chưa có sự kiện nào</p>
            <p className="text-[#8e8b82] text-sm mt-1">Sự kiện lịch sử sẽ xuất hiện ở đây sau khi được nhập liệu</p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Horizontal scrollable timeline */}
            <div className="relative flex-shrink-0" style={{ height: "240px" }}>

              {/* Left gradient fade + nav button */}
              <div
                className="absolute left-0 top-0 bottom-0 w-20 z-10 pointer-events-none transition-opacity duration-300"
                style={{
                  background: "linear-gradient(to right, #faf9f5 30%, transparent 100%)",
                  opacity: canScrollLeft ? 1 : 0,
                }}
              />
              <button
                onClick={() => scrollTimeline("left")}
                aria-label="Cuộn sang trái"
                className="absolute left-2 top-1/2 -translate-y-1/2 z-20 w-9 h-9 rounded-full bg-white shadow-md border border-[#e6dfd8] flex items-center justify-center text-[#6c6a64] hover:text-[#cc785c] hover:border-[#cc785c] hover:shadow-lg transition-all duration-200"
                style={{
                  opacity: canScrollLeft ? 1 : 0,
                  pointerEvents: canScrollLeft ? "auto" : "none",
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="15 18 9 12 15 6" />
                </svg>
              </button>

              {/* Right gradient fade + nav button */}
              <div
                className="absolute right-0 top-0 bottom-0 w-20 z-10 pointer-events-none transition-opacity duration-300"
                style={{
                  background: "linear-gradient(to left, #faf9f5 30%, transparent 100%)",
                  opacity: canScrollRight ? 1 : 0,
                }}
              />
              <button
                onClick={() => scrollTimeline("right")}
                aria-label="Cuộn sang phải"
                className="absolute right-2 top-1/2 -translate-y-1/2 z-20 w-9 h-9 rounded-full bg-white shadow-md border border-[#e6dfd8] flex items-center justify-center text-[#6c6a64] hover:text-[#cc785c] hover:border-[#cc785c] hover:shadow-lg transition-all duration-200"
                style={{
                  opacity: canScrollRight ? 1 : 0,
                  pointerEvents: canScrollRight ? "auto" : "none",
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>

              {/* Scrollable inner – hide native scrollbar */}
              <div
                ref={timelineRef}
                className="timeline-scroll absolute inset-0 overflow-x-auto overflow-y-hidden"
                style={{ scrollbarWidth: "none" } as React.CSSProperties}
              >
                <style>{`.timeline-scroll::-webkit-scrollbar { display: none; }`}</style>
                <div
                  className="relative flex items-center"
                  style={{ width: Math.max(events.length * 200 + 200, 900) + "px", height: "240px" }}
                >
                  {/* Timeline track */}
                  <div className="absolute top-1/2 -translate-y-1/2 h-0.5 bg-[#e6dfd8]" style={{ left: "100px", right: "100px" }} />

                  {/* Events – first event starts at 100px so its card never clips the left edge */}
                  {events.map((ev, idx) => {
                    const style = getPeriodStyle(ev.period)
                    const isExpanded = expandedEvent === ev.id
                    const isAbove = idx % 2 === 0

                    return (
                      <div
                        key={ev.id}
                        className="absolute flex flex-col items-center"
                        style={{ left: `${100 + idx * 200}px`, top: "50%", transform: "translateY(-50%)" }}
                      >
                        {/* Card above */}
                        {isAbove && (
                          <button
                            onClick={() => handleEventClick(ev.id)}
                            className={cn(
                              "absolute bottom-[calc(100%+8px)] w-44 text-left p-2.5 rounded-lg border text-xs transition-all duration-150 shadow-sm hover:shadow-md",
                              isExpanded
                                ? "bg-[#cc785c] text-white border-[#cc785c]"
                                : "bg-white border-[#e6dfd8] hover:border-[#cc785c] hover:text-[#cc785c]"
                            )}
                          >
                            <div className={cn("font-bold text-[10px] mb-0.5", isExpanded ? "text-white/80" : style.text)}>
                              {formatEventDate(ev)}
                            </div>
                            <div className={cn("font-medium leading-tight line-clamp-2", isExpanded ? "text-white" : "text-[#141413]")}>
                              {ev.title}
                            </div>
                          </button>
                        )}

                        {/* Dot */}
                        <div
                          className={cn(
                            "w-3 h-3 rounded-full border-2 border-white shadow-sm transition-transform duration-150",
                            style.dot,
                            isExpanded && "scale-150"
                          )}
                        />

                        {/* Card below */}
                        {!isAbove && (
                          <button
                            onClick={() => handleEventClick(ev.id)}
                            className={cn(
                              "absolute top-[calc(100%+8px)] w-44 text-left p-2.5 rounded-lg border text-xs transition-all duration-150 shadow-sm hover:shadow-md",
                              isExpanded
                                ? "bg-[#cc785c] text-white border-[#cc785c]"
                                : "bg-white border-[#e6dfd8] hover:border-[#cc785c]"
                            )}
                          >
                            <div className={cn("font-bold text-[10px] mb-0.5", isExpanded ? "text-white/80" : style.text)}>
                              {formatEventDate(ev)}
                            </div>
                            <div className={cn("font-medium leading-tight line-clamp-2", isExpanded ? "text-white" : "text-[#141413]")}>
                              {ev.title}
                            </div>
                          </button>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>

            {/* Event detail panel */}
            {expandedData && (
              <div className="flex-1 overflow-y-auto border-t border-[#e6dfd8] bg-white px-8 py-6 animate-fade-in">
                <div className="max-w-2xl mx-auto">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <div className={cn("text-[11px] font-bold mb-1", getPeriodStyle(expandedData.period).text)}>
                        {formatEventDate(expandedData)}
                      </div>
                      <h3 className="font-display text-xl text-[#141413]">{expandedData.title}</h3>
                    </div>
                    <button
                      onClick={() => setExpandedEvent(null)}
                      className="w-7 h-7 rounded-full flex items-center justify-center text-[#8e8b82] hover:bg-[#f5f0e8] hover:text-[#141413] transition-colors"
                    >
                      <IconX />
                    </button>
                  </div>

                  {expandedData.summary && (
                    <p className="text-sm text-[#3d3d3a] leading-relaxed mb-4">{expandedData.summary}</p>
                  )}

                  {expandedData.causes && expandedData.causes.length > 0 && (
                    <div className="mb-4">
                      <p className="text-[11px] font-semibold text-[#8e8b82] uppercase tracking-wider mb-2">Nguyên nhân</p>
                      <ul className="space-y-1">
                        {expandedData.causes.map((c, i) => (
                          <li key={i} className="flex gap-2 text-sm text-[#3d3d3a]">
                            <span className="text-[#cc785c] mt-0.5">•</span>
                            <span>{c}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {expandedData.effects && expandedData.effects.length > 0 && (
                    <div className="mb-4">
                      <p className="text-[11px] font-semibold text-[#8e8b82] uppercase tracking-wider mb-2">Kết quả</p>
                      <ul className="space-y-1">
                        {expandedData.effects.map((e, i) => (
                          <li key={i} className="flex gap-2 text-sm text-[#3d3d3a]">
                            <span className="text-[#5db8a6] mt-0.5">•</span>
                            <span>{e}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Action buttons */}
                  <div className="flex gap-3 pt-4 border-t border-[#e6dfd8]">
                    {expandedData.wiki_page_slug && (
                      <button
                        onClick={() => navigate(`/wiki/${expandedData.wiki_page_slug}`)}
                        className="flex items-center gap-1.5 px-3 py-2 bg-[#f5f0e8] hover:bg-[#ebe6df] text-[#3d3d3a] text-xs font-medium rounded-lg border border-[#e6dfd8] transition-colors"
                      >
                        <IconBook />
                        Xem wiki
                      </button>
                    )}
                    <button
                      onClick={() => navigate(`/chat?q=${encodeURIComponent(`Hãy kể cho tôi nghe về ${expandedData.title}`)}`)}
                      className="flex items-center gap-1.5 px-3 py-2 bg-[#cc785c] hover:bg-[#a9583e] text-white text-xs font-medium rounded-lg transition-colors shadow-sm"
                    >
                      <IconMessageSquare />
                      Hỏi chatbot
                    </button>
                  </div>
                </div>
              </div>
            )}

            {!expandedData && (
              <div className="flex-1 flex items-center justify-center text-[#8e8b82] text-sm">
                Nhấn vào một sự kiện để xem chi tiết
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
