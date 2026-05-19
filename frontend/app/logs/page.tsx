import { ScrollText, ShieldCheck } from "lucide-react";

import { DashboardPage } from "@/components/dashboard-page";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { auditLogRows } from "@/lib/dashboard-data";

export default function LogsPage() {
  return (
    <DashboardPage
      title="Logs and Audit Trail"
      description="Operational event stream for sensitive actions, memory writes, security scans, workflow decisions, and blocked execution."
    >
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Audit Events</CardTitle>
          <ScrollText className="h-5 w-5 text-cyan-200" />
        </CardHeader>
        <CardContent className="space-y-3">
          {auditLogRows.map((row) => (
            <div
              key={`${row.action}-${row.actor}`}
              className="grid gap-3 rounded-lg border border-white/10 bg-black/20 p-4 md:grid-cols-[1fr_0.8fr_0.6fr_1.2fr]"
            >
              <p className="text-sm font-medium text-white">{row.action}</p>
              <p className="text-sm text-slate-300">{row.actor}</p>
              <Badge tone="cyan">{row.result}</Badge>
              <p className="text-sm text-slate-400">{row.timestamp}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Audit Policy</CardTitle>
          <ShieldCheck className="h-5 w-5 text-emerald-200" />
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          {[
            "record every sensitive action",
            "redact secrets before logging",
            "include actor, source, risk, and result",
            "persist incident logs during lockdown",
            "separate user memory from system memory",
            "preserve verification output for replay"
          ].map((policy) => (
            <div key={policy} className="rounded-lg border border-white/10 bg-black/20 p-4">
              <p className="text-sm text-slate-200">{policy}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </DashboardPage>
  );
}
