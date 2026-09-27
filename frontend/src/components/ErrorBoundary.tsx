import React from 'react'

interface Props {
  children: React.ReactNode
}

interface State {
  hasError: boolean
}

// Required by spec: any render crash shows a friendly message, never a blank screen.
export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('VayuSetu UI error caught by ErrorBoundary:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen items-center justify-center p-8">
          <div className="max-w-md rounded-xl border border-slate-700 bg-slate-900 p-8 text-center">
            <h1 className="mb-2 text-xl font-semibold text-slate-100">Something went wrong</h1>
            <p className="mb-6 text-sm text-slate-400">
              An unexpected error occurred while rendering this page. Please refresh the browser.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500"
            >
              Refresh
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
