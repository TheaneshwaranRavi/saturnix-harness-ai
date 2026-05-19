import type { Metadata } from "next";
import type { ReactNode } from "react";
import { DashboardShell } from "@/components/dashboard-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "SATURNIX-HARNESS Dashboard",
  description: "Secure AI infrastructure dashboard for SATURNIX-HARNESS."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <DashboardShell>{children}</DashboardShell>
      </body>
    </html>
  );
}
