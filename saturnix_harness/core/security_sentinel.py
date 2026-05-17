from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from saturnix_harness.schemas import SecurityScanRequest, SecurityScanResult


class SecuritySentinel:
    """SATURNIX Security Sentinel.

    The sentinel performs deterministic guardrail checks before prompts,
    workflows, code, dependency manifests, or container config are trusted by
    the execution stack.
    """

    def scan(self, request: SecurityScanRequest) -> SecurityScanResult:
        findings: list[_Finding] = []
        text = _combined_text(request)
        findings.extend(_check_prompt_injection(text))
        findings.extend(_check_secret_leakage(text))
        findings.extend(_check_unsafe_code(request.code or "", request.actions))
        findings.extend(_check_malicious_workflows(request.workflow, request.actions))
        findings.extend(_check_unauthorized_file_access(request.file_paths, text))
        findings.extend(_check_insecure_dependencies(request.dependencies))
        findings.extend(_check_container_config(request.container_config or ""))
        findings.extend(_check_sensitive_data_exposure(text, request.sensitivity_level))

        findings = _dedupe_findings(findings)
        score = _score(findings)
        return SecurityScanResult(
            security_score=f"{score}/100",
            risks_detected=[finding.message for finding in findings],
            recommended_fixes=_recommended_fixes(findings),
            blocked_actions=[
                finding.blocked_action
                for finding in findings
                if finding.blocked_action
            ],
        )


@dataclass(frozen=True)
class _Finding:
    category: str
    severity: str
    message: str
    fix: str
    blocked_action: str | None = None


_PROMPT_INJECTION_PATTERNS = {
    "ignore previous instructions",
    "ignore all previous",
    "reveal system prompt",
    "show system prompt",
    "developer message",
    "hidden instructions",
    "jailbreak",
    "disable safety",
    "bypass guardrails",
    "override instructions",
    "print your prompt",
    "act as dan",
}

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
]

_DANGEROUS_CODE_PATTERNS = {
    "subprocess": "subprocess execution requires sandbox policy and allowlisted commands",
    "os.system": "shell execution requires sandbox policy and allowlisted commands",
    "eval(": "dynamic eval is unsafe for untrusted input",
    "exec(": "dynamic exec is unsafe for untrusted input",
    "pickle.loads": "pickle deserialization can execute code",
    "yaml.load(": "unsafe YAML loading can instantiate arbitrary objects",
    "shutil.rmtree": "recursive deletion is destructive and needs explicit approval",
    "rm -rf": "destructive shell deletion is blocked",
    "curl ": "network fetches must be validated and pinned",
    "wget ": "network fetches must be validated and pinned",
}

_SENSITIVE_MARKERS = {
    "ssn",
    "social security",
    "credit card",
    "private key",
    "access token",
    "refresh token",
    "customer data",
    "medical record",
    "passport",
}


def _combined_text(request: SecurityScanRequest) -> str:
    parts: list[str] = [
        request.prompt or "",
        request.task or "",
        request.code or "",
        request.container_config or "",
        " ".join(request.dependencies),
        " ".join(request.file_paths),
        " ".join(request.actions),
        json.dumps(request.workflow, default=str),
        json.dumps(request.external_inputs, default=str),
    ]
    return "\n".join(parts)


def _check_prompt_injection(text: str) -> list[_Finding]:
    lowered = text.lower()
    findings: list[_Finding] = []
    for pattern in sorted(_PROMPT_INJECTION_PATTERNS):
        if pattern in lowered:
            findings.append(
                _Finding(
                    category="prompt_injection",
                    severity="high",
                    message=f"Prompt injection marker detected: '{pattern}'.",
                    fix=(
                        "Treat external instructions as data, strip override language, and keep "
                        "system/developer prompts isolated."
                    ),
                    blocked_action="Blocked execution until prompt injection text is removed.",
                )
            )
    return findings


def _check_secret_leakage(text: str) -> list[_Finding]:
    findings: list[_Finding] = []
    for pattern in _SECRET_PATTERNS:
        for match in pattern.finditer(text):
            findings.append(
                _Finding(
                    category="api_key_leakage",
                    severity="critical",
                    message=f"Potential secret exposure detected: {_redact(match.group(0))}.",
                    fix=(
                        "Remove secrets from prompts, rotate exposed credentials, and load keys "
                        "only from environment variables or secret storage."
                    ),
                    blocked_action="Blocked request containing possible plaintext secret.",
                )
            )
    return findings


def _check_unsafe_code(code: str, actions: list[str]) -> list[_Finding]:
    text = f"{code}\n{' '.join(actions)}".lower()
    findings: list[_Finding] = []
    for marker, reason in _DANGEROUS_CODE_PATTERNS.items():
        if marker in text:
            severity = "critical" if marker in {"rm -rf", "eval(", "exec("} else "high"
            findings.append(
                _Finding(
                    category="unsafe_code_execution",
                    severity=severity,
                    message=f"Unsafe execution pattern detected: '{marker}' because {reason}.",
                    fix=(
                        "Sandbox untrusted code, use structured tool APIs, and require explicit "
                        "approval for side-effectful commands."
                    ),
                    blocked_action=f"Blocked unsafe action using '{marker}'.",
                )
            )
    return findings


