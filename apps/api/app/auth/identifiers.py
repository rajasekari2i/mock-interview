"""Canonical identity values accepted at the authentication boundary."""

from __future__ import annotations

import unicodedata

from email_validator import EmailNotValidError, validate_email


def canonicalize_domain(value: str) -> str:
    """Return one exact lower-case IDNA domain or reject ambiguous syntax."""

    raw = value.strip()
    if (
        not raw
        or len(raw) > 253
        or raw.endswith(".")
        or "@" in raw
        or "://" in raw
        or "*" in raw
    ):
        raise ValueError("Invalid domain")
    labels = raw.split(".")
    if len(labels) < 2 or any(not label for label in labels):
        raise ValueError("Invalid domain")
    try:
        encoded_labels = [label.encode("idna").decode("ascii").casefold() for label in labels]
    except UnicodeError as error:
        raise ValueError("Invalid domain") from error
    if any(
        len(label) > 63
        or label.startswith("-")
        or label.endswith("-")
        or not all(character.isalnum() or character == "-" for character in label)
        for label in encoded_labels
    ):
        raise ValueError("Invalid domain")
    domain = ".".join(encoded_labels)
    if len(domain) > 253:
        raise ValueError("Invalid domain")
    return domain


def normalize_verified_email(value: str) -> tuple[str, str, str]:
    """Validate a provider-verified email and return email, domain, and local part."""

    try:
        result = validate_email(
            value.strip(),
            check_deliverability=False,
            allow_smtputf8=False,
            test_environment=True,
        )
    except (EmailNotValidError, ValueError) as error:
        raise ValueError("Invalid verified email") from error
    normalized = result.normalized
    local_part, _, raw_domain = normalized.rpartition("@")
    domain = canonicalize_domain(raw_domain)
    return f"{local_part}@{domain}", domain, local_part


def display_name_from_claim(claim: object, *, fallback: str) -> str:
    """Normalize an optional signed name or use the validated email local part."""

    if isinstance(claim, str):
        normalized = " ".join(unicodedata.normalize("NFKC", claim).split())
        if (
            normalized
            and len(normalized) <= 200
            and not any(unicodedata.category(character).startswith("C") for character in normalized)
        ):
            return normalized
    return fallback
