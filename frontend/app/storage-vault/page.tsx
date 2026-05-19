import { Archive, Database, HardDrive, RotateCcw } from "lucide-react";

import { DashboardPage } from "@/components/dashboard-page";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const storageTiers = [
  {
    name: "External SSD",
    role: "fast AI memory, SQLite, ChromaDB, active snapshots",
    status: "ready",
    icon: HardDrive
  },
  {
    name: "HDD / 10TB Vault",
    role: "encrypted long-term archive and project vault",
    status: "planned",
    icon: Archive
  },
  {
    name: "Pendrive Recovery",
    role: "portable encrypted rescue and offline backup layer",
    status: "planned",
    icon: RotateCcw
  },
  {
    name: "Local Data Directory",
    role: "development-safe storage root with path traversal controls",
    status: "active",
    icon: Database
  }
];

export default function StorageVaultPage() {
  return (
    <DashboardPage
      title="Backup and Recovery Panel"
      description="SATURNIX storage control for SSD active memory, HDD vault backups, recovery media, snapshots, and secure file access."
    >
      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {storageTiers.map((tier) => {
          const Icon = tier.icon;
          return (
            <Card key={tier.name}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>{tier.name}</CardTitle>
                <Icon className="h-5 w-5 text-cyan-200" />
              </CardHeader>
              <CardContent>
                <p className="min-h-24 text-sm leading-6 text-slate-300">{tier.role}</p>
                <Badge tone={tier.status === "active" || tier.status === "ready" ? "green" : "amber"}>
                  {tier.status}
                </Badge>
              </CardContent>
            </Card>
          );
        })}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Data Guardian Protections</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          {[
            "classify data before storage",
            "encrypt secrets and personal memory",
            "block path traversal attempts",
            "snapshot important files before mutation",
            "detect duplicate or stale records",
            "audit backup and restore actions"
          ].map((rule) => (
            <div key={rule} className="rounded-lg border border-white/10 bg-black/20 p-4">
              <p className="text-sm text-slate-200">{rule}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </DashboardPage>
  );
}
