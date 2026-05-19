import { Mic2, Radio, Volume2 } from "lucide-react";

import { DashboardPage } from "@/components/dashboard-page";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function VoiceConsolePage() {
  return (
    <DashboardPage
      title="Voice Agent Console"
      description="Groq speech-to-text and text-to-speech control path with interruption handling, memory-aware context, and command confirmation for risky actions."
    >
      <section className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Voice Runtime</CardTitle>
            <Mic2 className="h-5 w-5 text-cyan-200" />
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              ["STT", "Groq whisper-large-v3-turbo"],
              ["Intent", "SATURNIX mapper and Brain Router"],
              ["Execution", "zero-trust workflow engine"],
              ["TTS", "Groq voice response"]
            ].map(([label, value]) => (
              <div
                key={label}
                className="rounded-lg border border-white/10 bg-black/20 p-4"
              >
                <Badge tone="cyan">{label}</Badge>
                <p className="mt-3 text-sm text-slate-300">{value}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Realtime Control Loop</CardTitle>
            <Radio className="h-5 w-5 text-emerald-200" />
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              {[
                ["Low latency", "voice route favors Groq and local state"],
                ["Interruptions", "new speech can stop pending responses"],
                ["Risk confirmation", "file, network, and admin actions require approval"]
              ].map(([title, body]) => (
                <div key={title} className="rounded-lg border border-white/10 bg-black/20 p-4">
                  <Volume2 className="h-5 w-5 text-cyan-200" />
                  <p className="mt-4 text-sm font-medium text-white">{title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-400">{body}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>
    </DashboardPage>
  );
}
