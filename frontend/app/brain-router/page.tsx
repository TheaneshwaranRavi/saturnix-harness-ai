"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { BrainCircuit, GitBranch, ShieldCheck } from "lucide-react";

import { DashboardPage } from "@/components/dashboard-page";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { brainTelemetry } from "@/lib/dashboard-data";

const routingRules = [
  ["GPT", "reasoning, coding, architecture, planning"],
  ["Claude", "long documents, deep analysis, large context"],
  ["Gemini", "structured JSON, schemas, function calling"],
  ["Gemma via Ollama", "local/private lightweight tasks"],
  ["Ollama coding model", "fast local code generation"],
  ["Groq", "speech-to-text, text-to-speech, voice interaction"]
];

export default function BrainRouterPage() {
  return (
    <DashboardPage
      title="Brain Router Monitor"
      description="Live routing view for cloud and local AI brains, with privacy-aware fallbacks and schema-first execution paths."
    >
      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Brain Usage</CardTitle>
            <BrainCircuit className="h-5 w-5 text-cyan-200" />
          </CardHeader>
          <CardContent className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={brainTelemetry}>
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
                <Bar dataKey="tasks" fill="#29D3FF" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Routing Rules</CardTitle>
            <GitBranch className="h-5 w-5 text-emerald-200" />
          </CardHeader>
          <CardContent className="space-y-3">
            {routingRules.map(([brain, rule]) => (
              <div key={brain} className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <Badge tone="cyan">{brain}</Badge>
                  <ShieldCheck className="h-4 w-4 text-emerald-200" />
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-300">{rule}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Latency and Reliability</CardTitle>
        </CardHeader>
        <CardContent className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={brainTelemetry}>
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
              <Line dataKey="latency" stroke="#F6C85F" strokeWidth={2} />
              <Line dataKey="reliability" stroke="#42F59E" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </DashboardPage>
  );
}