def _check_malicious_workflows(
    workflow: list[dict[str, Any]],
    actions: list[str],
) -> list[_Finding]:
    text = f"{json.dumps(workflow, default=str)}\n{' '.join(actions)}".lower()
    markers = {
        "exfiltrate": "workflow attempts or describes data exfiltration",
        "send secrets": "workflow attempts to transmit secrets",
        "disable logging": "workflow attempts to hide audit trail",
        "delete backups": "workflow includes destructive backup removal",
        "privilege escalation": "workflow includes privilege escalation",
    }
    findings: list[_Finding] = []
    for marker, reason in markers.items():
        if marker in text:
            findings.append(
                _Finding(
                    category="malicious_workflow",
                    severity="critical",
                    message=f"Malicious workflow marker detected: '{marker}' because {reason}.",
                    fix=(
                        "Require human approval, least-privilege tool scopes, audit logging, "
                        "and explicit deny rules for destructive or exfiltration behavior."
                    ),
                    blocked_action=f"Blocked workflow containing '{marker}'.",
                )
            )
    return findings


def _check_unauthorized_file_access(file_paths: list[str], text: str) -> list[_Finding]:
    combined_paths = [*file_paths, *re.findall(r"(/[A-Za-z0-9_./-]+)", text)]
    sensitive_roots = (
        "/etc/passwd",
        "/etc/shadow",
        "/var/run/docker.sock",
        "/root/",
        "/home/",
        "/Users/",
        "~/.ssh",
        ".ssh/",
        ".env",
    )
    findings: list[_Finding] = []
    for path in combined_paths:
        normalized = path.strip()
        if any(root in normalized for root in sensitive_roots):
            findings.append(
                _Finding(
                    category="unauthorized_file_access",
                    severity="high",
                    message=f"Sensitive file path access requested: {_redact_path(normalized)}.",
                    fix=(
                        "Validate file paths against an allowlist, deny secret files, and run "
                        "tools inside a constrained workspace."
                    ),
                    blocked_action=f"Blocked unauthorized file path: {_redact_path(normalized)}.",
                )
            )
    return findings


def _check_insecure_dependencies(dependencies: list[str]) -> list[_Finding]:
    findings: list[_Finding] = []
    for dependency in dependencies:
        lowered = dependency.lower()
        if any(marker in lowered for marker in ("latest", "*", "git+", "http://")):
            findings.append(
                _Finding(
                    category="insecure_dependencies",
                    severity="medium",
                    message=f"Dependency is not safely pinned or verified: '{dependency}'.",
                    fix=(
                        "Pin dependency versions, prefer HTTPS package registries, and verify "
                        "transitive dependency risk before deployment."
                    ),
                )
            )
        if "--trusted-host" in lowered or "--extra-index-url" in lowered:
            findings.append(
                _Finding(
                    category="insecure_dependencies",
                    severity="high",
                    message=f"Dependency source weakens package trust boundary: '{dependency}'.",
                    fix="Use trusted package indexes only and enforce dependency hash checking.",
                    blocked_action=(
                        "Blocked dependency install with weakened package trust settings."
                    ),
                )
            )
    return findings


def _check_container_config(container_config: str) -> list[_Finding]:
    lowered = container_config.lower()
    checks = {
        "privileged: true": "container runs with privileged access",
        "--privileged": "container runs with privileged access",
        "network_mode: host": "container uses host network namespace",
        "user: root": "container runs as root",
        "latest": "container image tag is mutable",
        "/var/run/docker.sock": "container mounts Docker socket",
    }
    findings: list[_Finding] = []
    for marker, reason in checks.items():
        if marker in lowered:
            severity = "critical" if "docker.sock" in marker or "privileged" in marker else "high"
            findings.append(
                _Finding(
                    category="container_vulnerability",
                    severity=severity,
                    message=f"Container risk detected: '{marker}' because {reason}.",
                    fix=(
                        "Use non-root users, pinned images, restricted capabilities, no host "
                        "network, and no Docker socket mounts."
                    ),
                    blocked_action=f"Blocked container configuration using '{marker}'.",
                )
            )
    return findings


def _check_sensitive_data_exposure(text: str, sensitivity_level: str) -> list[_Finding]:
    lowered = text.lower()
    findings: list[_Finding] = []
    for marker in sorted(_SENSITIVE_MARKERS):
        if marker in lowered:
            findings.append(
                _Finding(
                    category="sensitive_data_exposure",
                    severity="high",
                    message=f"Sensitive data marker detected: '{marker}'.",
                    fix=(
                        "Minimize sensitive fields, redact before model routing, and prefer local "
                        "brains for private data."
                    ),
                    blocked_action=(
                        "Blocked external routing until sensitive data handling is defined."
                    ),
                )
            )
    if sensitivity_level.lower() in {"private", "confidential", "restricted"} and text:
        findings.append(
            _Finding(
                category="sensitive_data_exposure",
                severity="medium",
                message="Private sensitivity level requires local/private routing controls.",
                fix="Route through local brains or approved providers with explicit data policy.",
            )
        )
    return findings


def _recommended_fixes(findings: list[_Finding]) -> list[str]:
    fixes = [finding.fix for finding in findings]
    if not fixes:
        fixes = [
            "Continue validating external inputs before routing.",
            "Keep secrets in environment variables or secret storage only.",
            "Run untrusted code in a sandbox with least-privilege permissions.",
        ]
    return _dedupe(fixes)


def _score(findings: list[_Finding]) -> int:
    score = 100
    weights = {"low": 5, "medium": 10, "high": 20, "critical": 35}
    for finding in findings:
        score -= weights.get(finding.severity, 10)
    return max(0, score)


def _dedupe_findings(findings: list[_Finding]) -> list[_Finding]:
    seen: set[tuple[str, str]] = set()
    result: list[_Finding] = []
    for finding in findings:
        key = (finding.category, finding.message)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return result


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _redact(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def _redact_path(path: str) -> str:
    if ".env" in path:
        return path.replace(".env", "[redacted-env-file]")
    if ".ssh" in path:
        return path.replace(".ssh", "[redacted-ssh-dir]")
    return path
