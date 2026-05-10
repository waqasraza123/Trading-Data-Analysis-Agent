export type MockApiScenario =
  | "empty-onboarding"
  | "partial-onboarding"
  | "ready-onboarding"
  | "backend-unavailable"
  | "command-incomplete"
  | "ready-overview"
  | "overview-missing-sections"
  | "overview-degraded"
  | "daily-workflow-populated"
  | "quick-action-unsupported"
  | "navigation-empty"
  | "safe-copy";

export const mockApiBaseUrl = process.env.E2E_MOCK_API_BASE_URL || "http://127.0.0.1:4010";

export async function setMockApiScenario(request: { post: (url: string, options: { data: unknown }) => Promise<unknown> }, scenario: MockApiScenario) {
  await request.post(`${mockApiBaseUrl}/__mock/scenario`, { data: { scenario } });
}
