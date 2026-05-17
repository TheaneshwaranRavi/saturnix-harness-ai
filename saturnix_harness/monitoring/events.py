from __future__ import annotations

import logging
from collections import deque
from typing import Any

from saturnix_harness.schemas import RuntimeEvent


class MonitoringLayer:
    """Lightweight runtime event layer for API, CLI, and future observability sinks."""

    def __init__(self, max_events: int = 500) -> None:
        self.events: deque[RuntimeEvent] = deque(maxlen=max_events)
        self.logger = logging.getLogger("saturnix_harness.monitoring")

    def record(
        self,
        name: str,
        message: str,
        level: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeEvent:
        event_level = level if level in {"debug", "info", "warning", "error"} else "info"
        event = RuntimeEvent(
            name=name,
            message=message,
            level=event_level,
            metadata=metadata or {},
        )
        self.events.append(event)
        log_method = getattr(self.logger, event_level, self.logger.info)
        log_method("%s: %s", name, message, extra={"metadata": event.metadata})
        return event

    def recent(self, limit: int = 50) -> list[RuntimeEvent]:
        return list(self.events)[-limit:]
