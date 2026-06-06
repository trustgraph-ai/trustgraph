/**
 * Ambient glow background -- forest green radial fields that drift and pulse.
 *
 * Ported from beep-effect4's GlowEffectPaper, adapted for plain CSS
 * with multiple independent fields for organic movement.
 */

const primaryGlow = "radial-gradient(ellipse at center, var(--tg-glow-primary-start) 0%, var(--tg-glow-primary-mid) 40%, transparent 70%)";
const secondaryGlow = "radial-gradient(ellipse at center, var(--tg-glow-secondary-start) 0%, var(--tg-glow-secondary-mid) 45%, transparent 70%)";
const tertiaryGlow = "radial-gradient(ellipse at center, var(--tg-glow-tertiary-start) 0%, var(--tg-glow-tertiary-mid) 50%, transparent 70%)";

export function GlowBackground() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 z-0 overflow-hidden animate-[glow-fade-in_1.2s_ease-out_forwards] opacity-0"
    >
      <div
        className="absolute left-1/2 top-1/3 h-[70vh] w-[70vw] -translate-x-1/2 -translate-y-1/2 animate-[glow-drift-1_20s_ease-in-out_infinite] rounded-full blur-[80px]"
        style={{ background: primaryGlow }}
      />

      <div
        className="absolute right-[10%] top-[20%] h-[50vh] w-[40vw] animate-[glow-drift-2_15s_ease-in-out_infinite] rounded-full blur-[60px]"
        style={{ background: secondaryGlow }}
      />

      <div
        className="absolute bottom-[5%] left-[15%] h-[45vh] w-[45vw] animate-[glow-drift-3_25s_ease-in-out_infinite] rounded-full blur-[70px]"
        style={{ background: tertiaryGlow }}
      />
    </div>
  );
}
