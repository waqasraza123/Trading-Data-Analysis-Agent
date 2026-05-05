import type { ReactNode } from "react";

type CardProps = {
  children: ReactNode;
  className?: string;
};

export function Card({ children, className = "" }: CardProps) {
  return <div className={`surface rounded-lg p-5 ${className}`}>{children}</div>;
}

export function MutedCard({ children, className = "" }: CardProps) {
  return <div className={`muted-surface rounded-lg p-4 ${className}`}>{children}</div>;
}
