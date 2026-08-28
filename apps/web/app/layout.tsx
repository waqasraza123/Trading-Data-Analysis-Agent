import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { getProductConfig } from "@/config/product";
import "./globals.css";

const product = getProductConfig();

export const metadata: Metadata = {
  metadataBase: new URL(product.siteUrl),
  title: {
    default: product.name,
    template: `%s · ${product.name}`,
  },
  description: product.description,
  applicationName: product.name,
  keywords: [
    "AI trading SaaS",
    "trading starter kit",
    "Next.js FastAPI starter",
    "Neon Postgres",
    "market intelligence",
    "paper trading agent",
  ],
  authors: [{ name: "Waqas Raza" }],
  creator: "Waqas Raza",
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url: "/",
    title: product.name,
    description: product.description,
    siteName: product.name,
  },
  twitter: {
    card: "summary_large_image",
    title: product.name,
    description: product.description,
  },
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = {
  colorScheme: "dark light",
  themeColor: "#050811",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
