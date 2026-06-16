import { useState, useRef, useEffect, type FormEvent } from "react";
import { useChatStore } from "@/stores/chatStore";
import { cn } from "@/lib/utils/cn";
import { Send, Paperclip, Search, Copy, ThumbsUp, ThumbsDown, RefreshCw, Share2, Square, Check, Key, Settings } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { Message, Citation } from "@/types";
import { LiveThinkingPanel } from "@/components/Chat/LiveThinkingPanel";
import { PROVINCES_DATA } from "@/components/ui/VietnamMap";

/* ========================================
   Spike-mark SVG Logo
   ======================================== */

function SpikeMarkLogo({ size = 40 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="#cc785c"
      aria-hidden="true"
    >
      {/* Central Star - Shining Gold at the heart of the Lotus */}
      <polygon points="50,42 52.5,50 60,50 54,55 56,62 50,58 44,62 46,55 40,50 47.5,50" fill="#f5c542" />
      {/* Central Petal */}
      <path d="M 50 15 C 44 32, 44 65, 50 82 C 56 65, 56 32, 50 15 Z" fill="currentColor" />
      {/* Inner Left Petal */}
      <path d="M 46 82 C 38 65, 28 42, 33 26 C 39 23, 44 48, 46 82 Z" fill="currentColor" />
      {/* Inner Right Petal */}
      <path d="M 54 82 C 62 65, 72 42, 67 26 C 61 23, 56 48, 54 82 Z" fill="currentColor" />
      {/* Outer Left Petal */}
      <path d="M 42 82 C 26 70, 10 52, 16 35 C 24 30, 34 55, 42 82 Z" fill="currentColor" />
      {/* Outer Right Petal */}
      <path d="M 58 82 C 74 70, 90 52, 84 35 C 76 30, 66 55, 58 82 Z" fill="currentColor" />
      {/* Supporting Bottom Leaves */}
      <path d="M 40 84 C 20 88, 12 88, 6 82 C 14 74, 30 74, 40 84 Z" fill="currentColor" opacity="0.8" />
      <path d="M 60 84 C 80 88, 88 88, 94 82 C 86 74, 70 74, 60 84 Z" fill="currentColor" opacity="0.8" />
    </svg>
  );
}

/* ========================================
   AI Avatar Icon
   ======================================== */

function AIAvatar({ size = 26 }: { size?: number }) {
  return (
    <div
      className="rounded-full flex items-center justify-center flex-shrink-0"
      style={{ width: size, height: size, backgroundColor: "var(--surface-card)" }}
    >
      <svg
        width={Math.round(size * 0.5)}
        height={Math.round(size * 0.5)}
        viewBox="0 0 13 13"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M6.5 1v11M1 6.5h11M2.3 2.3l8.4 8.4M10.7 2.3L2.3 10.7"
          stroke="var(--coral)"
          strokeWidth="1.4"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
}

/* ========================================
   Typing Indicator Dots
   ======================================== */

function TypingDots() {
  return (
    <div className="flex items-center gap-1">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            backgroundColor: "var(--muted)",
            display: "inline-block",
            animation: `typing-dot 1.2s ease-in-out ${delay}ms infinite`,
          }}
        />
      ))}
    </div>
  );
}

/* ========================================
   Message Action Buttons
   ======================================== */

interface MessageActionsProps {
  message: Message;
  onRegenerate?: () => void;
}

