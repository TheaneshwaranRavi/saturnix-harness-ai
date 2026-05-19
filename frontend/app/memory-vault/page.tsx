"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { DatabaseZap, Lock } from "lucide-react";

import { DashboardPage } from "@/components/dashboard-page";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { memoryClasses } from "@/lib/dashboard-data";

export default function MemoryVaultPage() {
  return (
    <DashboardPage
      title="Memory Vault Dashboard"
      description="Long-term intelligence memory with data classification, encrypted sensitive classes, SQLite starter storage, and ChromaDB-ready vector recall."
    >
      <section className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Memory Records</CardTitle>
            <DatabaseZap className="h-5 w-5 text-cyan-200" />
          </CardHeader>
          <CardContent className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={memoryClasses} margin={{ top: 8, right: 8, left: -18 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                <XAxis dataKey="name" stroke="#94A3B8" tick={{ fontSize: 11 }} />
                <YAxis stroke="#94A3B8" />
                <Tooltip
                  contentStyle={{
                    background: "#0D1324",
                    border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: 8
                  }}
                />
                <Bar dataKey="records" fill="#29D3FF" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Protection Rules</CardTitle>
            <Lock className="h-5 w-5 text-emerald-200" />
          </CardHeader>
          <CardContent className="space-y-3">
            {memoryClasses.map((item) => (
              <div
                key={item.name}
                className="flex flex-col gap-3 rounded-lg border border-white/10 bg-black/20 p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="text-sm font-medium text-white">{item.name}</p>
                  <p className="mt-1 text-xs text-slate-400">
                    sensitivity score {item.sensitivity}/100
                  </p>
                </div>
                <Badge tone={item.encrypted ? "green" : "neutral"}>
                  {item.encrypted ? "encrypted" : "controlled"}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </DashboardPage>
  );
}
