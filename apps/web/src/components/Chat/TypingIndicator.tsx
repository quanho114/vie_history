import { memo } from "react";
import { SpikeMark } from "../UI/SpikeMark";

export const TypingIndicator = memo(function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 10, marginBottom: 24 }}>
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
        }}
      >
        <SpikeMark size={12} color="var(--coral)" />
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 4, paddingTop: 5 }}>
        {[0, 150, 300].map((delay) => (
          <span
            key={delay}
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "var(--muted)",
              display: "inline-block",
              animation: `typing-dot 1.2s ease-in-out ${delay}ms infinite`,
            }}
          />
        ))}
      </div>
    </div>
  );
});
