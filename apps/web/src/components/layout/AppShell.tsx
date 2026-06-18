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
    <div className="flex h-screen bg-[#EBE7E0] text-[#1C2120] p-0 md:p-6 md:gap-6 overflow-hidden select-none">
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebarCollapse}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden bg-[#faf9f5] md:bg-[#faf9f5]/90 md:backdrop-blur-md md:rounded-[24px] md:border md:border-white/40 md:shadow-[0_20px_40px_rgba(11,48,48,0.04)]">
        {/* Mobile Topbar */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-hairline bg-[#faf9f5]">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 hover:bg-[#f5f0e8] rounded-md transition-colors"
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
        <div className="flex-1 flex flex-col overflow-hidden">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
