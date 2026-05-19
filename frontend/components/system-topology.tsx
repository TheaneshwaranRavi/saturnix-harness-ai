"use client";

import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";

const nodes = [
  { label: "MacBook M1 Core", x: "44%", y: "38%", tone: "cyan" },
  { label: "Brain Router", x: "17%", y: "18%", tone: "green" },
  { label: "Memory Vault", x: "68%", y: "16%", tone: "amber" },
  { label: "Raspberry Pi Edge", x: "72%", y: "62%", tone: "green" },
  { label: "Groq Voice", x: "16%", y: "64%", tone: "cyan" },
  { label: "Security Sentinel", x: "43%", y: "79%", tone: "red" }
] as const;

export function SystemTopology() {
  return (
    <div className="relative min-h-[360px] overflow-hidden rounded-lg border border-white/10 bg-black/30">
      <svg className="absolute inset-0 h-full w-full" aria-label="System topology">
        <motion.line
          x1="44%"
          y1="38%"
          x2="17%"
          y2="18%"
          stroke="rgba(41,211,255,.35)"
          strokeDasharray="6 7"
          animate={{ opacity: [0.35, 0.9, 0.35] }}
          transition={{ duration: 2.4, repeat: Infinity }}
        />
        <line x1="44%" y1="38%" x2="68%" y2="16%" stroke="rgba(41,211,255,.35)" />
        <line x1="44%" y1="38%" x2="72%" y2="62%" stroke="rgba(41,211,255,.35)" />
        <line x1="44%" y1="38%" x2="16%" y2="64%" stroke="rgba(41,211,255,.35)" />
        <line x1="44%" y1="38%" x2="43%" y2="79%" stroke="rgba(41,211,255,.35)" />
      </svg>
      {nodes.map((node) => (
        <div
          key={node.label}
          className="absolute -translate-x-1/2 -translate-y-1/2 rounded-lg border border-white/10 bg-slate-950/90 px-4 py-3 shadow-glow"
          style={{ left: node.x, top: node.y }}
        >
          <Badge tone={node.tone}>{node.label}</Badge>
        </div>
      ))}
    </div>
  );
}
