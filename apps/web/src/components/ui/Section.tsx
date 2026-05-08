import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";
import { Card } from "./Card";
import { SectionHeader } from "./SectionHeader";

type SectionProps = {
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  description?: string;
};

export function Section({ title, eyebrow, action, children, className, description }: SectionProps) {
  return (
    <Card className={cn("motion-hover-lift p-5", className)}>
      <SectionHeader title={title} eyebrow={eyebrow} description={description} action={action} />
      {children}
    </Card>
  );
}
