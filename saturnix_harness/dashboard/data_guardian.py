from __future__ import annotations

import hashlib
import json
from pathlib import Path

from saturnix_harness.config import Settings
from saturnix_harness.dashboard.crypto import SecretCipher
from saturnix_harness.schemas import (
    DataClass,
    DataGuardianClassifyRequest,
    DataGuardianClassifyResult,
)


class DataGuardian:
    """SATURNIX data-protection engine for memory, storage, and backups."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cipher = SecretCipher(settings)
        self.allowed_roots = [
            Path(root).expanduser().resolve()
            for root in settings.saturnix_allowed_storage_roots.split(",")
            if root.strip()
        ]

    def classify(self, request: DataGuardianClassifyRequest) -> DataGuardianClassifyResult:
        data_class = _classify(request.content, request.path)
        sensitivity = _sensitivity(data_class, request.content)
        blocked = _blocked_actions(data_class, request.intended_action)
        return DataGuardianClassifyResult(
            data_class=data_class,
            sensitivity_score=sensitivity,
            encryption_required=data_class in {
                DataClass.personal_memory,
                DataClass.api_secrets,
                DataClass.voice_records,
                DataClass.critical_backups,
            },
            storage_namespace=_namespace_for_class(data_class),
            allowed_actions=_allowed_actions(data_class),
            blocked_actions=blocked,
            retention_policy=_retention_policy(data_class),
        )

    def encrypt_if_sensitive(
        self,
        content: str,
        classification: DataGuardianClassifyResult,
    ) -> tuple[str, dict]:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        metadata = {
            "data_class": classification.data_class.value,
            "sensitivity_score": classification.sensitivity_score,
            "encrypted": classification.encryption_required,
            "sha256": digest,
        }
        if not classification.encryption_required:
            return content, metadata
        return self.cipher.encrypt(content), metadata

    def sanitize_path(self, path: str) -> Path:
        candidate = Path(path).expanduser().resolve()
        if ".." in Path(path).parts:
            raise ValueError("Path traversal is blocked.")
        if self.allowed_roots and not any(
            candidate == root or root in candidate.parents for root in self.allowed_roots
        ):
            raise ValueError("Path is outside SATURNIX allowed storage roots.")
        return candidate

    def storage_status(self) -> dict:
        roots = []
        for root in self.allowed_roots:
            roots.append(
                {
                    "path": str(root),
                    "exists": root.exists(),
                    "role": _storage_role(root),
                    "encryption_required": True,
                    "backup_policy": "snapshot critical SATURNIX memory and audit logs",
                }
            )
        return {
            "external_ssd": {
                "role": "fast AI memory",
                "mount_status": "configured" if roots else "not_configured",
            },
            "hdd_vault": {
                "role": "SATURNIX Vault",
                "capacity_target": "10TB",
                "encryption": "required for critical_backups and api_secrets",
            },
            "backup_layers": ["external SSD", "HDD vault", "optional pendrive recovery"],
            "allowed_roots": roots,
        }

    def backup_plan(self) -> dict:
        return {
            "snapshot_types": [
                DataClass.project_data.value,
                DataClass.personal_memory.value,
                DataClass.agent_logs.value,
                DataClass.critical_backups.value,
            ],
            "encryption": "encrypt sensitive snapshots before writing to vault",
            "deletion_protection": "two-step confirmation for critical_backups",
            "duplicate_detection": "sha256 content fingerprints",
            "recovery_manifest": "JSON manifest with checksum, timestamp, and namespace",
        }


def _classify(content: str, path: str | None) -> DataClass:
    text = f"{content} {path or ''}".lower()
    if any(marker in text for marker in {"api_key", "secret", "password", "token", "sk-"}):
        return DataClass.api_secrets
    if any(marker in text for marker in {"backup", "snapshot", "recovery", "vault"}):
        return DataClass.critical_backups
    if any(marker in text for marker in {"voice", "transcript", "audio"}):
        return DataClass.voice_records
    if any(marker in text for marker in {"preference", "profile", "personal", "memory"}):
        return DataClass.personal_memory
    if any(marker in text for marker in {"log", "audit", "agent run", "trace"}):
        return DataClass.agent_logs
    if any(marker in text for marker in {"project", "workflow", "code", "agent"}):
        return DataClass.project_data
    return DataClass.public_data


def _sensitivity(data_class: DataClass, content: str) -> int:
    base = {
        DataClass.public_data: 10,
        DataClass.project_data: 35,
        DataClass.personal_memory: 70,
        DataClass.api_secrets: 100,
        DataClass.agent_logs: 50,
        DataClass.voice_records: 75,
        DataClass.critical_backups: 90,
    }[data_class]
    if any(marker in content.lower() for marker in {"private key", "ssn", "credit card"}):
        base = max(base, 95)
    return base


def _namespace_for_class(data_class: DataClass) -> str:
    if data_class == DataClass.public_data:
        return "dashboard:public"
    if data_class == DataClass.project_data:
        return "dashboard:project"
    if data_class == DataClass.personal_memory:
        return "user:theaneshwaran"
    if data_class == DataClass.api_secrets:
        return "dashboard:secrets"
    if data_class == DataClass.agent_logs:
        return "dashboard:audit"
    if data_class == DataClass.voice_records:
        return "dashboard:voice"
    return "dashboard:vault"


def _allowed_actions(data_class: DataClass) -> list[str]:
    actions = ["classify", "search", "backup"]
    if data_class != DataClass.api_secrets:
        actions.append("memory_save")
    if data_class in {DataClass.public_data, DataClass.project_data}:
        actions.append("share_with_agent")
    return actions


def _blocked_actions(data_class: DataClass, intended_action: str) -> list[str]:
    blocked = []
    if data_class == DataClass.api_secrets and intended_action in {"log", "share", "export"}:
        blocked.append("Never log, export, or send raw API secrets to frontend or agents.")
    if data_class == DataClass.critical_backups and intended_action == "delete":
        blocked.append("Prevent accidental deletion of critical backups.")
    return blocked


def _retention_policy(data_class: DataClass) -> str:
    policies = {
        DataClass.public_data: "retain while useful",
        DataClass.project_data: "retain for project lifetime",
        DataClass.personal_memory: "retain with user-controlled deletion",
        DataClass.api_secrets: "retain encrypted only; rotate regularly",
        DataClass.agent_logs: "retain with audit log rotation",
        DataClass.voice_records: "short retention unless explicitly approved",
        DataClass.critical_backups: "retain with encrypted recovery snapshots",
    }
    return policies[data_class]


def _storage_role(root: Path) -> str:
    text = json.dumps(root.parts).lower()
    if "ssd" in text:
        return "fast AI memory"
    if "vault" in text or "hdd" in text:
        return "SATURNIX Vault"
    return "configured storage root"
