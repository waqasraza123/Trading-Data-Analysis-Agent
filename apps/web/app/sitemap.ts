import type { MetadataRoute } from "next";
import { getProductConfig } from "@/config/product";

export default function sitemap(): MetadataRoute.Sitemap {
  const product = getProductConfig();
  return [{ url: product.siteUrl, changeFrequency: "weekly", priority: 1 }];
}
