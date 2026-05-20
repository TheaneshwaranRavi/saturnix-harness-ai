import { Activity, GitBranch, Route, ShieldCheck, type LucideIcon } from "lucide-react";

import { DashboardPage } from "@/components/dashboard-page";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getTraceSummary } from "@/lib/dashboard-data";

export const dynamic = "force-dynamic";

export default async function TracingPage() {
  const traces = await getTraceSummary();
  const latest = traces.events.slice(-12).reverse();
  const metrics: Array<{ label: string; value: string | number; icon: LucideIcon }> = [
    { label: "Trace Events", value: traces.events.length, icon: Activity },
    { label: "Token Estimate", value: String(traces.token_usage.estimated_total || 0), icon: Route },
    { label: "Tool Events", value: traces.tool_usage.length, icon: GitBranch },
    { label: "Security Events", value: traces.security_events.length, icon: ShieldCheck }
  ];

  return (
    <DashboardPage
      title="Agent Tracing Dashboard"
      description="OpenAI Agents SDK-aware execution telemetry for agent timelines, handoffs, tool calls, memory access, token estimates, and security events."
    >
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, icon: Icon }) => (
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
          <CardHeader>
            <CardTitle>Agent Execution Timeline</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {latest.map((event) => (
              <div key={event.id} className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap gap-2">
                    <Badge tone="cyan">{event.event_type}</Badge>
                    <Badge tone="neutral">{event.agent_name}</Badge>
                  </div>
                  <p className="text-xs text-slate-500">{event.timestamp}</p>
                </div>
                <p className="mt-3 text-sm text-slate-200">{event.message}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>SDK Runtime Contract</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              "Agents use Pydantic structured outputs",
              "Runner sessions keep multi-turn continuity",
              "Guardrails block injection and unsafe tools",
              "Handoffs route Voice to Research to Coding",
              "Fallbacks use Ollama, Gemma, local coding, or mock output",
              "Trace events persist to SATURNIX memory"
            ].map((item) => (
              <div key={item} className="rounded-lg border border-white/10 bg-black/20 p-4">
                <p className="text-sm text-slate-200">{item}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </DashboardPage>
  );
}
