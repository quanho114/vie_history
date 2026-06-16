import { useState, useEffect, useRef } from "react"
import { cn } from "@/lib/utils/cn"
import {
  Compass,
  Search,
  Calendar,
  GitCommit,
  Brain,
  AlertTriangle,
  CheckCircle,
  Database,
  BookOpen,
  ChevronDown,
  Loader2,
  Sparkles,
} from "lucide-react"

export interface AgentTraceItem {
  agent: string
  action: string
  status: "success" | "failed" | "pending" | string
}

interface LiveThinkingPanelProps {
  liveTrace: AgentTraceItem[] | null
  isStreaming: boolean
  finalTrace: {
    agent_trace?: AgentTraceItem[]
    total_ms?: number
    workflow?: string
  } | null
}

// ── Agent Icon Selector ──────────────────────────────────────
function getAgentIcon(agentName: string, isActive: boolean = false) {
  const name = agentName.toLowerCase()
  const cls = "w-3.5 h-3.5"
  if (name.includes("supervisor") || name.includes("planner") || name.includes("greeting") || name.includes("fast") || name.includes("graph mode") || name.includes("agentic"))
    return <Compass className={cn(cls, isActive ? "text-amber-500" : "text-amber-600/70")} />
  if (name.includes("retrieval"))
    return <Search className={cn(cls, isActive ? "text-blue-500" : "text-blue-600/70")} />
  if (name.includes("timeline"))
    return <Calendar className={cn(cls, isActive ? "text-emerald-500" : "text-emerald-600/70")} />
  if (name.includes("graph"))
    return <GitCommit className={cn(cls, isActive ? "text-indigo-500" : "text-indigo-600/70")} />
  if (name.includes("world"))
    return <Sparkles className={cn(cls, isActive ? "text-violet-500" : "text-violet-600/70")} />
  if (name.includes("reasoning") || name.includes("synthesizer"))
    return <Brain className={cn(cls, isActive ? "text-rose-500" : "text-rose-600/70")} />
  if (name.includes("critic") || name.includes("reflection") || name.includes("early stop"))
    return <AlertTriangle className={cn(cls, isActive ? "text-orange-500" : "text-orange-600/70")} />
  if (name.includes("memory") || name.includes("consolidation"))
    return <Database className={cn(cls, isActive ? "text-teal-500" : "text-teal-600/70")} />
  return <BookOpen className={cn(cls, isActive ? "text-stone-500" : "text-stone-500/70")} />
}

// ── Elapsed Timer ────────────────────────────────────────────
function ElapsedTimer({ stopped }: { stopped?: boolean }) {
  const [elapsed, setElapsed] = useState(0)
  const startRef = useRef(Date.now())

  useEffect(() => {
    if (stopped) return
    const interval = setInterval(() => {
      setElapsed(Date.now() - startRef.current)
    }, 100)
    return () => clearInterval(interval)
  }, [stopped])

  return (
    <span className="tabular-nums font-mono text-[11px]" style={{ color: "var(--muted)" }}>
      {(elapsed / 1000).toFixed(1)}s
    </span>
  )
}

// ── Single Thinking Step ─────────────────────────────────────
function ThinkingStep({ step, isActive }: { step: AgentTraceItem; isActive: boolean }) {
  const isFailed = step.status === "failed"
  const isPending = step.status === "pending"

  return (
    <div className={cn("flex items-start gap-2.5 text-[12px] transition-all duration-500", isActive ? "opacity-100" : "opacity-60")}>
      <div
        className={cn(
          "w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5",
          isFailed ? "bg-red-50 border border-red-200" :
          isPending ? "bg-amber-50 border border-amber-200" :
          "bg-[#faf8f5] border border-[#e6dfd8]"
        )}
      >
        {getAgentIcon(step.agent, isActive)}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="font-semibold truncate" style={{ color: "var(--ink)", fontSize: 12 }}>
            {step.agent}
          </span>
          {isFailed && (
            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-red-50 text-red-600 border border-red-100 font-bold uppercase tracking-wider">
              retry
            </span>
          )}
        </div>
        <p className="leading-relaxed mt-0.5 line-clamp-3" style={{ color: "var(--muted)", fontSize: 11 }}>
          {step.action}
        </p>
      </div>
    </div>
  )
}

