import { createServer } from "node:http";

const port = Number(process.env.E2E_MOCK_API_PORT || 4010);
const demoWorkspaceId = "11111111-1111-4111-8111-111111111111";
const demoUserId = "22222222-2222-4222-8222-222222222222";
const overviewSignalId = "33333333-3333-4333-8333-333333333333";
let scenario = "ready-overview";

const demoWorkspace = {
  id: demoWorkspaceId,
  name: "Demo Analysis Workspace",
  createdAt: "2026-05-06T08:00:00.000Z",
  updatedAt: "2026-05-06T08:00:00.000Z",
};

const demoSymbol = {
  id: "55555555-5555-4555-8555-555555555555",
  symbol: "EURUSD",
  displayName: "EUR/USD",
  marketType: "forex",
  baseAsset: "EUR",
  quoteAsset: "USD",
  pipSize: "0.0001",
  tickSize: null,
  pricePrecision: 5,
  quantityPrecision: 0,
  isActive: true,
  createdAt: "2026-05-06T08:00:00.000Z",
  updatedAt: "2026-05-06T08:00:00.000Z",
};

const server = createServer(async (request, response) => {
  try {
    await handleRequest(request, response);
  } catch (error) {
    sendJson(response, 500, {
      error: {
        code: "mock_api_error",
        message: error instanceof Error ? error.message : "Mock API error",
      },
    });
  }
});

server.listen(port, "127.0.0.1", () => {
  process.stdout.write(`Mock API listening on ${port}\n`);
});

process.on("SIGTERM", () => server.close());
process.on("SIGINT", () => server.close());

async function handleRequest(request, response) {
  const url = new URL(request.url || "/", `http://${request.headers.host || "127.0.0.1"}`);
  if (request.method === "OPTIONS") {
    sendEmpty(response, 204);
    return;
  }
  if (request.method === "POST" && url.pathname === "/__mock/scenario") {
    const body = await readJsonBody(request);
    scenario = typeof body.scenario === "string" ? body.scenario : "ready-overview";
    sendJson(response, 200, { scenario });
    return;
  }
  if (request.method === "GET" && url.pathname === "/health") {
    sendJson(response, 200, { status: "ok", service: "mock-api" });
    return;
  }
  if (scenario === "backend-unavailable" && url.pathname === "/onboarding/status") {
    sendJson(response, 503, { error: { code: "backend_unavailable", message: "Mock backend unavailable." } });
    return;
  }
  if (request.method === "GET" && url.pathname === "/workspaces") {
    sendJson(response, 200, scenario === "empty-onboarding" || scenario === "navigation-empty" ? [] : [demoWorkspace]);
    return;
  }
  if (request.method === "GET" && url.pathname === "/workspaces/default-context") {
    sendJson(
      response,
      200,
      scenario === "empty-onboarding" || scenario === "navigation-empty"
        ? {
            status: "missing_workspace",
            workspace: null,
            user: null,
            availableWorkspaces: [],
          }
        : {
            status: "ready",
            workspace: demoWorkspace,
            user: { id: demoUserId, role: "analyst", name: "Demo Operator" },
            availableWorkspaces: [demoWorkspace],
          },
    );
    return;
  }
  if (request.method === "GET" && url.pathname === "/onboarding/status") {
    sendJson(response, 200, onboardingStatusForScenario());
    return;
  }
  if (request.method === "POST" && url.pathname === "/onboarding/actions") {
    sendJson(response, 200, {
      actionType: "create_workspace",
      status: "completed",
      message: "Workspace created.",
      workspaceId: demoWorkspaceId,
      userId: demoUserId,
      artifactIds: { workspaceId: demoWorkspaceId },
      onboardingStatus: partialOnboardingStatus(),
    });
    return;
  }
  const overviewMatch = url.pathname.match(/^\/workspaces\/([^/]+)\/overview$/);
  if (request.method === "GET" && overviewMatch) {
    if (scenario === "command-incomplete") {
      sendJson(response, 503, { error: { code: "overview_unavailable", message: "Overview unavailable." } });
      return;
    }
    sendJson(response, 200, overviewForScenario());
    return;
  }
  const quickActionMatch = url.pathname.match(/^\/workspaces\/([^/]+)\/quick-actions$/);
  if (request.method === "POST" && quickActionMatch) {
    if (scenario === "quick-action-unsupported") {
      sendJson(response, 400, { error: { code: "unsupported_action", message: "This backend-safe quick action is not available." } });
      return;
    }
    sendJson(response, 200, {
      workspaceId: demoWorkspaceId,
      actionType: "run_daily_workflow",
      status: "completed",
      summary: "Deterministic daily workflow completed.",
      createdArtifactIdsJson: { dailyWorkflowRunId: "44444444-4444-4444-8444-444444444444" },
      resultJson: { status: "completed" },
      warnings: [],
      missingSections: [],
    });
    return;
  }
  if (request.method === "POST" && url.pathname === "/daily-workflows/run") {
    sendJson(response, 200, dailyWorkflowRun());
    return;
  }
  if (request.method === "GET" && url.pathname === "/symbols") {
    sendJson(response, 200, scenario === "navigation-empty" ? [] : [demoSymbol]);
    return;
  }
  if (request.method === "GET" && url.pathname === "/health/workers") {
    sendJson(response, 200, { workers: [], staleWorkers: 0 });
    return;
  }
  if (request.method === "GET" && url.pathname === `/provider-health/workspaces/${demoWorkspaceId}/summary`) {
    sendJson(response, 200, {
      workspaceId: demoWorkspaceId,
      generatedAt: "2026-05-06T08:00:00.000Z",
      totalContextCount: 1,
      readyForDeterministicAnalysisCount: scenario === "overview-degraded" ? 0 : 1,
      freshCount: scenario === "overview-degraded" ? 0 : 1,
      staleCount: scenario === "overview-degraded" ? 1 : 0,
      degradedCount: 0,
      missingCandleCount: scenario === "overview-degraded" ? 2 : 0,
      providerFailureCount: 0,
      latestSnapshotAt: "2026-05-06T08:00:00.000Z",
      statusCountsJson: {},
      warningCountsJson: {},
    });
    return;
  }
  if (request.method === "GET" && arrayResponsePaths().some((path) => matchesPath(url.pathname, path))) {
    sendJson(response, 200, []);
    return;
  }
  if (request.method === "GET" && nullableMissingPaths().some((path) => matchesPath(url.pathname, path))) {
    sendJson(response, 404, { detail: "Optional endpoint unavailable." });
    return;
  }
  if (request.method === "POST" && url.pathname.includes("/historical-cases/search")) {
    sendJson(response, 200, { matches: [], warnings: [] });
    return;
  }
  if (["POST", "PATCH", "DELETE"].includes(request.method || "")) {
    sendJson(response, 404, { detail: "Optional endpoint unavailable." });
    return;
  }
  sendJson(response, 404, { detail: "Optional endpoint unavailable." });
}

