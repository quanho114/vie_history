import { useEffect, useState, useRef } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { useChatStore } from "@/stores/chatStore";
import { Sidebar } from "./Sidebar";
import { Menu } from "lucide-react";

export function AppShell() {
  useAuthStore();
  const { sessions, activeSessionId, deleteSession, loadSessions } = useChatStore();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const val = localStorage.getItem("sidebar_collapsed");
    return val === null ? true : val === "true";
  });
  
  const deletingSessionIdsRef = useRef<Set<string>>(new Set());

  const toggleSidebarCollapse = () => {
    const nextState = !sidebarCollapsed;
    setSidebarCollapsed(nextState);
    localStorage.setItem("sidebar_collapsed", String(nextState));
  };

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    const activeTimers: NodeJS.Timeout[] = [];

    // Find empty sessions created during this client session
    const emptySessions = sessions.filter(
      (session) => (session.message_count ?? 0) === 0 && (session as any).client_created_at !== undefined
    );

    emptySessions.forEach((session) => {
      if (deletingSessionIdsRef.current.has(session.id)) {
        return;
      }

      const clientTime = (session as any).client_created_at;
      const age = Date.now() - clientTime;

      if (age < 3000) {
        const remaining = 3000 - age;
        const timer = setTimeout(() => {
          const currentActiveId = useChatStore.getState().activeSessionId;
          const currentPathname = window.location.pathname;
          const isCurrentActive = currentPathname === "/chat" && session.id === currentActiveId;
          const freshSession = useChatStore.getState().sessions.find(s => s.id === session.id);
          const isEmpty = freshSession && (freshSession.message_count ?? 0) === 0;

          if (!isCurrentActive && isEmpty && !deletingSessionIdsRef.current.has(session.id)) {
            deletingSessionIdsRef.current.add(session.id);
            deleteSession(session.id).catch((err) => {
              console.error("Failed to clean up empty session in timeout:", err);
            });
          }
        }, remaining);
        activeTimers.push(timer);
        return;
      }

      const isCurrentActiveOnChat = location.pathname === "/chat" && session.id === activeSessionId;
      if (!isCurrentActiveOnChat) {
        deletingSessionIdsRef.current.add(session.id);
        deleteSession(session.id).catch((err) => {
          console.error("Failed to clean up empty session:", err);
        });
      }
    });

    return () => {
      activeTimers.forEach(clearTimeout);
    };
  }, [location.pathname, activeSessionId, sessions, deleteSession]);

  return (
    <div className="flex h-screen bg-[#faf9f5] text-[#1C2120] overflow-hidden select-none">
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebarCollapse}
      />

      {/* Main Content — flush, no rounding, no gap */}
      <main className="flex-1 flex flex-col overflow-hidden bg-[#faf9f5]">
        {/* Mobile Topbar */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-[#e8e2d9] bg-[#faf9f5]">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 hover:bg-[#f0ebe3] rounded-md transition-colors"
            aria-label="Mở menu"
          >
            <Menu className="w-5 h-5 text-[#737A77]" />
          </button>
          <div className="flex items-center gap-2">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-[#1C2120]">
              <path
                d="M9 1v16M1 9h16M3.2 3.2l11.6 11.6M14.8 3.2L3.2 14.8"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
            </svg>
            <span className="font-display text-[18px] font-normal text-[#1C2120]">HistoriAI</span>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 flex flex-col overflow-y-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