function MessageActions({ message, onRegenerate }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const [vote, setVote] = useState<"like" | "dislike" | null>(null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content || "");
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const handleShare = async () => {
    try {
      if (navigator.share) {
        await navigator.share({
          title: "HistoriAI Answer",
          text: message.content || "",
        });
      } else {
        await navigator.clipboard.writeText(window.location.href);
        alert("Đã sao chép liên kết cuộc trò chuyện vào bộ nhớ tạm!");
      }
    } catch (err) {
      console.error("Failed to share:", err);
    }
  };

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={handleCopy}
        className="p-1.5 rounded-md transition-colors hover:bg-stone-100"
        title="Sao chép"
        style={{ background: "none", border: "none", cursor: "pointer", color: copied ? "var(--success)" : "var(--soft)" }}
      >
        {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
      </button>
      <button
        onClick={() => setVote(vote === "like" ? null : "like")}
        className="p-1.5 rounded-md transition-colors hover:bg-stone-100"
        title="Thích"
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          color: vote === "like" ? "var(--coral)" : "var(--soft)",
        }}
      >
        <ThumbsUp className="w-3.5 h-3.5" fill={vote === "like" ? "var(--coral)" : "none"} />
      </button>
      <button
        onClick={() => setVote(vote === "dislike" ? null : "dislike")}
        className="p-1.5 rounded-md transition-colors hover:bg-stone-100"
        title="Không thích"
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          color: vote === "dislike" ? "var(--coral)" : "var(--soft)",
        }}
      >
        <ThumbsDown className="w-3.5 h-3.5" fill={vote === "dislike" ? "var(--coral)" : "none"} />
      </button>
      {onRegenerate && (
        <button
          onClick={onRegenerate}
          className="p-1.5 rounded-md transition-colors hover:bg-stone-100"
          title="Tái tạo"
          style={{ background: "none", border: "none", cursor: "pointer", color: "var(--soft)" }}
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      )}
      <button
        onClick={handleShare}
        className="p-1.5 rounded-md transition-colors hover:bg-stone-100"
        title="Chia sẻ"
        style={{ background: "none", border: "none", cursor: "pointer", color: "var(--soft)" }}
      >
        <Share2 className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

function formatCitationTitle(title: string) {
  if (!title) return "Tài liệu";
  if (title.startsWith("http://") || title.startsWith("https://")) {
    try {
      const url = new URL(title);
      const domain = url.hostname.replace("www.", "");
      const path = decodeURIComponent(url.pathname);
      if (path && path !== "/") {
        const lastPart = path.split("/").pop();
        if (lastPart) {
          return `${domain} › ${lastPart.replace(/_/g, " ")}`;
        }
      }
      return domain;
    } catch {
      return title;
    }
  }
  return title;
}

