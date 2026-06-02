import type { ReactNode } from "react";
import {
  ErrorBoundary as ReactErrorBoundary,
  type FallbackProps,
} from "react-error-boundary";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  /** Optional fallback -- if omitted, a default card is shown */
  fallback?: ReactNode;
}

const errorMessage = (error: unknown): string =>
  error instanceof Error ? error.message : "An unexpected error occurred.";

function DefaultFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <div className="flex h-full items-center justify-center p-8">
      <div className="max-w-md rounded-lg border border-error/30 bg-error/5 p-6 text-center">
        <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-error" />
        <h2 className="mb-2 text-lg font-semibold text-fg">
          Something went wrong
        </h2>
        <p className="mb-4 text-sm text-fg-muted">
          {errorMessage(error)}
        </p>
        <button
          onClick={() => resetErrorBoundary()}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Try Again
        </button>
      </div>
    </div>
  );
}

export function ErrorBoundary({ children, fallback }: Props) {
  return (
    <ReactErrorBoundary
      fallbackRender={(props) => fallback ?? <DefaultFallback {...props} />}
      onError={(error, info) => {
        console.error("[ErrorBoundary]", error, info.componentStack);
      }}
    >
      {children}
    </ReactErrorBoundary>
  );
}
