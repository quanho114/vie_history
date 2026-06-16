import { useEffect } from "react";

interface ToastProps {
  message: string;
  type?: "info" | "error" | "success";
  onClose: () => void;
}

export function Toast({ message, type = "info", onClose }: ToastProps) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);

  const colors = {
    info: { bg: "var(--surface-dark)", text: "var(--on-dark)" },
    error: { bg: "#3d1515", text: "#fca5a5" },
    success: { bg: "#153d1f", text: "#86efac" },
  }[type];

  return (
    <div
      style={{
        position: "fixed",
        bottom: 24,
        left: "50%",
        transform: "translateX(-50%)",
        background: colors.bg,
        color: colors.text,
        padding: "10px 18px",
        borderRadius: 10,
        fontSize: 13.5,
        fontWeight: 500,
        display: "flex",
        alignItems: "center",
        gap: 10,
        zIndex: 1000,
        animation: "slide-up 0.2s ease",
        fontFamily: "inherit",
      }}
    >
      <i
        className={`ti ti-${
          type === "error" ? "alert-circle" : type === "success" ? "check" : "info-circle"
        }`}
        style={{ fontSize: 16 }}
      />
      {message}
      <button
        onClick={onClose}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          color: "inherit",
          padding: 2,
        }}
      >
        <i className="ti ti-x" style={{ fontSize: 14 }} />
      </button>
    </div>
  );
}
