from __future__ import annotations

from app.main import create_app


def test_openapi_exposes_google_only_authentication_without_password_surfaces() -> None:
    document = create_app(testing=True).openapi()
    forbidden = ("password", "credential", "reset", "recovery", "lockout", "register", "signup")
    serialized = str(document).casefold()
    paths = tuple(document["paths"])

    assert "/api/v1/auth/google/login" in paths
    assert "/api/v1/auth/google/callback" in paths
    assert "/api/v1/admin/organization-domain-mappings" in paths
    assert not any(term in path.casefold() for path in paths for term in forbidden)
    assert 'type\': \'password' not in serialized
    callback = document["paths"]["/api/v1/auth/google/callback"]["get"]
    assert "requestBody" not in callback
    assert not any(
        parameter.get("name") in {"role", "organizationId"}
        for parameter in callback.get("parameters", [])
    )
