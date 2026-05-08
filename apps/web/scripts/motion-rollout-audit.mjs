import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const workingDir = process.cwd();
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDir, "..");
const manifestPath = path.resolve(scriptDir, "motion-rollout-manifest.json");
const cliArgs = process.argv.slice(2);
const isJsonOutput = cliArgs.includes("--json");
const strictMode = cliArgs.includes("--strict");
const isReportOutput = cliArgs.includes("--report");
const reportPathArg = cliArgs.find((arg) => arg.startsWith("--report-path="));
const defaultReportPath = "docs/motion-rollout-audit-report.md";
const reportOutputPath = path.resolve(
  workingDir,
  reportPathArg && path.isAbsolute(reportPathArg.slice(14))
    ? reportPathArg.slice(14)
    : reportPathArg
    ? reportPathArg.slice(14)
    : path.relative(workingDir, path.resolve(appRoot, defaultReportPath))
);
const failOnLegacyHelpers = strictMode ? true : !process.argv.includes("--allow-legacy");
const failOnCoverageGaps = strictMode ? true : !process.argv.includes("--allow-coverage-gaps");

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
const revealDensityValues = new Set(["compact", "regular", "comfortable"]);
const defaultRevealDensity = "regular";

function formatCell(value) {
  return String(value || "")
    .replace(/\\/g, "\\\\")
    .replace(/\r?\n/g, " ")
    .replace(/\|/g, "\\|")
    .trim();
}

function buildMarkdownReport(payload) {
  const rows = payload.routes.map((item) => ({
    route: item.route || "unknown",
    path: item.path || "unknown",
    status: item.status || "warn",
    density: item.revealDensity || defaultRevealDensity,
    notes: item.reason || "",
  }));

  const lines = [
    "# Motion Rollout Audit Report",
    "",
    `Generated: ${payload.generatedAt}`,
    "",
    "## Summary",
    `- Manifest version: ${payload.manifestVersion}`,
    `- Strict mode: ${payload.strictMode ? "enabled" : "disabled"}`,
    `- Total manifest routes: ${payload.totalManifestRoutes}`,
    `- Discovered routes checked: ${payload.coverage.discoveredCount}`,
    `- Exempt routes: ${payload.coverage.exemptRoutes.length}`,
    `- Pass: ${payload.summary.pass}`,
    `- Warn: ${payload.summary.warn}`,
    `- Fail: ${payload.summary.fail}`,
    "",
    "## Coverage",
    `- Discovered route list: ${payload.coverage.discoveredRoutes.length > 0 ? payload.coverage.discoveredRoutes.join(", ") : "none"}`,
    `- Manifest route list: ${payload.coverage.manifestRoutes.length > 0 ? payload.coverage.manifestRoutes.join(", ") : "none"}`,
    `- Missing from manifest: ${payload.coverage.missingFromManifest.length > 0 ? payload.coverage.missingFromManifest.join(", ") : "none"}`,
    `- Stale manifest routes: ${payload.coverage.staleManifestRoutes.length > 0 ? payload.coverage.staleManifestRoutes.join(", ") : "none"}`,
    "",
    "## Route checks",
    "| Route | Status | Path | Reveal density | Notes |",
    "| --- | --- | --- | --- | --- |",
    ...rows.map(
      (row) =>
        `| \`${formatCell(row.route)}\` | ${formatCell(row.status)} | \`${formatCell(row.path)}\` | ${formatCell(row.density)} | ${formatCell(row.notes)} |`
    ),
    "",
    "## Manifest validation issues",
  ];

  if (payload.manifestValidationIssues.length > 0) {
    for (const issue of payload.manifestValidationIssues) {
      const issueId = issue.route || `index ${issue.index ?? "n/a"}`;
      lines.push(`- ${issueId}: ${formatCell(issue.issue)}`);
      if (issue.manifestPath) {
        lines.push(`  - path: \`${formatCell(issue.manifestPath)}\``);
      }
    }
  } else {
    lines.push("- No manifest validation issues found.");
  }

  lines.push("");
  return `${lines.join("\n")}\n`;
}

async function writeReport(outputPath, payload) {
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, buildMarkdownReport(payload), "utf8");
}

const ignoredPathSegment = (segment) =>
  segment.startsWith(".") || (segment.startsWith("(") && segment.endsWith(")"));
const isString = (value) => typeof value === "string";

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

function isArrayOfStrings(value) {
  return Array.isArray(value) && value.every((item) => isString(item));
}

