import { Component, ReactNode, ErrorInfo } from "react"

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info.componentStack)
    this.props.onError?.(error, info)

    // Report to Sentry if available (integration with @sentry/react)
    if (import.meta.env.PROD) {
      this.reportToSentry(error, info)
    }
  }

  private async reportToSentry(error: Error, info: ErrorInfo) {
    try {
      // Dynamic import to avoid bundling Sentry in development
      const { captureException } = await import('@sentry/react')
      captureException(error, {
        extra: {
          componentStack: info.componentStack
        }
      })
    } catch {
      // Sentry not available, silently fail
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div
            role="alert"
            aria-live="assertive"
            className="flex items-center justify-center h-screen bg-[var(--canvas)]"
          >
            <div className="text-center p-8 max-w-md">
              <div className="mb-4">
                <svg
                  className="w-16 h-16 mx-auto text-[var(--error)]"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
                  />
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-[var(--ink)] mb-2 font-display">
                Đã xảy ra lỗi
              </h1>
              <p className="text-[var(--muted)] mb-6">
                Có lỗi không mong muốn xảy ra. Vui lòng tải lại trang.
              </p>
              <div className="flex gap-3 justify-center">
                <button
                  onClick={() => window.location.reload()}
                  className="px-4 py-2 bg-[var(--coral)] text-white rounded-lg hover:bg-[var(--coral-hover)] transition-colors"
                >
                  Tải lại trang
                </button>
                <button
                  onClick={() => this.setState({ hasError: false, error: undefined })}
                  className="px-4 py-2 bg-[var(--surface-soft)] text-[var(--ink)] rounded-lg hover:bg-[var(--surface-strong)] transition-colors"
                >
                  Thử lại
                </button>
              </div>
              {/* Error details - shown in development */}
              {import.meta.env.DEV && this.state.error && (
                <details className="mt-6 text-left text-xs text-[var(--muted)] bg-[var(--surface-soft)] rounded p-3">
                  <summary className="cursor-pointer font-medium mb-2">Chi tiết lỗi (Development)</summary>
                  <pre className="mt-2 overflow-auto max-h-48 text-left whitespace-pre-wrap">
                    {this.state.error.name}: {this.state.error.message}
                    {'\n\n'}
                    {this.state.error.stack}
                  </pre>
                </details>
              )}
            </div>
          </div>
        )
      )
    }
    return this.props.children
  }
}

// ─── Functional Error Boundary Hook ───────────────────────────────────────────
// For use with Suspense boundaries and functional components

interface FallbackProps {
  error: Error
  resetError: () => void
}

interface UseErrorBoundaryOptions {
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

/**
 * Hook for functional error boundaries
 * Note: This requires ErrorBoundary from react-error-boundary package
 * or can be used with the class-based ErrorBoundary above
 */
export function useErrorBoundary(options?: UseErrorBoundaryOptions) {
  // This is a placeholder - actual implementation would use react-error-boundary
  // For now, we export the class-based ErrorBoundary which is already in use
  return {
    showBoundary: (error: Error) => {
      console.error('Error boundary triggered:', error)
      options?.onError?.(error, { componentStack: '', errorInfo: '' })
    }
  }
}
