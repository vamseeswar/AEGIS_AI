"""AEGIS AI — PII Masking, Secret Redaction, & Prompt Injection Guardrails
Enforces enterprise data loss prevention (DLP) by identifying and redacting:
  - US Social Security Numbers (SSN)
  - Payment Card Industry (PCI) 13-16 digit Credit Cards (with Luhn checksum validation)
  - Cloud / API Provider Secrets (AWS, OpenAI, Google Gemini, GitHub, Generic Tokens)
  - Email addresses and International Phone Numbers
  - IBAN bank routing identifiers
Also inspects prompt tokens for injection / jailbreak patterns.
"""

import re
from dataclasses import dataclass

# 1. PII Regular Expression Patterns
PII_PATTERNS = {
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "PHONE": re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b"),
    "CREDIT_CARD_CANDIDATE": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
}

# 2. Secret & API Key Patterns
SECRET_PATTERNS = {
    "AWS_KEY": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GITHUB_TOKEN": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,255}\b"),
    "OPENAI_KEY": re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),
    "GEMINI_KEY": re.compile(r"\bAIzaSy[a-zA-Z0-9_-]{33}\b"),
    "GENERIC_BEARER": re.compile(r"(?i)\bbearer\s+[a-zA-Z0-9_\-\.]{20,}\b"),
}

# 3. Prompt Injection & Jailbreak Heuristics
INJECTION_KEYWORDS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts)",
    r"disregard\s+(all\s+)?(previous|prior)\s+(instructions|rules)",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"dan\s+mode",
    r"jailbreak",
    r"reveal\s+(your\s+)?(system\s+prompt|secret\s+key|api\s+key)",
    r"output\s+(the\s+)?system\s+prompt",
    r"bypass\s+security\s+protocols",
    r"simulate\s+an\s+evil\s+ai",
]
INJECTION_REGEXES = [re.compile(p, re.IGNORECASE) for p in INJECTION_KEYWORDS]


def luhn_verify(card_str: str) -> bool:
    """Validates 13-16 digit numbers against the Luhn modulo-10 checksum algorithm."""
    digits = [int(c) for c in card_str if c.isdigit()]
    if not (13 <= len(digits) <= 19):
        return False
    # Luhn algorithm
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = d * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


@dataclass
class GuardrailResult:
    is_safe: bool
    has_pii: bool
    pii_types_found: list[str]
    has_injection: bool
    injection_flags: list[str]
    sanitized_text: str
    redactions_count: int


class GuardrailsEngine:
    """Enterprise content guardrails and DLP inspection engine."""

    @classmethod
    def sanitize_and_inspect(
        cls,
        text: str,
        mask_pii: bool = True,
        check_injection: bool = True,
    ) -> GuardrailResult:
        """Inspects text for PII, secrets, and prompt injection; redacts sensitive data."""
        sanitized = text
        pii_types_found: list[str] = []
        injection_flags: list[str] = []
        redactions = 0

        # 1. Mask API Secrets
        if mask_pii:
            for sec_name, pattern in SECRET_PATTERNS.items():
                matches = pattern.findall(sanitized)
                if matches:
                    pii_types_found.append(f"SECRET_{sec_name}")
                    redactions += len(matches)
                    sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)

            # 2. Mask SSN
            ssn_matches = PII_PATTERNS["SSN"].findall(sanitized)
            if ssn_matches:
                pii_types_found.append("SSN")
                redactions += len(ssn_matches)
                sanitized = PII_PATTERNS["SSN"].sub("[REDACTED_SSN]", sanitized)

            # 3. Mask Credit Cards with Luhn Check
            for match in PII_PATTERNS["CREDIT_CARD_CANDIDATE"].finditer(sanitized):
                card_cand = match.group(0)
                clean_cand = re.sub(r"[ -]", "", card_cand)
                if luhn_verify(clean_cand):
                    if "CREDIT_CARD" not in pii_types_found:
                        pii_types_found.append("CREDIT_CARD")
                    redactions += 1
                    sanitized = sanitized.replace(card_cand, "[REDACTED_CREDIT_CARD]")

            # 4. Mask IBAN
            iban_matches = PII_PATTERNS["IBAN"].findall(sanitized)
            if iban_matches:
                pii_types_found.append("IBAN")
                redactions += len(iban_matches)
                sanitized = PII_PATTERNS["IBAN"].sub("[REDACTED_IBAN]", sanitized)

            # 5. Mask Email
            email_matches = PII_PATTERNS["EMAIL"].findall(sanitized)
            if email_matches:
                pii_types_found.append("EMAIL")
                redactions += len(email_matches)
                sanitized = PII_PATTERNS["EMAIL"].sub("[REDACTED_EMAIL]", sanitized)

            # 6. Mask Phone
            phone_matches = PII_PATTERNS["PHONE"].findall(sanitized)
            if phone_matches:
                pii_types_found.append("PHONE")
                redactions += len(phone_matches)
                sanitized = PII_PATTERNS["PHONE"].sub("[REDACTED_PHONE]", sanitized)

        # 2. Inspect for Prompt Injection
        if check_injection:
            for pattern in INJECTION_REGEXES:
                match = pattern.search(text)
                if match:
                    injection_flags.append(match.group(0))

        is_safe = len(injection_flags) == 0

        return GuardrailResult(
            is_safe=is_safe,
            has_pii=len(pii_types_found) > 0,
            pii_types_found=pii_types_found,
            has_injection=len(injection_flags) > 0,
            injection_flags=injection_flags,
            sanitized_text=sanitized,
            redactions_count=redactions,
        )