function CitationCard({ citation }: { citation: Citation }) {
  const friendlyTitle = formatCitationTitle(citation.document_title);

  return (
    <a
      href={citation.source_url || "#"}
      target="_blank"
      rel="noopener noreferrer"
      className="block p-2.5 rounded-lg border transition-all duration-150 hover:shadow-[0_2px_8px_rgba(0,0,0,0.03)] hover:border-[#cc785c] group"
      style={{
        backgroundColor: "#fcfbf9",
        borderColor: "#e8e2d9",
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <span
            className="font-medium text-[12px] truncate block group-hover:text-[#cc785c] transition-colors"
            style={{ color: "var(--body-strong)" }}
            title={friendlyTitle}
          >
            {friendlyTitle}
          </span>
          {citation.section_title && (
            <span className="text-[11px] block mt-0.5 font-normal truncate" style={{ color: "var(--muted)" }}>
              {citation.section_title}
            </span>
          )}
          <p
            className="mt-1 leading-normal line-clamp-1 text-[11px]"
            style={{ color: "var(--muted)" }}
          >
            {citation.excerpt}
          </p>
        </div>
        <span
          className="px-1.5 py-0.5 rounded text-[10px] flex-shrink-0 font-medium"
          style={{
            backgroundColor: "var(--surface-soft)",
            color: "var(--muted)",
          }}
        >
          {Math.round(citation.score * 100)}%
        </span>
      </div>
    </a>
  );
}

/* ========================================
   Code Block
   ======================================== */

interface CodeBlockProps {
  code: string;
  language?: string;
}

function CodeBlock({ code, language }: CodeBlockProps) {
  const lines = code.split("\n");

  return (
    <div className="my-4">
      <div
        className="flex items-center justify-between mb-3"
        style={{
          backgroundColor: "var(--surface-dark-el)",
          borderRadius: "var(--r-lg) var(--r-lg) 0 0",
          padding: "8px 12px",
        }}
      >
        <span
          className="text-[11px] uppercase tracking-wider"
          style={{ color: "var(--on-dark-soft)" }}
        >
          {language || "code"}
        </span>
        <button
          className="p-1 rounded transition-colors"
          style={{ background: "none", border: "none", cursor: "pointer", color: "var(--on-dark-soft)" }}
          title="Sao chép mã"
          aria-label="Sao chép mã"
        >
          <Copy className="w-3.5 h-3.5" />
        </button>
      </div>
      <pre
        className="overflow-x-auto"
        style={{
          backgroundColor: "var(--surface-dark)",
          borderRadius: "0 0 var(--r-lg) var(--r-lg)",
          padding: "12px",
          margin: 0,
        }}
      >
        <code>
          {lines.map((line, i) => (
            <div key={i} className="flex">
              <span
                className="select-none pr-4 text-right"
                style={{ userSelect: "none", minWidth: "2rem", color: "var(--on-dark-soft)" }}
              >
                {i + 1}
              </span>
              <span style={{ color: "var(--on-dark)" }}>{line}</span>
            </div>
          ))}
        </code>
      </pre>
    </div>
  );
}

/* ========================================
   Tag Component
   ======================================== */

function Tag({
  children,
  onClick,
}: {
  children: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="tag"
      style={onClick ? { cursor: "pointer" } : { cursor: "default" }}
    >
      {children}
    </button>
  );
}

/* ========================================
   Empty State
   ======================================== */

const SUGGESTED_PROMPTS = [
  "Ai là những nhân vật chính trong Cách mạng tháng Tám 1945?",
  "So sánh Hiệp định Genève 1954 và Hiệp định Paris 1973",
  "Diễn biến chiến dịch Điện Biên Phủ 1954",
  "Tóm tắt sự kiện Tết Mậu Thân 1968",
];

function EmptyState({ onSuggestion }: { onSuggestion: (text: string) => void }) {
  return (
    <div
      className="flex flex-col items-center justify-center h-full px-8 py-16"
      style={{ textAlign: "center" }}
    >
      {/* Spike-mark lớn */}
      <div className="mb-8">
        <SpikeMarkLogo size={48} />
      </div>

      {/* Tiêu đề */}
      <h2
        className="mb-3"
        style={{
          fontFamily: "var(--font-display)",
          fontSize: 22,
          fontWeight: 400,
          color: "var(--ink)",
          letterSpacing: "-0.4px",
        }}
      >
        Chào mừng đến với HistoriAI
      </h2>

      {/* Mô tả */}
      <p
        className="mb-10 leading-relaxed"
        style={{ fontSize: 14, color: "var(--muted)", maxWidth: 420 }}
      >
        Tôi có thể giúp bạn tra cứu thông tin về lịch sử Việt Nam từ 1945
        đến 1975. Hãy đặt câu hỏi về các sự kiện, nhân vật, hoặc so sánh
        các giai đoạn lịch sử.
      </p>

      {/* Quick-start pills */}
      <div
        className="flex flex-wrap justify-center gap-2"
        style={{ maxWidth: 640 }}
      >
        {SUGGESTED_PROMPTS.map((prompt, i) => (
          <button
            key={i}
            onClick={() => onSuggestion(prompt)}
            className="px-4 py-2.5 rounded-full text-[13px] transition-all duration-150"
            style={{
              backgroundColor: "transparent",
              border: "1px solid var(--hairline)",
              color: "var(--body)",
              cursor: "pointer",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--coral)";
              e.currentTarget.style.backgroundColor = "var(--surface-card)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--hairline)";
              e.currentTarget.style.backgroundColor = "transparent";
            }}
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ========================================
   Streaming Indicator (Dots)
   ======================================== */

function StreamingIndicator() {
  return (
    <div className="flex gap-3 animate-fade-in">
      <AIAvatar size={26} />
      <div className="flex items-center gap-2" style={{ color: "var(--muted)", paddingTop: 5 }}>
        <TypingDots />
      </div>
    </div>
  );
}

const STAGE_LABELS: Record<string, string> = {
  classifying: "Phân loại câu hỏi",
  retrieving: "Tìm nguồn",
  verifying: "Kiểm chứng",
  generating: "Soạn câu trả lời",
};

function StageIndicator({ stage }: { stage: string | null }) {
  if (!stage) return null;
  return (
    <span className="text-[12px]" style={{ color: "var(--soft)" }}>
      {STAGE_LABELS[stage] || stage}
    </span>
  );
}

/* ========================================
   Message Row
   ======================================== */

function MessageRow({
  message,
  isStreaming,
  onRegenerate,
  liveTrace,
}: {
  message: Message;
  isStreaming?: boolean;
  onRegenerate?: () => void;
  liveTrace?: Array<{ agent: string; action: string; status: string }> | null;
}) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn("msg-row flex gap-3 animate-fade-in w-full")}
      style={{
        justifyContent: isUser ? "flex-end" : "flex-start",
      }}
    >
      {/* Avatar for AI */}
      {!isUser && <AIAvatar size={26} />}

      {/* Content */}
      <div
        className={cn("flex flex-col gap-2", isUser ? "max-w-[70%]" : "flex-1 w-full max-w-none")}
        style={{
          alignItems: isUser ? "flex-end" : "flex-start",
        }}
      >
        {/* Live Thinking Panel — shown ABOVE content, visible during streaming */}
        {!isUser && (
          <LiveThinkingPanel
            liveTrace={isStreaming ? (liveTrace || null) : null}
            isStreaming={!!isStreaming}
            finalTrace={message.trace}
          />
        )}

        {/* Bubble */}
        <div
          className={isUser ? "bubble-user w-fit" : "bubble-ai w-full"}
          style={isUser ? {
            width: "fit-content",
            wordBreak: "normal",
            overflowWrap: "break-word",
            whiteSpace: "pre-wrap"
          } : undefined}
        >
          {/* AI message with markdown + cursor */}
          {!isUser && (
            <div className="prose prose-sm max-w-none w-full">
              <ReactMarkdown
                components={{
                  code({ className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    const isInline = !match;
                    return isInline ? (
                      <code
                        className="px-1.5 py-0.5 rounded text-[13px]"
                        style={{
                          backgroundColor: "var(--surface-soft)",
                          fontFamily: "var(--font-mono)",
                        }}
                        {...props}
                      >
                        {children}
                      </code>
                    ) : (
                      <CodeBlock code={String(children)} language={match?.[1]} />
                    );
                  },
                  a({ href, children }) {
                    return (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: "var(--coral)" }}
                      >
                        {children}
                      </a>
                    );
                  },
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-4 max-w-full rounded-xl border border-stone-200 select-text">
                      <table className="min-w-full font-serif text-[13px] text-stone-800 border-t-2 border-b-2 border-stone-800 border-collapse">
                        {children}
                      </table>
                    </div>
                  ),
                  thead: ({ children }) => <thead className="border-b border-stone-800 bg-stone-50/50">{children}</thead>,
                  th: ({ children }) => <th className="py-2 px-3 font-bold text-stone-950 text-left">{children}</th>,
                  td: ({ children }) => <td className="py-2 px-3 border-b border-stone-100">{children}</td>,
                }}
              >
                {message.content || ""}
              </ReactMarkdown>
              {/* Streaming cursor */}
              {isStreaming && (
                <span
                  className="inline-block w-2.5 h-2.5 rounded-full ml-1"
                  style={{
                    backgroundColor: "var(--coral)",
                    verticalAlign: "middle",
                    boxShadow: "0 0 8px var(--coral)",
                    animation: "cursor-pulse 1.2s ease-in-out infinite",
                  }}
                />
              )}
            </div>
          )}

          {/* User message plain text */}
          {isUser && message.content}

          {/* Actions hiện khi hover */}
          {!isUser && !isStreaming && message.content && (
            <div className="mt-2 flex items-center gap-2">
              <MessageActions message={message} onRegenerate={onRegenerate} />
            </div>
          )}
        </div>

        {/* Citations */}
        {!isUser &&
          message.citations &&
          message.citations.length > 0 && (
            <div
              className="mt-4 pt-4 w-full"
              style={{
                borderTop: "1px solid var(--hairline-soft)",
                maxWidth: "100%",
              }}
            >
              <p
                className="mb-3 text-[11px] font-medium uppercase tracking-wider"
                style={{ color: "var(--soft)" }}
              >
                Nguồn tham khảo
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {message.citations.map((citation, i) => (
                  <CitationCard key={i} citation={citation} />
                ))}
              </div>
            </div>
          )}
      </div>
    </div>
  );
}

/* ========================================
   Input Bar
   ======================================== */

interface InputBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  disabled?: boolean;
  placeholder?: string;
  onStop?: () => void;
  stage?: string | null;
  activeProvider: string;
  activeModel: string;
  isKeyMissing?: boolean;
}

