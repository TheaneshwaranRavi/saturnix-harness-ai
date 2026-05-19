import { FileKey, LockKeyhole } from "lucide-react";

import { ApiKeyPanel } from "@/components/api-key-panel";
import { DashboardPage } from "@/components/dashboard-page";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ApiKeysPage() {
  return (
    <DashboardPage
      title="API Key Management Panel"
      description="Secret-safe control surface for OpenAI, Claude, Gemini, Groq, and future provider credentials without exposing keys in the browser."
    >
      <section className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
        <ApiKeyPanel />

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Credential Rules</CardTitle>
            <LockKeyhole className="h-5 w-5 text-emerald-200" />
          </CardHeader>
          <CardContent className="grid gap-3">
            {[
              "never render raw keys in frontend responses",
              "encrypt sensitive credentials before storage",
              "redact credentials in logs and scans",
              "admin role required for writes",
              "rotate exposed keys immediately",
              "prefer deployment secret managers for production"
            ].map((rule) => (
              <div key={rule} className="rounded-lg border border-white/10 bg-black/20 p-4">
                <p className="text-sm text-slate-200">{rule}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Supported Providers</CardTitle>
          <FileKey className="h-5 w-5 text-cyan-200" />
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {["OpenAI", "Anthropic", "Google Gemini", "Groq", "Ollama local"].map(
            (provider) => (
              <div key={provider} className="rounded-lg border border-white/10 bg-black/20 p-4">
                <p className="text-sm font-medium text-white">{provider}</p>
              </div>
            )
          )}
        </CardContent>
      </Card>
    </DashboardPage>
  );
}
