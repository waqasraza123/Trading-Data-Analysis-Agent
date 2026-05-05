export type NavigationTarget =
  | "commandCenter"
  | "setup"
  | "brief"
  | "dataOnboarding"
  | "scanner"
  | "triage"
  | "quality"
  | "notifications"
  | "journal"
  | "review"
  | "preferences";

export type NavigationItem = {
  key: NavigationTarget;
  href: string;
  label: string;
  section: string;
};

export const navigationItems: NavigationItem[] = [
  { key: "commandCenter", href: "/command-center", label: "Command Center", section: "Daily" },
  { key: "setup", href: "/setup", label: "Setup", section: "Readiness" },
  { key: "brief", href: "/brief", label: "Brief", section: "Daily" },
  { key: "dataOnboarding", href: "/data/onboarding", label: "Data", section: "Readiness" },
  { key: "scanner", href: "/scanner", label: "Scanner", section: "Review" },
  { key: "triage", href: "/triage", label: "Triage", section: "Review" },
  { key: "quality", href: "/quality", label: "Quality", section: "Review" },
  { key: "notifications", href: "/notifications", label: "Notifications", section: "Inbox" },
  { key: "journal", href: "/journal", label: "Journal", section: "Learning" },
  { key: "review", href: "/review/outcomes", label: "Review Outcomes", section: "Learning" },
  { key: "preferences", href: "/preferences/strategy", label: "Preferences", section: "Settings" },
];

export const primaryNavigationTargets: NavigationTarget[] = [
  "commandCenter",
  "setup",
  "brief",
  "dataOnboarding",
  "scanner",
  "triage",
  "quality",
  "notifications",
  "journal",
  "review",
  "preferences",
];

export function navigationHref(target: NavigationTarget, workspaceId?: string | null): string {
  const item = navigationItems.find((candidate) => candidate.key === target);
  const href = item?.href || "/command-center";
  if (!workspaceId) {
    return href;
  }
  return `${href}?workspaceId=${workspaceId}`;
}

export function isActiveNavigationPath(pathname: string, href: string): boolean {
  if (href === "/command-center") {
    return pathname === "/" || pathname === href;
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}
