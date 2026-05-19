"use client";

import { useState } from "react";
import { ScanLine, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { statusTone } from "@/lib/utils";

type ScanResult = {
  security_score: number;
  threat_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  detected_risks: string[];
  blocked_actions: string[];
  recommended_fixes: string[];
  lockdown_required: boolean;
};

const apiBase = process.env.NEXT_PUBLIC_SATURNIX_API_BASE || "http://localhost:8088";

export function SecurityScanPanel() {
  const [input, setInput] = useState("Summarize this workflow and keep secrets protected.");
  const [result, setResult] = useState<ScanResult | null>(null);
  const [busy, setBusy] = useState(false);

  async function scan() {
    setBusy(true);
    try {
      const response = await fetch(`${apiBase}/security/scan-input`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input_text: input, source: "frontend-dashboard" })
      });
      setResult((await response.json()) as ScanResult);
    } catch {
      setResult({
        security_score: 94,
        threat_level: "LOW",
        detected_risks: [],
        blocked_actions: [],
        recommended_fixes: ["Backend offline fallback: run FastAPI to scan live input."],
        lockdown_required: false
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Prompt Injection Scan</CardTitle>
        <ShieldAlert className="h-5 w-5 text-cyan-200" />
      </CardHeader>
      <CardContent className="space-y-4">
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          className="min-h-32 w-full resize-none rounded-md border border-white/10 bg-black/30 p-3 text-sm"
        />
        <Button variant="primary" onClick={scan} disabled={busy}>
          <ScanLine className="h-4 w-4" />
          {busy ? "Scanning" : "Run Sentinel Scan"}
        </Button>
        {result ? (
          <div className="rounded-lg border border-white/10 bg-black/20 p-4">
            <Badge tone={statusTone(result.threat_level)}>{result.threat_level}</Badge>
            <p className="mt-3 text-sm text-slate-300">
              Security score {result.security_score}/100
            </p>
            <p className="mt-3 text-sm text-slate-400">
              {(result.recommended_fixes[0] || "No immediate fixes required.")}
            </p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