// ── Typing dots (shown when streaming but no steps yet) ───────
function TypingDots() {
  return (
    <div className="flex items-center gap-2 px-3.5 py-2">
      <div className="flex gap-1">
        {[0, 0.15, 0.3].map((delay, i) => (
          <span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-[#cc785c]"
            style={{ animation: `pulse 1s ease-in-out infinite`, animationDelay: `${delay}s` }}
          />
        ))}
      </div>
      <span className="text-[11px] italic" style={{ color: "var(--muted)" }}>
        Đang phân loại câu hỏi...
      </span>
    </div>
  )
}

// ── Main Component ───────────────────────────────────────────
export function LiveThinkingPanel({ liveTrace, isStreaming, finalTrace }: LiveThinkingPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  // What to render
  // IMPORTANT: while streaming, always prefer liveTrace (updated per-node via SSE).
  // Only switch to finalTrace after streaming is fully done.
  const isLive = isStreaming  // panel is "live" for the entire duration of the stream
  const traceItems = isStreaming
    ? (liveTrace || [])                                   // live: incremental per-node updates
    : (finalTrace?.agent_trace || liveTrace || [])        // done: use final trace from message
  const totalMs = finalTrace?.total_ms || 0
  const hasSteps = traceItems.length > 0

  // Expanded state: always open while streaming, collapsible after done
  const [isExpanded, setIsExpanded] = useState(true)

  // Keep expanded while streaming; auto-collapse 1.5s after streaming ends
  useEffect(() => {
    if (isStreaming) {
      setIsExpanded(true)
      return
    }
    if (!isStreaming && hasSteps) {
      const timer = setTimeout(() => setIsExpanded(false), 1500)
      return () => clearTimeout(timer)
    }
  }, [isStreaming, hasSteps])

  // Auto-scroll to latest step while live
  useEffect(() => {
    if (panelRef.current && isLive) {
      panelRef.current.scrollTop = panelRef.current.scrollHeight
    }
  }, [traceItems.length, isLive])

  // Show panel whenever streaming (even before first trace item)
  const shouldRender = isStreaming || hasSteps
  if (!shouldRender) return null

  return (
    <div
      className="mb-2 rounded-xl overflow-hidden"
      style={{
        border: `1px solid ${isLive ? "rgba(204,120,92,0.25)" : "var(--hairline)"}`,
        backgroundColor: isLive ? "rgba(254, 252, 250, 0.97)" : "rgba(250, 249, 245, 0.85)",
        transition: "border-color 0.3s, background-color 0.3s",
      }}
    >
      {/* ── Header ─────────────────────────────────────── */}
      <button
        onClick={() => !isLive && setIsExpanded(!isExpanded)}
        className="w-full px-3.5 py-2.5 flex items-center justify-between text-left"
        style={{ background: "none", border: "none", cursor: isLive ? "default" : "pointer" }}
      >
        <div className="flex items-center gap-2">
          {isLive ? (
            <div className="w-5 h-5 rounded-md bg-[#cc785c]/10 flex items-center justify-center">
              <Loader2 className="w-3 h-3 text-[#cc785c] animate-spin" />
            </div>
          ) : (
            <div className="w-5 h-5 rounded-md bg-emerald-50 flex items-center justify-center">
              <CheckCircle className="w-3 h-3 text-emerald-600" />
            </div>
          )}

          <div className="flex items-center gap-1.5 flex-wrap">
            <span
              className="font-semibold text-[12px]"
              style={{ color: isLive ? "var(--coral)" : "var(--body)" }}
            >
              {isLive ? "Đang suy luận..." : "Suy luận hoàn tất"}
            </span>
            <span className="text-[11px]" style={{ color: "var(--muted)" }}>•</span>
            {isLive ? (
              <ElapsedTimer />
            ) : (
              <span className="text-[11px] tabular-nums" style={{ color: "var(--muted)" }}>
                {totalMs > 0 ? `${(totalMs / 1000).toFixed(1)}s` : ""}
              </span>
            )}
            {hasSteps && (
              <>
                <span className="text-[11px]" style={{ color: "var(--muted)" }}>•</span>
                <span className="text-[11px]" style={{ color: "var(--muted)" }}>
                  {traceItems.length} bước
                </span>
              </>
            )}
          </div>
        </div>

        {/* Only show chevron when NOT live (collapsible after done) */}
        {!isLive && (
          <ChevronDown
            className={cn("w-4 h-4 transition-transform duration-200", isExpanded && "rotate-180")}
            style={{ color: "var(--muted)" }}
          />
        )}
      </button>

      {/* ── Body — always visible while live ───────────── */}
      <div
        ref={panelRef}
        className={cn(
          "overflow-hidden transition-all duration-300 ease-in-out",
          isLive
            ? "max-h-[500px] overflow-y-auto opacity-100"   // always open while streaming
            : isExpanded
              ? "max-h-[400px] overflow-y-auto opacity-100"  // manually expanded after done
              : "max-h-0 opacity-0"                          // collapsed
        )}
      >
        <div className="px-3.5 pb-3">
          <div className="h-px w-full mb-2.5" style={{ backgroundColor: "var(--hairline)" }} />

          {/* No steps yet: show typing indicator */}
          {!hasSteps && isLive && <TypingDots />}

          {/* Steps list */}
          <div className="space-y-2.5">
            {traceItems.map((step, idx) => (
              <ThinkingStep
                key={idx}
                step={step}
                isActive={isLive && idx === traceItems.length - 1}
              />
            ))}
          </div>

          {/* Live: "processing next step" indicator */}
          {isLive && hasSteps && (
            <div className="flex items-center gap-2 mt-2.5">
              <div className="flex gap-1">
                {[0, "0.2s", "0.4s"].map((delay, i) => (
                  <span
                    key={i}
                    className="w-1 h-1 rounded-full bg-[#cc785c] animate-pulse"
                    style={{ animationDelay: String(delay) }}
                  />
                ))}
              </div>
              <span className="text-[10px] italic" style={{ color: "var(--muted)" }}>
                Đang xử lý bước tiếp theo...
              </span>
            </div>
          )}

          {/* Done */}
          {!isLive && hasSteps && (
            <div className="flex items-center gap-2 mt-2.5">
              <CheckCircle className="w-3 h-3 text-emerald-500 flex-shrink-0" />
              <span className="text-[10px] italic" style={{ color: "var(--muted)" }}>
                Pipeline hoàn tất. Trả về kết quả tổng hợp.
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