function collectManifestIssues(entry) {
  const issues = [];
  if (!entry || typeof entry !== "object") {
    return ["manifest entry must be an object"];
  }

  if (!isString(entry.route) || entry.route.trim().length === 0) {
    issues.push("route must be a non-empty string");
  }

  if (!isString(entry.page) || entry.page.trim().length === 0) {
    issues.push("page must be a non-empty string");
  } else if (!entry.page.endsWith("/page.tsx")) {
    issues.push("page must end with /page.tsx");
  } else if (!entry.page.startsWith("app/")) {
    issues.push("page must be under app/");
  }

  if (entry.requires === undefined) {
    issues.push("requires is required");
  } else if (!isArrayOfStrings(entry.requires)) {
    issues.push("requires must be an array of strings");
  }

  if (entry.revealDensity !== undefined && !revealDensityValues.has(entry.revealDensity)) {
    issues.push(`revealDensity must be one of ${Array.from(revealDensityValues).join(", ")}`);
  }

  return issues;
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
    validationIssues: routes.flatMap((entry, index) => {
      const route = normalizeRouteForManifest(entry?.route);
      const normalizedPath = isString(entry?.page) ? entry.page : "";
      const issues = collectManifestIssues(entry);
      return issues.map((issue) => ({
        route: route || `unavailable_${index}`,
        index,
        issue,
        manifestPath: normalizedPath,
      }));
    }),
    routes: routes.map((entry) => ({
      ...entry,
      route: normalizeRouteForManifest(entry?.route),
      page: isString(entry?.page) ? entry.page : "",
      requires: isArrayOfStrings(entry?.requires) ? entry.requires : [],
      revealDensity: entry?.revealDensity,
      expectedPage: normalizeRouteForManifest(entry?.route)
        ? `app/${normalizeRouteForManifest(entry?.route)}/page.tsx`
        : "app/page.tsx",
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

async function checkRoutes() {
  const manifest = await collectManifest();
  const checks = manifest.routes;
  const manifestRoutes = new Set(checks.map((check) => check.route));
  const discoveredRoutes = await collectPageRoutes();
  const routeDensityByRoute = new Map(
    checks.map((check) => [check.route, check.revealDensity || defaultRevealDensity])
  );

  const failures = [];
  const summaries = [];
  const report = [];
  const routeNames = new Set();

  for (const issue of manifest.validationIssues) {
    const route = issue.route;
    const reason = `manifest issue (${issue.index}): ${issue.issue}`;
    failures.push(makeFailure(route, reason));
    summaries.push(`✗ manifest route '${route}': ${issue.issue}`);
    report.push({
      route,
      path: issue.manifestPath || "unknown",
      revealDensity: routeDensityByRoute.get(route) || defaultRevealDensity,
      status: "fail",
      reason,
    });
  }

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
          revealDensity: routeDensityByRoute.get(check.route) || defaultRevealDensity,
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
          revealDensity: routeDensityByRoute.get(check.route) || defaultRevealDensity,
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
          revealDensity: routeDensityByRoute.get(check.route) || defaultRevealDensity,
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
          revealDensity: routeDensityByRoute.get(check.route) || defaultRevealDensity,
          status: "fail",
          reason: "legacy motion helper call detected (motionRevealClass/motionRevealStyle)",
        });
        continue;
      }

      if (legacyHelpersUsed) {
        report.push({
          route: check.route,
          path: check.page,
          revealDensity: routeDensityByRoute.get(check.route) || defaultRevealDensity,
          status: "warn",
          reason: "legacy motion helper call remains in use",
        });
      }

      if (check.expectedPage && check.page !== check.expectedPage) {
        summaries.push(`! ${check.route}: manifest page path likely outdated`);
        report.push({
          route: check.route,
          path: check.page,
          revealDensity: routeDensityByRoute.get(check.route) || defaultRevealDensity,
          status: "warn",
          reason: "manifest page path not ending with current route/page.tsx",
        });
      }

      summaries.push(`✓ ${check.route}: motion rollout wiring present`);
        report.push({
          route: check.route,
          path: check.page,
          revealDensity: routeDensityByRoute.get(check.route) || defaultRevealDensity,
          status: "pass",
        });
    } catch (error) {
      const reason = String(error instanceof Error ? error.message : error);
      failures.push(makeFailure(check.route, reason));
      summaries.push(`✗ ${check.route}: ${reason}`);
      report.push({
        route: check.route,
        path: check.page,
        revealDensity: routeDensityByRoute.get(check.route) || defaultRevealDensity,
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
      revealDensity: "unassigned",
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
      revealDensity: routeDensityByRoute.get(route) || "unassigned",
      status: failOnCoverageGaps ? "fail" : "warn",
      reason: "manifest route has no corresponding app/page.tsx file",
    });
  }

  const discoveredCount = discoveredNonExempt.size;

  const reportPayload = {
    totalManifestRoutes: checks.length,
    manifestVersion: manifest.version,
    strictMode,
    coverage: {
      discoveredRoutes: Array.from(discoveredNonExempt).sort(),
      manifestRoutes: Array.from(manifestRoutes).sort(),
      staleManifestRoutes,
      missingFromManifest,
      exemptRoutes: Array.from(manifest.exemptRoutes).sort(),
      discoveredCount,
    },
    manifestValidationIssues: manifest.validationIssues,
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
    generatedAt: new Date().toISOString(),
  };

  if (isReportOutput) {
    await writeReport(reportOutputPath, reportPayload);
    if (!isJsonOutput) {
      process.stdout.write(`Motion rollout audit report written to ${reportOutputPath}\n`);
    }
  }

  if (isJsonOutput) {
    process.stdout.write(`${JSON.stringify(reportPayload, null, 2)}\n`);
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
