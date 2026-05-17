from __future__ import annotations

from abc import ABC, abstractmethod

from saturnix_harness.schemas import MemoryRecord


class MemoryStore(ABC):
    @abstractmethod
    def add(self, record: MemoryRecord) -> MemoryRecord:
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, namespace: str = "default", limit: int = 5) -> list[MemoryRecord]:
        raise NotImplementedError

    @abstractmethod
    def list(self, namespace: str = "default", limit: int = 50) -> list[MemoryRecord]:
        raise NotImplementedError

    @abstractmethod
    def get(self, record_id: str) -> MemoryRecord | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, record_id: str) -> bool:
        raise NotImplementedError
