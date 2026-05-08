import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const workingDir = process.cwd();
const inWebWorkspace = path.basename(workingDir) === "web";
const repoRoot = inWebWorkspace ? path.dirname(workingDir) : workingDir;
const appRoot = path.resolve(repoRoot, "apps/web");
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const manifestPath = path.resolve(scriptDir, "motion-rollout-manifest.json");
const isJsonOutput = process.argv.includes("--json");
const failOnLegacyHelpers = !process.argv.includes("--allow-legacy");

const motionRevealTokenPatterns = [
  /motionRevealDensityStyle\(/,
  /motionRevealPresetClass\(/,
  /motionRevealProfileStyle\(/,
  /motionRevealStyle\(/,
  /motionRevealClass\(/,
  /motionCardClass/,
];

const legacyHelperPatterns = [/motionRevealClass\(/, /motionRevealStyle\(/];

const privateImportPattern = /from\s+["']@\/components\/ui\/motion["']/;

function hasMotionRevealToken(contents) {
  return motionRevealTokenPatterns.some((pattern) => pattern.test(contents));
}

function hasLegacyMotionToken(contents) {
  return legacyHelperPatterns.some((pattern) => pattern.test(contents));
}

async function readManifest() {
  const rawManifest = await fs.readFile(manifestPath, "utf8");
  const parsedManifest = JSON.parse(rawManifest);
  if (!Array.isArray(parsedManifest?.routes)) {
    throw new Error("motion rollout manifest missing routes array");
  }
  return parsedManifest.routes;
}

function makeFailure(route, reason) {
  return { route, reason, status: "fail" };
}

async function checkRoutes() {
  const checks = await readManifest();
  const failures = [];
  const summaries = [];
  const report = [];
  const routeNames = new Set();

  for (const check of checks) {
    if (routeNames.has(check.route)) {
      failures.push(makeFailure(check.route, "duplicate manifest entry"));
      summaries.push(`✗ ${check.route}: duplicate manifest entry`);
      continue;
    }
    routeNames.add(check.route);

    const file = path.resolve(appRoot, check.page);
    try {
      const source = await fs.readFile(file, "utf8");
      const requiredTokens = Array.isArray(check.requires) ? check.requires : [];
      const missing = requiredTokens.filter((token) => !source.includes(token));
      if (missing.length > 0) {
        failures.push({ route: check.route, reason: `missing required token(s): ${missing.join(", ")}` });
        summaries.push(`✗ ${check.route}: missing ${missing.join(", ")}`);
        report.push({
          route: check.route,
          path: check.page,
          status: "fail",
          reason: `missing required token(s): ${missing.join(", ")}`,
        });
        continue;
      }

      if (!hasMotionRevealToken(source) && !requiredTokens.includes("motionRevealStyle")) {
        failures.push({ route: check.route, reason: "no motion helper token usage detected" });
        summaries.push(`✗ ${check.route}: no motion helper token usage`);
        report.push({
          route: check.route,
          path: check.page,
          status: "fail",
          reason: "no motion helper token usage detected",
        });
        continue;
      }

      if (privateImportPattern.test(source)) {
        failures.push({ route: check.route, reason: "legacy motion import path used (@/components/ui/motion)" });
        summaries.push(`✗ ${check.route}: legacy motion import path used (@/components/ui/motion)`);
        report.push({
          route: check.route,
          path: check.page,
          status: "fail",
          reason: "legacy motion import path used (@/components/ui/motion)",
        });
        continue;
      }

      const legacyHelpersUsed = hasLegacyMotionToken(source);
      if (failOnLegacyHelpers && legacyHelpersUsed) {
        failures.push({
          route: check.route,
          reason: "legacy motion helper call detected (motionRevealClass/motionRevealStyle)",
        });
        summaries.push(`✗ ${check.route}: legacy motion helper call detected`);
        report.push({
          route: check.route,
          path: check.page,
          status: "fail",
          reason: "legacy motion helper call detected (motionRevealClass/motionRevealStyle)",
        });
        continue;
      }

      if (legacyHelpersUsed) {
        report.push({
          route: check.route,
          path: check.page,
          status: "warn",
          reason: "legacy motion helper call remains in use",
        });
      }

      summaries.push(`✓ ${check.route}: motion rollout wiring present`);
      report.push({
        route: check.route,
        path: check.page,
        status: "pass",
      });
    } catch (error) {
      const reason = String(error instanceof Error ? error.message : error);
      failures.push({ route: check.route, reason });
      summaries.push(`✗ ${check.route}: ${String(error)}`);
      report.push({
        route: check.route,
        path: check.page,
        status: "fail",
        reason,
      });
    }
  }

  if (isJsonOutput) {
    process.stdout.write(
      `${JSON.stringify(
        {
          totalRoutes: checks.length,
          summary: {
            pass: report.filter((item) => item.status === "pass").length,
            warn: report.filter((item) => item.status === "warn").length,
            fail: failures.length,
          },
          routes: report,
          failedRoutes: failures,
          config: {
            routeCount: checks.length,
            failOnLegacyHelpers,
          },
        },
        null,
        2
      )}\n`
    );
  } else {
    for (const item of summaries) {
      process.stdout.write(`${item}\n`);
    }
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
