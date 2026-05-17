class SaturnixError(Exception):
    """Base exception for all framework-level failures."""


class ConfigurationError(SaturnixError):
    """Raised when the configured runtime cannot satisfy a requested operation."""


class BrainProviderError(SaturnixError):
    """Raised when a brain provider cannot complete a request."""


class RoutingError(SaturnixError):
    """Raised when no provider, agent, or tool can satisfy a request."""


class ToolExecutionError(SaturnixError):
    """Raised when a tool invocation fails."""


class MemoryError(SaturnixError):
    """Raised when memory persistence or retrieval fails."""


class VerificationError(SaturnixError):
    """Raised when verification cannot be completed."""

