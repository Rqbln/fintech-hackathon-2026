import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DORA AI Analyst",
  description: "AI-powered DORA compliance analysis for financial institutions",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full bg-[#080d1a] text-slate-200 antialiased">{children}</body>
    </html>
  );
}
