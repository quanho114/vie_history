import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { useChatStore } from "@/stores/chatStore";
import { Sidebar } from "./Sidebar";
import { Menu } from "lucide-react";

export function AppShell() {
  useAuthStore();
  const loadSessions = useChatStore((state) => state.loadSessions);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    return localStorage.getItem("sidebar_collapsed") === "true";
  });

  const toggleSidebarCollapse = () => {
    const nextState = !sidebarCollapsed;
    setSidebarCollapsed(nextState);
    localStorage.setItem("sidebar_collapsed", String(nextState));
  };

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  return (
    <div className="flex h-screen bg-canvas text-body-text">
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebarCollapse}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile Topbar */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-hairline bg-canvas">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 hover:bg-surface-soft rounded-md transition-colors"
            aria-label="Mở menu"
          >
            <Menu className="w-5 h-5 text-muted" />
          </button>
          <div className="flex items-center gap-2">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-ink">
              <path
                d="M9 1v16M1 9h16M3.2 3.2l11.6 11.6M14.8 3.2L3.2 14.8"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
            </svg>
            <span className="font-display text-[18px] font-normal text-ink">HistoriAI</span>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
