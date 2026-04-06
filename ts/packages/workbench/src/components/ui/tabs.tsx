import { cn } from "@/lib/utils";

interface TabItem {
  value: string;
  label: string;
}

interface TabsProps {
  items: TabItem[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

/**
 * Minimal segmented-control / tab bar.
 */
export function Tabs({ items, value, onChange, className }: TabsProps) {
  return (
    <div
      className={cn(
        "flex rounded-lg border border-border bg-surface-100 p-0.5",
        className,
      )}
    >
      {items.map((item) => (
        <button
          key={item.value}
          onClick={() => onChange(item.value)}
          className={cn(
            "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
            value === item.value
              ? "bg-brand-600 text-white"
              : "text-fg-muted hover:text-fg",
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
