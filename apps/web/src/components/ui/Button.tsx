import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  loading?: boolean;
};

type ButtonLinkProps = {
  href: string;
  children: ReactNode;
  variant?: ButtonVariant;
  className?: string;
};

const variantClassName: Record<ButtonVariant, string> = {
  primary: "border-[var(--accent)] bg-[var(--accent)] text-white hover:opacity-90",
  secondary: "border-[var(--line)] bg-[var(--panel)] text-[var(--strong)] hover:bg-slate-50 dark:hover:bg-slate-900",
  ghost: "border-transparent bg-transparent text-[var(--strong)] hover:bg-slate-100 dark:hover:bg-slate-900",
  danger: "border-red-300 bg-red-50 text-red-800 hover:bg-red-100 dark:border-red-900 dark:bg-red-950 dark:text-red-100",
};

export function Button({ variant = "secondary", loading = false, disabled, children, className = "", ...props }: ButtonProps) {
  return (
    <button
      className={buttonClassName(variant, className)}
      {...props}
      disabled={disabled || loading}
    >
      {loading ? "Loading" : children}
    </button>
  );
}

export function ButtonLink({ href, children, variant = "secondary", className = "" }: ButtonLinkProps) {
  return (
    <Link className={buttonClassName(variant, className)} href={href}>
      {children}
    </Link>
  );
}

function buttonClassName(variant: ButtonVariant, className: string): string {
  return `inline-flex min-h-10 items-center justify-center rounded-md border px-3 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${variantClassName[variant]} ${className}`;
}