function onboardingStatusForScenario() {
  if (scenario === "empty-onboarding" || scenario === "navigation-empty") {
    return missingWorkspaceOnboardingStatus();
  }
  if (scenario === "partial-onboarding" || scenario === "command-incomplete") {
    return partialOnboardingStatus();
  }
  if (scenario === "overview-degraded") {
    return {
      ...readyOnboardingStatus(),
      status: { readinessLabel: "degraded", readinessScore: 78, summary: "Readiness degraded." },
      warnings: ["Data stale."],
      missingSections: ["data_freshness"],
    };
  }
  return readyOnboardingStatus();
}

function missingWorkspaceOnboardingStatus() {
  return {
    status: { readinessLabel: "needs_setup", readinessScore: 10, summary: "Setup incomplete." },
    workspace: { exists: false, workspaceId: null, name: null },
    user: { exists: false, userId: null, role: null },
    symbols: { configured: false, count: 0, missing: true },
    dataSources: { configured: false, count: 0, missing: true, providerReady: false },
    dataFreshness: { label: "unknown", summary: "Freshness context unavailable." },
    watchlists: { configured: false, count: 0, missing: true },
    scanConfigs: { configured: false, count: 0, missing: true },
    dailyWorkflow: { available: true, lastRunStatus: null },
    demoMode: { available: true, enabled: true },
    nextStep: {
      key: "create_workspace",
      title: "Create workspace",
      description: "Create a workspace before daily analysis can load.",
      route: "/setup",
      actionType: "create_workspace",
    },
    steps: [
      step("workspace", "Workspace", "Create or select a workspace for deterministic analysis.", "incomplete", "/setup", "create_workspace"),
      step("symbols", "Symbols", "Seed symbols for analysis context.", "blocked", "/setup", "seed_symbols"),
      step("data_sources", "Data sources", "Configure a data source before freshness checks.", "blocked", "/data/onboarding", "seed_default_data_sources"),
      step("watchlist", "Watchlist", "Create a watchlist for deterministic scans.", "blocked", "/scanner", "create_basic_watchlist"),
      step("scan_config", "Scan config", "Create a scan config for the daily workflow.", "blocked", "/scanner", "create_basic_scan_config"),
    ],
    warnings: [],
    missingSections: ["workspace", "symbols", "data_sources", "watchlist", "scan_config"],
  };
}

