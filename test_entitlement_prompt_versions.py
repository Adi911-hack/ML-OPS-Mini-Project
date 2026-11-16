import pytest

from app.agents.entitlement_agent import (
    BASIC_PROMPT,
    SYSTEM_PROMPT,
    DEFAULT_PROMPT_VERSION,
    get_entitlement_prompt
)


def test_basic_prompt():
    prompt = get_entitlement_prompt("v1-basic")

    assert prompt == BASIC_PROMPT


def test_exception_aware_prompt():
    prompt = get_entitlement_prompt("v2-exception-aware")

    assert prompt == SYSTEM_PROMPT


def test_default_prompt():
    prompt = get_entitlement_prompt()

    assert prompt == SYSTEM_PROMPT
    assert DEFAULT_PROMPT_VERSION == "v2-exception-aware"


def test_prompt_versions_differ():
    basic = get_entitlement_prompt("v1-basic")
    improved = get_entitlement_prompt("v2-exception-aware")

    assert basic != improved
    assert "extraordinary circumstances" in improved.lower()


def test_invalid_prompt_version():
    with pytest.raises(ValueError):
        get_entitlement_prompt("invalid-version")