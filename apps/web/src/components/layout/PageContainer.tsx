import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";
import { AnimatedSection } from "@/components/ui/motion";

type PageContainerProps = {
  children: ReactNode;
  className?: string;
};

export function PageContainer({ children, className }: PageContainerProps) {
  return (
    <AnimatedSection
      as="main"
      preset="fade-in"
      className={cn("mx-auto w-full max-w-[1540px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7", className)}
    >
      {children}
    </AnimatedSection>
  );
}