function InputBar({
  value,
  onChange,
  onSubmit,
  disabled,
  placeholder,
  onStop,
  stage,
  activeProvider,
  activeModel,
  isKeyMissing,
}: InputBarProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedPeriods, setSelectedPeriods] = useState<string[]>(["1945-1954", "1954-1975"]);
  const [selectedSources, setSelectedSources] = useState<string[]>(["wiki", "timeline", "docs"]);

  // Attachment states
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  // Reset height when value is cleared
  useEffect(() => {
    if (value === "" && textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value]);

  // Auto-resize textarea
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
  };

  // Handle Enter/Shift+Enter
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) {
        const form = e.currentTarget.form;
        if (form) {
          form.dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
          );
        }
      }
    }
  };

  // Handle file select and background ingestion
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setAttachedFile(file);
      setUploadingFile(true);
      setUploadSuccess(false);
      try {
        const { ingestApi } = await import("@/lib/services/api");
        await ingestApi.submitFile(file, ["chat-upload"]);
        setUploadSuccess(true);
      } catch (err) {
        console.error("Failed to upload attached file:", err);
        alert("Đính kèm tư liệu thất bại: " + (err instanceof Error ? err.message : "Lỗi hệ thống"));
        setAttachedFile(null);
      } finally {
        setUploadingFile(false);
      }
    }
  };

  return (
    <form onSubmit={onSubmit} className="mx-auto w-full max-w-[760px] px-4 pb-6 relative">
      {/* Advanced Search Filters Popover */}
      {showFilters && (
        <div className="w-full mb-3 animate-fade-in text-left">
          <div
            className="rounded-2xl border border-[#e7e1d8] bg-white/95 p-4 shadow-[0_10px_25px_rgba(0,0,0,0.06)] backdrop-blur-md"
            style={{ border: "1px solid var(--hairline-soft)" }}
          >
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-[#f5f1ea]">
              <span className="text-[12px] font-bold text-[#2d2a26] uppercase tracking-wider flex items-center gap-1.5">
                <Search size={13} style={{ color: "var(--coral)" }} /> Bộ lọc RAG Nâng cao (Lịch sử 1945–1975)
              </span>
              <button
                type="button"
                onClick={() => setShowFilters(false)}
                className="text-[11px] font-medium hover:underline"
                style={{ color: "var(--coral)" }}
              >
                Đóng bộ lọc
              </button>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-[12px]">
              {/* Period filters */}
              <div>
                <p className="font-semibold text-[#6f675d] mb-2">Thời kỳ lịch sử</p>
                <div className="flex flex-col gap-1.5">
                  <label className="flex items-center gap-2 cursor-pointer text-[#2d2a26] hover:text-black">
                    <input
                      type="checkbox"
                      checked={selectedPeriods.includes("1945-1954")}
                      onChange={(e) => {
                        if (e.target.checked) setSelectedPeriods([...selectedPeriods, "1945-1954"]);
                        else setSelectedPeriods(selectedPeriods.filter(p => p !== "1945-1954"));
                      }}
                      className="cursor-pointer"
                      style={{ accentColor: "var(--coral)" }}
                    />
                    Kháng chiến chống Pháp (1945–1954)
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-[#2d2a26] hover:text-black">
                    <input
                      type="checkbox"
                      checked={selectedPeriods.includes("1954-1975")}
                      onChange={(e) => {
                        if (e.target.checked) setSelectedPeriods([...selectedPeriods, "1954-1975"]);
                        else setSelectedPeriods(selectedPeriods.filter(p => p !== "1954-1975"));
                      }}
                      className="cursor-pointer"
                      style={{ accentColor: "var(--coral)" }}
                    />
                    Kháng chiến chống Mỹ (1954–1975)
                  </label>
                </div>
              </div>

              {/* Source filters */}
              <div>
                <p className="font-semibold text-[#6f675d] mb-2">Kho tri thức liên kết</p>
                <div className="flex flex-col gap-1.5">
                  <label className="flex items-center gap-2 cursor-pointer text-[#2d2a26] hover:text-black">
                    <input
                      type="checkbox"
                      checked={selectedSources.includes("wiki")}
                      onChange={(e) => {
                        if (e.target.checked) setSelectedSources([...selectedSources, "wiki"]);
                        else setSelectedSources(selectedSources.filter(s => s !== "wiki"));
                      }}
                      className="cursor-pointer"
                      style={{ accentColor: "var(--coral)" }}
                    />
                    Wiki Lịch sử & Nhân vật
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-[#2d2a26] hover:text-black">
                    <input
                      type="checkbox"
                      checked={selectedSources.includes("timeline")}
                      onChange={(e) => {
                        if (e.target.checked) setSelectedSources([...selectedSources, "timeline"]);
                        else setSelectedSources(selectedSources.filter(s => s !== "timeline"));
                      }}
                      className="cursor-pointer"
                      style={{ accentColor: "var(--coral)" }}
                    />
                    Niên biểu mốc thời gian
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-[#2d2a26] hover:text-black">
                    <input
                      type="checkbox"
                      checked={selectedSources.includes("docs")}
                      onChange={(e) => {
                        if (e.target.checked) setSelectedSources([...selectedSources, "docs"]);
                        else setSelectedSources(selectedSources.filter(s => s !== "docs"));
                      }}
                      className="cursor-pointer"
                      style={{ accentColor: "var(--coral)" }}
                    />
                    Tư liệu văn kiện thư viện (RAG Docs)
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Attached File Preview Tag */}
      {attachedFile && (
        <div className="w-full mb-3 animate-fade-in text-left">
          <div className="inline-flex items-center gap-2 rounded-lg bg-[#f5f1ea] px-3 py-1.5 text-[12px] text-[#6f675d] border border-[#e7e1d8] shadow-sm">
            <span className="font-semibold truncate max-w-[240px]">📄 {attachedFile.name}</span>
            {uploadingFile ? (
              <div className="flex items-center gap-1.5 ml-1">
                <span className="w-3 h-3 rounded-full border-2 border-[var(--coral)] border-t-transparent animate-spin" />
                <span className="text-[11px] text-[#8a8175]">Đang tải lên...</span>
              </div>
            ) : uploadSuccess ? (
              <span className="text-[11px] font-bold text-[#5db872] ml-1 flex items-center gap-0.5">
                ✓ Đã nạp tri thức
              </span>
            ) : (
              <button
                type="button"
                onClick={() => setAttachedFile(null)}
                className="text-stone-400 hover:text-stone-600 font-bold ml-1 text-[13px] border-none bg-transparent cursor-pointer"
              >
                ×
              </button>
            )}
          </div>
        </div>
      )}

      {/* Active Model Indicator */}
      <div className="flex items-center justify-center gap-1.5 mb-2.5 text-[11px]" style={{ color: "var(--muted)" }}>
        {isKeyMissing ? (
          <>
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "var(--muted)" }} />
            <span className="font-semibold uppercase tracking-wider">Chưa cấu hình API</span>
          </>
        ) : (
          <>
            <span className="w-1.5 h-1.5 rounded-full bg-[#5db872] animate-pulse" />
            <span className="font-semibold uppercase tracking-wider">{activeProvider}</span>
            <span className="text-[#c4b8a8]">•</span>
            <span className="font-normal opacity-90">{activeModel}</span>
          </>
        )}
      </div>

      <div className="flex min-h-[56px] items-end gap-2 rounded-[24px] border border-[#e7e1d8] bg-white px-4 py-2.5 shadow-[0_2px_12px_rgba(0,0,0,0.04)]">
        {/* Hidden File input */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          style={{ display: "none" }}
          accept=".pdf,.txt,.docx,.md"
        />

        {/* Attachment Button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[#6f675d] hover:bg-[#f5f1ea] transition-colors mb-0.5"
          title="Đính kèm tài liệu"
          aria-label="Đính kèm tài liệu"
        >
          <Paperclip size={17} />
        </button>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={isKeyMissing ? "Vui lòng cấu hình API Key ở phía trên để trò chuyện..." : (placeholder || "Hỏi về lịch sử Việt Nam 1945–1975...")}
          disabled={disabled || isKeyMissing}
          rows={1}
          spellCheck={false}
          className="max-h-[120px] min-h-9 flex-1 resize-none bg-transparent px-1 py-1.5 text-[15px] leading-5 text-[#2d2a26] outline-none placeholder:text-[#aaa39a] focus:outline-none focus:ring-0 focus:border-none"
          style={{ border: 'none', boxShadow: 'none', outline: 'none' }}
        />



        {/* Send / Stop Button */}
        <button
          type={disabled ? "button" : "submit"}
          onClick={disabled ? onStop : undefined}
          disabled={disabled ? false : (isKeyMissing ? true : !value.trim())}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#2f2a25] text-white disabled:bg-[#ded9d2] disabled:text-white transition-colors disabled:cursor-not-allowed hover:bg-stone-800 mb-0.5"
          title={disabled ? "Dừng" : "Gửi tin nhắn"}
          aria-label={disabled ? "Dừng phản hồi" : "Gửi tin nhắn"}
        >
          {disabled ? (
            <Square size={16} className="text-white" />
          ) : (
            <Send size={15} className="text-white ml-0.5" />
          )}
        </button>
      </div>
    </form>
  );
}

/* ========================================
   Chat Page
   ======================================== */

const GROQ_LEGACY_MODEL_MAP: Record<string, string> = {
  "llama3-70b-8192": "llama-3.3-70b-versatile",
  "llama3-8b-8192": "llama-3.1-8b-instant",
  "mixtral-8x7b-32768": "llama-3.3-70b-versatile",
};

function getStoredModel(provider: string) {
  const fallback = provider === "gemini"
    ? "gemini-1.5-pro"
    : provider === "groq"
      ? "llama-3.3-70b-versatile"
      : provider === "openai"
        ? "gpt-4o"
        : "llama3";
  const model = localStorage.getItem(`${provider}_model`) || fallback;
  if (provider !== "groq") return model;
  const normalized = GROQ_LEGACY_MODEL_MAP[model] || model;
  if (normalized !== model) {
    localStorage.setItem("groq_model", normalized);
  }
  return normalized;
}

export function ChatPage() {
  const [query, setQuery] = useState("");
  const {
    messages,
    activeSessionId,
    isStreaming,
    currentStage,
    liveTrace,
    error,
    clearError,
    sendMessage,
    abortStreaming,
  } = useChatStore();

  const [activeProvider, setActiveProvider] = useState(() => localStorage.getItem("active_provider") || "gemini");
  const [activeModel, setActiveModel] = useState(() => {
    const provider = localStorage.getItem("active_provider") || "gemini";
    return getStoredModel(provider);
  });
  const [isKeyMissing, setIsKeyMissing] = useState(() => {
    const provider = localStorage.getItem("active_provider") || "gemini";
    if (provider === "ollama") return false;
    const key = localStorage.getItem(`${provider}_key`);
    return !key || key.trim() === "";
  });

  useEffect(() => {
    const handleSettingsChange = () => {
      const provider = localStorage.getItem("active_provider") || "gemini";
      setActiveProvider(provider);
      setActiveModel(getStoredModel(provider));
      
      if (provider === "ollama") {
        setIsKeyMissing(false);
      } else {
        const key = localStorage.getItem(`${provider}_key`);
        setIsKeyMissing(!key || key.trim() === "");
      }
    };

    window.addEventListener("llm_settings_changed", handleSettingsChange);
    return () => window.removeEventListener("llm_settings_changed", handleSettingsChange);
  }, []);

  const currentMessages = activeSessionId
    ? messages[activeSessionId] || []
    : [];
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentMessages, isStreaming]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery || isStreaming || isKeyMissing) return;

    setQuery("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    clearError();
    await sendMessage(trimmedQuery);
  };

  const handleRegenerate = async (msg: Message) => {
    if (isStreaming) return;
    const msgIndex = currentMessages.findIndex((m) => m.id === msg.id);
    if (msgIndex <= 0) return;
    const prevUserMsg = currentMessages[msgIndex - 1];
    if (prevUserMsg && prevUserMsg.role === "user") {
      clearError();
      await sendMessage(prevUserMsg.content);
    }
  };

  const handleSuggestion = (text: string) => {
    setQuery(text);
  };

  // Check if we need to show typing dots (first token not received yet)
  const showTypingDots = isStreaming && currentMessages.length === 0;

  return (
    <div
      className="flex flex-col h-full"
      style={{ backgroundColor: "var(--canvas)" }}
    >
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto">
        {currentMessages.length === 0 && !isStreaming ? (
          <EmptyState onSuggestion={handleSuggestion} />
        ) : (
          <div style={{ maxWidth: 820, margin: "0 auto", padding: "24px" }}>
            <div className="space-y-8">
              {currentMessages.map((message, index) => (
                <MessageRow
                  key={message.id}
                  message={message}
                  onRegenerate={
                    index > 0 && currentMessages[index - 1].role === "user"
                      ? () => handleRegenerate(message)
                      : undefined
                  }
                  isStreaming={
                    isStreaming &&
                    index === currentMessages.length - 1 &&
                    message.role === "assistant"
                  }
                  liveTrace={
                    isStreaming &&
                    index === currentMessages.length - 1 &&
                    message.role === "assistant"
                      ? liveTrace
                      : null
                  }
                />
              ))}
            </div>

            {/* Typing dots - show when waiting for first token */}
            {showTypingDots && <StreamingIndicator />}

            {/* Scroll anchor */}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Bar */}
      {(error || isKeyMissing) && (
        <div className="mx-auto mb-4 w-full max-w-[760px] px-4">
          {(() => {
            const isApiError = isKeyMissing || (error && (
              error.includes("API_KEY_MISSING") || 
              error.toLowerCase().includes("api key") || 
              error.toLowerCase().includes("connect") ||
              error.toLowerCase().includes("unauthorized") ||
              error.toLowerCase().includes("auth") ||
              error.toLowerCase().includes("provider") ||
              error.toLowerCase().includes("configured")
            ));

            if (isApiError) {
              return (
                <div 
                  className="relative overflow-hidden rounded-2xl border p-4 shadow-sm backdrop-blur-sm animate-fade-in flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-left"
                  style={{
                    backgroundColor: "var(--surface-soft)",
                    borderColor: "var(--hairline)",
                    borderLeft: "4px solid var(--amber)",
                  }}
                >
                  <div className="flex items-start gap-3">
                    <div 
                      className="p-2 rounded-xl mt-0.5 flex-shrink-0 animate-pulse"
                      style={{
                        backgroundColor: "rgba(232, 165, 90, 0.12)",
                        color: "var(--amber)",
                      }}
                    >
                      <Key className="w-5 h-5" />
                    </div>
                    <div className="space-y-0.5">
                      <h4 className="font-display text-[14px] font-semibold leading-tight" style={{ color: "var(--ink)" }}>
                        Cấu hình API chưa hoàn thiện
                      </h4>
                      <p className="text-[12px] leading-relaxed max-w-lg" style={{ color: "var(--body)" }}>
                        {isKeyMissing 
                          ? `Vui lòng nhập API Key cho nhà cung cấp ${activeProvider.toUpperCase()} để bắt đầu trò chuyện tìm kiếm lịch sử.`
                          : error?.replace("API_KEY_MISSING:", "").trim()}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      window.dispatchEvent(new CustomEvent("open_settings", { detail: { tab: "ai_api" } }));
                    }}
                    className="flex-shrink-0 flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl text-[12.5px] font-semibold shadow-sm hover:scale-[1.02] active:scale-[0.98] transition-all duration-150 cursor-pointer"
                    style={{
                      backgroundColor: "var(--coral)",
                      color: "var(--on-primary)",
                      border: "none",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = "var(--coral-hover)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = "var(--coral)";
                    }}
                  >
                    <Settings className="w-3.5 h-3.5 animate-spin-slow" />
                    <span>Thiết lập API Key</span>
                  </button>
                </div>
              );
            }

            return (
              <div className="rounded-xl border border-red-200/80 bg-red-50/80 dark:bg-red-950/20 dark:border-red-900/50 px-4 py-3 text-[13px] text-red-700 dark:text-red-300 flex items-center justify-between gap-3 shadow-sm animate-fade-in text-left">
                <span>{error}</span>
                <button
                  type="button"
                  onClick={clearError}
                  className="px-2 py-1 rounded-md text-[11px] font-semibold hover:bg-red-100 dark:hover:bg-red-950/50"
                >
                  Đóng
                </button>
              </div>
            );
          })()}
        </div>
      )}
      <InputBar
        value={query}
        onChange={setQuery}
        onSubmit={handleSubmit}
        disabled={isStreaming}
        onStop={abortStreaming}
        stage={currentStage}
        placeholder="Hỏi về lịch sử Việt Nam 1945–1975..."
        activeProvider={activeProvider}
        activeModel={activeModel}
        isKeyMissing={isKeyMissing}
      />
    </div>
  );
}