function partialOnboardingStatus() {
  return {
    ...missingWorkspaceOnboardingStatus(),
    status: { readinessLabel: "needs_setup", readinessScore: 48, summary: "Setup incomplete." },
    workspace: { exists: true, workspaceId: demoWorkspaceId, name: demoWorkspace.name },
    user: { exists: true, userId: demoUserId, role: "analyst" },
    symbols: { configured: true, count: 3, missing: false },
    dataSources: { configured: false, count: 0, missing: true, providerReady: false },
    dataFreshness: { label: "no_data", summary: "No final candles are available." },
    watchlists: { configured: false, count: 0, missing: true },
    scanConfigs: { configured: false, count: 0, missing: true },
    nextStep: {
      key: "configure_data_source",
      title: "Configure data source",
      description: "Review data onboarding before scanner setup.",
      route: "/data/onboarding",
      actionType: "seed_default_data_sources",
    },
    steps: [
      step("workspace", "Workspace", "Create or select a workspace for deterministic analysis.", "complete", "/setup", null),
      step("symbols", "Symbols", "Seed symbols for analysis context.", "complete", "/setup", null),
      step("data_sources", "Data sources", "Configure a data source before freshness checks.", "incomplete", "/data/onboarding", "seed_default_data_sources"),
      step("watchlist", "Watchlist", "Create a watchlist for deterministic scans.", "incomplete", "/scanner", "create_basic_watchlist"),
      step("scan_config", "Scan config", "Create a scan config for the daily workflow.", "incomplete", "/scanner", "create_basic_scan_config"),
    ],
    missingSections: ["data_sources", "watchlist", "scan_config"],
  };
}

function readyOnboardingStatus() {
  return {
    ...partialOnboardingStatus(),
    status: { readinessLabel: "ready", readinessScore: 96, summary: "Command center ready." },
    dataSources: { configured: true, count: 1, missing: false, providerReady: true },
    dataFreshness: { label: "fresh", summary: "Data fresh." },
    watchlists: { configured: true, count: 1, missing: false },
    scanConfigs: { configured: true, count: 1, missing: false },
    nextStep: {
      key: "open_command_center",
      title: "Open command center",
      description: "Workspace is ready for deterministic analysis.",
      route: "/command-center",
      actionType: null,
    },
    steps: [
      step("workspace", "Workspace", "Create or select a workspace for deterministic analysis.", "complete", "/setup", null),
      step("symbols", "Symbols", "Seed symbols for analysis context.", "complete", "/setup", null),
      step("data_sources", "Data sources", "Configure a data source before freshness checks.", "complete", "/data/onboarding", null),
      step("watchlist", "Watchlist", "Create a watchlist for deterministic scans.", "complete", "/scanner", null),
      step("scan_config", "Scan config", "Create a scan config for the daily workflow.", "complete", "/scanner", null),
    ],
    warnings: [],
    missingSections: [],
  };
}

function step(key, title, description, state, route, actionType) {
  return { key, title, description, state, route, actionType, metadata: {} };
}

function overviewForScenario() {
  const overview = readyOverview();
  if (scenario === "overview-missing-sections") {
    return { ...overview, missingSections: ["notifications", "journal"], warnings: ["Optional endpoint unavailable."] };
  }
  if (scenario === "overview-degraded") {
    return {
      ...overview,
      readiness: { status: "degraded", label: "Setup incomplete", summary: "Review setup context.", metadataJson: {} },
      dataFreshness: { status: "stale", label: "Data stale", summary: "Data stale.", metadataJson: { freshCount: 0, staleOrDegradedCount: 2 } },
      warnings: ["Data stale."],
    };
  }
  return overview;
}

