import time
from threading import Lock


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold=3,
        recovery_timeout=30,
        clock=None
    ):
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be positive")

        if recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")

        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.clock = clock or time.monotonic

        self.state = "closed"
        self.failure_count = 0
        self.opened_at = None
        self.trial_in_progress = False
        self.lock = Lock()

    def call(self, function, *args, **kwargs):
        with self.lock:
            if self.state == "open":
                elapsed = self.clock() - self.opened_at

                if elapsed < self.recovery_timeout:
                    raise CircuitOpenError(
                        "Provider circuit breaker is open"
                    )

                self.state = "half-open"

            if self.state == "half-open":
                if self.trial_in_progress:
                    raise CircuitOpenError(
                        "Provider recovery trial is in progress"
                    )

                self.trial_in_progress = True

        try:
            result = function(*args, **kwargs)

        except Exception:
            with self.lock:
                self.failure_count += 1

                if (
                    self.state == "half-open"
                    or self.failure_count >= self.failure_threshold
                ):
                    self.state = "open"
                    self.opened_at = self.clock()

                self.trial_in_progress = False

            raise

        with self.lock:
            self.state = "closed"
            self.failure_count = 0
            self.opened_at = None
            self.trial_in_progress = False

        return result