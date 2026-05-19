from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from fastapi import Header, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from saturnix_harness.config import Settings
from saturnix_harness.schemas import DashboardSecurityScanRequest, DashboardSecurityScanResult


class DashboardSecuritySentinel:
    """Dashboard-focused Security Sentinel with zero-trust scoring."""

    def scan(self, request: DashboardSecurityScanRequest) -> DashboardSecurityScanResult:
        findings: list[_Risk] = []
        text = _combined_text(request)
        findings.extend(_prompt_injection(text))
        findings.extend(_malicious_commands(request.commands, text))
        findings.extend(_suspicious_file_access(request.file_paths, text))
        findings.extend(_exposed_api_keys(text))
        findings.extend(_unsafe_code_execution(text))
        findings.extend(_abnormal_request_rate(request.request_count_last_minute))
        findings.extend(_unknown_connections(request.external_connections))
        findings.extend(_unauthorized_access(request.auth_context))
        findings.extend(_weak_authentication(request.auth_context))
        findings.extend(_dangerous_workflows(request.workflow))
        findings = _dedupe(findings)
        score = _score(findings)
        threat = _threat_level(score, findings)
        return DashboardSecurityScanResult(
            security_score=score,
            threat_level=threat,
            detected_risks=[risk.message for risk in findings],
            blocked_actions=[risk.blocked_action for risk in findings if risk.blocked_action],
            recommended_fixes=_recommended_fixes(findings),
            lockdown_required=threat == "CRITICAL",
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self.limit = settings.saturnix_rate_limit_per_minute
        self.window_seconds = 60
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = self.requests[client]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.limit:
            raise HTTPException(status_code=429, detail="SATURNIX dashboard rate limit exceeded.")
        bucket.append(now)
        return await call_next(request)


class JwtService:
    def __init__(self, settings: Settings) -> None:
        configured = (
            settings.saturnix_jwt_secret.get_secret_value()
            if settings.saturnix_jwt_secret
            else ""
        )
        if not configured:
            raise HTTPException(
                status_code=500,
                detail="SATURNIX_JWT_SECRET is required when dashboard auth is enabled.",
            )
        self.secret = configured

    def issue(self, subject: str, role: str = "admin", ttl_seconds: int = 3600) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": subject,
            "role": role,
            "iat": int(time.time()),
            "exp": int(time.time()) + ttl_seconds,
        }
        signing_input = f"{_b64(header)}.{_b64(payload)}"
        signature = hmac.new(
            self.secret.encode("utf-8"),
            signing_input.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{signing_input}.{_b64_bytes(signature)}"

    def verify(self, token: str) -> dict[str, Any]:
        try:
            header_part, payload_part, signature_part = token.split(".")
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid dashboard token.") from exc
        signing_input = f"{header_part}.{payload_part}"
        expected = hmac.new(
            self.secret.encode("utf-8"),
            signing_input.encode("ascii"),
            hashlib.sha256,
        ).digest()
        provided = _unb64(signature_part)
        if not hmac.compare_digest(expected, provided):
            raise HTTPException(status_code=401, detail="Invalid dashboard token signature.")
        payload = json.loads(_unb64(payload_part))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise HTTPException(status_code=401, detail="Dashboard token expired.")
        return payload


def dashboard_identity(
    settings: Settings,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    if not settings.saturnix_dashboard_auth_required:
        return {"sub": "local-dev", "role": "admin", "auth_required": False}
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Dashboard authentication required.")
    return JwtService(settings).verify(authorization.removeprefix("Bearer ").strip())


@dataclass(frozen=True)
class _Risk:
    category: str
    severity: str
    message: str
    fix: str
    blocked_action: str | None = None


_PROMPT_INJECTION = {
    "act as dan",
    "bypass guardrails",
    "developer message",
    "disable safety",
    "hidden instructions",
    "ignore previous instructions",
    "override instructions",
    "print your prompt",
    "reveal system prompt",
    "show system prompt",
}

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
]

_UNSAFE_CODE = {"eval(", "exec(", "pickle.loads", "subprocess", "os.system", "rm -rf"}
_DANGEROUS_COMMANDS = {"rm -rf", "format disk", "delete backups", "exfiltrate", "curl | sh"}


def _combined_text(request: DashboardSecurityScanRequest) -> str:
    return "\n".join(
        [
            request.input_text,
            " ".join(request.file_paths),
            " ".join(request.commands),
            " ".join(request.external_connections),
            json.dumps(request.workflow, default=str),
            json.dumps(request.auth_context, default=str),
        ]
    )


def _prompt_injection(text: str) -> list[_Risk]:
    lowered = text.lower()
    return [
        _Risk(
            category="prompt_injection",
            severity="high",
            message=f"Prompt injection marker detected: {marker}.",
            fix="Treat user-supplied instructions as data and strip override language.",
            blocked_action="Blocked prompt injection attempt.",
        )
        for marker in sorted(_PROMPT_INJECTION)
        if marker in lowered
    ]


def _malicious_commands(commands: list[str], text: str) -> list[_Risk]:
    lowered = f"{' '.join(commands)}\n{text}".lower()
    return [
        _Risk(
            category="malicious_command",
            severity="critical",
            message=f"Malicious command marker detected: {marker}.",
            fix="Block command execution and require admin review.",
            blocked_action=f"Blocked command containing {marker}.",
        )
        for marker in sorted(_DANGEROUS_COMMANDS)
        if marker in lowered
    ]


def _suspicious_file_access(file_paths: list[str], text: str) -> list[_Risk]:
    paths = [*file_paths, *re.findall(r"(/[A-Za-z0-9_./-]+|\.\./[A-Za-z0-9_./-]+)", text)]
    findings: list[_Risk] = []
    for path in paths:
        if ".." in path or any(marker in path for marker in (".env", ".ssh", "/etc/", "/root/")):
            findings.append(
                _Risk(
                    category="suspicious_file_access",
                    severity="high",
                    message=f"Suspicious file access requested: {_redact_path(path)}.",
                    fix="Sanitize file paths and enforce an allowlisted storage root.",
                    blocked_action=f"Blocked unsafe file path {_redact_path(path)}.",
                )
            )
    return findings


def _exposed_api_keys(text: str) -> list[_Risk]:
    risks: list[_Risk] = []
    for pattern in _SECRET_PATTERNS:
        for match in pattern.finditer(text):
            risks.append(
                _Risk(
                    category="exposed_api_key",
                    severity="critical",
                    message=f"Potential exposed credential: {_redact_secret(match.group(0))}.",
                    fix="Remove plaintext secret, rotate credential, and store encrypted.",
                    blocked_action="Blocked secret-bearing request.",
                )
            )
    return risks


def _unsafe_code_execution(text: str) -> list[_Risk]:
    lowered = text.lower()
    return [
        _Risk(
            category="unsafe_code_execution",
            severity="high",
            message=f"Unsafe code execution marker detected: {marker}.",
            fix="Use sandboxed tool APIs and allowlisted commands.",
            blocked_action=f"Blocked unsafe code marker {marker}.",
        )
        for marker in sorted(_UNSAFE_CODE)
        if marker in lowered
    ]


def _abnormal_request_rate(count: int) -> list[_Risk]:
    if count < 120:
        return []
    severity = "critical" if count >= 300 else "medium"
    return [
        _Risk(
            category="abnormal_request_rate",
            severity=severity,
            message=f"Abnormal request rate detected: {count} requests/minute.",
            fix="Throttle client, check audit logs, and rotate tokens if abuse is confirmed.",
            blocked_action="Rate limited suspicious client." if severity == "critical" else None,
        )
    ]


def _unknown_connections(connections: list[str]) -> list[_Risk]:
    unknown = [
        item for item in connections if not item.startswith(("https://api.", "http://localhost"))
    ]
    return [
        _Risk(
            category="unknown_external_connection",
            severity="medium",
            message=f"Unknown external connection attempt: {connection}.",
            fix="Allowlist external domains and block unknown egress by default.",
        )
        for connection in unknown
    ]


def _unauthorized_access(auth_context: dict[str, Any]) -> list[_Risk]:
    if auth_context.get("authenticated", True):
        return []
    return [
        _Risk(
            category="unauthorized_access",
            severity="high",
            message="Unauthenticated dashboard access attempt detected.",
            fix="Require JWT authentication and audit source IP.",
            blocked_action="Blocked unauthenticated dashboard action.",
        )
    ]


def _weak_authentication(auth_context: dict[str, Any]) -> list[_Risk]:
    if not auth_context.get("weak_password") and not auth_context.get("missing_mfa"):
        return []
    return [
        _Risk(
            category="weak_authentication",
            severity="medium",
            message="Weak authentication posture detected.",
            fix="Use strong credentials, short-lived JWTs, and MFA for admin security actions.",
        )
    ]


def _dangerous_workflows(workflow: dict[str, Any]) -> list[_Risk]:
    text = json.dumps(workflow, default=str).lower()
    markers = {"delete production", "disable logging", "send secrets", "privilege escalation"}
    return [
        _Risk(
            category="dangerous_workflow_execution",
            severity="critical",
            message=f"Dangerous workflow marker detected: {marker}.",
            fix="Require admin approval and run workflow through Security Sentinel first.",
            blocked_action=f"Blocked workflow containing {marker}.",
        )
        for marker in sorted(markers)
        if marker in text
    ]


def _score(risks: list[_Risk]) -> int:
    penalties = {"low": 5, "medium": 12, "high": 25, "critical": 45}
    score = 100
    for risk in risks:
        score -= penalties.get(risk.severity, 10)
    return max(0, score)


def _threat_level(score: int, risks: list[_Risk]) -> str:
    if any(risk.severity == "critical" for risk in risks) or score < 35:
        return "CRITICAL"
    if score < 60:
        return "HIGH"
    if score < 85:
        return "MEDIUM"
    return "LOW"


def _recommended_fixes(risks: list[_Risk]) -> list[str]:
    fixes: list[str] = []
    for risk in risks:
        if risk.fix not in fixes:
            fixes.append(risk.fix)
    if not fixes:
        fixes.append("No immediate security fixes required; continue monitoring.")
    return fixes


def _dedupe(risks: list[_Risk]) -> list[_Risk]:
    seen: set[tuple[str, str]] = set()
    deduped: list[_Risk] = []
    for risk in risks:
        key = (risk.category, risk.message)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(risk)
    return deduped


def _redact_secret(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def _redact_path(path: str) -> str:
    return path.replace("/Users/", "/Users/<redacted>/")


def _b64(value: dict[str, Any]) -> str:
    return _b64_bytes(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def _b64_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))
