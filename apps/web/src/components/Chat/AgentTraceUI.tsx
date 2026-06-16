import { useState, useCallback } from "react"
import { cn } from "@/lib/utils/cn"
import { 
  ChevronDown, 
  ChevronUp, 
  Compass, 
  Search, 
  Calendar, 
  GitCommit, 
  BookOpen, 
  AlertTriangle, 
  CheckCircle, 
  Brain,
  HelpCircle,
  Database
} from "lucide-react"

export interface AgentTraceItem {
  agent: string
  action: string
  status: "success" | "failed" | "pending" | string
}

interface AgentTraceUIProps {
  trace: {
    agent_trace?: AgentTraceItem[]
    total_ms?: number
    workflow?: string
  } | null
}

// ── Agent Icon Selector ──────────────────────────────────────
function getAgentIcon(agentName: string) {
  const name = agentName.toLowerCase()
  if (name.includes("supervisor") || name.includes("planner")) {
    return <Compass className="w-4 h-4 text-amber-600" aria-hidden="true" />
  }
  if (name.includes("retrieval")) {
    return <Search className="w-4 h-4 text-blue-600" aria-hidden="true" />
  }
  if (name.includes("timeline")) {
    return <Calendar className="w-4 h-4 text-emerald-600" aria-hidden="true" />
  }
  if (name.includes("graph")) {
    return <GitCommit className="w-4 h-4 text-indigo-600" aria-hidden="true" />
  }
  if (name.includes("reasoning") || name.includes("synthesizer")) {
    return <Brain className="w-4 h-4 text-rose-600" aria-hidden="true" />
  }
  if (name.includes("critic") || name.includes("reflection")) {
    return <AlertTriangle className="w-4 h-4 text-orange-600" aria-hidden="true" />
  }
  if (name.includes("memory") || name.includes("consolidation")) {
    return <Database className="w-4 h-4 text-teal-600" aria-hidden="true" />
  }
  return <BookOpen className="w-4 h-4 text-stone-600" aria-hidden="true" />
}

// Status label helper
function getStatusLabel(status: string): string {
  switch (status) {
    case "failed": return "Thất bại"
    case "pending": return "Đang xử lý"
    case "success": return "Thành công"
    default: return status
  }
}

export function AgentTraceUI({ trace }: AgentTraceUIProps) {
  const [expanded, setExpanded] = useState(false)

  // Keyboard handler for header toggle
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      setExpanded(prev => !prev)
    }
  }, [])

  if (!trace || !trace.agent_trace || trace.agent_trace.length === 0) {
    return null
  }

  const agentTrace = trace.agent_trace
  const totalMs = trace.total_ms || 0
  const workflow = trace.workflow || "Multi-Agent System"
  const totalSteps = agentTrace.length

  return (
    <div 
      className="mt-4 border border-[#e6dfd8] rounded-xl bg-white shadow-[0_2px_8px_rgba(0,0,0,0.015)] overflow-hidden transition-all duration-200"
      style={{ fontFamily: "var(--font-sans)" }}
      role="region"
      aria-label="Quá trình suy luận đa tác nhân"
    >
      {/* Header Bar - Accessible toggle button */}
      <button
        onClick={() => setExpanded(!expanded)}
        onKeyDown={handleKeyDown}
        className="w-full px-4 py-3 flex items-center justify-between bg-[#faf9f5] border-b border-[#f0eae1] hover:bg-[#f5f0e8] transition-colors cursor-pointer text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-inset"
        aria-expanded={expanded}
        aria-controls="agent-trace-content"
      >
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-lg bg-[#cc785c]/10 text-[#cc785c] flex items-center justify-center border border-[#cc785c]/20">
            <Compass className="w-3.5 h-3.5" aria-hidden="true" />
          </div>
          <div>
            <span className="text-[12px] font-bold text-[#cc785c] uppercase tracking-wider block">
              Agentic Thought Trace
            </span>
            <span className="text-xs text-[#8e8b82]">
              {workflow} • Phản tư & Suy luận đa tác nhân ({totalMs > 0 ? `${(totalMs / 1000).toFixed(2)}s` : "Hoàn tất"})
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs font-semibold text-[#cc785c]">
          <span className="sr-only">
            {expanded ? "Thu gọn chi tiết" : "Xem chi tiết luồng"}
          </span>
          <span aria-hidden="true">{expanded ? "Thu gọn" : "Xem chi tiết"}</span>
          {expanded ? <ChevronUp className="w-4 h-4" aria-hidden="true" /> : <ChevronDown className="w-4 h-4" aria-hidden="true" />}
        </div>
      </button>

      {/* Expanded Trace Details */}
      <div 
        id="agent-trace-content"
        className={cn(
          "transition-all duration-300 ease-in-out",
          expanded ? "max-h-[800px] opacity-100 overflow-y-auto" : "max-h-0 opacity-0 overflow-hidden"
        )}
        role="list"
        aria-label={`Danh sách ${totalSteps} bước suy luận`}
      >
        <div className="p-5 space-y-4 bg-white relative">
          {/* Vertical Connection Line */}
          <div className="absolute left-[33px] top-6 bottom-8 w-[1.5px] bg-dashed border-l border-dashed border-[#e6dfd8]" aria-hidden="true" />

          {agentTrace.map((step, idx) => {
            const isFailed = step.status === "failed"
            const isPending = step.status === "pending"
            const isSuccess = step.status === "success" || (!isFailed && !isPending)

            return (
              <div 
                key={idx} 
                className={cn(
                  "flex items-start gap-4 text-xs animate-fade-in relative z-10",
                  isFailed && "opacity-90"
                )}
                role="listitem"
              >
                {/* Agent Icon Roundel */}
                <div 
                  className={cn(
                    "w-7 h-7 rounded-full flex items-center justify-center border-2 shadow-sm transition-all duration-300",
                    isFailed ? "bg-red-50 border-red-200 text-red-600 scale-95" :
                    isPending ? "bg-[#faf9f5] border-[#cc785c]/30 text-[#cc785c] animate-pulse" :
                    "bg-[#faf9f5] border-[#cc785c]/40 text-[#cc785c]"
                  )}
                  aria-hidden="true"
                >
                  {getAgentIcon(step.agent)}
                </div>

                {/* Content Block */}
                <div className="flex-1 bg-[#faf9f5] border border-[#e6dfd8] rounded-xl p-3.5 hover:border-[#cc785c]/35 transition-colors">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-bold text-[#141413] text-[13px]">
                      {step.agent}
                    </span>
                    <span 
                      className={cn(
                        "text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider border",
                        isFailed ? "bg-red-50 text-red-600 border-red-100" :
                        isPending ? "bg-amber-50 text-amber-600 border-amber-100" :
                        "bg-emerald-50 text-emerald-700 border-emerald-100"
                      )}
                      aria-label={`Trạng thái: ${getStatusLabel(step.status)}`}
                    >
                      {getStatusLabel(step.status)}
                    </span>
                  </div>
                  <p className="text-[#6c6a64] leading-relaxed text-[12px]">
                    {step.action}
                  </p>
                </div>
              </div>
            )
          })}

          {/* Success Step Card */}
          <div className="flex items-center gap-4 text-xs relative z-10 pl-0.5" role="listitem">
            <div className="w-6 h-6 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-200 shadow-sm ml-0.5" aria-hidden="true">
              <CheckCircle className="w-3.5 h-3.5" />
            </div>
            <div className="text-[#8e8b82] italic text-[11px]">
              Đồ thị kết thúc. Trả về kết quả suy luận tổng hợp hoàn chỉnh.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
