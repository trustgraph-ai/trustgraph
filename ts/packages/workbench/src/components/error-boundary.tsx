import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  /** Optional fallback -- if omitted, a default card is shown */
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  override render() {
    if (this.state.hasError) {
      if (this.props.fallback !== undefined) return this.props.fallback;

      return (
        <div className="flex h-full items-center justify-center p-8">
          <div className="max-w-md rounded-lg border border-error/30 bg-error/5 p-6 text-center">
            <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-error" />
            <h2 className="mb-2 text-lg font-semibold text-fg">
              Something went wrong
            </h2>
            <p className="mb-4 text-sm text-fg-muted">
              {this.state.error?.message ?? "An unexpected error occurred."}
            </p>
            <button
              onClick={this.handleReset}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
