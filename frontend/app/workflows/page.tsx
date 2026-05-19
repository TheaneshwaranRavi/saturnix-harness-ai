import { GitBranch, PlayCircle, ShieldCheck } from "lucide-react";

import { DashboardPage } from "@/components/dashboard-page";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { workflowRows } from "@/lib/dashboard-data";
import { statusTone } from "@/lib/utils";

export default function WorkflowsPage() {
  return (
    <DashboardPage
      title="Workflow Automation Panel"
      description="Dependency-aware SATURNIX workflows for agent construction, voice routing, secure memory backup, verification, and recovery."
    >
      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Workflow Queue</CardTitle>
            <PlayCircle className="h-5 w-5 text-cyan-200" />
          </CardHeader>
          <CardContent className="space-y-4">
            {workflowRows.map((workflow) => (
              <div key={workflow.name} className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm font-medium text-white">{workflow.name}</p>
                  <div className="flex gap-2">
                    <Badge tone={statusTone(workflow.status)}>{workflow.status}</Badge>
                    <Badge tone={statusTone(workflow.risk)}>{workflow.risk}</Badge>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {workflow.steps.map((step) => (
                    <Badge key={step} tone="neutral">
                      {step}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Execution Policy</CardTitle>
            <ShieldCheck className="h-5 w-5 text-emerald-200" />
          </CardHeader>
          <CardContent className="grid gap-3">
            {[
              "route before execution",
              "validate risky actions",
              "require confirmation for file or network changes",
              "save execution trace to audit logs",
              "store only approved useful memory",
              "trigger recursive improvement after every run"
            ].map((policy) => (
              <div key={policy} className="rounded-lg border border-white/10 bg-black/20 p-4">
                <p className="text-sm text-slate-200">{policy}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Execution Graph</CardTitle>
          <GitBranch className="h-5 w-5 text-cyan-200" />
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-5">
            {["intent", "agent design", "brain routing", "execution", "verification"].map(
              (step, index) => (
                <div key={step} className="rounded-lg border border-cyan-300/20 bg-cyan-400/10 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-cyan-200">
                    step {index + 1}
                  </p>
                  <p className="mt-3 text-sm font-medium text-white">{step}</p>
                </div>
              )
            )}
          </div>
        </CardContent>
      </Card>
    </DashboardPage>
  );
}
