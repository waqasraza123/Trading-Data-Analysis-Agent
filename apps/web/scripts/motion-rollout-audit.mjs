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
const failOnCoverageGaps = !process.argv.includes("--allow-coverage-gaps");

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

const ignoredPathSegment = (segment) =>
  segment.startsWith(".") || (segment.startsWith("(") && segment.endsWith(")"));

function hasMotionRevealToken(contents) {
  return motionRevealTokenPatterns.some((pattern) => pattern.test(contents));
}

function hasLegacyMotionToken(contents) {
  return legacyHelperPatterns.some((pattern) => pattern.test(contents));
}

function normalizeRouteFromFile(pageFile) {
  const relative = path.relative(appRoot, pageFile);
  const routeDir = path.dirname(relative);
  const segments = routeDir === "." || routeDir === "" ? [] : routeDir.split(path.sep);
  if (segments[0] === "app") {
    segments.shift();
  }
  if (segments.length === 0) {
    return "";
  }
  return segments.join("/");
}

function normalizeRouteForManifest(route) {
  return String(route || "").replace(/^\/+/, "");
}

async function collectManifest() {
  const rawManifest = await fs.readFile(manifestPath, "utf8");
  const parsedManifest = JSON.parse(rawManifest);
  const routes = parsedManifest?.routes;
  if (!Array.isArray(routes)) {
    throw new Error("motion rollout manifest missing routes array");
  }

  return {
    version: parsedManifest.version || "1.0",
    exemptRoutes: new Set(Array.isArray(parsedManifest.exemptRoutes) ? parsedManifest.exemptRoutes : []),
    routes: routes.map((entry) => ({
      ...entry,
      route: normalizeRouteForManifest(entry.route),
    })),
  };
}

async function collectPageRoutes() {
  const discovered = new Set();
  const walk = async (entryPath) => {
    const entries = await fs.readdir(entryPath, { withFileTypes: true });
    for (const entry of entries) {
      if (ignoredPathSegment(entry.name)) {
        continue;
      }
      const absolutePath = path.resolve(entryPath, entry.name);
      if (entry.isDirectory()) {
        await walk(absolutePath);
        continue;
      }

      if (entry.isFile() && entry.name === "page.tsx") {
        const route = normalizeRouteFromFile(absolutePath);
        const hasIgnoredSegment = route
          .split("/")
          .some((segment) => ignoredPathSegment(segment));
        if (hasIgnoredSegment) {
          continue;
        }
        discovered.add(route);
      }
    }
  };

  await walk(appRoot);
  return discovered;
}

function makeFailure(route, reason) {
  return { route, reason, status: "fail" };
}

function routeHasPathManifestMismatch(route, manifestEntry) {
  return manifestEntry?.page && manifestEntry.page !== `app/${route}/page.tsx`;
}

async function checkRoutes() {
  const manifest = await collectManifest();
  const checks = manifest.routes;
  const manifestRoutes = new Set(checks.map((check) => check.route));
  const discoveredRoutes = await collectPageRoutes();

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
        failures.push(makeFailure(check.route, `missing required token(s): ${missing.join(", ")}`));
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
        failures.push(makeFailure(check.route, "no motion helper token usage detected"));
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
        failures.push(makeFailure(check.route, "legacy motion import path used (@/components/ui/motion)"));
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
        failures.push(
          makeFailure(
            check.route,
            "legacy motion helper call detected (motionRevealClass/motionRevealStyle)"
          )
        );
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

      if (routeHasPathManifestMismatch(check.route, checks.find((entry) => entry.route === check.route))) {
        summaries.push(`! ${check.route}: manifest page path likely outdated`);
        report.push({
          route: check.route,
          path: check.page,
          status: "warn",
          reason: "manifest page path not ending with current route/page.tsx",
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
      failures.push(makeFailure(check.route, reason));
      summaries.push(`✗ ${check.route}: ${reason}`);
      report.push({
        route: check.route,
        path: check.page,
        status: "fail",
        reason,
      });
    }
  }

  const discoveredNonExempt = new Set(
    Array.from(discoveredRoutes).filter((route) => !manifest.exemptRoutes.has(route))
  );

  const staleManifestRoutes = [];
  const missingFromManifest = [];

  for (const discoveredRoute of discoveredNonExempt) {
    if (!manifestRoutes.has(discoveredRoute)) {
      missingFromManifest.push(discoveredRoute);
    }
  }

  for (const routeEntry of manifestRoutes) {
    if (!discoveredRoutes.has(routeEntry)) {
      staleManifestRoutes.push(routeEntry);
    }
  }

  for (const route of missingFromManifest) {
    if (failOnCoverageGaps) {
      failures.push(makeFailure(route, "discovered route missing from motion rollout manifest"));
    }
    summaries.push(`✗ coverage: discovered route '${route}' not in manifest`);
    report.push({
      route,
      path: `app/${route}/page.tsx`,
      status: failOnCoverageGaps ? "fail" : "warn",
      reason: "discovered route not listed in motion rollout manifest",
    });
  }

  for (const route of staleManifestRoutes) {
    if (failOnCoverageGaps) {
      failures.push(makeFailure(route, "manifest route no longer present as app/page.tsx"));
    }
    summaries.push(`✗ coverage: manifest route '${route}' no longer has page route`);
    const manifestEntry = checks.find((entry) => entry.route === route);
    report.push({
      route,
      path: manifestEntry?.page || "unknown",
      status: failOnCoverageGaps ? "fail" : "warn",
      reason: "manifest route has no corresponding app/page.tsx file",
    });
  }

  const discoveredCount = discoveredNonExempt.size;

  if (isJsonOutput) {
    process.stdout.write(
      `${JSON.stringify(
        {
          totalManifestRoutes: checks.length,
          manifestVersion: manifest.version,
          coverage: {
            discoveredRoutes: Array.from(discoveredNonExempt).sort(),
            manifestRoutes: Array.from(manifestRoutes).sort(),
            staleManifestRoutes,
            missingFromManifest,
            exemptRoutes: Array.from(manifest.exemptRoutes).sort(),
            discoveredCount,
          },
          summary: {
            pass: report.filter((item) => item.status === "pass").length,
            warn: report.filter((item) => item.status === "warn").length,
            fail: failures.length,
          },
          routes: report,
          failedRoutes: failures,
          config: {
            failOnLegacyHelpers,
            failOnCoverageGaps,
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

  process.stdout.write(
    `\nMotion rollout gate: all ${checks.length} manifest routes pass with ${discoveredCount} discovered route(s) checked.\n`
  );
}

void checkRoutes();
