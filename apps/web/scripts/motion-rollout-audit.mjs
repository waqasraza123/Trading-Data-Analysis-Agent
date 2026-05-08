import fs from "node:fs/promises";
import path from "node:path";

const workingDir = process.cwd();
const inWebWorkspace = path.basename(workingDir) === "web";
const repoRoot = inWebWorkspace ? path.dirname(workingDir) : workingDir;
const appRoot = path.resolve(repoRoot, "apps/web");

const checks = [
  { route: "command-center", page: "app/command-center/page.tsx", requires: ["AnimatedSection"] },
  { route: "dashboard", page: "app/dashboard/page.tsx", requires: ["AnimatedSection"] },
  { route: "triage", page: "app/triage/page.tsx", requires: ["AnimatedSection"] },
  { route: "brief", page: "app/brief/page.tsx", requires: ["AnimatedSection"] },
  { route: "scanner", page: "app/scanner/page.tsx", requires: ["AnimatedSection"] },
  { route: "quality", page: "app/quality/page.tsx", requires: ["AnimatedSection"] },
  { route: "notifications", page: "app/notifications/page.tsx", requires: ["AnimatedSection"] },
  { route: "journal", page: "app/journal/page.tsx", requires: ["AnimatedSection"] },
  { route: "review/outcomes", page: "app/review/outcomes/page.tsx", requires: ["AnimatedSection"] },
  { route: "readiness", page: "app/readiness/page.tsx", requires: ["AnimatedSection"] },
  { route: "onboarding", page: "app/onboarding/page.tsx", requires: ["AnimatedSection"] },
  { route: "setup", page: "app/setup/page.tsx", requires: ["AnimatedSection"] },
  { route: "signals/[signalId]", page: "app/signals/[signalId]/page.tsx", requires: ["AnimatedSection"] },
  { route: "symbols/[symbolId]", page: "app/symbols/[symbolId]/page.tsx", requires: ["AnimatedSection"] },
  { route: "data/onboarding", page: "app/data/onboarding/page.tsx", requires: ["AnimatedSection"] },
  { route: "equity-research", page: "app/equity-research/page.tsx", requires: ["AnimatedSection"] },
  { route: "preferences/strategy", page: "app/preferences/strategy/page.tsx", requires: ["AnimatedSection"] },
  { route: "demo", page: "app/demo/page.tsx", requires: ["AnimatedSection"] },
  { route: "journal/[entryId]", page: "app/journal/[entryId]/page.tsx", requires: ["AnimatedSection"] },
];

const hasMotionRevealToken = (contents) =>
  contents.includes("motionRevealDensityStyle(") ||
  contents.includes("motionRevealPresetClass(") ||
  contents.includes("motionRevealProfileStyle(") ||
  contents.includes("motionRevealStyle(") ||
  contents.includes("motionRevealClass(");

async function checkRoutes() {
  const failures = [];
  const summaries = [];

  for (const check of checks) {
    const file = path.resolve(appRoot, check.page);
    try {
      const source = await fs.readFile(file, "utf8");
      const missing = check.requires.filter((token) => !source.includes(token));
      if (missing.length > 0) {
        failures.push({ route: check.route, reason: `missing required token(s): ${missing.join(", ")}` });
        summaries.push(`✗ ${check.route}: missing ${missing.join(", ")}`);
        continue;
      }

      if (!hasMotionRevealToken(source)) {
        failures.push({ route: check.route, reason: "no motion helper token usage detected" });
        summaries.push(`✗ ${check.route}: no motion helper token usage`);
        continue;
      }

      summaries.push(`✓ ${check.route}: motion rollout wiring present`);
    } catch (error) {
      failures.push({ route: check.route, reason: String(error) });
      summaries.push(`✗ ${check.route}: ${String(error)}`);
    }
  }

  for (const item of summaries) {
    process.stdout.write(`${item}\n`);
  }

  if (failures.length > 0) {
    process.stderr.write(`\nMotion rollout gate: ${failures.length} route(s) require review.\n`);
    for (const failure of failures) {
      process.stderr.write(`- ${failure.route}: ${failure.reason}\n`);
    }
    process.exit(1);
  }

  process.stdout.write(`\nMotion rollout gate: all ${checks.length} routes pass.\n`);
}

void checkRoutes();
