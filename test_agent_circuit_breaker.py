import pytest

from app.agents.reliability import CircuitBreaker, CircuitOpenError


def test_successful_call():
    breaker = CircuitBreaker()

    result = breaker.call(lambda: "success")

    assert result == "success"
    assert breaker.state == "closed"


def test_circuit_opens_after_failures():
    breaker = CircuitBreaker(failure_threshold=3)

    def failing_call():
        raise RuntimeError("Provider unavailable")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            breaker.call(failing_call)

    assert breaker.state == "open"

    with pytest.raises(CircuitOpenError):
        breaker.call(lambda: "success")


def test_circuit_recovers():
    current_time = [0]

    def clock():
        return current_time[0]

    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=30,
        clock=clock
    )

    def failing_call():
        raise RuntimeError("Provider unavailable")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            breaker.call(failing_call)

    assert breaker.state == "open"

    current_time[0] = 31

    result = breaker.call(lambda: "recovered")

    assert result == "recovered"
    assert breaker.state == "closed"
    assert breaker.failure_count == 0


def test_success_resets_failure_count():
    breaker = CircuitBreaker(failure_threshold=3)

    def failing_call():
        raise RuntimeError("Temporary failure")

    with pytest.raises(RuntimeError):
        breaker.call(failing_call)

    assert breaker.failure_count == 1

    assert breaker.call(lambda: "success") == "success"

    assert breaker.failure_count == 0
    assert breaker.state == "closed"