function readyOverview() {
  return {
    workspaceId: demoWorkspaceId,
    generatedAt: "2026-05-06T08:00:00.000Z",
    overviewVersion: "e2e-smoke",
    readiness: { status: "ready", label: "Command center ready", summary: "Workspace is ready for deterministic analysis.", metadataJson: {} },
    dataFreshness: { status: "fresh", label: "Data fresh", summary: "Fresh data contexts are available.", metadataJson: { freshCount: 2, staleOrDegradedCount: 0 } },
    providerHealth: { status: "healthy", label: "Provider context healthy", summary: "No provider issues in the smoke fixture.", metadataJson: { missingCandleCount: 0 } },
    dailyBrief: { status: "completed", label: "Brief ready", summary: "Brief context is available.", metadataJson: {} },
    workflow: { status: "completed", label: "Workflow ready", summary: "Daily workflow context is available.", metadataJson: { staleInstanceCount: 0 } },
    reviewFirst: [overviewItem("review-first-1", "Review first context", "Setup context is ready for review.")],
    needsConfirmation: [overviewItem("needs-confirmation-1", "Confirmation context", "Additional confirmation context is pending.", "Needs confirmation.")],
    avoidConditions: [overviewItem("avoid-1", "Avoid condition", "No directional signal.", "No directional signal.")],
    outcomeUpdates: [overviewItem("outcome-1", "Outcome update", "Outcome ready.", "Outcome ready.")],
    pendingActions: [overviewItem("pending-action-1", "Run deterministic scan", "Run deterministic scan.", "Review setup context.", "/scanner")],
    notifications: { unreadCount: 0, acknowledgedCount: 1, latest: [], metadataJson: {} },
    journalPrompts: [overviewItem("journal-1", "Journal prompt", "Review setup context.", "Review setup context.", "/journal")],
    qualityWarnings: [overviewItem("quality-1", "Quality warning", "Review recommended.", "Review recommended.", "/quality")],
    navigationHints: [],
    missingSections: [],
    warnings: [],
  };
}

function overviewItem(id, title, summary, reason = "Review recommended.", href = `/signals/${overviewSignalId}`) {
  return {
    id,
    title,
    summary,
    reason,
    symbolId: demoSymbol.id,
    symbol: demoSymbol.symbol,
    timeframe: "1m",
    signalId: overviewSignalId,
    analysisRunId: null,
    bias: "no directional signal",
    confidenceLabel: "medium",
    priorityLabel: "review recommended",
    setupQualityLabel: "review recommended",
    freshnessLabel: "data fresh",
    dataQualityLabel: "outcome ready",
    href,
    metadataJson: {},
  };
}

function dailyWorkflowRun() {
  return {
    id: "44444444-4444-4444-8444-444444444444",
    workspaceId: demoWorkspaceId,
    workflowType: "daily_scan",
    status: "completed",
    summary: "Deterministic daily workflow completed.",
    watchlistId: null,
    preferenceProfileId: null,
    requestedByUserId: null,
    startedAt: "2026-05-06T08:00:00.000Z",
    completedAt: "2026-05-06T08:00:01.000Z",
    failedStepKey: null,
    optionsJson: {},
    filtersJson: {},
    createdArtifactIdsJson: {},
    resultJson: {},
    errorJson: null,
    createdAt: "2026-05-06T08:00:00.000Z",
    updatedAt: "2026-05-06T08:00:01.000Z",
  };
}

function arrayResponsePaths() {
  return [
    "/market-memory/snapshots",
    "/read-models/signals",
    "/market-watchlists",
    "/scanner-presets",
    "/scheduled-scan-configs",
    "/scheduled-scan-configs/due",
    "/daily-workflows/runs",
    "/daily-routines/templates",
    "/daily-routines/runs",
    "/journal-entries",
    "/provider-health/snapshots",
    "/provider-polling/requests",
    "/notification-events",
    "/data-sources",
    "/provider-credentials",
    "/preference-profiles",
    "/analysis-runs",
    "/signal-digests",
    "/operator-reviews",
    "/action-items/due",
    "/outcomes/performance/patterns",
    "/profile-diagnostics/strategy-profiles",
    "/profile-diagnostics/patterns",
    "/profile-diagnostics/recommendations",
    "/confidence-calibration/runs",
    "/cohort-drift/results/recent",
    "/pattern-attribution/runs",
    "/backtest-experiments/cohorts",
  ];
}

function nullableMissingPaths() {
  return [
    "/read-models/command-center",
    `/workspaces/${demoWorkspaceId}/daily-brief/latest`,
    `/preference-profiles/default`,
    `/runtime-supervisor/health`,
    `/product-readiness/latest`,
  ];
}

function matchesPath(pathname, pattern) {
  return pathname === pattern || pathname.startsWith(`${pattern}/`);
}

async function readJsonBody(request) {
  const chunks = [];
  for await (const chunk of request) {
    chunks.push(chunk);
  }
  const text = Buffer.concat(chunks).toString("utf8");
  if (!text) {
    return {};
  }
  return JSON.parse(text);
}

function sendJson(response, status, payload) {
  response.writeHead(status, {
    "content-type": "application/json",
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,PATCH,DELETE,OPTIONS",
    "access-control-allow-headers": "content-type,authorization,x-user-id,x-workspace-id",
  });
  response.end(JSON.stringify(payload));
}

function sendEmpty(response, status) {
  response.writeHead(status, {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,PATCH,DELETE,OPTIONS",
    "access-control-allow-headers": "content-type,authorization,x-user-id,x-workspace-id",
  });
  response.end();
}
