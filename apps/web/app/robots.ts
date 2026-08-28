import type { MetadataRoute } from "next";
import { getProductConfig } from "@/config/product";

export default function robots(): MetadataRoute.Robots {
  const product = getProductConfig();
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [
        "/api/",
        "/account",
        "/brief",
        "/command-center",
        "/dashboard",
        "/data/",
        "/demo",
        "/equity-research",
        "/journal",
        "/notifications",
        "/onboarding",
        "/preferences/",
        "/quality",
        "/readiness",
        "/review/",
        "/scanner",
        "/setup",
        "/signals/",
        "/symbols/",
        "/trade-agent",
        "/triage",
      ],
    },
    sitemap: `${product.siteUrl}/sitemap.xml`,
  };
}
