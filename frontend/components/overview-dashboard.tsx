"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { Bot, DatabaseZap, ShieldCheck, Workflow } from "lucide-react";
import { SystemTopology } from "@/components/system-topology";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { brainTelemetry, memoryClasses } from "@/lib/dashboard-data";
import type { DashboardOverview } from "@/lib/dashboard-data";
import { statusTone } from "@/lib/utils";

const activity = [
  { time: "00", tokens: 1200 },
  { time: "04", tokens: 2100 },
  { time: "08", tokens: 4600 },
  { time: "12", tokens: 5900 },
  { time: "16", tokens: 4300 },
  { time: "20", tokens: 3800 }
];

export function OverviewDashboard({ overview }: { overview: DashboardOverview }) {
  const metrics = [
    ["Agents Online", overview.system_health.agents_online, Bot],
    ["Security Score", `${overview.system_health.security_score}/100`, ShieldCheck],
    ["Active Workflows", overview.live_metrics.active_workflows, Workflow],
    ["Memory Records", overview.live_metrics.memory_records, DatabaseZap]
  ] as const;
  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map(([label, value, Icon]) => (
          <Card key={label}>
            <CardContent className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">{label}</p>
                <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
              </div>
              <Icon className="h-5 w-5 text-cyan-200" />
            </CardContent>
          </Card>
        ))}
      </section>
      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>System Topology</CardTitle>
            <Badge tone={statusTone(overview.system_health.status)}>
              {overview.system_health.status}
            </Badge>
          </CardHeader>
          <CardContent><SystemTopology /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Brain Usage</CardTitle></CardHeader>
          <CardContent className="h-[390px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={brainTelemetry}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                <XAxis dataKey="name" stroke="#94A3B8" tick={{ fontSize: 11 }} />
                <YAxis stroke="#94A3B8" />
                <Tooltip contentStyle={{ background: "#0D1324", borderRadius: 8 }} />
                <Bar dataKey="tasks" fill="#29D3FF" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </section>
      <section className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Live Cognitive Load</CardTitle></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={activity}>
                <XAxis dataKey="time" stroke="#94A3B8" />
                <YAxis stroke="#94A3B8" />
                <Tooltip contentStyle={{ background: "#0D1324", borderRadius: 8 }} />
                <Area dataKey="tokens" stroke="#42F59E" fill="rgba(66,245,158,.18)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Memory Class Mix</CardTitle></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={memoryClasses.slice(0, 5)} dataKey="records" nameKey="name">
                  {memoryClasses.slice(0, 5).map((entry, index) => (
                    <Cell key={entry.name} fill={["#29D3FF", "#42F59E", "#F6C85F", "#FF5D73", "#8B5CF6"][index]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#0D1324", borderRadius: 8 }} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
