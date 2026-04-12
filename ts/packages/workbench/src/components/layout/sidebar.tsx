import { NavLink } from "react-router";
import {
  MessageSquareText,
  LibraryBig,
  Rotate3d,
  MessageCircleCode,
  Coins,
  BrainCircuit,
  Workflow,
  Plug,
  Settings,
  Wifi,
  WifiOff,
  Database,
  ChevronDown,
} from "lucide-react";
import { BeepGraphLogo } from "./beep-graph-logo";
import { cn } from "@/lib/utils";
import { useConnectionState } from "@/providers/socket-provider";
import { useSessionStore } from "@/hooks/use-session-store";
import { useFlows } from "@/hooks/use-flows";
import { useSettings } from "@/providers/settings-provider";

// ---------------------------------------------------------------------------
// Nav item
// ---------------------------------------------------------------------------

interface NavItemProps {
  to: string;
  icon: React.ElementType;
  label: string;
}

function NavItem({ to, icon: Icon, label }: NavItemProps) {
  return (
    <NavLink to={to} className="w-full rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 focus-visible:ring-offset-surface-50">
      {({ isActive }) => (
        <div
          className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
            isActive
              ? "bg-brand-600/20 text-brand-400"
              : "text-fg-muted hover:bg-surface-200 hover:text-fg",
          )}
        >
          <Icon className="h-4 w-4 shrink-0" />
          <span className="truncate">{label}</span>
        </div>
      )}
    </NavLink>
  );
}

// ---------------------------------------------------------------------------
// Connection status badge
// ---------------------------------------------------------------------------

function ConnectionBadge() {
  const state = useConnectionState();

  const isConnected =
    state.status === "connected" ||
    state.status === "authenticated" ||
    state.status === "unauthenticated";

  const isWarning = state.status === "unauthenticated";

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium",
        isWarning
          ? "text-warning"
          : isConnected
            ? "text-success"
            : "text-fg-muted",
      )}
    >
      <span
        className={cn(
          "h-2 w-2 shrink-0 rounded-full",
          isWarning
            ? "bg-warning animate-pulse"
            : isConnected
              ? "bg-success animate-pulse"
              : "bg-fg-subtle",
        )}
      />
      {isConnected ? (
        <Wifi className="h-3.5 w-3.5" />
      ) : (
        <WifiOff className="h-3.5 w-3.5" />
      )}
      <span className="truncate capitalize">
        {isWarning ? "Connected (no auth)" : state.status}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Flow selector dropdown
// ---------------------------------------------------------------------------

function FlowSelectorDropdown() {
  const { flows } = useFlows();
  const flowId = useSessionStore((s) => s.flowId);
  const setFlowId = useSessionStore((s) => s.setFlowId);
  const collection = useSettings((s) => s.settings.collection);

  return (
    <div className="space-y-2 px-3">
      {/* Flow selector */}
      <div className="space-y-1">
        <label htmlFor="sidebar-flow-select" className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-fg-subtle">
          <Workflow className="h-3 w-3" />
          Flow
        </label>
        <div className="relative">
          <select
            id="sidebar-flow-select"
            value={flowId}
            onChange={(e) => setFlowId(e.target.value)}
            className="w-full appearance-none rounded-md border border-border bg-surface-100 py-1.5 pl-2.5 pr-7 text-xs text-fg focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="default">default</option>
            {flows.map((f) => (
              <option key={f.id} value={f.id}>
                {f.id}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-fg-subtle" />
        </div>
      </div>

      {/* Collection badge */}
      <div className="flex items-center gap-1.5 rounded-md bg-surface-100 px-2.5 py-1.5 text-xs text-fg-muted">
        <Database className="h-3 w-3 shrink-0 text-fg-subtle" />
        <span className="truncate">{collection}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

export function Sidebar() {
  const { featureSwitches } = useSettings((s) => s.settings);

  return (
    <aside aria-label="Sidebar" className="flex h-screen w-sidebar shrink-0 flex-col border-r border-border bg-surface-50">
      {/* Logo area */}
      <div className="flex h-14 items-center gap-2.5 px-4">
        <BeepGraphLogo className="h-7 w-7 shrink-0 text-brand-400" />
        <span className="text-lg font-bold text-fg">Beep Graph</span>
      </div>

      {/* Divider */}
      <div className="mx-3 border-t border-border" />

      {/* Flow & collection selectors */}
      <div className="py-3">
        <FlowSelectorDropdown />
      </div>

      {/* Divider */}
      <div className="mx-3 border-t border-border" />

      {/* Navigation links */}
      <nav aria-label="Main navigation" className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-3">
        <NavItem to="/chat" icon={MessageSquareText} label="Chat" />
        <NavItem to="/library" icon={LibraryBig} label="Library" />
        <NavItem to="/graph" icon={Rotate3d} label="Graph" />
        <NavItem to="/prompts" icon={MessageCircleCode} label="Prompts" />
        <NavItem to="/token-cost" icon={Coins} label="Token Cost" />
        <NavItem to="/knowledge-cores" icon={BrainCircuit} label="Knowledge Cores" />
        <NavItem to="/flows" icon={Workflow} label="Flows" />
        {featureSwitches.mcpTools && (
          <NavItem to="/mcp-tools" icon={Plug} label="MCP Tools" />
        )}
        <NavItem to="/settings" icon={Settings} label="Settings" />
      </nav>

      {/* Footer: connection badge */}
      <div className="border-t border-border px-2 py-2">
        <ConnectionBadge />
      </div>
    </aside>
  );
}
