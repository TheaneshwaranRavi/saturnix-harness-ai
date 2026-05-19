export type AgentDefinition = {
  name: string;
  purpose: string;
  best_brain: string;
  tools: string[];
  permissions: string[];
  memory_access_level: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  validation_rules: string[];
};

export type DashboardOverview = {
  model_name: string;
  purpose: string;
  core_control_center: string;
  edge_node: string;
  storage: Record<string, string>;
  system_health: { status: string; agents_online: number; security_score: number };
  live_metrics: {
    active_workflows: number;
    memory_records: number;
    audit_events: number;
    voice_status: string;
  };
  topology: Array<{ source: string; target: string }>;
};

export type SecurityStatus = {
  security_score: number;
  threat_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  detected_risks: string[];
  blocked_actions: string[];
  recommended_fixes: string[];
  lockdown_required: boolean;
  lockdown_mode?: boolean;
  security_controls?: string[];
};

const apiBase = process.env.NEXT_PUBLIC_SATURNIX_API_BASE || "http://localhost:8088";

async function apiFetch<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${apiBase}${path}`, {
      cache: "no-store",
      headers: { Accept: "application/json" }
    });
    return response.ok ? ((await response.json()) as T) : fallback;
  } catch {
    return fallback;
  }
}

export const fallbackOverview: DashboardOverview = {
  model_name: "SATURNIX-HARNESS",
  purpose: "Secure AI operating dashboard for multi-agent infrastructure.",
  core_control_center: "MacBook Air M1",
  edge_node: "Raspberry Pi 4B+",
  storage: {
    fast_memory: "External SSD",
    vault: "HDD / 10TB SATURNIX Vault",
    recovery: "Encrypted pendrive recovery layer"
  },
  system_health: { status: "operational", agents_online: 10, security_score: 94 },
  live_metrics: {
    active_workflows: 3,
    memory_records: 128,
    audit_events: 42,
    voice_status: "configured"
  },
  topology: [
    { source: "Dashboard", target: "SATURNIX Core" },
    { source: "SATURNIX Core", target: "Brain Router" },
    { source: "SATURNIX Core", target: "Raspberry Pi Edge Node" },
    { source: "SATURNIX Core", target: "Memory Vault" },
    { source: "Brain Router", target: "Cloud APIs" },
    { source: "Voice Console", target: "Groq STT/TTS" }
  ]
};

export const fallbackAgents: AgentDefinition[] = [
  ["Personal Assistant Agent", "Coordinate daily SATURNIX assistance.", "GPT", "LOW"],
  ["Coding Agent", "Build, debug, and verify software systems.", "GPT", "MEDIUM"],
  ["Research Agent", "Analyze sources and synthesize grounded research.", "Claude", "LOW"],
  ["Security Agent", "Detect threats and enforce zero-trust controls.", "GPT", "HIGH"],
  ["Memory Agent", "Maintain safe long-term user and system memory.", "Gemma via Ollama", "MEDIUM"],
  ["Workflow Agent", "Plan and run validated automation workflows.", "Gemini", "MEDIUM"],
  ["Voice Agent", "Handle Groq voice commands and confirmations.", "Groq", "HIGH"],
  ["Raspberry Pi Edge Agent", "Coordinate edge automation safely.", "Gemma via Ollama", "HIGH"],
  ["Job Application Agent", "Create verified career materials.", "GPT", "MEDIUM"],
  ["Semiconductor Design Agent", "Analyze semiconductor and EDA tasks.", "Claude", "MEDIUM"]
].map(([name, purpose, best_brain, risk_level]) => ({
  name,
  purpose,
  best_brain,
  tools: ["memory_search", "security_scan"],
  permissions:
    name === "Security Agent" ? ["READ_ONLY", "ADMIN_SECURITY"] : ["READ_ONLY"],
  memory_access_level: name.includes("Voice") ? "voice" : "project",
  risk_level: risk_level as AgentDefinition["risk_level"],
  validation_rules: ["validate input", "apply least privilege", "verify output"]
}));

export const brainTelemetry = [
  { name: "GPT", tasks: 42, latency: 820, reliability: 96 },
  { name: "Claude", tasks: 18, latency: 1100, reliability: 94 },
  { name: "Gemini", tasks: 26, latency: 760, reliability: 92 },
  { name: "Gemma", tasks: 31, latency: 520, reliability: 88 },
  { name: "Ollama Coding", tasks: 22, latency: 610, reliability: 87 },
  { name: "Groq Voice", tasks: 34, latency: 190, reliability: 95 }
];

export const memoryClasses = [
  { name: "public_data", records: 18, sensitivity: 10, encrypted: false },
  { name: "project_data", records: 43, sensitivity: 35, encrypted: false },
  { name: "personal_memory", records: 29, sensitivity: 70, encrypted: true },
  { name: "api_secrets", records: 6, sensitivity: 100, encrypted: true },
  { name: "agent_logs", records: 52, sensitivity: 50, encrypted: false },
  { name: "voice_records", records: 8, sensitivity: 75, encrypted: true },
  { name: "critical_backups", records: 12, sensitivity: 90, encrypted: true }
];

export const workflowRows = [
  { name: "secure-agent-build", status: "ready", risk: "MEDIUM", steps: ["intent", "agents", "routing", "execution", "verification"] },
  { name: "voice-command-routing", status: "ready", risk: "HIGH", steps: ["stt", "intent", "confirmation", "execution", "tts"] },
  { name: "memory-vault-backup", status: "planned", risk: "LOW", steps: ["classify", "encrypt", "snapshot", "checksum", "audit"] }
];

export const auditLogRows = [
  { action: "security.scan", actor: "dashboard", result: "LOW", timestamp: "live endpoint when backend is running" },
  { action: "memory.save", actor: "Memory Agent", result: "encrypted", timestamp: "classified before write" },
  { action: "agent.execute.blocked", actor: "Security Agent", result: "requires confirmation", timestamp: "zero trust policy" }
];

export function getOverview(): Promise<DashboardOverview> {
  return apiFetch("/dashboard/overview", fallbackOverview);
}

export function getAgents(): Promise<AgentDefinition[]> {
  return apiFetch("/agents", fallbackAgents);
}

export function getSecurityStatus(): Promise<SecurityStatus> {
  return apiFetch("/security/status", {
    security_score: 94,
    threat_level: "LOW",
    detected_risks: [],
    blocked_actions: [],
    recommended_fixes: ["Continue monitoring and keep secrets encrypted."],
    lockdown_required: false,
    lockdown_mode: false,
    security_controls: ["JWT authentication", "audit logging", "rate limiting"]
  });
}
