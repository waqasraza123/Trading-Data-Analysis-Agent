export const defaultProductName = "AI Trading SaaS Starter Kit";
export const defaultProductDescription =
  "Open-source infrastructure for building explainable, read-only AI trading intelligence products.";
export const defaultSiteUrl = "https://ai-trading-agent-seven.vercel.app";
export const defaultRepositoryUrl =
  "https://github.com/waqasraza123/Trading-Data-Analysis-Agent";

export type ProductConfig = {
  name: string;
  description: string;
  siteUrl: string;
  repositoryUrl: string;
  templateUrl: string;
};

export function getProductConfig(): ProductConfig {
  const repositoryUrl = normalizeUrl(
    process.env.NEXT_PUBLIC_REPOSITORY_URL,
    defaultRepositoryUrl,
  );

  return {
    name: process.env.NEXT_PUBLIC_APP_NAME?.trim() || defaultProductName,
    description: defaultProductDescription,
    siteUrl: normalizeUrl(process.env.NEXT_PUBLIC_SITE_URL, defaultSiteUrl),
    repositoryUrl,
    templateUrl: `${repositoryUrl}/generate`,
  };
}

function normalizeUrl(value: string | undefined, fallback: string): string {
  const candidate = value?.trim() || fallback;
  try {
    return new URL(candidate).toString().replace(/\/$/, "");
  } catch {
    return fallback;
  }
}
