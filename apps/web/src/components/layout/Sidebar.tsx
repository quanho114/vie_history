import { useState, useEffect } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useChatStore } from "@/stores/chatStore";
import { useAuthStore } from "@/stores/authStore";
import { draftsApi, graphDraftsApi } from "@/lib/api/brain";
import { cn } from "@/lib/utils/cn";
import { t } from "@/lib/services/i18n";
import {
  PlusCircle,
  Settings,
  LogOut,
  Shield,
  Trash2,
  Edit,
  Check,
  X,
  User,
  Key,
  Database,
  Palette,
  Eye,
  EyeOff,
  Sun,
  Moon,
  Globe,
  Sliders,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Loader2,
  ChevronRight,
  Lock,
} from "lucide-react";
import { PROVINCES_DATA } from "@/components/ui/VietnamMap";

/* ========================================
   Tabler-style SVG Icons
   ======================================== */

function IconHome({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9,22 9,12 15,12 15,22" />
    </svg>
  );
}

function IconSearch({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}

function IconCollapse({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <rect width="18" height="18" x="3" y="3" rx="2" />
      <path d="M9 3v18" />
      <path d="m16 15-3-3 3-3" />
    </svg>
  );
}

function IconExpand({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <rect width="18" height="18" x="3" y="3" rx="2" />
      <path d="M9 3v18" />
      <path d="m13 15 3-3-3-3" />
    </svg>
  );
}

function IconPencil({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
      <path d="m15 5 4 4" />
    </svg>
  );
}

function IconApps({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <rect width="7" height="7" x="3" y="3" rx="1" />
      <rect width="7" height="7" x="14" y="3" rx="1" />
      <rect width="7" height="7" x="14" y="14" rx="1" />
      <rect width="7" height="7" x="3" y="14" rx="1" />
    </svg>
  );
}

function IconStar({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26 12,2" />
    </svg>
  );
}

function IconDots({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="12" cy="12" r="1" />
      <circle cx="19" cy="12" r="1" />
      <circle cx="5" cy="12" r="1" />
    </svg>
  );
}

/* ========================================
   Spike-mark SVG Logo (Anthropic style)
   ======================================== */

function SpikeMarkLogo({ size = 18, className = "" }: { size?: number; className?: string }) {
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

function IconBookOpen({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  );
}

function IconTimeline({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function IconDocuments({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  );
}

function IconGitCommit({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="12" cy="12" r="4" />
      <line x1="12" y1="2" x2="12" y2="8" />
      <line x1="12" y1="16" x2="12" y2="22" />
    </svg>
  );
}

function IconBrain({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M12 2a5 5 0 0 0-5 5v1a4 4 0 0 0 2 3.5 4 4 0 0 0 2 3.5v2a1 1 0 0 0 1 1h0a1 1 0 0 0 1-1v-2a4 4 0 0 0 2-3.5 4 4 0 0 0 2-3.5V7a5 5 0 0 0-5-5z" />
      <path d="M18 11.5a4.5 4.5 0 0 1-3.5-1.5" />
      <path d="M6 11.5a4.5 4.5 0 0 0 3.5-1.5" />
    </svg>
  );
}

/* ========================================
   Custom Museum Archive Icons
   ======================================== */

function IconTrangChu({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9,22 9,12 15,12 15,22" />
    </svg>
  );
}

function IconTimelineCustom({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function IconNhanVat({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function IconSuKien({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="m9 12 2 2 4-4" />
      <circle cx="12" cy="12" r="10" />
    </svg>
  );
}

function IconTaiLieu({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  );
}

function IconAIAssistant({ className = "" }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M12 8V4H8" />
      <rect width="16" height="12" x="4" y="8" rx="2" />
      <path d="M9 13h.01" />
      <path d="M15 13h.01" />
      <path d="M10 16h4" />
    </svg>
  );
}

/* ========================================
   Nav Items Config
   ======================================== */

const navItems = [
  { to: "/timeline", icon: IconTimelineCustom, label: "Dòng thời gian" },
  { to: "/wiki", icon: IconNhanVat, label: "Wiki Lịch sử" },
  { to: "/graph", icon: IconSuKien, label: "Bản đồ tri thức" },
  { to: "/documents", icon: IconTaiLieu, label: "Tư liệu lịch sử" },
  { to: "/brain-builder", icon: IconBrain, label: "Biên dịch Tri thức" },
];

const GROQ_LEGACY_MODEL_MAP: Record<string, string> = {
  "llama3-70b-8192": "llama-3.3-70b-versatile",
  "llama3-8b-8192": "llama-3.1-8b-instant",
  "mixtral-8x7b-32768": "llama-3.3-70b-versatile",
};

function getStoredGroqModel() {
  const model = localStorage.getItem("groq_model") || "llama-3.3-70b-versatile";
  const normalized = GROQ_LEGACY_MODEL_MAP[model] || model;
  if (normalized !== model) {
    localStorage.setItem("groq_model", normalized);
  }
  return normalized;
}

/* ========================================
   Sidebar Component
   ======================================== */

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function Sidebar({
  isOpen = false,
  onClose,
  isCollapsed = false,
  onToggleCollapse,
}: SidebarProps) {
  const { sessions, createSession, setActiveSession, activeSessionId, renameSession, deleteSession, deleteAllSessions, abortStreaming, isStreaming } = useChatStore();
  const { user, logout, updateUserProfile } = useAuthStore();

  const [pendingGraphCount, setPendingGraphCount] = useState<number>(0);
  const [pendingWikiCount, setPendingWikiCount] = useState<number>(0);

  useEffect(() => {
    const isAdminOrEditor = user?.role === "admin" || user?.role === "editor";
    if (!isAdminOrEditor) return;

    const fetchCounts = async () => {
      try {
        const [gRes, wRes] = await Promise.all([
          graphDraftsApi.list({ status: "pending" }),
          draftsApi.list({ status: "pending" }),
        ]);
        setPendingGraphCount(gRes?.length || 0);
        setPendingWikiCount(wRes?.length || 0);
      } catch (err) {
        console.error("Lỗi khi tải số lượng bản thảo chưa duyệt", err);
      }
    };

    fetchCounts();
    const interval = setInterval(fetchCounts, 15000); // Poll every 15 seconds
    return () => clearInterval(interval);
  }, [user]);

  const [searchTerm, setSearchTerm] = useState("");
  const [isHeaderHovered, setIsHeaderHovered] = useState(false);

  const [settingsOpen, setSettingsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"profile" | "ai_api" | "rag_search" | "preferences">("profile");

  // Profile States
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // AI & API States
  const [activeProvider, setActiveProvider] = useState("gemini");
  const [geminiKey, setGeminiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("gemini-1.5-pro");
  const [groqKey, setGroqKey] = useState("");
  const [groqModel, setGroqModel] = useState("llama-3.3-70b-versatile");
  const [openaiKey, setOpenAIKey] = useState("");
  const [openaiModel, setOpenAIModel] = useState("gpt-4o");
  const [ollamaUrl, setOllamaUrl] = useState("http://localhost:11434");
  const [ollamaModel, setOllamaModel] = useState("llama3");

  // RAG States
  const [ragMode, setRagMode] = useState("hybrid");
  const [chunkLimit, setChunkLimit] = useState(8);
  const [llmTemperature, setLlmTemperature] = useState(0.1);

  // Preference States
  const [theme, setTheme] = useState("light");
  const [language, setLanguage] = useState("vi");

  // Password / API Key visibility
  const [showApiKey, setShowApiKey] = useState(false);

  // Loading, saving, error & success toast states
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [saving, setSaving] = useState(false);

  // Synchronize component state with store whenever modal opens or user profile changes
  useEffect(() => {
    if (settingsOpen && user) {
      setUsername(user.username || "");
      setEmail(user.email || "");
      setPassword(""); // Clear password field on load

      const s = user.settings || {};
      setActiveProvider(s.active_provider || localStorage.getItem("active_provider") || "gemini");

      setGeminiKey(s.gemini_key !== undefined ? s.gemini_key : (localStorage.getItem("gemini_key") || ""));
      setGeminiModel(s.gemini_model || localStorage.getItem("gemini_model") || "gemini-1.5-pro");

      setGroqKey(s.groq_key !== undefined ? s.groq_key : (localStorage.getItem("groq_key") || ""));
      setGroqModel(s.groq_model || localStorage.getItem("groq_model") || "llama-3.3-70b-versatile");

      setOpenAIKey(s.openai_key !== undefined ? s.openai_key : (localStorage.getItem("openai_key") || ""));
      setOpenAIModel(s.openai_model || localStorage.getItem("openai_model") || "gpt-4o");

      setOllamaUrl(s.ollama_url || localStorage.getItem("ollama_url") || "http://localhost:11434");
      setOllamaModel(s.ollama_model || localStorage.getItem("ollama_model") || "llama3");

      setRagMode(s.rag_mode || localStorage.getItem("rag_mode") || "hybrid");
      setChunkLimit(Number(s.chunk_limit !== undefined ? s.chunk_limit : (localStorage.getItem("chunk_limit") || 8)));
      setLlmTemperature(Number(s.llm_temperature !== undefined ? s.llm_temperature : (localStorage.getItem("llm_temperature") || 0.1)));

      setTheme(s.theme || localStorage.getItem("theme") || "light");
      setLanguage(s.language || localStorage.getItem("language") || "vi");

      setShowApiKey(false);
      setToast(null);
    }
  }, [settingsOpen, user]);

  // Listen for global open_settings / settings:open events (e.g. from ChatPage to configure API keys)
  useEffect(() => {
    const handleOpenSettings = (e: Event) => {
      const customEvent = e as CustomEvent;
      const tab = customEvent.detail?.tab || "profile";
      setActiveTab(tab as "profile" | "ai_api" | "rag_search" | "preferences");
      setSettingsOpen(true);
    };
    window.addEventListener("open_settings", handleOpenSettings);
    window.addEventListener("settings:open", handleOpenSettings);
    return () => {
      window.removeEventListener("open_settings", handleOpenSettings);
      window.removeEventListener("settings:open", handleOpenSettings);
    };
  }, []);

  const handleSaveAllSettings = async () => {
    setSaving(true);
    setToast(null);

    const sPayload = {
      active_provider: activeProvider,
      gemini_key: geminiKey,
      gemini_model: geminiModel,
      groq_key: groqKey,
      groq_model: groqModel,
      openai_key: openaiKey,
      openai_model: openaiModel,
      ollama_url: ollamaUrl,
      ollama_model: ollamaModel,
      rag_mode: ragMode,
      chunk_limit: chunkLimit,
      llm_temperature: llmTemperature,
      theme: theme,
      language: language,
    };

    const updatePayload: {
      username?: string;
      email?: string;
      password?: string;
      settings?: Record<string, unknown>;
    } = {
      settings: sPayload as Record<string, unknown>,
    };

    if (username.trim() && username !== user?.username) {
      updatePayload.username = username.trim();
    }
    if (email.trim() && email !== user?.email) {
      updatePayload.email = email.trim();
    }
    if (password) {
      updatePayload.password = password;
    }

    try {
      await updateUserProfile(updatePayload);

      // Apply the theme immediately
      if (theme === "dark") {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }

      setToast({
        type: "success",
        message: t("saved_success"),
      });

      setPassword("");

      // Delay modal closing so user sees the success toast
      setTimeout(() => {
        setSettingsOpen(false);
        setToast(null);
      }, 1500);
    } catch (err) {
      const errorMsg = (err instanceof Error) ? err.message : t("save_failed");
      setToast({
        type: "error",
        message: errorMsg,
      });
    } finally {
      setSaving(false);
    }
  };

  const navigate = useNavigate();
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [showAllSessions, setShowAllSessions] = useState(false);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);
  const [isDeletingAll, setIsDeletingAll] = useState(false);
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const filteredSessions = sessions.filter(session =>
    session.title?.toLowerCase().includes(searchTerm.toLowerCase())
  );
  const visibleSessions = showAllSessions ? filteredSessions : filteredSessions.slice(0, 8);

  const handleNewChat = async () => {
    setSessionError(null);

    // Cancel any ongoing stream before switching
    if (isStreaming) {
      abortStreaming();
    }

    const activeSession = sessions.find((s) => s.id === activeSessionId);
    
    if (activeSession && (activeSession.message_count ?? 0) === 0) {
      navigate("/chat");
      onClose?.();
      return;
    }

    try {
      const session = await createSession(t("new_chat"));
      setActiveSession(session.id);
      navigate("/chat");
      onClose?.();
    } catch (e) {
      console.error("Failed to create new chat:", e);
      setSessionError(e instanceof Error ? e.message : "Không thể tạo cuộc trò chuyện mới.");
    }
  };

  const handleSessionClick = (sessionId: string) => {
    setSessionError(null);
    // Cancel any ongoing stream before switching to another session
    if (isStreaming) {
      abortStreaming();
    }
    setActiveSession(sessionId);
    navigate("/chat");
    onClose?.();
  };

  const handleSaveRename = async (sessionId: string) => {
    if (editTitle.trim()) {
      try {
        await renameSession(sessionId, editTitle.trim());
        setSessionError(null);
      } catch (error) {
        setSessionError(error instanceof Error ? error.message : "Không thể đổi tên cuộc trò chuyện.");
      }
    }
    setEditingSessionId(null);
  };

  const handleDeleteSession = async (sessionId: string) => {
    setDeletingSessionId(sessionId);
    setSessionError(null);
    try {
      await deleteSession(sessionId);
    } catch (error) {
      setSessionError(error instanceof Error ? error.message : "Không thể xóa cuộc trò chuyện.");
    } finally {
      setDeletingSessionId(null);
    }
  };

  const handleDeleteAllSessions = async () => {
    setIsDeletingAll(true);
    setSessionError(null);
    setConfirmDeleteAll(false);
    try {
      await deleteAllSessions();
    } catch (error) {
      setSessionError(error instanceof Error ? error.message : "Không thể xóa tất cả cuộc trò chuyện.");
    } finally {
      setIsDeletingAll(false);
    }
  };

  const translatedLabel = (to: string, fallback: string) => {
    switch (to) {
      case "/chat": return "Trang chủ";
      case "/wiki": return "Wiki Lịch sử";
      case "/timeline": return "Dòng thời gian";
      case "/graph": return "Bản đồ tri thức";
      case "/documents": return "Tư liệu lịch sử";
      case "/brain-builder": return "Biên dịch Tri thức";
      default: return fallback;
    }
  };

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-50 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "sidebar",
          isOpen ? "open" : "",
          isCollapsed ? "collapsed" : ""
        )}
      >
        {/* Mobile Close Button */}
        <div className="flex items-center justify-between p-4 border-b border-hairline md:hidden">
          <div className="flex items-center">
            <span className="font-semibold text-[18px] text-[#1C2120]" style={{ fontFamily: "var(--font-heading)" }}>
              HistoriAI
            </span>
          </div>
        </div>

        {/* Brand Row with Actions */}
        {!isCollapsed ? (
          <div className="px-5 py-4 flex items-center justify-between flex-shrink-0">
            {/* App Name */}
            <div className="flex items-center gap-2.5">
              <SpikeMarkLogo size={22} className="text-[#D4AF37]" />
              <span className="font-semibold text-xl text-[#1C2120]" style={{ fontFamily: "var(--font-heading)" }}>
                HistoriAI
              </span>
            </div>

            {/* Icon Buttons - Toggle Collapse */}
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={onToggleCollapse}
                className="w-[28px] h-[28px] rounded-lg flex items-center justify-center text-[#737A77] hover:text-[#1C2120] hover:bg-white/40 transition-colors"
                title="Thu nhỏ sidebar"
                aria-label="Thu nhỏ sidebar"
              >
                <IconCollapse className="w-[18px] h-[18px]" />
              </button>
            </div>
          </div>
        ) : (
          <div 
            className="h-[56px] flex items-center justify-center flex-shrink-0"
            onMouseEnter={() => setIsHeaderHovered(true)}
            onMouseLeave={() => setIsHeaderHovered(false)}
          >
            {isHeaderHovered ? (
              <button
                type="button"
                onClick={onToggleCollapse}
                className="w-9 h-9 rounded-xl flex items-center justify-center text-[#737A77] hover:text-[#1C2120] hover:bg-white/40 transition-all duration-150"
                title="Mở rộng sidebar"
                aria-label="Mở rộng sidebar"
              >
                <IconExpand className="w-[18px] h-[18px]" />
              </button>
            ) : (
              <div className="w-9 h-9 flex items-center justify-center">
                <SpikeMarkLogo size={24} className="text-[#D4AF37]" />
              </div>
            )}
          </div>
        )}

        {/* Navigation */}
        <nav className={cn("pt-2 pb-1 flex-shrink-0 space-y-1", isCollapsed ? "px-1" : "px-3")}>
          {/* New Chat Button */}
          <button
            type="button"
            onClick={handleNewChat}
            className={cn(
              "flex items-center rounded-lg text-[13.5px] font-medium text-[#0B3030] hover:bg-[#0B3030]/10 hover:translate-x-1 transition-all duration-200 text-left w-full",
              isCollapsed ? "justify-center w-8 h-8 mx-auto py-0 px-0 hover:translate-x-0" : "gap-2.5 px-3 py-2"
            )}
            title={t("new_chat")}
            aria-label={t("new_chat")}
          >
            <PlusCircle className="w-[18px] h-[18px] text-[#D4AF37] flex-shrink-0" />
            {!isCollapsed && <span style={{ fontFamily: "var(--font-body-custom)" }}>{t("new_chat")}</span>}
          </button>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center rounded-lg text-[13.5px] font-medium transition-all duration-200 hover:translate-x-1",
                  isCollapsed ? "justify-center w-8 h-8 mx-auto py-0 px-0 hover:translate-x-0" : "gap-2.5 px-3 py-2",
                  isActive
                    ? "bg-[#EBE7E0]/85 text-[#0B3030] shadow-sm font-semibold border border-white/20"
                    : "text-[#1C2120]/80 hover:bg-white/40 hover:text-[#1C2120]"
                )
              }
              onClick={onClose}
              title={translatedLabel(item.to, item.label)}
            >
              {({ isActive }) => (
                <>
                  <item.icon
                    className={cn(
                      "w-[18px] h-[18px] flex-shrink-0",
                      isActive ? "text-[#D4AF37]" : "text-[#737A77]"
                    )}
                  />
                  {!isCollapsed && <span style={{ fontFamily: "var(--font-body-custom)" }}>{translatedLabel(item.to, item.label)}</span>}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Search input for past chats */}
        {!isCollapsed && (
          <div className="px-3 pt-2 pb-1 flex-shrink-0">
            <div className="relative">
              <IconSearch className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-muted pointer-events-none" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Tìm cuộc trò chuyện..."
                className="w-full pl-8 pr-2.5 py-1.5 rounded-lg border border-hairline bg-[rgba(20,20,18,.02)] dark:bg-white/5 text-[12px] text-ink placeholder-soft focus:bg-white dark:focus:bg-[#1f1e1b] focus:border-coral transition-colors outline-none"
              />
            </div>
          </div>
        )}

        {/* Divider */}
        <div className={cn("mt-3 border-t border-hairline", isCollapsed ? "mx-2" : "mx-3")} />

        {/* Recents Section */}
        {!isCollapsed && (
          <div className="flex-1 min-h-0 overflow-y-auto px-3">
            {/* Section Label */}
            <div className="flex items-center justify-between pt-3 pb-1">
              <span className="text-[10px] font-medium text-soft uppercase tracking-wider">
                {t("recent_chats")}
              </span>
              {sessions.length > 0 && (
                <button
                  type="button"
                  onClick={() => setConfirmDeleteAll(true)}
                  className="flex items-center gap-1 text-[10px] text-muted hover:text-red-500 transition-colors rounded px-1.5 py-0.5 hover:bg-red-50 dark:hover:bg-red-950/20"
                  title={language === "en" ? "Delete all chats" : "Xóa tất cả đoạn chat"}
                  aria-label={language === "en" ? "Delete all chats" : "Xóa tất cả đoạn chat"}
                >
                  <Trash2 size={10} />
                  <span>{language === "en" ? "Clear all" : "Xóa tất cả"}</span>
                </button>
              )}
            </div>

            {/* Session List - Interactive rows */}
            <div className="space-y-0.5">
              {sessionError && (
                <p className="text-[11px] text-red-600 bg-red-50 border border-red-100 rounded-md px-2 py-1.5">
                  {sessionError}
                </p>
              )}
              {visibleSessions.map((session) => {
                const isEditing = editingSessionId === session.id;
                const isActive = session.id === activeSessionId;
                const isDeleting = deletingSessionId === session.id;

                if (isEditing) {
                  return (
                    <div
                      key={session.id}
                      className="flex items-center gap-1 px-2 py-[5px] bg-surface-strong rounded-md"
                    >
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            handleSaveRename(session.id);
                          } else if (e.key === "Escape") {
                            setEditingSessionId(null);
                          }
                        }}
                        className="flex-1 bg-white border border-[#e6dfd8] rounded px-1.5 py-0.5 text-[12px] text-ink outline-none"
                        autoFocus
                      />
                      <button
                        onClick={() => handleSaveRename(session.id)}
                        className="text-[#5db872] hover:text-[#5db872]/85 p-0.5"
                        title={language === "en" ? "Save" : "Lưu"}
                        aria-label={language === "en" ? "Save rename" : "Lưu đổi tên"}
                      >
                        <Check size={14} />
                      </button>
                      <button
                        onClick={() => setEditingSessionId(null)}
                        className="text-[#c64545] hover:text-[#c64545]/85 p-0.5"
                        title={language === "en" ? "Cancel" : "Hủy"}
                        aria-label={language === "en" ? "Cancel rename" : "Hủy đổi tên"}
                      >
                        <X size={14} />
                      </button>
                    </div>
                  );
                }

                return (
                  <div
                    key={session.id}
                    className={cn(
                      "group relative w-full flex items-center justify-between px-3 py-[7px] rounded-md text-[12.5px] text-body-text hover:bg-[rgba(20,20,18,.04)] dark:hover:bg-white/5 transition-all duration-150",
                      isActive && "bg-surface-strong text-ink font-medium"
                    )}
                    onClick={() => handleSessionClick(session.id)}
                    style={{ cursor: "pointer" }}
                  >
                    <span className="truncate pr-8 select-none">
                      {session.title || (language === "en" ? "Untitled Chat" : "Cuộc trò chuyện")}
                    </span>

                    {/* Action buttons (rename/delete) visible on hover */}
                    <div className="absolute right-2 opacity-0 group-hover:opacity-100 flex items-center gap-1 bg-transparent transition-opacity duration-150">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingSessionId(session.id);
                          setEditTitle(session.title || "");
                        }}
                        className="p-1 rounded text-muted hover:text-ink hover:bg-[rgba(20,20,18,.06)] dark:hover:bg-white/5 transition-colors"
                        aria-label={`${language === "en" ? "Rename" : "Đổi tên"} ${session.title || "chat"}`}
                        title={language === "en" ? "Rename" : "Đổi tên"}
                      >
                        <Edit size={12} />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteSession(session.id);
                        }}
                        disabled={isDeleting}
                        className="p-1 rounded text-muted hover:text-[#c64545] hover:bg-[rgba(198,69,69,.08)] transition-colors"
                        aria-label={`${language === "en" ? "Delete" : "Xóa"} ${session.title || "chat"}`}
                        title={language === "en" ? "Delete" : "Xóa"}
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                );
              })}
              {filteredSessions.length === 0 && (
                <p className="text-[12px] text-soft px-3 py-2">
                  {searchTerm 
                    ? (language === "en" ? "No matches found" : "Không tìm thấy kết quả")
                    : (language === "en" ? "No chats yet" : "Chưa có cuộc trò chuyện nào")
                  }
                </p>
              )}
            </div>

            {/* View All Link */}
            {filteredSessions.length > 8 && (
              <button
                onClick={() => setShowAllSessions((value) => !value)}
                className="mt-2 text-[12px] text-coral hover:text-coral-hover font-medium transition-colors"
                aria-label={showAllSessions ? (language === "en" ? "Collapse session list" : "Thu gọn danh sách") : (language === "en" ? `View all ${filteredSessions.length} sessions` : `Xem tất cả ${filteredSessions.length} cuộc trò chuyện`)}
              >
                {showAllSessions
                  ? (language === "en" ? "Collapse ↑" : "Thu gọn ↑")
                  : (language === "en" ? `View all (${filteredSessions.length}) →` : `Xem tất cả (${filteredSessions.length}) →`)
                }
              </button>
            )}
          </div>
        )}

        {/* Divider */}
        <div className={cn("border-t border-hairline", isCollapsed ? "mx-2" : "mx-3")} />

        {/* Admin Links (Only for Admin role) */}
        {user?.role === "admin" && (
          <div className={cn("py-0.5 flex-shrink-0", isCollapsed ? "px-1" : "px-3")}>
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                cn(
                  "flex items-center rounded-lg text-[13.5px] font-medium transition-all duration-200 hover:translate-x-1",
                  isCollapsed ? "justify-center w-8 h-8 mx-auto py-0 px-0 hover:translate-x-0" : "gap-2.5 px-3 py-2",
                  isActive
                    ? "bg-[#EBE7E0]/85 text-[#0B3030] shadow-sm font-semibold border border-white/20"
                    : "text-[#1C2120]/80 hover:bg-white/40 hover:text-[#1C2120]"
                )
              }
              onClick={onClose}
              title="Admin"
            >
              {({ isActive }) => (
                <>
                  <Shield className={cn("w-[18px] h-[18px] flex-shrink-0", isActive ? "text-[#D4AF37]" : "text-[#737A77]")} />
                  {!isCollapsed && <span style={{ fontFamily: "var(--font-body-custom)" }}>Admin</span>}
                </>
              )}
            </NavLink>
          </div>
        )}

        {/* Wiki Drafts Review Link (For Admins and Editors) */}
        {(user?.role === "admin" || user?.role === "editor") && (
          <div className={cn("py-0.5 flex-shrink-0", isCollapsed ? "px-1" : "px-3")}>
            <NavLink
              to="/wiki/drafts/review"
              className={({ isActive }) =>
                cn(
                  "flex items-center rounded-lg text-[13.5px] font-medium transition-all duration-200 hover:translate-x-1",
                  isCollapsed ? "justify-center w-8 h-8 mx-auto py-0 px-0 hover:translate-x-0" : "gap-2.5 px-3 py-2",
                  isActive
                    ? "bg-[#EBE7E0]/85 text-[#0B3030] shadow-sm font-semibold border border-white/20"
                    : "text-[#1C2120]/80 hover:bg-white/40 hover:text-[#1C2120]"
                )
              }
              onClick={onClose}
              title="Duyệt Wiki"
            >
              {({ isActive }) => (
                <div className={cn("flex items-center w-full", isCollapsed ? "justify-center" : "justify-between")}>
                  <div className={cn("flex items-center", isCollapsed ? "" : "gap-2.5")}>
                    <div className="relative">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className={cn("w-[18px] h-[18px] flex-shrink-0", isActive ? "text-[#D4AF37]" : "text-[#737A77]")}
                      >
                        <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
                        <path d="M6 6h10" />
                        <path d="M6 10h10" />
                      </svg>
                      {isCollapsed && pendingWikiCount > 0 && (
                        <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-[#cc785c] rounded-full ring-2 ring-white dark:ring-stone-900" />
                      )}
                    </div>
                    {!isCollapsed && <span style={{ fontFamily: "var(--font-body-custom)" }}>Duyệt Wiki</span>}
                  </div>
                  {!isCollapsed && pendingWikiCount > 0 && (
                    <span className="ml-auto bg-[#cc785c] text-white text-[10.5px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] h-[18px] flex items-center justify-center">
                      {pendingWikiCount}
                    </span>
                  )}
                </div>
              )}
            </NavLink>
          </div>
        )}

        {/* Knowledge Evolution Link (For Admins and Editors) */}
        {(user?.role === "admin" || user?.role === "editor") && (
          <div className={cn("py-0.5 flex-shrink-0", isCollapsed ? "px-1" : "px-3")}>
            <NavLink
              to="/graph/drafts/review"
              className={({ isActive }) =>
                cn(
                  "flex items-center rounded-lg text-[13.5px] font-medium transition-all duration-200 hover:translate-x-1",
                  isCollapsed ? "justify-center w-8 h-8 mx-auto py-0 px-0 hover:translate-x-0" : "gap-2.5 px-3 py-2",
                  isActive
                    ? "bg-[#EBE7E0]/85 text-[#0B3030] shadow-sm font-semibold border border-white/20"
                    : "text-[#1C2120]/80 hover:bg-white/40 hover:text-[#1C2120]"
                )
              }
              onClick={onClose}
              title="Tiến hóa Tri thức"
            >
              {({ isActive }) => (
                <div className={cn("flex items-center w-full", isCollapsed ? "justify-center" : "justify-between")}>
                  <div className={cn("flex items-center", isCollapsed ? "" : "gap-2.5")}>
                    <div className="relative">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className={cn("w-[18px] h-[18px] flex-shrink-0", isActive ? "text-[#D4AF37]" : "text-[#737A77]")}
                      >
                        <circle cx="12" cy="12" r="3" />
                        <circle cx="6" cy="18" r="3" />
                        <circle cx="18" cy="6" r="3" />
                        <line x1="9" y1="15" x2="12" y2="12" />
                        <line x1="12" y1="12" x2="15" y2="9" />
                      </svg>
                      {isCollapsed && pendingGraphCount > 0 && (
                        <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-[#cc785c] rounded-full ring-2 ring-white dark:ring-stone-900" />
                      )}
                    </div>
                    {!isCollapsed && <span style={{ fontFamily: "var(--font-body-custom)" }}>Tiến hóa Tri thức</span>}
                  </div>
                  {!isCollapsed && pendingGraphCount > 0 && (
                    <span className="ml-auto bg-[#cc785c] text-white text-[10.5px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] h-[18px] flex items-center justify-center">
                      {pendingGraphCount}
                    </span>
                  )}
                </div>
              )}
            </NavLink>
          </div>
        )}

        {/* User Row - Clickable to open settings */}
        <div className={cn("pb-3 pt-2 flex-shrink-0 flex justify-center", isCollapsed ? "px-1" : "px-3")}>
          <button
            type="button"
            onClick={() => setSettingsOpen(true)}
            className={cn(
              "flex items-center rounded-xl hover:bg-white/40 transition-all duration-150 group",
              isCollapsed ? "justify-center w-8 h-8 p-0" : "gap-3 w-full text-left p-1.5"
            )}
            title={user?.username || "Guest"}
          >
            {/* Avatar */}
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#D4AF37] to-amber-500 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform duration-150 shadow-sm border border-amber-100/20">
              <span className="text-white text-[13px] font-bold leading-none select-none flex items-center justify-center">
                {user?.username?.[0]?.toUpperCase() || "?"}
              </span>
            </div>

            {/* Name */}
            {!isCollapsed && (
              <div className="flex-1 min-w-0" style={{ fontFamily: "var(--font-body-custom)" }}>
                <p className="text-[13px] font-semibold text-[#1C2120] truncate leading-tight">
                  {user?.username || "Guest"}
                </p>
                <p className="text-[10px] text-[#737A77] mt-0.5 truncate">
                  {t("settings")}
                </p>
              </div>
            )}

            {/* Dots Icon */}
            {!isCollapsed && (
              <div className="w-[26px] h-[26px] rounded-md flex items-center justify-center text-[#737A77] group-hover:text-[#1C2120] transition-colors">
                <IconDots className="w-[18px] h-[18px]" />
              </div>
            )}
          </button>
        </div>

        {/* Bottom Spacer to prevent cutoff */}
        <div className="h-1 flex-shrink-0" />
      </aside>

      {/* Clear All Confirmation Modal */}
      {confirmDeleteAll && (
        <div className="fixed inset-0 z-[1060] flex items-center justify-center bg-black/50 dark:bg-black/75 backdrop-blur-[2px] p-4 animate-fade-in">
          <div className="bg-canvas dark:bg-surface-soft border border-hairline rounded-2xl w-full max-w-md p-6 shadow-2xl relative animate-scale-up flex flex-col gap-4">
            {/* Warning Icon & Title */}
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-full bg-red-50 dark:bg-red-950/30 flex items-center justify-center flex-shrink-0 text-[#c64545] dark:text-red-400">
                <AlertTriangle className="w-5 h-5 animate-pulse" />
              </div>
              <div className="flex-1">
                <h3 className="font-display text-[17px] font-bold text-ink leading-tight">
                  {language === "en" ? "Clear Chat History?" : "Xóa Lịch sử Trò chuyện?"}
                </h3>
                <p className="text-[12.5px] text-muted mt-2 leading-relaxed">
                  {language === "en" 
                    ? "This action will permanently delete all your chat history. You cannot retrieve them later. Are you sure you want to continue?" 
                    : "Hành động này sẽ xóa vĩnh viễn tất cả lịch sử cuộc trò chuyện của bạn. Bạn sẽ không thể khôi phục lại chúng. Bạn có chắc chắn muốn tiếp tục?"}
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2.5 mt-2">
              <button
                type="button"
                onClick={() => setConfirmDeleteAll(false)}
                disabled={isDeletingAll}
                className="px-3.5 py-1.5 rounded-lg text-[12.5px] font-medium text-body hover:bg-surface-strong/60 dark:hover:bg-white/5 border border-hairline transition-all duration-150"
              >
                {language === "en" ? "Cancel" : "Hủy"}
              </button>
              <button
                type="button"
                onClick={async () => {
                  await handleDeleteAllSessions();
                  setConfirmDeleteAll(false);
                }}
                disabled={isDeletingAll}
                className="px-3.5 py-1.5 rounded-lg text-[12.5px] font-semibold text-white bg-[#c64545] hover:bg-[#b03d3d] transition-all duration-150 flex items-center gap-1.5 shadow-sm disabled:opacity-60"
              >
                {isDeletingAll ? (
                  <span>{language === "en" ? "Clearing..." : "Đang xóa..."}</span>
                ) : (
                  <>
                    <Trash2 size={13} />
                    <span>{language === "en" ? "Clear all" : "Xóa tất cả"}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Settings Modal */}
      {settingsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/75 backdrop-blur-[3px] p-4 animate-fade-in">
          <div className="bg-canvas dark:bg-surface-soft border border-hairline rounded-2xl w-full max-w-3xl h-[560px] max-h-[85vh] overflow-hidden shadow-2xl relative animate-scale-up flex flex-col">
            {/* Header */}
            <div className="px-5 py-3.5 border-b border-hairline flex items-center justify-between bg-surface-soft/40">
              <div className="flex items-center gap-2 text-[#cc785c]">
                <Settings className="w-4.5 h-4.5 animate-spin-slow" />
                <h3 className="font-display text-[16px] font-semibold text-ink">
                  {t("settings")}
                </h3>
              </div>
          <button
            type="button"
            onClick={() => setSettingsOpen(false)}
            className="w-7 h-7 rounded-full flex items-center justify-center text-muted hover:text-ink hover:bg-surface-strong/60 transition-colors"
            aria-label="Đóng cài đặt"
          >
                <X size={16} />
              </button>
            </div>

            {/* Main Area: Two Columns */}
            <div className="flex-1 flex min-h-0">
              {/* Left Column: Tab Sidebar */}
              <div className="w-48 md:w-52 border-r border-hairline flex flex-col p-2 bg-surface-soft/20 select-none justify-between">
                <div className="flex-1 flex flex-col gap-1 overflow-y-auto">
                  {[
                    { id: "profile", label: t("profile"), icon: User },
                    { id: "ai_api", label: t("ai_api"), icon: Key },
                    { id: "rag_search", label: t("rag_search"), icon: Sliders },
                    { id: "preferences", label: t("preferences"), icon: Palette }
                  ].map((tab) => {
                    const Icon = tab.icon;
                    const isActive = activeTab === tab.id;
                    return (
                      <button
                        key={tab.id}
                        type="button"
                        onClick={() => setActiveTab(tab.id as "profile" | "ai_api" | "rag_search" | "preferences")}
                        className={cn(
                          "flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-normal transition-colors text-left w-full border-0 cursor-pointer bg-transparent",
                          isActive
                            ? "bg-surface-strong text-ink font-medium"
                            : "text-body-text hover:bg-surface-strong/40"
                        )}
                      >
                        <Icon className={cn("w-4.5 h-4.5", isActive ? "text-[#cc785c]" : "text-muted")} />
                        <span>{tab.label}</span>
                      </button>
                    );
                  })}
                </div>

                {/* Logout Button */}
                <div className="pt-2 border-t border-hairline mt-2 flex-shrink-0">
                  <button
                    type="button"
                    onClick={() => {
                      logout();
                      setSettingsOpen(false);
                    }}
                    className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-normal text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors text-left w-full border-0 cursor-pointer bg-transparent"
                    aria-label={t("logout")}
                  >
                    <LogOut className="w-4.5 h-4.5" />
                    <span>{t("logout")}</span>
                  </button>
                </div>
              </div>

              {/* Right Column: Tab Content */}
              <div className="flex-1 overflow-y-auto p-5 space-y-5 bg-white dark:bg-canvas">
                {/* Profile Tab */}
                {activeTab === "profile" && (
                  <div className="space-y-4 animate-fade-in">
                    <h4 className="font-display text-[15px] font-semibold text-ink border-b border-hairline pb-1.5">
                      {t("personal_info")}
                    </h4>
                    <div className="space-y-3.5">
                      <div className="space-y-1">
                        <label className="text-[12px] font-medium text-body-strong block">{t("username")}</label>
                        <input
                          type="text"
                          value={username}
                          onChange={(e) => setUsername(e.target.value)}
                          className="w-full bg-surface-soft/20 border border-hairline rounded-lg px-3 py-2 text-[13px] text-ink outline-none focus:border-[#cc785c] transition-all"
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[12px] font-medium text-body-strong block">{t("email")}</label>
                        <input
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          className="w-full bg-surface-soft/20 border border-hairline rounded-lg px-3 py-2 text-[13px] text-ink outline-none focus:border-[#cc785c] transition-all"
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[12px] font-medium text-body-strong block flex items-center gap-1">
                          <Lock className="w-3.5 h-3.5 text-muted" />
                          <span>{language === "en" ? "Change Password" : "Đổi mật khẩu"}</span>
                        </label>
                        <input
                          type="password"
                          placeholder={t("new_password_placeholder")}
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          className="w-full bg-surface-soft/20 border border-hairline rounded-lg px-3 py-2 text-[13px] text-ink outline-none focus:border-[#cc785c] transition-all"
                        />
                      </div>
                    </div>

                    {/* Danger Zone */}
                    <div className="pt-2 border-t border-hairline space-y-2">
                      <h4 className="font-display text-[13px] font-semibold text-red-600 flex items-center gap-1.5">
                        <Trash2 className="w-3.5 h-3.5" />
                        {language === "en" ? "Danger Zone" : "Vùng nguy hiểm"}
                      </h4>
                      <div className="flex items-center justify-between p-3 rounded-xl border border-red-100 bg-red-50/40">
                        <div>
                          <p className="text-[12px] font-medium text-ink">
                            {language === "en" ? "Delete all chats" : "Xóa tất cả đoạn chat"}
                          </p>
                          <p className="text-[11px] text-muted mt-0.5">
                            {language === "en"
                              ? "Permanently removes all conversation history."
                              : "Xóa vĩnh viễn toàn bộ lịch sử trò chuyện."}
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setConfirmDeleteAll(true)}
                          disabled={sessions.length === 0 || isDeletingAll}
                          className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium text-red-600 border border-red-200 hover:bg-red-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                          aria-label={language === "en" ? "Delete all chats" : "Xóa tất cả đoạn chat"}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          {language === "en" ? "Delete all" : "Xóa tất cả"}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* AI & API Keys Tab */}
                {activeTab === "ai_api" && (
                  <div className="space-y-4 animate-fade-in">
                    <h4 className="font-display text-[15px] font-semibold text-ink border-b border-hairline pb-1.5">
                      {t("provider")}
                    </h4>
                    <div className="grid grid-cols-4 gap-2">
                      {[
                        { id: "gemini", name: "Gemini", icon: SpikeMarkLogo },
                        { id: "groq", name: "Groq", icon: Sliders },
                        { id: "openai", name: "OpenAI", icon: Database },
                        { id: "ollama", name: "Ollama", icon: ChevronRight }
                      ].map((prov) => {
                        const Icon = prov.icon;
                        const isActive = activeProvider === prov.id;
                        return (
                          <button
                            key={prov.id}
                            type="button"
                            onClick={() => setActiveProvider(prov.id)}
                            className={cn(
                              "flex flex-col items-center justify-center p-2.5 rounded-xl border transition-all duration-200 gap-1.5",
                              isActive
                                ? "border-[#cc785c] bg-white dark:bg-canvas text-[#cc785c] shadow-sm font-semibold"
                                : "border-hairline bg-surface-soft/30 text-muted hover:text-ink hover:bg-surface-soft/80"
                            )}
                          >
                            <Icon size={16} className={isActive ? "text-[#cc785c]" : "text-soft"} />
                            <span className="text-xs">{prov.name}</span>
                          </button>
                        );
                      })}
                    </div>

                    <div className="pt-2 border-t border-hairline space-y-3.5">
                      {activeProvider === "gemini" && (
                        <div className="space-y-3.5 animate-fade-in">
                          <div className="space-y-1">
                            <label className="text-[12px] font-medium text-body-strong block">{t("api_key")}</label>
                            <div className="relative">
                              <input
                                type={showApiKey ? "text" : "password"}
                                placeholder="AIzaSy..."
                                value={geminiKey}
                                onChange={(e) => setGeminiKey(e.target.value)}
                                className="w-full bg-surface-soft/20 border border-hairline rounded-lg pl-3 pr-10 py-2 text-[13px] text-ink outline-none focus:border-[#cc785c] transition-all"
                              />
                              <button
                                type="button"
                                onClick={() => setShowApiKey(!showApiKey)}
                                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-ink"
                                aria-label={showApiKey ? "Ẩn khóa API" : "Hiện khóa API"}
                              >
                                {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                              </button>
                            </div>
                          </div>
                          <div className="space-y-1">
                            <label className="text-[12px] font-medium text-body-strong block">{t("active_model")}</label>
                            <select
                              value={geminiModel}
                              onChange={(e) => setGeminiModel(e.target.value)}
                              className="w-full bg-surface-soft/20 border border-hairline rounded-lg px-3 py-2 text-[13px] text-ink outline-none focus:border-[#cc785c] transition-all"
                            >
                              <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                              <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                              <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                            </select>
                          </div>
                        </div>
                      )}

                      {activeProvider === "groq" && (
                        <div className="space-y-3.5 animate-fade-in">
                          <div className="space-y-1">
                            <label className="text-[12px] font-medium text-body-strong block">{t("api_key")}</label>
                            <div className="relative">
                              <input
                                type={showApiKey ? "text" : "password"}
                                placeholder="gsk_..."
                                value={groqKey}
                                onChange={(e) => setGroqKey(e.target.value)}
                                className="w-full bg-surface-soft/20 border border-hairline rounded-lg pl-3 pr-10 py-2 text-[13px] text-ink outline-none focus:border-[#cc785c] transition-all"
                              />
                              <button
                                type="button"
                                onClick={() => setShowApiKey(!showApiKey)}
                                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-ink"
                                aria-label={showApiKey ? "Ẩn khóa API" : "Hiện khóa API"}
                              >
                                {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                              </button>
                            </div>
                          </div>
                          <div className="space-y-1">
                            <label className="text-[12px] font-medium text-body-strong block">{t("active_model")}</label>
                            <select
                              value={groqModel}
                              onChange={(e) => setGroqModel(e.target.value)}
                              className="w-full bg-surface-soft/20 border border-hairline rounded-lg px-3 py-2 text-[13px] text-ink outline-none focus:border-[#cc785c] transition-all"
                            >
                              <option value="llama-3.3-70b-versatile">Llama 3.3 70B Versatile</option>
                              <option value="llama-3.1-8b-instant">Llama 3.1 8B Instant</option>
                              <option value="meta-llama/llama-4-scout-17b-16e-instruct">Llama 4 Scout 17B 16E Instruct</option>
                            </select>
                          </div>
                        </div>
                      )}

                      {activeProvider === "openai" && (
                        <div className="space-y-3.5 animate-fade-in">
                          <div className="space-y-1">
                            <label className="text-[12px] font-medium text-body-strong block">{t("api_key")}</label>
                            <div className="relative">
                              <input
                                type={showApiKey ? "text" : "password"}
                                placeholder="sk-proj-..."
                                value={openaiKey}
                                onChange={(e) => setOpenAIKey(e.target.value)}
                                className="w-full bg-surface-soft/20 border border-hairline rounded-lg pl-3 pr-10 py-2 text-[13px] text-ink outline-none focus:border-[#cc785c] transition-all"
                              />
                              <button
                                type="button"
                                onClick={() => setShowApiKey(!showApiKey)}
                                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-ink"
                                aria-label={showApiKey ? "Ẩn khóa API" : "Hiện khóa API"}
                              >
                                {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                              </button>
                            </div>
                          </div>
                          <div className="space-y-1">
                            <label className="text-[12px] font-medium text-body-strong block">{t("active_model")}</label>
                            <select
                              value={openaiModel}
                              onChange={(e) => setOpenAIModel(e.target.value)}
                              className="w-full bg-surface-soft/20 border border-hairline rounded-lg px-3 py-2 text-[13px] text-ink outline-none focus:border-[#cc785c] transition-all"
                            >
                              <option value="gpt-4o">GPT-4o (OpenAI)</option>
                              <option value="gpt-4-turbo">GPT-4 Turbo (OpenAI)</option>
                              <option value="gpt-3.5-turbo">GPT-3.5 Turbo (OpenAI)</option>
                            </select>
                          </div>
                        </div>
                      )}

                      {activeProvider === "ollama" && (
                        <div className="space-y-3.5 animate-fade-in">
                          <div className="space-y-1">
                            <label className="text-[12px] font-medium text-body-strong block">{t("ollama_url")}</label>
                            <input
                              type="text"
                              placeholder="http://localhost:11434"
                              value={ollamaUrl}
                              onChange={(e) => setOllamaUrl(e.target.value)}
                              className="w-full bg-surface-soft/20 border border-hairline rounded-lg px-3 py-2 text-[13px] text-ink outline-none focus:border-[#cc785c] transition-all"
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="text-[12px] font-medium text-body-strong block">{t("ollama_model")}</label>
                            <input
                              type="text"
                              placeholder="llama3"
                              value={ollamaModel}
                              onChange={(e) => setOllamaModel(e.target.value)}
                              className="w-full bg-surface-soft/20 border border-hairline rounded-lg px-3 py-2 text-[13px] text-ink outline-none focus:border-[#cc785c] transition-all"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* RAG & Search Tab */}
                {activeTab === "rag_search" && (
                  <div className="space-y-5 animate-fade-in">
                    <h4 className="font-display text-[15px] font-semibold text-ink border-b border-hairline pb-1.5">
                      {t("rag_mode")}
                    </h4>

                    <div className="space-y-2.5">
                      {[
                        { id: "hybrid", title: t("rag_hybrid"), desc: language === "en" ? "Retrieves with Vector & BM25 in parallel, combining with RRF." : "Chạy song song Vector & BM25, kết hợp RRF tối ưu." },
                        { id: "vector", title: t("rag_vector"), desc: language === "en" ? "Retrieves solely via semantic embedding similarities." : "Chỉ sử dụng Qdrant Vector search, bỏ qua BM25 search." },
                        { id: "keyword", title: t("rag_keyword"), desc: language === "en" ? "Retrieves solely via BM25 lexical keyword matching." : "Chỉ sử dụng Elasticsearch BM25, bỏ qua Vector search." }
                      ].map((mode) => (
                        <button
                          key={mode.id}
                          type="button"
                          onClick={() => setRagMode(mode.id)}
                          className={cn(
                            "w-full text-left p-3 rounded-xl border transition-all duration-200 flex flex-col gap-1",
                            ragMode === mode.id
                              ? "border-[#cc785c] bg-white dark:bg-canvas shadow-sm"
                              : "border-hairline bg-surface-soft/30 hover:bg-surface-soft/60"
                          )}
                        >
                          <span className={cn("text-xs font-semibold", ragMode === mode.id ? "text-[#cc785c]" : "text-ink")}>
                            {mode.title}
                          </span>
                          <span className="text-[11px] text-muted leading-relaxed">
                            {mode.desc}
                          </span>
                        </button>
                      ))}
                    </div>

                    <div className="pt-2 border-t border-hairline space-y-4">
                      {/* Chunk Limit Slider */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <label className="font-medium text-body-strong">{t("chunk_limit")}</label>
                          <span className="font-mono text-[#cc785c] font-semibold bg-[#cc785c]/10 px-2 py-0.5 rounded">
                            {chunkLimit} chunks
                          </span>
                        </div>
                        <input
                          type="range"
                          min="1"
                          max="20"
                          value={chunkLimit}
                          onChange={(e) => setChunkLimit(Number(e.target.value))}
                          className="w-full h-1.5 bg-surface-soft rounded-lg appearance-none cursor-pointer accent-[#cc785c]"
                        />
                      </div>

                      {/* Temperature Slider */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <label className="font-medium text-body-strong">{t("temperature")}</label>
                          <span className="font-mono text-[#cc785c] font-semibold bg-[#cc785c]/10 px-2 py-0.5 rounded">
                            {llmTemperature.toFixed(1)}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0.0"
                          max="1.0"
                          step="0.1"
                          value={llmTemperature}
                          onChange={(e) => setLlmTemperature(Number(e.target.value))}
                          className="w-full h-1.5 bg-surface-soft rounded-lg appearance-none cursor-pointer accent-[#cc785c]"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Preferences Tab */}
                {activeTab === "preferences" && (
                  <div className="space-y-5 animate-fade-in">
                    {/* Theme Preference */}
                    <div className="space-y-2">
                      <h4 className="font-display text-[15px] font-semibold text-ink border-b border-hairline pb-1.5">
                        {t("theme")}
                      </h4>
                      <div className="grid grid-cols-2 gap-4 pt-1">
                        <button
                          type="button"
                          onClick={() => setTheme("light")}
                          className={cn(
                            "flex flex-col items-center gap-2.5 p-4 rounded-xl border text-center transition-all duration-200 select-none",
                            theme === "light"
                              ? "border-[#cc785c] bg-white dark:bg-canvas text-[#cc785c] shadow-sm font-medium"
                              : "border-hairline bg-surface-soft/30 text-muted hover:text-ink hover:bg-surface-soft/80"
                          )}
                        >
                          <Sun className="w-5 h-5 text-amber-500" />
                          <span className="text-xs">{t("theme_light")}</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setTheme("dark")}
                          className={cn(
                            "flex flex-col items-center gap-2.5 p-4 rounded-xl border text-center transition-all duration-200 select-none",
                            theme === "dark"
                              ? "border-[#cc785c] bg-white dark:bg-canvas text-[#cc785c] shadow-sm font-medium"
                              : "border-hairline bg-surface-soft/30 text-muted hover:text-ink hover:bg-surface-soft/80"
                          )}
                        >
                          <Moon className="w-5 h-5 text-indigo-400" />
                          <span className="text-xs">{t("theme_dark")}</span>
                        </button>
                      </div>
                    </div>

                    {/* Language Preference */}
                    <div className="space-y-2 pt-2 border-t border-hairline">
                      <h4 className="font-display text-[15px] font-semibold text-ink border-b border-hairline pb-1.5">
                        {t("language")}
                      </h4>
                      <div className="grid grid-cols-2 gap-4 pt-1">
                        <button
                          type="button"
                          onClick={() => setLanguage("vi")}
                          className={cn(
                            "flex items-center justify-center gap-3 p-4 rounded-xl border transition-all duration-200 select-none",
                            language === "vi"
                              ? "border-[#cc785c] bg-white dark:bg-canvas text-[#cc785c] shadow-sm font-medium"
                              : "border-hairline bg-surface-soft/30 text-muted hover:text-ink hover:bg-surface-soft/80"
                          )}
                        >
                          <Globe className="w-5 h-5 text-emerald-500" />
                          <span className="text-xs font-medium">{t("lang_vi")}</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setLanguage("en")}
                          className={cn(
                            "flex items-center justify-center gap-3 p-4 rounded-xl border transition-all duration-200 select-none",
                            language === "en"
                              ? "border-[#cc785c] bg-white dark:bg-canvas text-[#cc785c] shadow-sm font-medium"
                              : "border-hairline bg-surface-soft/30 text-muted hover:text-ink hover:bg-surface-soft/80"
                          )}
                        >
                          <Globe className="w-5 h-5 text-sky-500" />
                          <span className="text-xs font-medium">{t("lang_en")}</span>
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="px-5 py-4 border-t border-hairline bg-surface-soft/40 flex items-center justify-between gap-4">
              {/* Toast Messages */}
              <div className="flex-1 min-w-0">
                {toast && (
                  <div className={cn(
                    "flex items-center gap-2 p-2 rounded-lg text-xs font-medium animate-fade-in transition-all",
                    toast.type === "success"
                      ? "bg-emerald-50 dark:bg-emerald-950/20 text-emerald-800 dark:text-emerald-400 border border-emerald-200/50 dark:border-emerald-900/40"
                      : "bg-red-50 dark:bg-red-950/20 text-red-800 dark:text-red-400 border border-red-200/50 dark:border-red-900/40"
                  )}>
                    {toast.type === "success" ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />}
                    <span className="truncate">{toast.message}</span>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => setSettingsOpen(false)}
                  className="px-3.5 py-1.5 rounded-lg text-[13px] font-medium border border-hairline text-muted hover:text-ink hover:bg-surface-strong/50 transition-all disabled:opacity-50 select-none"
                >
                  {t("cancel")}
                </button>
                <button
                  type="button"
                  disabled={saving}
                  onClick={handleSaveAllSettings}
                  className="px-4 py-1.5 rounded-lg text-[13px] font-medium bg-[#cc785c] text-white hover:bg-[#a9583e] transition-all shadow-sm flex items-center gap-1.5 disabled:opacity-75 select-none"
                >
                  {saving ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>{t("loading")}</span>
                    </>
                  ) : (
                    <span>{t("save_settings")}</span>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ========================================
   Export Components
   ======================================== */

export { SpikeMarkLogo };
