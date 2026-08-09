from __future__ import annotations

import pytest
from app.auth.identifiers import (
    canonicalize_domain,
    display_name_from_claim,
    normalize_verified_email,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" Example.COM ", "example.com"),
        ("bücher.example", "xn--bcher-kva.example"),
        ("staff.example.com", "staff.example.com"),
    ],
)
def test_domains_are_canonicalized_for_exact_matching(raw: str, expected: str) -> None:
    assert canonicalize_domain(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "https://example.com",
        "*.example.com",
        "user@example.com",
        ".example.com",
        "example.com.",
        "-bad.example",
        "bad-.example",
        "bad..example",
    ],
)
def test_invalid_or_implicit_domain_syntax_is_rejected(raw: str) -> None:
    with pytest.raises(ValueError):
        canonicalize_domain(raw)


def test_domain_rejects_unencodable_and_idna_expanded_overall_lengths() -> None:
    with pytest.raises(ValueError):
        canonicalize_domain("\ud800.example")
    expanded = ".".join(["é" * 20] * 10)
    assert len(expanded) <= 253
    with pytest.raises(ValueError):
        canonicalize_domain(expanded)


def test_verified_email_is_validated_and_subdomains_do_not_match_parents() -> None:
    email, domain, local_part = normalize_verified_email(" Person@Staff.Example.COM ")
    assert (email, domain, local_part) == (
        "Person@staff.example.com",
        "staff.example.com",
        "Person",
    )
    assert domain != canonicalize_domain("example.com")
    with pytest.raises(ValueError):
        normalize_verified_email("not-an-email")


@pytest.mark.parametrize("claim", [None, "", "   ", "bad\x00name", "x" * 201, object()])
def test_unusable_display_name_falls_back_to_email_local_part(claim: object) -> None:
    assert display_name_from_claim(claim, fallback="candidate") == "candidate"


def test_display_name_normalizes_unicode_whitespace() -> None:
    assert display_name_from_claim("  Ada\t  Lovelace  ", fallback="ada") == "Ada Lovelace"
