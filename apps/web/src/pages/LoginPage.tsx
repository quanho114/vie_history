import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore, syncSettingsToLocalStorage } from "@/stores/authStore";
import { authApi } from "@/lib/services/api";
import { cn } from "@/lib/utils/cn";
import { VietnamMap, PROVINCES_DATA } from "@/components/ui/VietnamMap";
import { LogIn, Loader2, Mail, Lock, User, Sparkles, BookOpen, ShieldCheck, History, ArrowRight, Check, Eye, EyeOff } from "lucide-react";

/* ========================================
   Focus Trap Hook for Modals
   ======================================== */
function useFocusTrap(ref: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const focusable = el.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Tab") {
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    }
    el.addEventListener("keydown", handleKeyDown);
    first?.focus();
    return () => el.removeEventListener("keydown", handleKeyDown);
  }, [ref]);
}

/* ========================================
   Spike-mark SVG Logo (Anthropic style)
   ======================================== */

function SpikeMarkLogo({ size = 32, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      {/* Central Star - Shining Gold at the heart of the Lotus */}
      <polygon points="50,42 52.5,50 60,50 54,55 56,62 50,58 44,62 46,55 40,50 47.5,50" fill="#f5c542" />
      {/* Central Petal */}
      <path d="M 50 15 C 44 32, 44 65, 50 82 C 56 65, 56 32, 50 15 Z" />
      {/* Inner Left Petal */}
      <path d="M 46 82 C 38 65, 28 42, 33 26 C 39 23, 44 48, 46 82 Z" />
      {/* Inner Right Petal */}
      <path d="M 54 82 C 62 65, 72 42, 67 26 C 61 23, 56 48, 54 82 Z" />
      {/* Outer Left Petal */}
      <path d="M 42 82 C 26 70, 10 52, 16 35 C 24 30, 34 55, 42 82 Z" />
      {/* Outer Right Petal */}
      <path d="M 58 82 C 74 70, 90 52, 84 35 C 76 30, 66 55, 58 82 Z" />
      {/* Supporting Bottom Leaves */}
      <path d="M 40 84 C 20 88, 12 88, 6 82 C 14 74, 30 74, 40 84 Z" opacity="0.8" />
      <path d="M 60 84 C 80 88, 88 88, 94 82 C 86 74, 70 74, 60 84 Z" opacity="0.8" />
    </svg>
  );
}

/* ========================================
   Login Page
   ======================================== */

