import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";
import { Card } from "./Card";
import { SectionHeader } from "./SectionHeader";
import { MOTION_INTERACTIVE_CLASS } from "@/lib/ui/motion";

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
    <Card className={cn(MOTION_INTERACTIVE_CLASS, "p-5", className)}>
      <SectionHeader title={title} eyebrow={eyebrow} description={description} action={action} />
      {children}
    </Card>
  );
}
