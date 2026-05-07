export type NavigationTarget =
  | "commandCenter"
  | "onboarding"
  | "dashboard"
  | "setup"
  | "readiness"
  | "brief"
  | "dataOnboarding"
  | "scanner"
  | "equityResearch"
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
  shortLabel?: string;
  description: string;
};

export const navigationItems: NavigationItem[] = [
  { key: "commandCenter", href: "/command-center", label: "Command Center", shortLabel: "Command", section: "Command Center", description: "Daily cockpit and workflow overview" },
  { key: "onboarding", href: "/onboarding", label: "Onboarding", section: "Command Center", description: "First-run setup and readiness gate" },
  { key: "dashboard", href: "/dashboard", label: "Dashboard", section: "Command Center", description: "Read-only market intelligence summary" },
  { key: "brief", href: "/brief", label: "Brief", section: "Brief", description: "Workspace daily brief and review focus" },
  { key: "dataOnboarding", href: "/data/onboarding", label: "Data", section: "Data", description: "Freshness, source, and gap readiness" },
  { key: "scanner", href: "/scanner", label: "Scanner", section: "Scanner", description: "Watchlists and deterministic scan configs" },
  { key: "equityResearch", href: "/equity-research", label: "Equity Research", shortLabel: "Equities", section: "Scanner", description: "Stock universes and swing setup candidate review" },
  { key: "triage", href: "/triage", label: "Triage", section: "Triage", description: "Prioritized deterministic signal review" },
  { key: "quality", href: "/quality", label: "Quality", section: "Quality", description: "Observed behavior and reliability diagnostics" },
  { key: "notifications", href: "/notifications", label: "Notifications", shortLabel: "Inbox", section: "Notifications", description: "In-app intelligence event review" },
  { key: "journal", href: "/journal", label: "Journal", section: "Journal", description: "Observation notes and outcome reflection" },
  { key: "review", href: "/review/outcomes", label: "Review Outcomes", shortLabel: "Outcomes", section: "Journal", description: "Observed outcome review queue" },
  { key: "setup", href: "/setup", label: "Setup", section: "Preferences", description: "Workspace setup wizard" },
  { key: "readiness", href: "/readiness", label: "Readiness", section: "Preferences", description: "Daily-use readiness checklist" },
  { key: "preferences", href: "/preferences/strategy", label: "Preferences", section: "Preferences", description: "Review filter profiles" },
];

export const primaryNavigationTargets: NavigationTarget[] = [
  "commandCenter",
  "onboarding",
  "dashboard",
  "brief",
  "dataOnboarding",
  "scanner",
  "equityResearch",
  "triage",
  "quality",
  "notifications",
  "journal",
  "review",
  "preferences",
];

export const secondaryNavigationTargets: NavigationTarget[] = ["setup", "readiness"];

export const navigationSections = Array.from(new Set(navigationItems.map((item) => item.section)));

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
