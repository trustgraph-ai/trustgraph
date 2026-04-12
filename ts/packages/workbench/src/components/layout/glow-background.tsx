/**
 * Ambient glow background — forest green radial blobs that drift and pulse.
 *
 * Ported from beep-effect4's GlowEffectPaper, adapted for plain CSS
 * with multiple independent blobs for organic movement.
 */

export function GlowBackground() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 z-0 overflow-hidden animate-[glow-fade-in_1.2s_ease-out_forwards] opacity-0"
    >
      {/* Primary blob — large, centered, slow drift */}
      <div className="absolute left-1/2 top-1/3 h-[70vh] w-[70vw] -translate-x-1/2 -translate-y-1/2 animate-[glow-drift-1_20s_ease-in-out_infinite] rounded-full bg-[radial-gradient(ellipse_at_center,rgba(61,125,61,0.35)_0%,rgba(45,99,45,0.15)_40%,transparent_70%)] blur-[80px]" />

      {/* Secondary blob — smaller, offset right, faster */}
      <div className="absolute right-[10%] top-[20%] h-[50vh] w-[40vw] animate-[glow-drift-2_15s_ease-in-out_infinite] rounded-full bg-[radial-gradient(ellipse_at_center,rgba(92,154,92,0.28)_0%,rgba(61,125,61,0.12)_45%,transparent_70%)] blur-[60px]" />

      {/* Tertiary blob — bottom left, subtle */}
      <div className="absolute bottom-[5%] left-[15%] h-[45vh] w-[45vw] animate-[glow-drift-3_25s_ease-in-out_infinite] rounded-full bg-[radial-gradient(ellipse_at_center,rgba(33,78,33,0.30)_0%,rgba(26,58,26,0.12)_50%,transparent_70%)] blur-[70px]" />
    </div>
  );
}
