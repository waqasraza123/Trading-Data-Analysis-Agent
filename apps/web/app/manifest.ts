import type { MetadataRoute } from "next";
import { getProductConfig } from "@/config/product";

export default function manifest(): MetadataRoute.Manifest {
  const product = getProductConfig();
  return {
    name: product.name,
    short_name: "Trading SaaS Kit",
    description: product.description,
    start_url: "/",
    display: "standalone",
    background_color: "#050811",
    theme_color: "#050811",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
