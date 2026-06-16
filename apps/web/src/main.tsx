import React from "react"
import ReactDOM from "react-dom/client"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter } from "react-router-dom"
import { HelmetProvider, Helmet } from "react-helmet-async"
import * as Sentry from "@sentry/react"
import App from "./App"
import "./index.css"
import { ErrorBoundary } from "@/components/ErrorBoundary"

// Initialize Sentry for error monitoring
Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN || "",
  integrations: [Sentry.browserTracingIntegration()],
  tracesSampleRate: 0.1,
  environment: import.meta.env.MODE,
})

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
      <HelmetProvider>
        <Helmet>
          <title>HistoriAI - Hệ thống Trí tuệ Nhân tạo Lịch sử Việt Nam</title>
          <meta name="description" content="Trợ lý học thuật tối ưu hỗ trợ tìm kiếm tài liệu lưu trữ, xác thực sự kiện và thiết lập bản đồ tri thức lịch sử tự động." />
          <meta name="keywords" content="lịch sử việt nam, trí tuệ nhân tạo, AI lịch sử, tra cứu lịch sử, wiki việt nam" />
          <meta property="og:title" content="HistoriAI - Hệ thống Trí tuệ Nhân tạo Lịch sử Việt Nam" />
          <meta property="og:description" content="Trợ lý học thuật tối ưu hỗ trợ tìm kiếm tài liệu lưu trữ, xác thực sự kiện và thiết lập bản đồ tri thức lịch sử tự động." />
          <meta property="og:type" content="website" />
        </Helmet>
        <Sentry.ErrorBoundary fallback={({ error, resetError }) => (
          <div className="min-h-screen flex items-center justify-center bg-[#faf8f4]">
            <div className="text-center p-8">
              <h2 className="text-2xl font-serif text-[#141413] mb-4">Lỗi không mong muốn</h2>
              <p className="text-[#6c6a64] mb-6">Đã xảy ra lỗi. Vui lòng thử tải lại trang.</p>
              <button
                onClick={resetError}
                className="px-6 py-2 bg-[#cc785c] text-white rounded-xl font-medium hover:bg-[#a9583e] transition-colors"
              >
                Thử lại
              </button>
            </div>
          </div>
        )}>
          <ErrorBoundary>
            <QueryClientProvider client={queryClient}>
              <BrowserRouter>
                <App />
              </BrowserRouter>
            </QueryClientProvider>
          </ErrorBoundary>
        </Sentry.ErrorBoundary>
      </HelmetProvider>
  </React.StrictMode>,
)
