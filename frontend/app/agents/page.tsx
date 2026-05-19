import { Bot, ShieldCheck, Wrench } from "lucide-react";

import { DashboardPage } from "@/components/dashboard-page";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getAgents } from "@/lib/dashboard-data";
import { statusTone } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function AgentsPage() {
  const agents = await getAgents();

  return (
    <DashboardPage
      title="Agent Control Center"
      description="Default SATURNIX specialists with least-privilege permissions, risk labels, memory boundaries, and validation rules."
    >
      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {agents.map((agent) => (
          <Card key={agent.name}>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>{agent.name}</CardTitle>
              <Bot className="h-5 w-5 text-cyan-200" />
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="min-h-16 text-sm leading-6 text-slate-300">
                {agent.purpose}
              </p>
              <div className="flex flex-wrap gap-2">
                <Badge tone="cyan">{agent.best_brain}</Badge>
                <Badge tone={statusTone(agent.risk_level)}>{agent.risk_level}</Badge>
                <Badge tone="neutral">{agent.memory_access_level}</Badge>
              </div>
              <div className="grid gap-3">
                <div>
                  <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-slate-400">
                    <Wrench className="h-3.5 w-3.5" />
                    Tools
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {agent.tools.map((tool) => (
                      <Badge key={tool} tone="neutral">
                        {tool}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-slate-400">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    Permissions
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {agent.permissions.map((permission) => (
                      <Badge key={permission} tone="green">
                        {permission}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </section>
    </DashboardPage>
  );
}
