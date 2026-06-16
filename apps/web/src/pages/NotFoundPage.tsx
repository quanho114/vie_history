import { useNavigate } from "react-router-dom"
import { useAuthStore } from "@/stores/authStore"

export function NotFoundPage() {
  const navigate = useNavigate()
  const { isAuthenticated, user } = useAuthStore()

  const handleGoHome = () => {
    if (!isAuthenticated) {
      navigate("/login", { replace: true })
    } else {
      navigate(user?.role === "admin" ? "/admin" : "/chat", { replace: true })
    }
  }

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-center bg-[#faf8f4] text-[#141413] relative overflow-hidden">
      {/* Background decoration */}
      <div
        className="absolute inset-0 opacity-[0.025] pointer-events-none"
        style={{
          backgroundImage: "radial-gradient(#cc785c 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
      />
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-[#cc785c] to-transparent opacity-60" />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center text-center px-6 max-w-lg">

        {/* Seal / Logo */}
        <div className="w-20 h-20 rounded-2xl bg-[#f5f0e8] border border-[#e6dfd8] flex items-center justify-center mb-8 shadow-sm">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#cc785c" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>

        {/* 404 number */}
        <div className="relative mb-4">
          <span
            className="text-[120px] font-black leading-none select-none"
            style={{
              background: "linear-gradient(135deg, #e6dfd8 0%, #cc785c 40%, #b86246 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
              fontFamily: "Georgia, serif",
            }}
          >
            404
          </span>
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div
              className="w-full h-full rounded-full opacity-10 blur-3xl"
              style={{ background: "radial-gradient(circle, #cc785c 0%, transparent 70%)" }}
            />
          </div>
        </div>

        {/* Divider */}
        <div className="flex items-center gap-3 mb-6 w-full max-w-xs">
          <div className="flex-1 h-px bg-gradient-to-r from-transparent to-[#e6dfd8]" />
          <span className="text-[#cc785c] text-lg">✦</span>
          <div className="flex-1 h-px bg-gradient-to-l from-transparent to-[#e6dfd8]" />
        </div>

        {/* Message */}
        <h1 className="text-2xl font-semibold text-[#141413] mb-3" style={{ fontFamily: "Georgia, serif" }}>
          Trang không tồn tại
        </h1>
        <p className="text-[#6c6a64] text-sm leading-relaxed mb-8">
          Trang bạn đang tìm kiếm không có trong hệ thống lưu trữ lịch sử này.
          Có thể đường dẫn đã thay đổi hoặc không bao giờ tồn tại.
        </p>

        {/* Action buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <button
            onClick={handleGoHome}
            className="px-6 py-2.5 rounded-xl bg-[#cc785c] hover:bg-[#b86246] text-white text-sm font-semibold transition-all duration-200 hover:scale-105 active:scale-95 shadow-sm hover:shadow-md flex items-center gap-2"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            Về trang chủ
          </button>
          <button
            onClick={() => navigate(-1)}
            className="px-6 py-2.5 rounded-xl border border-[#e6dfd8] bg-white hover:bg-[#f5f0e8] text-[#3d3d3a] text-sm font-medium transition-all duration-200 flex items-center gap-2"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            Quay lại
          </button>
        </div>

        {/* Footer note */}
        <p className="mt-12 text-[11px] text-[#8e8b82] tracking-wider uppercase">
          HistoriAI · Lịch sử Việt Nam
        </p>
      </div>
    </div>
  )
}
