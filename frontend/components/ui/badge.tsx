import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type BadgeTone = "green" | "amber" | "red" | "cyan" | "neutral";

const tones: Record<BadgeTone, string> = {
  green: "border-emerald-300/30 bg-emerald-400/10 text-emerald-200",
  amber: "border-amber-300/30 bg-amber-400/10 text-amber-200",
  red: "border-rose-300/30 bg-rose-400/10 text-rose-200",
  cyan: "border-cyan-300/30 bg-cyan-400/10 text-cyan-200",
  neutral: "border-white/15 bg-white/10 text-slate-200"
};

export function Badge({
  tone = "neutral",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      className={cn(
        "inline-flex min-h-7 items-center rounded-md border px-2.5 text-xs font-medium",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}
