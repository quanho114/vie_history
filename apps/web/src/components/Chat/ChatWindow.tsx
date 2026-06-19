import { useEffect, useRef, memo, useCallback } from "react";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import type { ChatMessage } from "../../types";

interface ChatWindowProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string | null;
  onRetry?: () => void;
}

export const ChatWindow = memo(function ChatWindow({ messages, isStreaming, error, onRetry }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const lastMessageCountRef = useRef(messages.length);

  // Auto-scroll on new messages
  useEffect(() => {
    if (messages.length > lastMessageCountRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
    lastMessageCountRef.current = messages.length;
  }, [messages]);

  // Keyboard navigation within chat
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "PageUp") {
      containerRef.current?.scrollBy({ top: -300, behavior: "smooth" });
      e.preventDefault();
    }
    if (e.key === "PageDown") {
      containerRef.current?.scrollBy({ top: 300, behavior: "smooth" });
      e.preventDefault();
    }
    // Home key scrolls to top
    if (e.key === "Home" && e.altKey) {
      containerRef.current?.scrollTo({ top: 0, behavior: "smooth" });
      e.preventDefault();
    }
    // End key scrolls to bottom
    if (e.key === "End" && e.altKey) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
      e.preventDefault();
    }
  }, []);

  // Calculate aria-posinset and aria-setsize for each message
  const totalMessages = messages.length;

  return (
    <div
      ref={containerRef}
      role="log"
      aria-label="Cuộc trò chuyện nghiên cứu lịch sử"
      aria-live="polite"
      aria-relevant="additions"
      aria-atomic="false"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      className="flex flex-col h-full overflow-y-auto focus:outline-none focus-visible:ring-2 focus-visible:ring-coral/50 focus-visible:ring-inset"
      style={{
        flex: 1,
        padding: "24px 0",
        background: "var(--canvas)",
      }}
    >
      {/* Skip link for keyboard users */}
      <a
        href="#chat-input"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-3 focus:py-2 focus:bg-coral focus:text-on-primary focus:rounded"
      >
        Chuyển đến ô nhập tin nhắn
      </a>

      <div style={{ maxWidth: 820, margin: "0 auto", padding: "0 24px" }}>
        {messages.map((msg, i) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            isLast={i === messages.length - 1}
            isStreaming={isStreaming && i === messages.length - 1 && msg.role === "assistant"}
            ariaPosInSet={i + 1}
            ariaSetSize={totalMessages}
          />
        ))}

        {isStreaming && messages[messages.length - 1]?.content === "" && (
          <div role="status" aria-label="Đang trả lời">
            <TypingIndicator />
          </div>
        )}

        {error && (
          <div
            role="alert"
            aria-live="assertive"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "12px 16px",
              borderRadius: 10,
              background: "#fff0f0",
              border: "1px solid #fcc",
              marginTop: 12,
              fontSize: 13.5,
              color: "var(--error)",
            }}
          >
            <i className="ti ti-alert-circle" style={{ fontSize: 16, flexShrink: 0 }} aria-hidden="true" />
            <span style={{ flex: 1 }}>{error}</span>
            {onRetry && (
              <button
                onClick={onRetry}
                aria-label="Thử lại"
                style={{
                  padding: "4px 12px",
                  borderRadius: 7,
                  border: "1px solid var(--error)",
                  background: "transparent",
                  color: "var(--error)",
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: "pointer",
                }}
              >
                Thử lại
              </button>
            )}
          </div>
        )}

        <div ref={bottomRef} id="chat-bottom" tabIndex={-1} />
      </div>
    </div>
  );
});
