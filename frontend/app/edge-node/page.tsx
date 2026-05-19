import { Cpu, Network, RadioTower, type LucideIcon } from "lucide-react";

import { DashboardPage } from "@/components/dashboard-page";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const nodeCards: Array<{
  label: string;
  value: string;
  icon: LucideIcon;
  tone: "green" | "amber";
}> = [
  { label: "Node", value: "Raspberry Pi 4B+", icon: Cpu, tone: "green" },
  {
    label: "Role",
    value: "SATURNIX Edge Automation Node",
    icon: Network,
    tone: "green"
  },
  {
    label: "Heartbeat",
    value: "pending real device integration",
    icon: RadioTower,
    tone: "amber"
  }
];

export default function EdgeNodePage() {
  return (
    <DashboardPage
      title="Raspberry Pi Edge Node Monitor"
      description="Edge automation plan for Raspberry Pi 4B+ with signed command queues, sensor intake, local failover, and offline-safe execution."
    >
      <section className="grid gap-6 lg:grid-cols-3">
        {nodeCards.map((card) => {
          const Icon = card.icon;
          return (
            <Card key={card.label}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>{card.label}</CardTitle>
                <Icon className="h-5 w-5 text-cyan-200" />
              </CardHeader>
              <CardContent>
                <p className="text-xl font-semibold text-white">{card.value}</p>
                <Badge tone={card.tone} className="mt-4">
                  {card.tone === "amber" ? "pending" : "configured"}
                </Badge>
              </CardContent>
            </Card>
          );
        })}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Edge Execution Controls</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          {[
            "signed commands from MacBook M1 core",
            "local offline queue with replay receipts",
            "GPIO and automation permissions isolated",
            "health check before dispatch",
            "emergency stop command path",
            "audit every edge action"
          ].map((control) => (
            <div key={control} className="rounded-lg border border-white/10 bg-black/20 p-4">
              <p className="text-sm text-slate-200">{control}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </DashboardPage>
  );
}
