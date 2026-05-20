from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE = os.environ.get("SATURNIX_API_BASE", "http://localhost:8088").rstrip("/")
DASHBOARD_BASE = os.environ.get("SATURNIX_DASHBOARD_BASE", "http://localhost:3000").rstrip("/")


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def main() -> int:
    checks: list[Check] = []
    checks.extend(_check_backend())
    checks.extend(_check_frontend())

    for check in checks:
        marker = "PASS" if check.ok else "FAIL"
        print(f"[{marker}] {check.name}: {check.detail}")

    return 0 if all(check.ok for check in checks) else 1


def _check_backend() -> list[Check]:
    checks: list[Check] = []
    for path in [
        "/health",
        "/dashboard/overview",
        "/dashboard/doctrine",
        "/agents",
        "/brains",
        "/security/status",
        "/workflows",
    ]:
        checks.append(_get_json(f"backend {path}", f"{API_BASE}{path}"))
    checks.append(
        _get_json(
            "backend /memory",
            f"{API_BASE}/memory",
            expected=lambda payload: isinstance(payload, list),
        )
    )

    checks.append(
        _post_json(
            "backend security scan",
            f"{API_BASE}/security/scan-input",
            {
                "input_text": "Verify this SATURNIX workflow before execution.",
                "source": "smoke_mvp",
            },
        )
    )
    checks.append(
        _post_json(
            "backend agent dry-run",
            f"{API_BASE}/agents/execute",
            {
                "agent_name": "Security Agent",
                "goal": "Dry-run security validation for local MVP smoke test.",
                "dry_run": True,
            },
        )
    )
    checks.append(
        _post_json(
            "backend risky action approval gate",
            f"{API_BASE}/agents/execute",
            {
                "agent_name": "Security Agent",
                "goal": "Execute a non-dry-run admin security workflow.",
                "dry_run": False,
            },
            expected=lambda payload: payload.get("confirmation_required") is True,
        )
    )
    return checks


def _check_frontend() -> list[Check]:
    return [
        _get_text(f"frontend {path}", f"{DASHBOARD_BASE}{path}")
        for path in [
            "/",
            "/agents",
            "/security-center",
            "/memory-vault",
            "/brain-router",
            "/workflows",
        ]
    ]


def _get_json(name: str, url: str, expected=lambda payload: bool(payload)) -> Check:
    return _request_json(name, Request(url, headers={"Accept": "application/json"}), expected)


def _post_json(
    name: str,
    url: str,
    payload: dict[str, Any],
    expected=lambda payload: bool(payload),
) -> Check:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    return _request_json(name, request, expected=expected)


def _request_json(name: str, request: Request, expected=lambda payload: bool(payload)) -> Check:
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
            ok = 200 <= response.status < 300 and expected(payload)
            return Check(name, ok, f"HTTP {response.status}")
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return Check(name, False, str(exc))


def _get_text(name: str, url: str) -> Check:
    try:
        with urlopen(url, timeout=10) as response:
            body = response.read(256).decode("utf-8", errors="ignore")
            ok = 200 <= response.status < 300 and bool(body)
            return Check(name, ok, f"HTTP {response.status}")
    except (HTTPError, URLError, TimeoutError) as exc:
        return Check(name, False, str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
