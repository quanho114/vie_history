import { useState, memo } from "react";
import ReactMarkdown from "react-markdown";
import { SpikeMark } from "../UI/SpikeMark";
import type { ChatMessage } from "../../types";

interface MessageBubbleProps {
  message: ChatMessage;
  isLast?: boolean;
  isStreaming?: boolean;
  ariaPosInSet?: number;
  ariaSetSize?: number;
}

export const MessageBubble = memo(function MessageBubble({
  message,
  isLast,
  isStreaming,
  ariaPosInSet,
  ariaSetSize
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Build accessible label for the message
  const messageLabel = message.role === "user"
    ? "Tin nhắn của bạn"
    : "Phản hồi từ HistoriAI";

  if (message.role === "user") {
    return (
      <article
        role="article"
        aria-label={messageLabel}
        aria-posinset={ariaPosInSet}
        aria-setsize={ariaSetSize}
        style={{ display: "flex", justifyContent: "flex-end", marginBottom: 20 }}
      >
        <div
          style={{
            background: "var(--coral)",
            color: "#fff",
            padding: "12px 18px",
            borderRadius: "18px 18px 4px 18px",
            maxWidth: "68%",
            fontSize: 14,
            lineHeight: 1.6,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {message.content}
        </div>
      </article>
    );
  }

  return (
    <article
      role="article"
      aria-label={messageLabel}
      aria-posinset={ariaPosInSet}
      aria-setsize={ariaSetSize}
      aria-live={isStreaming ? "polite" : undefined}
      style={{ display: "flex", gap: 10, marginBottom: 24 }}
      className="ai-message-row"
    >
      <div
        style={{
          width: 26,
          height: 26,
          borderRadius: "50%",
          background: "var(--surface-card)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          marginTop: 3,
        }}
        aria-hidden="true"
      >
        <SpikeMark size={12} color="var(--coral)" />
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 14,
            lineHeight: 1.75,
            color: "var(--body)",
          }}
        >
          <div className="markdown-content">
            <ReactMarkdown>{message.content || ""}</ReactMarkdown>
          </div>
          {isStreaming && (
            <span
              aria-hidden="true"
              style={{
                display: "inline-block",
                width: 2,
                height: 16,
                background: "var(--coral)",
                marginLeft: 2,
                verticalAlign: "text-bottom",
                animation: "blink 1s step-end infinite",
              }}
            />
          )}
        </div>

        {!isStreaming && message.tags && message.tags.length > 0 && (
          <div
            role="list"
            aria-label="Thẻ nội dung"
            style={{
              display: "flex",
              gap: 6,
              marginTop: 10,
              flexWrap: "wrap",
            }}
          >
            {message.tags.map((tag) => (
              <span
                key={tag}
                role="listitem"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  padding: "3px 10px",
                  borderRadius: 9999,
                  border: "1px solid var(--hairline)",
                  fontSize: 11.5,
                  fontWeight: 500,
                  color: "var(--soft)",
                  background: "var(--canvas)",
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {!isStreaming && message.content && (
          <div
            className="msg-actions"
            role="group"
            aria-label="Hành động tin nhắn"
            style={{
              display: "flex",
              gap: 2,
              marginTop: 6,
              opacity: 0,
              transition: "opacity 0.15s",
            }}
          >
            <button
              onClick={copyToClipboard}
              aria-label={copied ? "Đã sao chép" : "Sao chép nội dung"}
              aria-pressed={copied}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                padding: "4px 8px",
                borderRadius: 6,
                border: "none",
                background: "transparent",
                cursor: "pointer",
                fontSize: 12,
                color: copied ? "var(--success)" : "var(--soft)",
              }}
            >
              <i className={`ti ti-${copied ? "check" : "copy"}`} style={{ fontSize: 13 }} aria-hidden="true" />
              <span className="sr-only">{copied ? "Đã sao chép" : "Sao chép"}</span>
            </button>
            <button
              onClick={() => {}}
              aria-label="Tái tạo câu trả lời"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                padding: "4px 8px",
                borderRadius: 6,
                border: "none",
                background: "transparent",
                cursor: "pointer",
                fontSize: 12,
                color: "var(--soft)",
              }}
            >
              <i className="ti ti-refresh" style={{ fontSize: 13 }} aria-hidden="true" />
              <span className="sr-only">Tái tạo</span>
            </button>
            <button
              onClick={() => {}}
              aria-label="Chia sẻ câu trả lời"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                padding: "4px 8px",
                borderRadius: 6,
                border: "none",
                background: "transparent",
                cursor: "pointer",
                fontSize: 12,
                color: "var(--soft)",
              }}
            >
              <i className="ti ti-share" style={{ fontSize: 13 }} aria-hidden="true" />
              <span className="sr-only">Chia sẻ</span>
            </button>
          </div>
        )}
      </div>
    </article>
  );
});
