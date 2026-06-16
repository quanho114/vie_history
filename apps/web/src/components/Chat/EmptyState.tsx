import { SpikeMark } from "../UI/SpikeMark";

const SUGGESTIONS = [
  "Ai là những nhân vật chính trong Cách mạng tháng Tám 1945?",
  "So sánh Hiệp định Genève 1954 và Hiệp định Paris 1973",
  "Diễn biến chiến dịch Điện Biên Phủ 1954",
  "Tóm tắt sự kiện Tết Mậu Thân 1968",
];

interface EmptyStateProps {
  onSuggestionClick: (text: string) => void;
}

export function EmptyState({ onSuggestionClick }: EmptyStateProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        flex: 1,
        padding: "48px 24px",
        textAlign: "center",
      }}
    >
      <SpikeMark size={36} color="var(--hairline)" style={{ marginBottom: 24 }} />

      <h1
        style={{
          fontFamily: "'EB Garamond', Georgia, serif",
          fontSize: 26,
          fontWeight: 400,
          letterSpacing: "-0.4px",
          color: "var(--ink)",
          marginBottom: 10,
        }}
      >
        Chào mừng đến với HistoriAI
      </h1>

      <p
        style={{
          fontSize: 14,
          color: "var(--muted)",
          maxWidth: 420,
          lineHeight: 1.6,
          marginBottom: 36,
        }}
      >
        Tôi có thể giúp bạn tra cứu thông tin về lịch sử Việt Nam từ 1945 đến
        1975. Hãy đặt câu hỏi về các sự kiện, nhân vật, hoặc so sánh các giai
        đoạn lịch sử.
      </p>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 10,
          justifyContent: "center",
          maxWidth: 640,
        }}
      >
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSuggestionClick(s)}
            style={{
              padding: "10px 18px",
              border: "1px solid var(--hairline)",
              borderRadius: 9999,
              background: "transparent",
              fontSize: 13.5,
              color: "var(--body)",
              cursor: "pointer",
              fontFamily: "inherit",
              transition: "border-color 0.15s, background 0.15s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--coral)";
              e.currentTarget.style.background = "var(--surface-card)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--hairline)";
              e.currentTarget.style.background = "transparent";
            }}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
