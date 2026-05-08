import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "quiet";
type ButtonSize = "sm" | "md" | "lg";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
};

type ButtonLinkProps = {
  href: string;
  children: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
};

const variantClassName: Record<ButtonVariant, string> = {
  primary: "border-[var(--accent)] bg-[linear-gradient(135deg,var(--accent)_0%,var(--accent-strong)_100%)] text-white shadow-soft hover:shadow-glow",
  secondary: "premium-control text-[var(--strong)]",
  ghost: "border-transparent bg-transparent text-[var(--strong)] hover:bg-[var(--surface-muted)]",
  quiet: "border-transparent bg-[var(--surface-muted)] text-[var(--strong)] hover:bg-[var(--surface-elevated)]",
  danger: "border-rose-300 bg-rose-50 text-rose-800 hover:bg-rose-100 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-100",
};

const sizeClassName: Record<ButtonSize, string> = {
  sm: "min-h-8 px-2.5 py-1.5 text-xs",
  md: "min-h-10 px-3.5 py-2 text-sm",
  lg: "min-h-11 px-4 py-2.5 text-sm",
};

export function Button({ variant = "secondary", size = "md", loading = false, disabled, children, className, ...props }: ButtonProps) {
  return (
    <button
      className={buttonClassName(variant, size, className)}
      {...props}
      disabled={disabled || loading}
    >
      {loading ? "Loading" : children}
    </button>
  );
}

export function ButtonLink({ href, children, variant = "secondary", size = "md", className }: ButtonLinkProps) {
  return (
    <Link className={buttonClassName(variant, size, className)} href={href}>
      {children}
    </Link>
  );
}

function buttonClassName(variant: ButtonVariant, size: ButtonSize, className?: string): string {
  return cn(
    "inline-flex items-center justify-center gap-2 rounded-xl border font-semibold transition duration-200 focus-visible:ring-4 focus-visible:ring-[var(--ring)] disabled:cursor-not-allowed disabled:opacity-60",
    "motion-hover-lift",
    sizeClassName[size],
    variantClassName[variant],
    className,
  );
}
