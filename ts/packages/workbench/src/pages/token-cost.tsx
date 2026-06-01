import { useAtomRefresh, useAtomValue } from "@effect/atom-react";
import { Coins, Loader2, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { resultData, resultError, resultLoading, tokenCostsAtom } from "@/atoms/workbench";

function formatPrice(price: number) {
  if (!Number.isFinite(price)) return "--";
  return `$${price.toFixed(2)}`;
}

export default function TokenCostPage() {
  const result = useAtomValue(tokenCostsAtom);
  const refresh = useAtomRefresh(tokenCostsAtom);
  const costs = resultData(result, []);
  const loading = resultLoading(result, costs);
  const error = resultError(result);

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <Coins className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">Token Cost</h1>
          {!loading && (
            <span className="ml-2 rounded bg-surface-200 px-2 py-0.5 text-xs text-fg-muted">
              {costs.length} model{costs.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-fg-muted transition-colors hover:bg-surface-200 disabled:opacity-40"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {loading && costs.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="mr-2 h-5 w-5 animate-spin text-fg-subtle" />
          <span className="text-fg-subtle">Loading token costs...</span>
        </div>
      )}

      {error !== null && (
        <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">
          {error}
        </p>
      )}

      {!loading && error === null && costs.length === 0 && (
        <div className="flex flex-1 flex-col items-center justify-center">
          <Coins className="mb-3 h-10 w-10 text-fg-subtle opacity-30" />
          <p className="text-fg-subtle">No token cost data available.</p>
        </div>
      )}

      {costs.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface-100 text-fg-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Model</th>
                <th className="px-4 py-3 font-medium text-right">Input Price ($/1M tokens)</th>
                <th className="px-4 py-3 font-medium text-right">Output Price ($/1M tokens)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {costs.map((cost) => (
                <tr key={cost.model} className="hover:bg-surface-100/50">
                  <td className="px-4 py-3">
                    <span className="font-mono text-sm text-fg">{cost.model}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-fg-muted">
                    {formatPrice(cost.input_price)}
                  </td>
                  <td className="px-4 py-3 text-right text-fg-muted">
                    {formatPrice(cost.output_price)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
