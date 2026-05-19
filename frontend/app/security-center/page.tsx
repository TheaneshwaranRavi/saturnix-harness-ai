import { ShieldAlert, ShieldCheck } from "lucide-react";

import { DashboardPage } from "@/components/dashboard-page";
import { SecurityScanPanel } from "@/components/security-scan-panel";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getSecurityStatus } from "@/lib/dashboard-data";
import { statusTone } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function SecurityCenterPage() {
  const security = await getSecurityStatus();

  return (
    <DashboardPage
      title="Security Command Center"
      description="SATURNIX Security Sentinel protects prompts, workflows, credentials, files, containers, memory writes, and high-risk agent actions."
    >
      <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Security Status</CardTitle>
            <ShieldCheck className="h-5 w-5 text-emerald-200" />
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border border-white/10 bg-black/20 p-5">
              <p className="text-sm text-slate-400">Security Score</p>
              <p className="mt-2 text-4xl font-semibold text-white">
                {security.security_score}/100
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Badge tone={statusTone(security.threat_level)}>
                  {security.threat_level}
                </Badge>
                <Badge tone={security.lockdown_mode ? "red" : "green"}>
                  {security.lockdown_mode ? "lockdown" : "operational"}
                </Badge>
              </div>
            </div>
            <div className="space-y-2">
              {(security.security_controls || []).map((control) => (
                <div key={control} className="rounded-md bg-white/[0.04] px-3 py-2 text-sm">
                  {control}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <SecurityScanPanel />
      </section>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Threat Detection Coverage</CardTitle>
          <ShieldAlert className="h-5 w-5 text-rose-200" />
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-4">
          {[
            "prompt injection",
            "malicious commands",
            "path traversal",
            "secret leakage",
            "unsafe code execution",
            "abnormal request rate",
            "unknown egress",
            "dangerous workflow execution"
          ].map((risk) => (
            <div key={risk} className="rounded-lg border border-white/10 bg-black/20 p-4">
              <p className="text-sm text-slate-200">{risk}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </DashboardPage>
  );
}
