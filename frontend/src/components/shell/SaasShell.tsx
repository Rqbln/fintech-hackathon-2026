"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import {
  Bell,
  Gauge,
  HelpCircle,
  Map,
  ScanText,
  Search,
  UserCircle2,
  Wrench,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface TabItem {
  id: string;
  label: string;
}

interface ShellProps {
  title: string;
  subtitle?: string;
  topTabs?: TabItem[];
  activeTabId?: string;
  rightActions?: ReactNode;
  children: ReactNode;
}

const NAV_ITEMS = [
  { label: "Dashboard", href: "/", icon: Gauge },
  { label: "Risk Map", href: "/graph", icon: Map },
  { label: "Document Analysis", href: "/investigation", icon: ScanText },
  { label: "Remediation Register", href: "/register", icon: Wrench },
];

export default function SaasShell({
  title,
  subtitle,
  topTabs = [],
  activeTabId,
  rightActions,
  children,
}: ShellProps) {
  const pathname = usePathname();
  const isAnalysisRoute = pathname.startsWith("/investigation");

  return (
    <div className="flex h-screen min-h-screen bg-[#f8f9ff]">
      <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white lg:flex lg:flex-col">
        <div className="flex items-center gap-3 border-b border-slate-200 px-5 py-4">
          <div className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-md border border-slate-200 bg-white">
            <img src="/shipper-logo.png" alt="Shipper logo" className="h-full w-full object-cover" />
          </div>
          <div>
            <p className="text-base font-bold text-slate-900">Shipper</p>
            <p className="text-xs text-slate-500">Regulatory Intelligence</p>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto px-2 py-4">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active =
              pathname === item.href ||
              (item.href === "/investigation" && isAnalysisRoute);
            return (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  "mb-1 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition",
                  active
                    ? "bg-slate-100 font-semibold text-slate-900"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                )}
              >
                <Icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-200 p-2">
          <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900">
            <HelpCircle size={18} />
            Help Center
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-slate-200 bg-white/90 backdrop-blur">
          <div className="flex h-16 items-center justify-between px-6">
            <div className="min-w-0">
              <h1 className="truncate text-xl font-semibold text-slate-900">{title}</h1>
              {subtitle && <p className="truncate text-xs text-slate-500">{subtitle}</p>}
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden h-10 min-w-[240px] items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm text-slate-500 md:flex">
                <Search size={14} />
                Search...
            </div>
              {rightActions}
              <button className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800">
                <Bell size={18} />
              </button>
              <button className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800">
                <UserCircle2 size={20} />
              </button>
            </div>
          </div>
          {topTabs.length > 0 && (
            <div className="flex gap-2 border-t border-slate-100 px-6 py-2">
              {topTabs.map((tab) => (
                <span
                  key={tab.id}
                  className={cn(
                    "rounded-md px-2.5 py-1 text-xs font-medium",
                    activeTabId === tab.id
                      ? "bg-[#131b2e] text-white"
                      : "bg-slate-100 text-slate-600"
                  )}
                >
                  {tab.label}
                </span>
              ))}
            </div>
          )}
        </header>

        <main className="min-h-0 flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
