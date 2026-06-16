import { useState, useRef, useEffect } from "react";
import type { ChatDocument } from "../../types";

interface InputBarProps {
  onSend: (content: string, docIds: string[]) => void;
  isStreaming: boolean;
  onStop: () => void;
  documents: ChatDocument[];
}

export function InputBar({ onSend, isStreaming, onStop, documents }: InputBarProps) {
  const [value, setValue] = useState("");
  const [attachedDocIds, setAttachedDocIds] = useState<string[]>([]);
  const [showDocPicker, setShowDocPicker] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  }, [value]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setShowDocPicker(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (!value.trim() || isStreaming) return;
    onSend(value.trim(), attachedDocIds);
    setValue("");
    setAttachedDocIds([]);
  };

  const removeDoc = (id: string) =>
    setAttachedDocIds((prev) => prev.filter((d) => d !== id));

  const attachedDocs = documents.filter((d) => attachedDocIds.includes(d.id));

  return (
    <div style={{ padding: "12px 24px 18px", background: "var(--canvas)" }}>
      <div style={{ maxWidth: 820, margin: "0 auto" }}>
        {attachedDocs.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
            {attachedDocs.map((doc) => (
              <span
                key={doc.id}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 5,
                  padding: "3px 10px",
                  borderRadius: 9999,
                  border: "1px solid var(--hairline)",
                  background: "var(--surface-card)",
                  fontSize: 12,
                  color: "var(--body)",
                }}
              >
                <i className="ti ti-file-text" style={{ fontSize: 12 }} />
                {doc.name.length > 20 ? doc.name.slice(0, 20) + "..." : doc.name}
                <button
                  onClick={() => removeDoc(doc.id)}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    color: "var(--soft)",
                    padding: 0,
                    lineHeight: 1,
                  }}
                >
                  <i className="ti ti-x" style={{ fontSize: 11 }} />
                </button>
              </span>
            ))}
          </div>
        )}

        <div
          style={{
            background: "#ffffff",
            border: "1px solid var(--hairline)",
            borderRadius: 14,
            padding: "10px 12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "flex-end", gap: 8 }}>
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Hỏi về lịch sử Việt Nam 1945–1975..."
              rows={1}
              disabled={isStreaming}
              style={{
                flex: 1,
                border: "none",
                background: "transparent",
                outline: "none",
                fontFamily: "inherit",
                fontSize: 14,
                color: "var(--ink)",
                resize: "none",
                lineHeight: 1.6,
                minHeight: 24,
                maxHeight: 160,
                overflowY: "hidden",
              }}
            />

            {isStreaming ? (
              <button
                onClick={onStop}
                style={{
                  width: 34,
                  height: 34,
                  borderRadius: 9,
                  background: "var(--surface-card)",
                  border: "1px solid var(--hairline)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <i className="ti ti-square" style={{ fontSize: 16, color: "var(--body)" }} />
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!value.trim()}
                style={{
                  width: 34,
                  height: 34,
                  borderRadius: 9,
                  background: value.trim() ? "var(--coral)" : "var(--coral-disabled)",
                  border: "none",
                  cursor: value.trim() ? "pointer" : "default",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  transition: "background 0.15s",
                }}
              >
                <i className="ti ti-send" style={{ fontSize: 16, color: "#fff" }} />
              </button>
            )}
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginTop: 8,
            }}
          >
            <div style={{ display: "flex", gap: 4, position: "relative" }}>
              <button
                onClick={() => setShowDocPicker((v) => !v)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 5,
                  padding: "4px 10px",
                  borderRadius: 7,
                  border: "1px solid var(--hairline)",
                  background: "transparent",
                  fontSize: 12,
                  fontWeight: 500,
                  color: "var(--muted)",
                  cursor: "pointer",
                  fontFamily: "inherit",
                }}
              >
                <i className="ti ti-paperclip" style={{ fontSize: 14 }} />
                Đính kèm
              </button>

              {showDocPicker && documents.length > 0 && (
                <div
                  ref={pickerRef}
                  style={{
                    position: "absolute",
                    bottom: "calc(100% + 8px)",
                    left: 0,
                    background: "#fff",
                    border: "1px solid var(--hairline)",
                    borderRadius: 10,
                    padding: "6px 0",
                    minWidth: 220,
                    boxShadow: "0 4px 16px rgba(0,0,0,.08)",
                    zIndex: 50,
                  }}
                >
                  <p
                    style={{
                      fontSize: 11,
                      color: "var(--soft)",
                      padding: "4px 12px 6px",
                      fontWeight: 500,
                    }}
                  >
                    CHỌN TÀI LIỆU
                  </p>
                  {documents.map((doc) => {
                    const selected = attachedDocIds.includes(doc.id);
                    return (
                      <button
                        key={doc.id}
                        onClick={() => {
                          setAttachedDocIds((prev) =>
                            selected
                              ? prev.filter((id) => id !== doc.id)
                              : [...prev, doc.id]
                          );
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          width: "100%",
                          padding: "7px 12px",
                          border: "none",
                          background: selected ? "var(--surface-card)" : "transparent",
                          cursor: "pointer",
                          fontSize: 13,
                          color: "var(--body)",
                          textAlign: "left",
                          fontFamily: "inherit",
                        }}
                      >
                        <i
                          className="ti ti-file-text"
                          style={{ fontSize: 14, color: "var(--muted)" }}
                        />
                        <span
                          style={{
                            flex: 1,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {doc.name}
                        </span>
                        {selected && (
                          <i
                            className="ti ti-check"
                            style={{ fontSize: 13, color: "var(--coral)" }}
                          />
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <span style={{ fontSize: 11, color: "var(--soft)" }}>
              Enter gửi · Shift+Enter xuống dòng
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
