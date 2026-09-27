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
        <div className="flex h-screen items-center justify-center bg-haze p-8">
          <div className="panel max-w-md p-8 text-center">
            <h1 className="font-display text-xl font-bold text-soot">Something went wrong</h1>
            <p className="measure mx-auto mt-2 mb-6 text-sm text-ash">
              An unexpected error occurred while rendering this page. Refresh the browser to reload the dashboard.
            </p>
            <button onClick={() => window.location.reload()} className="btn-primary">
              Refresh
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
