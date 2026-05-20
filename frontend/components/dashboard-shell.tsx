"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Bot,
  BrainCircuit,
  DatabaseZap,
  FileKey,
  HardDrive,
  LayoutDashboard,
  Mic2,
  Network,
  Route,
  ScrollText,
  Settings,
  ShieldAlert,
  Workflow
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const navigation = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/brain-router", label: "Brain Router", icon: BrainCircuit },
  { href: "/tracing", label: "Tracing", icon: Route },
  { href: "/workflows", label: "Workflows", icon: Workflow },
  { href: "/memory-vault", label: "Memory Vault", icon: DatabaseZap },
  { href: "/voice-console", label: "Voice Console", icon: Mic2 },
  { href: "/security-center", label: "Security Center", icon: ShieldAlert },
  { href: "/edge-node", label: "Edge Node", icon: Network },
  { href: "/storage-vault", label: "Storage Vault", icon: HardDrive },
  { href: "/api-keys", label: "API Keys", icon: FileKey },
  { href: "/logs", label: "Logs", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings }
];

export function DashboardShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="min-h-screen lg:flex">
      <aside className="border-b border-white/10 bg-black/30 backdrop-blur-xl lg:fixed lg:inset-y-0 lg:left-0 lg:w-72 lg:border-b-0 lg:border-r">
        <div className="border-b border-white/10 p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-cyan-300/30 bg-cyan-400/10">
              <Activity className="h-5 w-5 text-cyan-200" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">SATURNIX</p>
              <p className="text-xs text-slate-400">HARNESS OMEGA</p>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2 text-xs text-slate-300">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-300 shadow-[0_0_18px_rgba(66,245,158,0.9)]" />
            Core Control Center
          </div>
        </div>
        <nav className="flex gap-2 overflow-x-auto p-3 lg:flex-col lg:overflow-visible">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex min-h-11 shrink-0 items-center gap-3 rounded-md px-3 text-sm",
                  "text-slate-300 transition hover:bg-white/10 hover:text-white",
                  pathname === item.href && "bg-cyan-400/12 text-cyan-100"
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="hidden border-t border-white/10 p-4 lg:block">
          <Badge tone="cyan">Zero Trust Active</Badge>
        </div>
      </aside>
      <main className="min-h-screen px-4 py-6 sm:px-6 lg:ml-72 lg:px-8">
        <div className="mx-auto max-w-7xl">{children}</div>
      </main>
    </div>
  );
}
