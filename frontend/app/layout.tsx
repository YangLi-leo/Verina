import { cn } from "@/lib/utils";
import type { Metadata, Viewport } from "next";
import { Dancing_Script, Inter } from "next/font/google";
import type React from "react";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import "./globals.css";

const dancingScript = Dancing_Script({
  subsets: ["latin"],
  variable: "--font-brand",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Verina - AI Search",
  description: "A minimal, powerful AI-powered search engine.",
  keywords: ["AI", "search", "artificial intelligence", "search engine"],
  authors: [{ name: "Verina Team" }],
  generator: "v0.app",
  icons: {
    icon: [
      { url: "/logo.png", sizes: "any" },
      { url: "/logo.png", sizes: "32x32", type: "image/png" },
      { url: "/logo.png", sizes: "16x16", type: "image/png" },
    ],
    apple: "/logo.png",
    shortcut: "/logo.png",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body
        className={cn(
          "h-full bg-white font-sans antialiased",
          inter.variable,
          dancingScript.variable
        )}
      >
        <ErrorBoundary>{children}</ErrorBoundary>
      </body>
    </html>
  );
}
