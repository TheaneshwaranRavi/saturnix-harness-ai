export function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export function statusTone(status: string): "green" | "amber" | "red" | "cyan" {
  const normalized = status.toLowerCase();
  if (["healthy", "online", "operational", "ready", "low"].includes(normalized)) {
    return "green";
  }
  if (["planned", "pending", "medium", "configured"].includes(normalized)) {
    return "amber";
  }
  if (["critical", "high", "offline", "blocked", "lockdown"].includes(normalized)) {
    return "red";
  }
  return "cyan";
}