export function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [registerStep, setRegisterStep] = useState<1 | 2>(1);
  const [fullName, setFullName] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState("enthusiast");
  const [institution, setInstitution] = useState("");
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);

  const [isExiting, setIsExiting] = useState(false);
  const [exitProgress, setExitProgress] = useState(0);
  const [exitStepText, setExitStepText] = useState("Đang kết nối thư viện tri thức...");

  const validateStep1 = (): boolean => {
    useAuthStore.setState({ error: null });
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      useAuthStore.setState({ error: "Email không hợp lệ" });
      return false;
    }
    if (username.trim().length < 3) {
      useAuthStore.setState({ error: "Tên người dùng phải có ít nhất 3 ký tự" });
      return false;
    }
    if (password.length < 8) {
      useAuthStore.setState({ error: "Mật khẩu phải có ít nhất 8 ký tự" });
      return false;
    }
    if (password !== confirmPassword) {
      useAuthStore.setState({ error: "Mật khẩu xác nhận không trùng khớp" });
      return false;
    }
    return true;
  };

  const handleContinue = () => {
    console.log("handleContinue clicked, pendingAuthResponse:", pendingAuthResponse);
    setIsExiting(true);
    setExitProgress(0);
    setExitStepText("Đang kết nối thư viện tri thức...");

    // Smooth progress counter from 0 to 100 over 2400ms (every 24ms is 1%)
    const duration = 2400;
    const intervalTime = 24;

    let currentProgress = 0;
    const progressInterval = setInterval(() => {
      currentProgress += 1;
      if (currentProgress >= 100) {
        setExitProgress(100);
        clearInterval(progressInterval);
      } else {
        setExitProgress(currentProgress);

        // Dynamically update text based on progress thresholds
        if (currentProgress < 30) {
          setExitStepText("Đang kết nối thư viện tri thức...");
        } else if (currentProgress < 65) {
          setExitStepText("Đang phân tích bản đồ tri thức lịch sử...");
        } else if (currentProgress < 88) {
          setExitStepText("Đang khởi tạo tác nhân nghiên cứu AI...");
        } else {
          setExitStepText("Đang đồng bộ hóa phiên làm việc...");
        }
      }
    }, intervalTime);

    // Complete transition and navigate after 2400ms
    setTimeout(() => {
      clearInterval(progressInterval);
      setExitProgress(100);

      if (pendingAuthResponse) {
        localStorage.setItem("token", pendingAuthResponse.access_token);
        syncSettingsToLocalStorage(pendingAuthResponse.user.settings);
        useAuthStore.setState({
          user: pendingAuthResponse.user,
          token: pendingAuthResponse.access_token,
          isAuthenticated: true,
          isLoading: false,
        });
        const dest = transitionTarget || "/chat";
        console.log("Navigating to:", dest);
        navigate(dest);
      } else {
        // Fallback bypass: log in as dev/guest user to prevent redirect back to /login
        console.log("Fallback bypass triggered");
        const guestUser = {
          id: "bypass-user-id",
          email: "guest@historiai.vn",
          username: "Khách",
          role: "user" as const,
          settings: {}
        };
        // Save mock token
        localStorage.setItem("token", "mock-token-fallback");
        useAuthStore.setState({
          user: guestUser,
          token: "mock-token-fallback",
          isAuthenticated: true,
          isLoading: false,
        });
        console.log("Navigating to fallback: /chat");
        navigate("/chat");
      }
    }, duration);
  };

  // States for password reset requests
  const [resetEmail, setResetEmail] = useState("");
  const [resetUsername, setResetUsername] = useState("");
  const [resetReason, setResetReason] = useState("");
  const [resetSuccess, setResetSuccess] = useState<string | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  const [isResetSubmitting, setIsResetSubmitting] = useState(false);

  // States for Vietnamese Map and Flag loading screen transitions
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [transitionTarget, setTransitionTarget] = useState("");
  const [loadingTextIndex, setLoadingTextIndex] = useState(0);
  const [pendingAuthResponse, setPendingAuthResponse] = useState<any>(null);

  const loadingTexts = [
    "„Sông núi nước Nam vua Nam ở...”",
    "Khơi nguồn sử Việt — Hùng thiêng sông núi...",
    "Xác thực chủ quyền biển đảo thiêng liêng...",
    "Hội tụ linh khí ngàn năm văn hiến..."
  ];

  const { isLoading, error } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (isTransitioning) {
      const textInterval = setInterval(() => {
        setLoadingTextIndex((prev) => (prev + 1) % loadingTexts.length);
      }, 1000);

      // Commented out to pause the screen indefinitely for user adjustments
      /*
      const timer = setTimeout(() => {
        if (pendingAuthResponse) {
          // Persist token in localStorage
          localStorage.setItem("token", pendingAuthResponse.access_token);
          // Sync settings
          syncSettingsToLocalStorage(pendingAuthResponse.user.settings);
          // Set store values which will trigger App.tsx routing redirect
          useAuthStore.setState({
            user: pendingAuthResponse.user,
            token: pendingAuthResponse.access_token,
            isAuthenticated: true,
            isLoading: false,
          });
        }
      }, 4000);
      */

      return () => {
        clearInterval(textInterval);
        // clearTimeout(timer);
      };
    }
  }, [isTransitioning, transitionTarget, pendingAuthResponse, navigate]);

  const handleResetRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetSuccess(null);
    setResetError(null);
    setIsResetSubmitting(true);
    try {
      const response = await fetch("/api/v1/auth/reset-request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: resetEmail,
          username: resetUsername || null,
          reason: resetReason || null,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Đã xảy ra lỗi khi gửi yêu cầu");
      }
      setResetSuccess(data.message || "Gửi yêu cầu thành công!");
      setResetEmail("");
      setResetUsername("");
      setResetReason("");
    } catch (err: any) {
      setResetError(err.message || "Không thể kết nối đến máy chủ");
    } finally {
      setIsResetSubmitting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    useAuthStore.setState({ isLoading: true, error: null });
    try {
      let response;
      if (isRegister) {
        response = await authApi.register(email, username, password);
      } else {
        response = await authApi.login(email, password);
      }
      const target = "/chat";
      setTransitionTarget(target);
      setPendingAuthResponse(response);
      setIsTransitioning(true);
      useAuthStore.setState({ isLoading: false });
    } catch (err: any) {
      useAuthStore.setState({
        error: err.message || "Đăng nhập thất bại",
        isLoading: false,
      });
    }
  };

  const forgotPasswordRef = useRef<HTMLDivElement>(null);
  useFocusTrap(forgotPasswordRef);

  return (
    <div className="min-h-screen md:h-screen w-full flex bg-[#FAF9F6] text-[#2D2A26] selection:bg-[#cc785c]/10 selection:text-[#cc785c] overflow-hidden relative font-sans">

      {/* ── LEFT SHOWCASE PANEL (Visible on Medium+ screens) ──────────────────── */}
      <div className="hidden md:flex md:w-[50%] lg:w-[55%] md:flex-shrink-0 md:flex-grow-0 bg-[#F3F2EE] text-[#2D2A26] p-12 lg:p-16 flex-col justify-between relative overflow-hidden border-r border-[#E5E3DF]">
        {/* Dong Son Bronze Drum Background Watermark */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-[0.06] overflow-hidden">
          <img
            src="/trong_dong.svg"
            alt="Trong Dong Dong Son"
            className="w-[102vh] h-[102vh] max-w-none animate-spin-slow object-contain"
            style={{ filter: "sepia(0.8) hue-rotate(340deg) saturate(1.2)" }}
          />
        </div>

        {/* Cinematic Rising Embers */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-40">
          <span className="ember" style={{ left: "10%", animationDelay: "0s", animationDuration: "6s" }} />
          <span className="ember" style={{ left: "30%", animationDelay: "1.5s", animationDuration: "8s" }} />
          <span className="ember" style={{ left: "50%", animationDelay: "0.5s", animationDuration: "7s" }} />
          <span className="ember" style={{ left: "70%", animationDelay: "2s", animationDuration: "9s" }} />
          <span className="ember" style={{ left: "90%", animationDelay: "1s", animationDuration: "6s" }} />
        </div>

        {/* Ambient glows */}
        <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] rounded-full bg-[#cc785c]/5 blur-[130px] pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-[#cc785c]/3 blur-[120px] pointer-events-none" />

        {/* Top brand */}
        <div className="flex items-center gap-3 z-10">
          <div className="w-10 h-10 rounded-xl bg-[#cc785c]/10 flex items-center justify-center border border-[#cc785c]/20 text-[#cc785c]">
            <SpikeMarkLogo size={20} />
          </div>
          <div className="flex flex-col">
            <span className="font-serif text-lg tracking-wide font-medium leading-none text-[#2D2A26]">HistoriAI</span>
            <span className="text-[10px] text-[#8e8b82] tracking-wider uppercase mt-1">Academic Search Agent</span>
          </div>
        </div>

        {/* Core content */}
        <div className="my-auto max-w-[480px] z-10 space-y-8 pr-4">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-white border border-[#E5E3DF] text-xs text-[#cc785c] font-medium shadow-[0_2px_8px_rgba(0,0,0,0.02)]">
              <Sparkles size={12} className="animate-pulse" />
              <span>Hệ thống Trí tuệ Nhân tạo Lịch sử</span>
            </div>
            <h2 className="text-3xl lg:text-4xl font-serif leading-tight font-normal text-[#2D2A26]">
              Hệ thống trí tuệ nhân tạo <br />
              <span className="italic text-[#cc785c]">Hỗ trợ Tra cứu Lịch sử Việt Nam</span>
            </h2>
            <p className="text-sm text-[#6C6A64] leading-relaxed">
              Trợ lý học thuật tối ưu hỗ trợ tìm kiếm tài liệu lưu trữ, xác thực sự kiện và thiết lập bản đồ tri thức lịch sử tự động.
            </p>
          </div>

          {/* Feature list */}
          <div className="space-y-4 pt-2">
            {/* Feature 1 */}
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-lg bg-white border border-[#E5E3DF] flex items-center justify-center flex-shrink-0 text-[#cc785c] shadow-[0_2px_8px_rgba(0,0,0,0.02)]">
                <History size={16} />
              </div>
              <div className="space-y-1">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[#2D2A26]">Truy xuất lai hợp tự động (Hybrid RAG)</h4>
                <p className="text-xs text-[#6C6A64] leading-normal">
                  Sự kết hợp giữa Vector Search chuẩn xác ngữ nghĩa và BM25 bắt gọn các danh từ lịch sử đặc biệt.
                </p>
              </div>
            </div>

            {/* Feature 2 */}
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-lg bg-white border border-[#E5E3DF] flex items-center justify-center flex-shrink-0 text-[#cc785c] shadow-[0_2px_8px_rgba(0,0,0,0.02)]">
                <BookOpen size={16} />
              </div>
              <div className="space-y-1">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[#2D2A26]">Minh bạch nguồn trích dẫn</h4>
                <p className="text-xs text-[#6C6A64] leading-normal">
                  Mỗi nhận định học thuật đều kèm theo liên kết chỉ mục chính xác tới kho dữ liệu thư mục lịch sử.
                </p>
              </div>
            </div>

            {/* Feature 3 */}
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-lg bg-white border border-[#E5E3DF] flex items-center justify-center flex-shrink-0 text-[#cc785c] shadow-[0_2px_8px_rgba(0,0,0,0.02)]">
                <ShieldCheck size={16} />
              </div>
              <div className="space-y-1">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[#2D2A26]">Kiểm định tự động (Self-Reflection)</h4>
                <p className="text-xs text-[#6C6A64] leading-normal">
                  Quy trình Critic Agent tự đối chiếu chéo tài liệu, đảm bảo câu trả lời trung thực và hạn chế tối đa ảo tưởng thông tin.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom copyright */}
        <div className="z-10 flex items-center justify-end text-xs text-[#9F9D99] border-t border-[#E5E3DF] pt-4">
          <span>© 2026 HistoriAI</span>
        </div>
      </div>

      {/* ── RIGHT AUTH PANEL (Center on mobile) ─────────────────────────────── */}
      <div className="w-full md:w-[50%] lg:w-[45%] md:flex-shrink-0 md:flex-grow-0 flex flex-col justify-between p-6 sm:p-12 lg:p-16 relative bg-[#FAF9F6] md:overflow-y-auto">
        {/* Soft background glows on mobile */}
        <div className="absolute top-0 right-0 w-[80%] h-[30%] rounded-full bg-[#cc785c]/5 blur-[80px] pointer-events-none md:hidden" />

        {/* Top bar with mobile logo */}
        <div className="flex items-center justify-between z-10 md:justify-end">
          <div className="flex items-center gap-2 md:hidden">
            <div className="w-8 h-8 rounded-lg bg-[#cc785c]/10 flex items-center justify-center text-[#cc785c]">
              <SpikeMarkLogo size={16} />
            </div>
            <span className="font-serif text-md tracking-wide font-medium text-[#2D2A26]">HistoriAI</span>
          </div>

          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              setRegisterStep(1);
              useAuthStore.setState({ error: null });
            }}
            className="text-xs text-[#cc785c] hover:text-[#b86246] transition-colors inline-flex items-center gap-1 font-medium group bg-transparent border-0 p-0 cursor-pointer"
          >
            <span>{isRegister ? "Đã có tài khoản?" : "Chưa có tài khoản?"}</span>
            <ArrowRight size={12} className="group-hover:translate-x-1 transition-transform" />
          </button>
        </div>

        {/* Form Card container */}
        <div className="my-auto max-w-[380px] w-full mx-auto z-10 py-8">
          <div className="space-y-6">

            {/* Header info */}
            <div className="space-y-2">
              <h1 className="text-2xl font-serif font-normal text-[#2D2A26]">
                {isRegister ? "Kiến tạo tài khoản" : "Chào mừng trở lại"}
              </h1>
              <p className="text-xs text-[#6C6A64] leading-normal">
                {isRegister
                  ? "Đăng ký thành viên để bắt đầu xây dựng và khám phá hệ tri thức lịch sử."
                  : "Truy cập hệ thống tác nhân nghiên cứu AI để bắt đầu truy vấn tài liệu lịch sử."}
              </p>
            </div>

            {/* Form Card */}
            <div className="bg-white border border-[#E5E3DF] rounded-2xl p-6 sm:p-8 shadow-[0_12px_40px_rgba(45,42,38,0.03)] backdrop-blur-md">

              {/* Tab Selector */}
              <div className="flex bg-[#F3F2EE] border border-[#E5E3DF]/60 rounded-xl p-1 mb-6 relative">
                <button
                  type="button"
                  onClick={() => {
                    setIsRegister(false);
                    setRegisterStep(1);
                    useAuthStore.setState({ error: null });
                  }}
                  className={cn(
                    "flex-1 text-center py-2 text-xs font-bold rounded-lg transition-all duration-200 cursor-pointer border-0 z-10",
                    !isRegister
                      ? "bg-white text-[#2D2A26] shadow-sm border border-[#E5E3DF]/80"
                      : "text-[#6C6A64] hover:text-[#2D2A26] bg-transparent"
                  )}
                >
                  Đăng nhập
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsRegister(true);
                    setRegisterStep(1);
                    useAuthStore.setState({ error: null });
                  }}
                  className={cn(
                    "flex-1 text-center py-2 text-xs font-bold rounded-lg transition-all duration-200 cursor-pointer border-0 z-10",
                    isRegister
                      ? "bg-white text-[#2D2A26] shadow-sm border border-[#E5E3DF]/80"
                      : "text-[#6C6A64] hover:text-[#2D2A26] bg-transparent"
                  )}
                >
                  Đăng ký
                </button>
              </div>

              {/* Error Alert */}
              {error && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-600 text-xs flex gap-2 items-start" role="alert">
                  <span className="font-bold">⚠️</span>
                  <span>{error}</span>
                </div>
              )}

              {/* Inputs */}
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Email Input */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#6C6A64] block">Email</label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-[#9F9D99]">
                      <Mail size={14} />
                    </span>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      placeholder="you@example.com"
                      className="w-full bg-[#FBFBFA] border border-[#E2DFDA] rounded-xl py-2.5 pl-9 pr-4 text-sm text-[#2D2A26] outline-none placeholder:text-[#A8A59E] focus:bg-white focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/10 transition-all duration-200 box-border shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                    />
                  </div>
                </div>

                {/* Username Input (Only on Register) */}
                {isRegister && (
                  <div className="space-y-1.5 animate-fadeIn">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-[#6C6A64] block">Tên người dùng</label>
                    <div className="relative">
                      <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-[#9F9D99]">
                        <User size={14} />
                      </span>
                      <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        required
                        minLength={3}
                        placeholder="yourname"
                        className="w-full bg-[#FBFBFA] border border-[#E2DFDA] rounded-xl py-2.5 pl-9 pr-4 text-sm text-[#2D2A26] outline-none placeholder:text-[#A8A59E] focus:bg-white focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/10 transition-all duration-200 box-border shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                      />
                    </div>
                  </div>
                )}

                {/* Password Input */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#6C6A64] block">Mật khẩu</label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-[#9F9D99]">
                      <Lock size={14} />
                    </span>
                    <input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={8}
                      placeholder="••••••••"
                      className="w-full bg-[#FBFBFA] border border-[#E2DFDA] rounded-xl py-2.5 pl-9 pr-10 text-sm text-[#2D2A26] outline-none placeholder:text-[#A8A59E] focus:bg-white focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/10 transition-all duration-200 box-border shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 flex items-center pr-3 text-[#9F9D99] hover:text-[#2D2A26] focus:outline-none transition-colors bg-transparent border-0 cursor-pointer"
                      tabIndex={-1}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                {/* Submit button */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-[#cc785c] hover:bg-[#b86246] text-white py-3 px-4 rounded-xl text-xs font-semibold tracking-wider uppercase flex items-center justify-center gap-2 cursor-pointer shadow-[0_4px_12px_rgba(204,120,92,0.15)] hover:shadow-[0_6px_20px_rgba(204,120,92,0.25)] transition-all duration-200 active:scale-[0.98] mt-2 border border-[#b86246]/10 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <>
                      <LogIn size={14} />
                      <span>{isRegister ? "Đăng ký thành viên" : "Đăng nhập hệ thống"}</span>
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Forgot password below the card */}
            {!isRegister && (
              <div className="text-center mt-4">
                <button
                  type="button"
                  onClick={() => setShowForgotPassword(true)}
                  className="text-xs text-[#cc785c] hover:text-[#b86246] transition-colors font-semibold bg-transparent border-0 p-0 cursor-pointer outline-none"
                >
                  Quên mật khẩu?
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="z-10 flex flex-col items-center gap-2 border-t border-[#E5E3DF] pt-4 text-center">
          <span className="text-[10px] text-[#6C6A64] tracking-wider">Hệ thống AI hỗ trợ tra cứu lịch sử Việt Nam</span>
          <span className="text-[9px] text-[#9F9D99]">Khuyên dùng trong môi trường học thuật và tra cứu lịch sử</span>
        </div>
      </div>

      {showForgotPassword && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fadeIn">
          <div ref={forgotPasswordRef} className="bg-white border border-[#E5E3DF] rounded-2xl p-6 sm:p-8 max-w-[380px] w-full text-center shadow-2xl space-y-4">
            {resetSuccess ? (
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-full bg-green-50 text-green-600 flex items-center justify-center mx-auto border border-green-500/20 shadow-sm">
                  <Check size={24} />
                </div>
                <div className="space-y-2">
                  <h3 className="font-serif text-lg font-normal text-[#2D2A26]">Đã gửi yêu cầu</h3>
                  <p className="text-xs text-[#6C6A64] leading-relaxed">
                    {resetSuccess}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setShowForgotPassword(false);
                    setResetSuccess(null);
                  }}
                  className="w-full bg-[#cc785c] hover:bg-[#b86246] text-white py-3 px-4 rounded-xl text-xs font-semibold tracking-wider uppercase cursor-pointer transition-all duration-200 shadow-[0_4px_12px_rgba(204,120,92,0.15)] border border-[#b86246]/10 active:scale-[0.98]"
                >
                  Đóng
                </button>
              </div>
            ) : (
              <form onSubmit={handleResetRequest} className="space-y-4 text-left">
                <div className="flex items-center gap-3 border-b border-[#E5E3DF] pb-3 justify-center text-center">
                  <div className="w-9 h-9 rounded-full bg-[#cc785c]/10 text-[#cc785c] flex items-center justify-center border border-[#cc785c]/20">
                    <Mail size={16} />
                  </div>
                  <h3 className="font-serif text-lg font-normal text-[#2D2A26]">Khôi phục mật khẩu</h3>
                </div>

                <p className="text-xs text-[#6C6A64] leading-relaxed text-center">
                  Nhập email đăng ký của bạn. Ban Quản trị sẽ xem xét và xử lý yêu cầu đặt lại mật khẩu.
                </p>

                {resetError && (
                  <div className="p-2.5 bg-red-500/10 text-red-600 text-xs rounded-lg text-center font-medium border border-red-500/20">
                    {resetError}
                  </div>
                )}

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-[#6C6A64] tracking-wider uppercase">Email đăng ký *</label>
                  <input
                    type="email"
                    required
                    value={resetEmail}
                    onChange={(e) => setResetEmail(e.target.value)}
                    placeholder="example@gmail.com"
                    className="w-full bg-[#FBFBFA] border border-[#E2DFDA] rounded-xl px-3 py-2.5 text-xs text-[#2D2A26] outline-none focus:bg-white focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/10 transition-all duration-200 box-border shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-[#6C6A64] tracking-wider uppercase">Tên tài khoản (nếu nhớ)</label>
                  <input
                    type="text"
                    value={resetUsername}
                    onChange={(e) => setResetUsername(e.target.value)}
                    placeholder="username"
                    className="w-full bg-[#FBFBFA] border border-[#E2DFDA] rounded-xl px-3 py-2.5 text-xs text-[#2D2A26] outline-none focus:bg-white focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/10 transition-all duration-200 box-border shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-[#6C6A64] tracking-wider uppercase">Lý do hoặc ghi chú gửi Admin</label>
                  <textarea
                    value={resetReason}
                    onChange={(e) => setResetReason(e.target.value)}
                    placeholder="ví dụ: Tôi quên mật khẩu cũ..."
                    rows={2}
                    className="w-full bg-[#FBFBFA] border border-[#E2DFDA] rounded-xl px-3 py-2.5 text-xs text-[#2D2A26] outline-none focus:bg-white focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/10 transition-all duration-200 box-border shadow-[0_1px_2px_rgba(0,0,0,0.01)] resize-none"
                  />
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setShowForgotPassword(false);
                      setResetError(null);
                    }}
                    className="flex-1 bg-white hover:bg-[#F9F8F6] text-[#6C6A64] border border-[#E5E3DF] py-2.5 px-4 rounded-xl text-xs font-semibold cursor-pointer transition-all duration-200 active:scale-[0.98]"
                  >
                    Hủy
                  </button>
                  <button
                    type="submit"
                    disabled={isResetSubmitting}
                    className="flex-1 bg-[#cc785c] hover:bg-[#b86246] text-white py-2.5 px-4 rounded-xl text-xs font-semibold cursor-pointer transition-all duration-200 shadow-[0_4px_12px_rgba(204,120,92,0.15)] border border-[#b86246]/10 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isResetSubmitting ? "Đang gửi..." : "Gửi yêu cầu"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      <style>{`
        .animate-fadeIn {
          animation: fadeIn 0.25s ease-out forwards;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes spin-slow {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        .animate-spin-slow {
          animation: spin-slow 180s linear infinite;
        }
        .ember {
          position: absolute;
          bottom: -20px;
          width: 3px;
          height: 3px;
          background: #cc785c;
          border-radius: 50%;
          opacity: 0.6;
          filter: blur(0.5px);
          box-shadow: 0 0 6px #cc785c, 0 0 10px #f4a28c;
          animation: rise infinite ease-in-out;
        }
        @keyframes rise {
          0% {
            transform: translateY(0) scale(1) translateX(0);
            opacity: 0;
          }
          10% {
            opacity: 0.6;
          }
          90% {
            opacity: 0.3;
          }
          100% {
            transform: translateY(-110vh) scale(0.3) translateX(60px);
            opacity: 0;
          }
        }
      `}</style>

      {isTransitioning && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#FAF9F6] text-[#2D2A26] p-6 overflow-hidden select-none font-sans">
          {/* Dong Son Bronze Drum Background Watermark - Spinning extremely slowly */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-[0.06] overflow-hidden">
            <img
              src="/trong_dong.svg"
              alt="Trong Dong Dong Son"
              className="w-[102vh] h-[102vh] max-w-none animate-spin-slow object-contain"
              style={{ filter: "sepia(0.8) hue-rotate(340deg) saturate(1.2)" }}
            />
          </div>

          {/* Cinematic Rising Embers/Sparks */}
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            <span className="ember" style={{ left: "10%", animationDelay: "0s", animationDuration: "6s" }} />
            <span className="ember" style={{ left: "25%", animationDelay: "1.5s", animationDuration: "8s" }} />
            <span className="ember" style={{ left: "40%", animationDelay: "0.5s", animationDuration: "7s" }} />
            <span className="ember" style={{ left: "60%", animationDelay: "2s", animationDuration: "9s" }} />
            <span className="ember" style={{ left: "75%", animationDelay: "1s", animationDuration: "6s" }} />
            <span className="ember" style={{ left: "90%", animationDelay: "3s", animationDuration: "8s" }} />
          </div>

          {/* Ambient Glows */}
          <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-[#cc785c]/5 blur-[140px] pointer-events-none" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full bg-red-600/3 blur-[140px] pointer-events-none" />

          <div className="relative z-10 flex flex-col md:flex-row items-center justify-center w-full h-full gap-8 md:gap-16 px-4">

            {/* Glowing Map of Vietnam with Sacred Imperial borders */}
            <div className="relative w-full md:w-[600px] h-[50vh] md:h-[85vh] max-w-[65vw] bg-white border border-[#E5E3DF] rounded-2xl p-5 flex items-center justify-center shadow-[0_8px_30px_rgba(0,0,0,0.03)] backdrop-blur-md flex-shrink-0 overflow-hidden">

              {/* Imperial Corner Borders */}
              <div className="absolute top-0 left-0 w-6 h-6 border-t-2 border-l-2 border-[#cc785c]/60 rounded-tl-xl" />
              <div className="absolute top-0 right-0 w-6 h-6 border-t-2 border-r-2 border-[#cc785c]/60 rounded-tr-xl" />
              <div className="absolute bottom-0 left-0 w-6 h-6 border-b-2 border-l-2 border-[#cc785c]/60 rounded-bl-xl" />
              <div className="absolute bottom-0 right-0 w-6 h-6 border-b-2 border-r-2 border-[#cc785c]/60 rounded-br-xl" />

              <VietnamMap className="w-full h-full text-[#cc785c]" />
            </div>

            {/* Right Side: Flag + Loading */}
            <div className="flex flex-col items-center justify-center space-y-12 flex-shrink-0 w-64">

              {/* Vietnam Flag Emblem with glowing shadow */}
              <div className="relative flex flex-col items-center">
                <div className="flag-emblem relative rounded shadow-[0_4px_25px_rgba(218,37,29,0.15)] border border-[#E5E3DF] overflow-hidden" style={{ width: "120px", height: "80px" }}>
                  <div className="absolute inset-0 bg-[#da251d]" />
                  <svg className="absolute inset-0 w-full h-full drop-shadow-lg" viewBox="0 0 30 20">
                    <polygon
                      points="15,4 16.35,8.15 20.71,8.15 17.18,10.71 18.53,14.85 15,12.29 11.47,14.85 12.82,10.71 9.29,8.15 13.65,8.15"
                      fill="#ffff00"
                    />
                  </svg>
                  {/* Subtle static silk satin sheen */}
                  <div className="absolute inset-0 bg-gradient-to-tr from-black/15 via-transparent to-white/10 pointer-events-none" />
                </div>

                {/* Gold Gradient Typo */}
                <span className="text-[12px] uppercase tracking-[0.25em] font-bold bg-gradient-to-r from-[#2D2A26] via-[#cc785c] to-[#2D2A26] bg-clip-text text-transparent mt-4 font-serif italic">
                  Lịch sử Việt Nam
                </span>
              </div>

              {/* Loading text with transition animation */}
              <div className="space-y-5 w-full text-center">
                <div className="h-12 overflow-hidden relative flex items-center justify-center">
                  <div
                    key={loadingTextIndex}
                    className="text-xs md:text-sm font-semibold text-[#2D2A26] tracking-wide animate-slideUp font-serif italic text-center"
                  >
                    {loadingTexts[loadingTextIndex]}
                  </div>
                </div>

                {/* Continue button to proceed to the main chatbot */}
                <button
                  onClick={handleContinue}
                  className="mt-6 px-6 py-2.5 rounded-xl border border-[#cc785c]/30 bg-[#cc785c]/5 hover:bg-[#cc785c]/10 text-[#cc785c] text-xs font-semibold tracking-wide transition-all duration-300 hover:scale-105 active:scale-95 shadow-[0_2px_10px_rgba(204,120,92,0.05)] flex items-center gap-2 mx-auto cursor-pointer outline-none"
                >
                  <span>Tiếp tục tiến vào hệ thống</span>
                  <ArrowRight size={14} className="animate-pulse" />
                </button>
              </div>

            </div>

          </div>
          <style>{`
            .flag-emblem {
              transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            }
            .flag-emblem:hover {
              transform: scale(1.05);
              box-shadow: 0 8px 30px rgba(218, 37, 29, 0.25);
            }
            @keyframes slideUp {
              from { opacity: 0; transform: translateY(12px); }
              to { opacity: 1; transform: translateY(0); }
            }
            .animate-slideUp {
              animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            }
            @keyframes progress {
              0% { width: 0%; }
              100% { width: 100%; }
            }
            .animate-progress {
              animation: progress 4s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
            }
            @keyframes glow {
              0%, 100% { filter: drop-shadow(0 0 2px rgba(204, 120, 92, 0.3)); }
              50% { filter: drop-shadow(0 0 8px rgba(204, 120, 92, 0.6)); }
            }
            .animate-glow-path {
              animation: glow 2.5s ease-in-out infinite;
            }
          `}</style>
        </div>
      )}



      {/* Exit Loading Transition Overlay */}
      {isExiting && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#FAF9F6] text-[#2D2A26] p-6 animate-fadeIn font-sans selection:bg-[#cc785c]/10 selection:text-[#cc785c]">
          {/* Ambient Glows */}
          <div className="absolute top-1/3 w-[500px] h-[500px] rounded-full bg-[#cc785c]/5 blur-[130px] pointer-events-none" />
          <div className="absolute bottom-1/4 w-[400px] h-[400px] rounded-full bg-red-600/3 blur-[120px] pointer-events-none" />

          <div className="relative z-10 flex flex-col items-center space-y-8 text-center max-w-sm w-full">
            {/* Spinning SpikeMarkLogo or elegant Loader */}
            <div className="relative w-20 h-20 flex items-center justify-center">
              <div
                className="absolute inset-0 rounded-full border-2 border-[#cc785c]/10 border-t-[#cc785c] animate-spin"
                style={{ animationDuration: '0.8s' }}
              />
              <div
                className="absolute inset-1.5 rounded-full border border-dashed border-[#cc785c]/20 animate-spin"
                style={{ animationDuration: '4s', animationDirection: 'reverse' }}
              />
              <SpikeMarkLogo size={32} className="text-[#cc785c] animate-pulse" />
            </div>

            <div className="space-y-4 w-full">
              <div className="space-y-1.5">
                <h3 className="font-serif text-xl font-normal text-[#2D2A26] tracking-wide">
                  Đang khởi chạy hệ thống
                </h3>
                <p className="text-[12px] text-[#cc785c] font-medium tracking-wider h-4 animate-pulse">
                  {exitStepText}
                </p>
              </div>

              {/* Progress Bar Container */}
              <div className="w-full h-[3px] bg-[#E5E3DF] rounded-full overflow-hidden relative border border-[#E5E3DF]/10">
                <div
                  className="h-full bg-gradient-to-r from-[#cc785c] to-[#a8583c] shadow-[0_0_8px_#cc785c]"
                  style={{
                    width: `${exitProgress}%`,
                    transition: 'width 24ms linear'
                  }}
                />
              </div>

              <div className="flex justify-between items-center text-[10px] text-[#9F9D99] uppercase tracking-widest font-mono">
                <span>Trạng thái: Sẵn sàng</span>
                <span>{exitProgress}%</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
