import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Shipper",
  description: "Shipper - AI-powered DORA compliance analysis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full app-shell text-slate-900 antialiased">{children}</body>
    </html>
  );
}
