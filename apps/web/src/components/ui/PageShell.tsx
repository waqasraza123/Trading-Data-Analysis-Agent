import type { ReactNode } from "react";
import { PageContainer } from "@/components/layout/PageContainer";

type PageShellProps = {
  children: ReactNode;
};

export function PageShell({ children }: PageShellProps) {
  return <PageContainer>{children}</PageContainer>;
}
