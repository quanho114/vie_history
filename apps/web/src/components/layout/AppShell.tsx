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
    <div className="flex h-screen bg-ethereal text-[var(--color-text)] p-0 md:p-6 md:gap-6 overflow-hidden select-none">
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebarCollapse}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden bg-[var(--color-surface)] md:backdrop-blur-[24px] md:rounded-[var(--radius-lg)] md:border md:border-[var(--color-surface-border)] md:shadow-[var(--shadow-ambient)]">
        {/* Mobile Topbar */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-[var(--color-surface-border)] bg-[var(--color-surface)] backdrop-blur-md">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 hover:bg-white/10 rounded-md transition-colors"
            aria-label="Mở menu"
          >
            <Menu className="w-5 h-5 text-[var(--color-muted)]" />
          </button>
          <div className="flex items-center gap-2">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-[var(--color-text)]">
              <path
                d="M9 1v16M1 9h16M3.2 3.2l11.6 11.6M14.8 3.2L3.2 14.8"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
            </svg>
            <span className="font-display text-[18px] font-normal text-[var(--color-text)]" style={{ fontFamily: "var(--font-heading)" }}>HistoriAI</span>
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
