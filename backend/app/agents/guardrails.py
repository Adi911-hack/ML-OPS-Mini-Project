import re


INJECTION_PATTERNS = [
    r"ignore (all |your |previous |above )*instructions",
    r"disregard (all |your |previous |above )*instructions",
    r"override (your |the )*(system|developer|safety) (prompt|instructions|rules)",
    r"reveal (your |the )*(system prompt|developer instructions)",
    r"you are now (a |an )?",
    r"act as (a |an )?(system|developer|administrator)",
    r"bypass (the |your )*(safety|security|verification)",
    r"approve (my |this |the )*claim (regardless|without verification)",
]


TOXICITY_PATTERNS = [
    r"\bi will kill you\b",
    r"\bi will hurt you\b",
    r"\bkill yourself\b",
    r"\bviolent threat\b",
]


ALLOWED_ROUTES = {
    "pay-as-computed",
    "request-further-evidence",
    "decline"
}


def detect_prompt_injection(text):
    if not isinstance(text, str):
        return False

    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in INJECTION_PATTERNS
    )


def detect_toxicity(text):
    if not isinstance(text, str):
        return False

    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in TOXICITY_PATTERNS
    )


def check_claim_input(claim):
    description = claim.get("description", "")

    return {
        "prompt_injection_detected": detect_prompt_injection(
            description
        ),
        "toxicity_detected": detect_toxicity(description),
    }


def validate_agent_output(result):
    if not isinstance(result, dict):
        return False

    route = result.get("route")

    if route not in ALLOWED_ROUTES:
        return False

    if (
        route in {"pay-as-computed", "decline"}
        and result.get("verified") is not True
    ):
        return False

    if route == "pay-as-computed":
        monetary = result.get("monetary_compensation") or {}
        amount = monetary.get("amount_inr")

        if isinstance(amount, bool):
            return False

        if not isinstance(amount, (int, float)):
            return False

        if amount < 0:
            return False

    return True