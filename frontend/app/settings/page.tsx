import { Settings, UserRoundCog } from "lucide-react";

import { DashboardPage } from "@/components/dashboard-page";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const profile = {
  name: "Theaneshwaran Ravi",
  preferred_projects: [
    "agentic AI",
    "embedded systems",
    "automation",
    "AI jobs",
    "semiconductor tools"
  ],
  hardware: ["MacBook Air M1", "Raspberry Pi 4B+", "external SSD", "HDD vault"],
  preferred_style: "technical, structured, practical",
  learning_mode: "teacher-like guidance"
};

export default function SettingsPage() {
  return (
    <DashboardPage
      title="User Profile Personalization"
      description="Personal SATURNIX profile, preferred engineering domains, hardware topology, explanation style, and local-first security preferences."
    >
      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Profile</CardTitle>
            <UserRoundCog className="h-5 w-5 text-cyan-200" />
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-slate-400">Name</p>
              <p className="mt-1 text-xl font-semibold text-white">{profile.name}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {profile.preferred_projects.map((item) => (
                <Badge key={item} tone="cyan">
                  {item}
                </Badge>
              ))}
            </div>
            <p className="text-sm leading-6 text-slate-300">
              Style: {profile.preferred_style}. Learning mode: {profile.learning_mode}.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Environment</CardTitle>
            <Settings className="h-5 w-5 text-emerald-200" />
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {profile.hardware.map((item) => (
              <div key={item} className="rounded-lg border border-white/10 bg-black/20 p-4">
                <p className="text-sm text-slate-200">{item}</p>
              </div>
            ))}
            {[
              "dashboard auth via JWT",
              "CORS allowlist",
              "encrypted API key storage",
              "emergency lockdown mode"
            ].map((setting) => (
              <div key={setting} className="rounded-lg border border-white/10 bg-black/20 p-4">
                <p className="text-sm text-slate-200">{setting}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </DashboardPage>
  );
}
