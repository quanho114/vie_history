import { useEffect, lazy, Suspense } from "react"
import { Navigate, Route, Routes, useLocation } from "react-router-dom"
import { AppShell } from "@/components/layout"
import { useAuthStore } from "@/stores/authStore"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { PageSkeleton } from "@/components/ui"
import { ToastContainer } from "@/components/UI/ToastContainer"
import { ConfirmModal } from "@/components/UI/ConfirmModal"

// Lazy load all pages — reduces initial bundle size by loading
// each page only when its route is first accessed.
const ChatPage = lazy(() => import("@/pages/ChatPage").then(m => ({ default: m.ChatPage })))
const DocumentsPage = lazy(() => import("@/pages/DocumentsPage").then(m => ({ default: m.DocumentsPage })))
const DocumentDetailPage = lazy(() => import("@/pages/DocumentDetailPage").then(m => ({ default: m.DocumentDetailPage })))
const LoginPage = lazy(() => import("@/pages/LoginPage").then(m => ({ default: m.LoginPage })))
const WikiBrowserPage = lazy(() => import("@/pages/WikiBrowserPage").then(m => ({ default: m.WikiBrowserPage })))
const WikiDetailPage = lazy(() => import("@/pages/WikiDetailPage").then(m => ({ default: m.WikiDetailPage })))
const TimelinePage = lazy(() => import("@/pages/TimelinePage").then(m => ({ default: m.TimelinePage })))
const GraphPage = lazy(() => import("@/pages/GraphPage").then(m => ({ default: m.GraphPage })))
const AdminPage = lazy(() => import("@/pages/AdminPage").then(m => ({ default: m.AdminPage })))
const BrainBuilderPage = lazy(() => import("@/pages/BrainBuilderPage").then(m => ({ default: m.BrainBuilderPage })))
const DraftsReviewPage = lazy(() => import("@/pages/DraftsReviewPage").then(m => ({ default: m.DraftsReviewPage })))
const KnowledgeEvolutionDashboard = lazy(() => import("@/pages/KnowledgeEvolutionDashboard").then(m => ({ default: m.KnowledgeEvolutionDashboard })))
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage").then(m => ({ default: m.NotFoundPage })))

export default function App() {
  const { isAuthenticated, user, checkAuth, logout } = useAuthStore()
  const location = useLocation()

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  // Auto-logout when any API call returns 401 (token expired)
  useEffect(() => {
    const handleExpired = () => {
      logout()
    }
    window.addEventListener("auth:expired", handleExpired)
    return () => window.removeEventListener("auth:expired", handleExpired)
  }, [logout])

  // Silence background music immediately on any route change unless the user is on the Knowledge Map screen (/graph)
  useEffect(() => {
    if (location.pathname !== "/graph") {
      const globalAudio = (window as any).__histori_bg_audio__
      if (globalAudio) {
        try {
          globalAudio.pause()
          ;(window as any).__histori_bg_audio__ = null
          console.log("Navigated away from Map: stopped background music.")
        } catch (e) {
          console.warn("Failed to pause background audio", e)
        }
      }
    }
  }, [location.pathname])

  const defaultRedirect = "/chat"
  const protectedRoutes = isAuthenticated ? <AppShell /> : <Navigate to="/login" replace />
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        // Log to error reporting service
        console.error('App Error:', error, errorInfo)
      }}
    >
      <Routes>
        <Route path="/login" element={isAuthenticated ? <Navigate to={defaultRedirect} replace /> : <Suspense fallback={<PageSkeleton />}><LoginPage /></Suspense>} />
        <Route element={protectedRoutes}>
          <Route index element={<Navigate to={defaultRedirect} replace />} />
          <Route path="/chat" element={<Suspense fallback={<PageSkeleton />}><ChatPage /></Suspense>} />
          <Route path="/documents" element={<Suspense fallback={<PageSkeleton />}><DocumentsPage /></Suspense>} />
          <Route path="/documents/:id" element={<Suspense fallback={<PageSkeleton />}><DocumentDetailPage /></Suspense>} />
          <Route path="/ingest" element={<Navigate to="/documents" replace />} />
          <Route path="/admin" element={<Suspense fallback={<PageSkeleton />}><AdminPage /></Suspense>} />
          <Route path="/wiki" element={<Suspense fallback={<PageSkeleton />}><WikiBrowserPage /></Suspense>} />
          <Route path="/wiki/:slug" element={<Suspense fallback={<PageSkeleton />}><WikiDetailPage /></Suspense>} />
          <Route path="/wiki/drafts/review" element={<Suspense fallback={<PageSkeleton />}><DraftsReviewPage /></Suspense>} />
          <Route path="/graph/drafts/review" element={<Suspense fallback={<PageSkeleton />}><KnowledgeEvolutionDashboard /></Suspense>} />
          <Route path="/timeline" element={<Suspense fallback={<PageSkeleton />}><TimelinePage /></Suspense>} />
          <Route path="/graph" element={<Suspense fallback={<PageSkeleton />}><GraphPage /></Suspense>} />
          <Route path="/brain-builder" element={<Suspense fallback={<PageSkeleton />}><BrainBuilderPage /></Suspense>} />
        </Route>
        {/* 404 – outside AppShell so no sidebar */}
        <Route path="*" element={<Suspense fallback={<PageSkeleton />}><NotFoundPage /></Suspense>} />
      </Routes>
      <ToastContainer />
      <ConfirmModal />
    </ErrorBoundary>
  )
}
