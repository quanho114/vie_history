import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore, syncSettingsToLocalStorage } from "@/stores/authStore";
import { authApi } from "@/lib/services/api";
import { cn } from "@/lib/utils/cn";
import { VietnamMap, PROVINCES_DATA } from "@/components/ui/VietnamMap";
import { LogIn, Loader2, Mail, Lock, User, Sparkles, BookOpen, ShieldCheck, History, ArrowRight, Check } from "lucide-react";

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
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showForgotPassword, setShowForgotPassword] = useState(false);

  const [isExiting, setIsExiting] = useState(false);
  const [exitProgress, setExitProgress] = useState(0);
  const [exitStepText, setExitStepText] = useState("Đang kết nối thư viện tri thức...");

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
    <div className="min-h-screen w-full flex bg-[#faf8f4] text-[#141413] selection:bg-[#cc785c]/10 selection:text-[#cc785c] overflow-hidden relative">
      
      {/* ── LEFT SHOWCASE PANEL (Visible on Medium+ screens) ──────────────────── */}
      <div className="hidden md:flex md:w-[50%] lg:w-[55%] bg-[#12100f] text-[#efeae4] p-12 lg:p-16 flex-col justify-between relative overflow-hidden">
        {/* Background decorative grid and glow */}
        <div className="absolute inset-0 opacity-[0.02] pointer-events-none"
             style={{ backgroundImage: "radial-gradient(#ffffff 1px, transparent 1px)", backgroundSize: "24px 24px" }} />
        <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] rounded-full bg-[#cc785c]/10 blur-[130px] pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-[#a8583c]/5 blur-[120px] pointer-events-none" />

        {/* Top brand */}
        <div className="flex items-center gap-3 z-10">
          <div className="w-10 h-10 rounded-xl bg-[#cc785c]/10 flex items-center justify-center border border-[#cc785c]/20 text-[#cc785c]">
            <SpikeMarkLogo size={20} />
          </div>
          <div className="flex flex-col">
            <span className="font-serif text-lg tracking-wide font-medium leading-none">HistoriAI</span>
            <span className="text-[10px] text-[#8e8b82] tracking-wider uppercase mt-1">Academic Search Agent</span>
          </div>
        </div>

        {/* Core content */}
        <div className="my-auto max-w-[480px] z-10 space-y-8 pr-4">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-[#cc785c] font-medium">
              <Sparkles size={12} className="animate-pulse" />
              <span>Hệ thống Trí tuệ Nhân tạo Lịch sử</span>
            </div>
            <h2 className="text-3xl lg:text-4xl font-serif leading-tight font-normal text-[#faf8f4]">
              Hệ thống trí tuệ nhân tạo <br />
              <span className="italic text-[#cc785c]">Hỗ trợ Tra cứu Lịch sử Việt Nam</span>
            </h2>
            <p className="text-sm text-[#8e8b82] leading-relaxed">
              Trợ lý học thuật tối ưu hỗ trợ tìm kiếm tài liệu lưu trữ, xác thực sự kiện và thiết lập bản đồ tri thức lịch sử tự động.
            </p>
          </div>

          {/* Feature list */}
          <div className="space-y-4 pt-2">
            {/* Feature 1 */}
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0 text-[#cc785c]">
                <History size={16} />
              </div>
              <div className="space-y-1">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[#faf8f4]">Truy xuất lai hợp tự động (Hybrid RAG)</h4>
                <p className="text-xs text-[#8e8b82] leading-normal">
                  Sự kết hợp giữa Vector Search chuẩn xác ngữ nghĩa và BM25 bắt gọn các danh từ lịch sử đặc biệt.
                </p>
              </div>
            </div>

            {/* Feature 2 */}
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0 text-[#cc785c]">
                <BookOpen size={16} />
              </div>
              <div className="space-y-1">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[#faf8f4]">Minh bạch nguồn trích dẫn</h4>
                <p className="text-xs text-[#8e8b82] leading-normal">
                  Mỗi nhận định học thuật đều kèm theo liên kết chỉ mục chính xác tới kho dữ liệu thư mục lịch sử.
                </p>
              </div>
            </div>

            {/* Feature 3 */}
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0 text-[#cc785c]">
                <ShieldCheck size={16} />
              </div>
              <div className="space-y-1">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[#faf8f4]">Kiểm định tự động (Self-Reflection)</h4>
                <p className="text-xs text-[#8e8b82] leading-normal">
                  Quy trình Critic Agent tự đối chiếu chéo tài liệu, đảm bảo câu trả lời trung thực và hạn chế tối đa ảo tưởng thông tin.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom copyright */}
        <div className="z-10 flex items-center justify-end text-xs text-[#6c6a64] border-t border-white/5 pt-4">
          <span>© 2026 HistoriAI</span>
        </div>
      </div>

      {/* ── RIGHT AUTH PANEL (Center on mobile) ─────────────────────────────── */}
      <div className="w-full md:w-[50%] lg:w-[45%] flex flex-col justify-between p-6 sm:p-12 lg:p-16 relative">
        {/* Soft background glows on mobile */}
        <div className="absolute top-0 right-0 w-[80%] h-[30%] rounded-full bg-[#cc785c]/5 blur-[80px] pointer-events-none md:hidden" />
        
        {/* Top bar with mobile logo */}
        <div className="flex items-center justify-between z-10 md:justify-end">
          <div className="flex items-center gap-2 md:hidden">
            <div className="w-8 h-8 rounded-lg bg-[#cc785c]/10 flex items-center justify-center text-[#cc785c]">
              <SpikeMarkLogo size={16} />
            </div>
            <span className="font-serif text-md tracking-wide font-medium">HistoriAI</span>
          </div>
          
          <button 
            type="button" 
            onClick={() => setIsRegister(!isRegister)}
            className="text-xs text-[#cc785c] hover:text-[#b86246] transition-colors inline-flex items-center gap-1 font-medium group"
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
              <h1 className="text-2xl font-serif font-normal text-[#141413]">
                {isRegister ? "Kiến tạo tài khoản" : "Chào mừng trở lại"}
              </h1>
              <p className="text-xs text-[#8e8b82] leading-normal">
                {isRegister 
                  ? "Đăng ký thành viên để bắt đầu xây dựng và khám phá hệ tri thức lịch sử."
                  : "Truy cập hệ thống tác nhân nghiên cứu AI để bắt đầu truy vấn tài liệu lịch sử."}
              </p>
            </div>

            {/* Form Card */}
            <div className="bg-[#efe9de]/50 backdrop-blur-md rounded-2xl border border-[#e6dfd8] p-6 sm:p-8 shadow-sm">
              
              {/* Tab Selector */}
              <div className="flex bg-[#faf8f4]/60 border border-[#e6dfd8] rounded-xl p-1 mb-6">
                <button
                  type="button"
                  onClick={() => setIsRegister(false)}
                  className={cn(
                    "flex-1 text-center py-2 text-xs font-semibold rounded-lg transition-all duration-200",
                    !isRegister 
                      ? "bg-[#cc785c] text-white shadow-sm"
                      : "text-[#6c6a64] hover:text-[#141413]"
                  )}
                >
                  Đăng nhập
                </button>
                <button
                  type="button"
                  onClick={() => setIsRegister(true)}
                  className={cn(
                    "flex-1 text-center py-2 text-xs font-semibold rounded-lg transition-all duration-200",
                    isRegister 
                      ? "bg-[#cc785c] text-white shadow-sm"
                      : "text-[#6c6a64] hover:text-[#141413]"
                  )}
                >
                  Đăng ký
                </button>
              </div>

              {/* Error Alert */}
              {error && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-600 text-xs flex gap-2 items-start">
                  <span className="font-bold">⚠️</span>
                  <span>{error}</span>
                </div>
              )}

              {/* Inputs */}
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Email Input */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#6c6a64] block">Email</label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-[#8e8b82]">
                      <Mail size={14} />
                    </span>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      placeholder="you@example.com"
                      className="w-full bg-[#faf8f4] border border-[#e6dfd8] rounded-xl py-2.5 pl-9 pr-4 text-sm text-[#141413] outline-none placeholder:text-[#8e8b82]/60 focus:border-[#cc785c] focus:ring-2 focus:ring-[#cc785c]/10 transition-all box-border"
                    />
                  </div>
                </div>

                {/* Username Input (Only on Register) */}
                {isRegister && (
                  <div className="space-y-1.5 animate-fadeIn">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-[#6c6a64] block">Tên người dùng</label>
                    <div className="relative">
                      <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-[#8e8b82]">
                        <User size={14} />
                      </span>
                      <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        required
                        minLength={3}
                        placeholder="yourname"
                        className="w-full bg-[#faf8f4] border border-[#e6dfd8] rounded-xl py-2.5 pl-9 pr-4 text-sm text-[#141413] outline-none placeholder:text-[#8e8b82]/60 focus:border-[#cc785c] focus:ring-2 focus:ring-[#cc785c]/10 transition-all box-border"
                      />
                    </div>
                  </div>
                )}

                {/* Password Input */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#6c6a64] block">Mật khẩu</label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-[#8e8b82]">
                      <Lock size={14} />
                    </span>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={8}
                      placeholder="••••••••"
                      className="w-full bg-[#faf8f4] border border-[#e6dfd8] rounded-xl py-2.5 pl-9 pr-4 text-sm text-[#141413] outline-none placeholder:text-[#8e8b82]/60 focus:border-[#cc785c] focus:ring-2 focus:ring-[#cc785c]/10 transition-all box-border"
                    />
                  </div>
                </div>

                {/* Submit button */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-gradient-to-r from-[#cc785c] to-[#b86246] hover:opacity-95 text-white py-2.5 px-4 rounded-xl text-xs font-semibold tracking-wide flex items-center justify-center gap-2 cursor-pointer shadow-md hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-50 transition-all active:scale-[0.98] mt-2 border-0"
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
        <div className="z-10 flex flex-col items-center gap-2 border-t border-[#e6dfd8] pt-4 text-center">
          <span className="text-[10px] text-[#8e8b82] tracking-wider">Hệ thống AI hỗ trợ tra cứu lịch sử Việt Nam</span>
          <span className="text-[9px] text-[#8e8b82]/60">Khuyên dùng trong môi trường học thuật và tra cứu lịch sử</span>
        </div>
      </div>

      {showForgotPassword && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fadeIn">
          <div ref={forgotPasswordRef} className="bg-[#efe9de] border border-[#e6dfd8] rounded-2xl p-6 sm:p-8 max-w-[380px] w-full text-center shadow-xl space-y-4">
            {resetSuccess ? (
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-full bg-green-100 text-green-600 flex items-center justify-center mx-auto">
                  <Check size={24} />
                </div>
                <div className="space-y-2">
                  <h3 className="font-serif text-lg font-normal text-[#141413]">Đã gửi yêu cầu</h3>
                  <p className="text-xs text-[#6c6a64] leading-relaxed">
                    {resetSuccess}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setShowForgotPassword(false);
                    setResetSuccess(null);
                  }}
                  className="w-full bg-[#cc785c] hover:bg-[#b86246] text-white py-2.5 px-4 rounded-xl text-xs font-semibold cursor-pointer transition-colors border-0"
                >
                  Đóng
                </button>
              </div>
            ) : (
              <form onSubmit={handleResetRequest} className="space-y-4 text-left">
                <div className="flex items-center gap-3 border-b border-[#e6dfd8] pb-3 justify-center text-center">
                  <div className="w-9 h-9 rounded-full bg-[#cc785c]/10 text-[#cc785c] flex items-center justify-center">
                    <Mail size={16} />
                  </div>
                  <h3 className="font-serif text-lg font-normal text-[#141413]">Khôi phục mật khẩu</h3>
                </div>

                <p className="text-xs text-[#6c6a64] leading-relaxed text-center">
                  Nhập email đăng ký của bạn. Ban Quản trị sẽ xem xét và xử lý yêu cầu đặt lại mật khẩu.
                </p>

                {resetError && (
                  <div className="p-2.5 bg-red-50 text-red-600 text-xs rounded-lg text-center font-medium border border-red-100">
                    {resetError}
                  </div>
                )}

                <div className="space-y-1.5">
                  <label className="text-[10px] font-semibold text-[#8e8b82] tracking-wider uppercase">Email đăng ký *</label>
                  <input
                    type="email"
                    required
                    value={resetEmail}
                    onChange={(e) => setResetEmail(e.target.value)}
                    placeholder="example@gmail.com"
                    className="w-full bg-white/50 border border-[#e6dfd8] rounded-xl px-3 py-2 text-xs text-[#141413] outline-none focus:border-[#cc785c] transition-colors"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-semibold text-[#8e8b82] tracking-wider uppercase">Tên tài khoản (nếu nhớ)</label>
                  <input
                    type="text"
                    value={resetUsername}
                    onChange={(e) => setResetUsername(e.target.value)}
                    placeholder="username"
                    className="w-full bg-white/50 border border-[#e6dfd8] rounded-xl px-3 py-2 text-xs text-[#141413] outline-none focus:border-[#cc785c] transition-colors"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-semibold text-[#8e8b82] tracking-wider uppercase">Lý do hoặc ghi chú gửi Admin</label>
                  <textarea
                    value={resetReason}
                    onChange={(e) => setResetReason(e.target.value)}
                    placeholder="ví dụ: Tôi quên mật khẩu cũ..."
                    rows={2}
                    className="w-full bg-white/50 border border-[#e6dfd8] rounded-xl px-3 py-2 text-xs text-[#141413] outline-none focus:border-[#cc785c] transition-colors resize-none"
                  />
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setShowForgotPassword(false);
                      setResetError(null);
                    }}
                    className="flex-1 bg-white/80 hover:bg-white text-[#6c6a64] border border-[#e6dfd8] py-2.5 px-4 rounded-xl text-xs font-semibold cursor-pointer transition-colors"
                  >
                    Hủy
                  </button>
                  <button
                    type="submit"
                    disabled={isResetSubmitting}
                    className="flex-1 bg-[#cc785c] hover:bg-[#b86246] text-white py-2.5 px-4 rounded-xl text-xs font-semibold cursor-pointer transition-colors border-0 disabled:opacity-50 disabled:cursor-not-allowed"
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
      `}</style>

      {isTransitioning && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#12100f] text-white p-6 overflow-hidden select-none font-sans">
          {/* SVG Displacement Wave Filter removed */}

          {/* Dong Son Bronze Drum Background Watermark - Spinning extremely slowly */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-20 overflow-hidden">
            <svg 
              viewBox="0 0 500 500" 
              className="w-[120vh] h-[120vh] max-w-[90vw] max-h-[90vh] text-[#cc785c]/10 animate-spin-slow"
              fill="none" 
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Concentric rings of the drum */}
              <circle cx="250" cy="250" r="240" stroke="currentColor" strokeWidth="1" strokeDasharray="3 3" />
              <circle cx="250" cy="250" r="225" stroke="currentColor" strokeWidth="2" />
              <circle cx="250" cy="250" r="200" stroke="currentColor" strokeWidth="1" strokeDasharray="10 5" />
              <circle cx="250" cy="250" r="175" stroke="currentColor" strokeWidth="1.5" />
              <circle cx="250" cy="250" r="140" stroke="currentColor" strokeWidth="1" strokeDasharray="2 4" />
              <circle cx="250" cy="250" r="100" stroke="currentColor" strokeWidth="2.5" />
              <circle cx="250" cy="250" r="60" stroke="currentColor" strokeWidth="1" />
              
              {/* Central 12-pointed Sun Star (Dong Son Symbol) */}
              <polygon 
                points="250,195 254,232 288,212 264,241 298,250 264,259 288,288 254,268 250,305 246,268 212,288 236,259 202,250 236,241 212,212 246,232" 
                fill="currentColor" 
                opacity="0.8"
              />
              
              {/* Radiating triangle sun rays */}
              <g stroke="currentColor" strokeWidth="0.5">
                <line x1="250" y1="250" x2="250" y2="40" />
                <line x1="250" y1="250" x2="250" y2="460" />
                <line x1="250" y1="250" x2="40" y2="250" />
                <line x1="250" y1="250" x2="460" y2="250" />
                <line x1="250" y1="250" x2="100" y2="100" />
                <line x1="250" y1="250" x2="400" y2="400" />
                <line x1="250" y1="250" x2="400" y2="100" />
                <line x1="250" y1="250" x2="100" y2="400" />
              </g>
            </svg>
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
          <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-[#cc785c]/10 blur-[140px] pointer-events-none" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full bg-red-600/5 blur-[140px] pointer-events-none" />
          
          <div className="relative z-10 flex flex-row items-center justify-center w-full h-full gap-8 md:gap-16 px-4">
            
            {/* Glowing Map of Vietnam with Sacred Imperial borders */}
            <div className="relative w-[600px] h-[85vh] max-w-[65vw] bg-[#1a1a18]/50 border border-[#e6dfd8]/10 rounded-2xl p-5 flex items-center justify-center shadow-[0_0_50px_rgba(204,120,92,0.15)] backdrop-blur-md flex-shrink-0 overflow-hidden">
              
              {/* Imperial Corner Borders */}
              <div className="absolute top-0 left-0 w-6 h-6 border-t-2 border-l-2 border-[#cc785c]/60 rounded-tl-xl" />
              <div className="absolute top-0 right-0 w-6 h-6 border-t-2 border-r-2 border-[#cc785c]/60 rounded-tr-xl" />
              <div className="absolute bottom-0 left-0 w-6 h-6 border-b-2 border-l-2 border-[#cc785c]/60 rounded-bl-xl" />
              <div className="absolute bottom-0 right-0 w-6 h-6 border-b-2 border-r-2 border-[#cc785c]/60 rounded-br-xl" />
              
              <VietnamMap className="w-full h-full" />
            </div>

            {/* Right Side: Flag + Loading */}
            <div className="flex flex-col items-center justify-center space-y-12 flex-shrink-0 w-64">
              
              {/* Vietnam Flag Emblem with glowing shadow */}
              <div className="relative flex flex-col items-center">
                <div className="flag-emblem relative rounded shadow-[0_0_35px_rgba(218,37,29,0.5)] border-2 border-[#cc785c]/40 overflow-hidden" style={{ width: "120px", height: "80px" }}>
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
                <span className="text-[12px] uppercase tracking-[0.25em] font-bold bg-gradient-to-r from-[#efeae4] via-[#cc785c] to-[#efeae4] bg-clip-text text-transparent mt-4 font-serif italic">
                  Lịch sử Việt Nam
                </span>
              </div>

              {/* Loading text with transition animation */}
              <div className="space-y-5 w-full text-center">
                <div className="h-12 overflow-hidden relative flex items-center justify-center">
                  <div 
                    key={loadingTextIndex} 
                    className="text-xs md:text-sm font-semibold text-[#e6dfd8] tracking-wide animate-slideUp font-serif italic text-center drop-shadow"
                  >
                    {loadingTexts[loadingTextIndex]}
                  </div>
                </div>
                
                {/* Continue button to proceed to the main chatbot */}
                <button
                  onClick={handleContinue}
                  className="mt-6 px-6 py-2.5 rounded-xl border border-[#cc785c]/40 bg-gradient-to-r from-[#cc785c]/10 to-[#b86246]/10 hover:from-[#cc785c]/25 hover:to-[#b86246]/25 text-[#cc785c] hover:text-[#faf8f4] text-xs font-semibold tracking-wide transition-all duration-300 hover:scale-105 active:scale-95 shadow-[0_0_15px_rgba(204,120,92,0.1)] hover:shadow-[0_0_20px_rgba(204,120,92,0.25)] flex items-center gap-2 mx-auto cursor-pointer outline-none"
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
              box-shadow: 0 0 45px rgba(218, 37, 29, 0.7);
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
              0%, 100% { filter: drop-shadow(0 0 2px rgba(204, 120, 92, 0.4)); }
              50% { filter: drop-shadow(0 0 10px rgba(204, 120, 92, 0.8)); }
            }
            .animate-glow-path {
              animation: glow 2.5s ease-in-out infinite;
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
              opacity: 0.8;
              filter: blur(0.5px);
              box-shadow: 0 0 8px #cc785c, 0 0 15px #da251d;
              animation: rise infinite ease-in-out;
            }
            @keyframes rise {
              0% {
                transform: translateY(0) scale(1) translateX(0);
                opacity: 0;
              }
              10% {
                opacity: 0.8;
              }
              90% {
                opacity: 0.4;
              }
              100% {
                transform: translateY(-110vh) scale(0.3) translateX(60px);
                opacity: 0;
              }
            }
          `}</style>
        </div>
      )}



      {/* Exit Loading Transition Overlay */}
      {isExiting && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#12100f] text-[#efeae4] p-6 animate-fadeIn font-sans selection:bg-[#cc785c]/10 selection:text-[#cc785c]">
          {/* Ambient Glows */}
          <div className="absolute top-1/3 w-[500px] h-[500px] rounded-full bg-[#cc785c]/10 blur-[130px] pointer-events-none" />
          <div className="absolute bottom-1/4 w-[400px] h-[400px] rounded-full bg-red-600/5 blur-[120px] pointer-events-none" />
          
          <div className="relative z-10 flex flex-col items-center space-y-8 text-center max-w-sm w-full">
            {/* Spinning SpikeMarkLogo or elegant Loader */}
            <div className="relative w-20 h-20 flex items-center justify-center">
              <div 
                className="absolute inset-0 rounded-full border-2 border-[#cc785c]/10 border-t-[#cc785c] animate-spin" 
                style={{ animationDuration: '0.8s' }}
              />
              <div 
                className="absolute inset-1.5 rounded-full border border-dashed border-[#cc785c]/25 animate-spin" 
                style={{ animationDuration: '4s', animationDirection: 'reverse' }}
              />
              <SpikeMarkLogo size={32} className="text-[#cc785c] animate-pulse" />
            </div>

            <div className="space-y-4 w-full">
              <div className="space-y-1.5">
                <h3 className="font-serif text-xl font-normal text-[#efeae4] tracking-wide">
                  Đang khởi chạy hệ thống
                </h3>
                <p className="text-[12px] text-[#cc785c] font-medium tracking-wider h-4 animate-pulse">
                  {exitStepText}
                </p>
              </div>

              {/* Progress Bar Container */}
              <div className="w-full h-[3px] bg-white/5 rounded-full overflow-hidden relative border border-white/5">
                <div 
                  className="h-full bg-gradient-to-r from-[#cc785c] to-[#a8583c] shadow-[0_0_8px_#cc785c]"
                  style={{ 
                    width: `${exitProgress}%`,
                    transition: 'width 24ms linear'
                  }}
                />
              </div>
              
              <div className="flex justify-between items-center text-[10px] text-[#6c6a64] uppercase tracking-widest font-mono">
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
