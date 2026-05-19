"use client";

import { FormEvent, useState } from "react";
import { KeyRound, LockKeyhole } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const apiBase = process.env.NEXT_PUBLIC_SATURNIX_API_BASE || "http://localhost:8088";

export function ApiKeyPanel() {
  const [provider, setProvider] = useState("openai");
  const [label, setLabel] = useState("primary");
  const [apiKey, setApiKey] = useState("");
  const [message, setMessage] = useState("Secrets are submitted only to FastAPI.");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const response = await fetch(`${apiBase}/api-keys/store`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, label, api_key: apiKey })
      });
      const result = (await response.json()) as { preview?: string };
      setMessage(`Stored encrypted. Preview: ${result.preview || "***"}`);
      setApiKey("");
    } catch {
      setMessage("Backend offline fallback: key was not sent or stored.");
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Encrypted Provider Key Store</CardTitle>
        <LockKeyhole className="h-5 w-5 text-emerald-200" />
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="grid gap-4 md:grid-cols-[1fr_1fr_2fr_auto]">
          <select value={provider} onChange={(event) => setProvider(event.target.value)} className="min-h-10 rounded-md border border-white/10 bg-black/30 px-3 text-sm">
            <option value="openai">OpenAI</option>
            <option value="anthropic">Claude</option>
            <option value="google">Gemini</option>
            <option value="groq">Groq</option>
          </select>
          <input value={label} onChange={(event) => setLabel(event.target.value)} className="min-h-10 rounded-md border border-white/10 bg-black/30 px-3 text-sm" />
          <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} className="min-h-10 rounded-md border border-white/10 bg-black/30 px-3 text-sm" type="password" autoComplete="off" required />
          <Button variant="primary" disabled={!apiKey}><KeyRound className="h-4 w-4" />Store</Button>
        </form>
        <div className="mt-4 flex flex-wrap gap-2">
          <Badge tone="green">Frontend never displays raw secrets</Badge>
          <Badge tone="cyan">{message}</Badge>
        </div>
      </CardContent>
    </Card>
  );
}
