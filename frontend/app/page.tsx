import { DashboardPage } from "@/components/dashboard-page";
import { OverviewDashboard } from "@/components/overview-dashboard";
import { getOverview } from "@/lib/dashboard-data";

export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  const overview = await getOverview();
  return (
    <DashboardPage
      title="AI Infrastructure Control Center"
      description="A personalized command surface for SATURNIX-HARNESS agents, brains, memory, security, storage, voice, and edge-node operations."
    >
      <OverviewDashboard overview={overview} />
    </DashboardPage>
  );
}
