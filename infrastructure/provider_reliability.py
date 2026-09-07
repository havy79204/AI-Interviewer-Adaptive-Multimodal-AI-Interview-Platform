from __future__ import annotations

from enum import Enum
from time import monotonic


class ProviderHealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OPEN = "open"
    RECOVERING = "recovering"


class ProviderErrorClassifier:
    """Normalize provider failure modes and decide whether a retry is safe."""

    RETRYABLE_CODES = {
        "timeout",
        "network_error",
        "rate_limit",
        "server_error",
        "transient",
        "retryable",
    }
    NON_RETRYABLE_CODES = {
        "auth_error",
        "invalid_request",
        "malformed_config",
        "validation_error",
        "permission_error",
    }

    def is_retryable(self, code: str | None) -> bool:
        if code is None:
            return False
        normal = code.lower().replace("-", "_")
        return normal in self.RETRYABLE_CODES or "timeout" in normal or "rate" in normal or "error" in normal and "auth" not in normal

    def classify(self, error: Exception | str | None) -> str:
        if isinstance(error, Exception):
            message = str(error).lower()
            if "auth" in message or "forbidden" in message or "invalid api key" in message:
                return "auth_error"
            if "timeout" in message:
                return "timeout"
            if "rate" in message or "429" in message:
                return "rate_limit"
            if "network" in message or "connection" in message:
                return "network_error"
            return "transient"
        if error is None:
            return "unknown"
        return str(error).lower().replace("-", "_")


class CircuitBreaker:
    """Simple circuit breaker to protect downstream providers from retry storms."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout_seconds: int = 30, success_threshold: int = 2) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.success_threshold = success_threshold
        self.state = ProviderHealthState.HEALTHY
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = 0.0

    def allow_request(self) -> bool:
        if self.state == ProviderHealthState.OPEN:
            if monotonic() - self.opened_at >= self.recovery_timeout_seconds:
                self.state = ProviderHealthState.RECOVERING
                self.success_count = 0
                return True
            return False
        return True

    def record_success(self) -> None:
        if self.state == ProviderHealthState.RECOVERING:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = ProviderHealthState.HEALTHY
                self.failure_count = 0
                self.success_count = 0
                return
        if self.state == ProviderHealthState.HEALTHY:
            self.failure_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.state == ProviderHealthState.HEALTHY and self.failure_count >= self.failure_threshold:
            self.state = ProviderHealthState.OPEN
            self.opened_at = monotonic()
            self.failure_count = 0
        elif self.state == ProviderHealthState.RECOVERING:
            self.state = ProviderHealthState.OPEN
            self.opened_at = monotonic()
            self.failure_count = 0
            self.success_count = 0

    def snapshot(self) -> dict[str, str | int | float]:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "opened_at": self.opened_at,
        }
