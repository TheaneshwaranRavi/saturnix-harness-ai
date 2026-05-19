import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "danger";
const variants: Record<ButtonVariant, string> = {
  primary: "border-cyan-300/40 bg-cyan-400/15 text-cyan-100 hover:bg-cyan-400/25",
  secondary: "border-white/10 bg-white/5 text-slate-100 hover:bg-white/10",
  danger: "border-rose-300/40 bg-rose-500/15 text-rose-100 hover:bg-rose-500/25"
};

export function Button({
  variant = "secondary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      className={cn(
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-md border px-4",
        "text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-60",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}
