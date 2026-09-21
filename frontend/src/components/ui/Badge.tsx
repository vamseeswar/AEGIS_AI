import React, { HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold tracking-wide transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border border-slate-700 bg-slate-800 text-slate-200",
        success:
          "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
        warning:
          "border border-amber-500/30 bg-amber-500/10 text-amber-400",
        danger:
          "border border-rose-500/30 bg-rose-500/10 text-rose-400",
        cyan:
          "border border-cyan-500/30 bg-cyan-500/10 text-cyan-400",
        teal:
          "border border-teal-500/30 bg-teal-500/10 text-teal-400",
        purple:
          "border border-purple-500/30 bg-purple-500/10 text-purple-400",
        secondary:
          "border border-slate-800 bg-slate-900/60 text-slate-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
