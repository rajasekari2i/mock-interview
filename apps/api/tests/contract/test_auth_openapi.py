from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import yaml

CONTRACT_PATH = Path("specs/001-user-auth/contracts/auth.openapi.yaml")


@pytest.fixture(scope="module")
def contract() -> dict[str, object]:
    document = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return cast(dict[str, object], document)


def resolve(document: dict[str, object], reference: str) -> dict[str, object]:
    assert reference.startswith("#/")
    current: object = document
    for part in reference[2:].split("/"):
        assert isinstance(current, dict) and part in current
        current = current[part]
    assert isinstance(current, dict)
    return cast(dict[str, object], current)


def validate_sample(document: dict[str, object], schema: dict[str, object], value: object) -> None:
    if "$ref" in schema:
        validate_sample(document, resolve(document, cast(str, schema["$ref"])), value)
        return
    if "allOf" in schema:
        for option in cast(list[dict[str, object]], schema["allOf"]):
            validate_sample(document, option, value)
        return
    if "oneOf" in schema:
        options = cast(list[dict[str, object]], schema["oneOf"])
        valid = 0
        for option in options:
            try:
                validate_sample(document, option, value)
            except AssertionError:
                continue
            valid += 1
        assert valid == 1
        return
    if schema.get("type") == "object":
        assert isinstance(value, dict)
        properties = cast(dict[str, dict[str, object]], schema.get("properties", {}))
        assert set(cast(list[str], schema.get("required", []))) <= set(value)
        if schema.get("additionalProperties") is False:
            assert set(value) <= set(properties)
        for key, item in value.items():
            if key in properties:
                validate_sample(document, properties[key], item)
        return
    if "const" in schema:
        assert value == schema["const"]
    if "enum" in schema:
        assert value in cast(list[object], schema["enum"])


def test_openapi_document_and_every_local_reference_are_executable(
    contract: dict[str, object],
) -> None:
    assert contract["openapi"] == "3.1.0"

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if "$ref" in value:
                resolve(contract, cast(str, value["$ref"]))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(contract)


@pytest.mark.parametrize(
    "user",
    [
        {
            "id": "10000000-0000-0000-0000-000000000001",
            "organizationId": "20000000-0000-0000-0000-000000000001",
            "displayName": "Candidate",
            "email": "candidate@example.test",
            "profilePictureUrl": None,
            "role": "CANDIDATE",
            "candidateProfileId": "30000000-0000-0000-0000-000000000001",
        },
        {
            "id": "10000000-0000-0000-0000-000000000002",
            "organizationId": "20000000-0000-0000-0000-000000000001",
            "displayName": "Manager",
            "email": "manager@example.test",
            "profilePictureUrl": "https://lh3.googleusercontent.com/manager",
            "role": "MANAGER",
        },
        {
            "id": "10000000-0000-0000-0000-000000000003",
            "organizationId": "20000000-0000-0000-0000-000000000001",
            "displayName": "Admin",
            "email": "admin@example.test",
            "profilePictureUrl": None,
            "role": "ADMIN",
        },
    ],
)
def test_current_user_one_of_samples_validate_exactly_one_role(
    contract: dict[str, object], user: dict[str, object]
) -> None:
    response = {
        "user": user,
        "session": {
            "absoluteExpiresAt": "2026-08-09T18:00:00Z",
            "idleExpiresAt": "2026-08-09T12:00:00Z",
        },
    }
    schema = resolve(contract, "#/components/schemas/CurrentUserResponse")
    validate_sample(contract, schema, response)


def test_redirect_cookie_cache_and_csrf_contracts_are_explicit(
    contract: dict[str, object],
) -> None:
    paths = cast(dict[str, dict[str, dict[str, object]]], contract["paths"])
    login_redirect = paths["/auth/google/login"]["get"]["responses"]["302"]
    callback_redirect = paths["/auth/google/callback"]["get"]["responses"]["303"]
    logout = paths["/auth/logout"]["post"]

    assert "Location" in cast(dict[str, object], login_redirect["headers"])
    assert "Cache-Control" in cast(dict[str, object], callback_redirect["headers"])
    cookie_description = cast(dict[str, dict[str, object]], callback_redirect["headers"])[
        "Set-Cookie"
    ]["description"]
    assert all(
        value in cast(str, cookie_description)
        for value in ("__Host-mi_session", "HttpOnly", "SameSite=Lax", "mi_csrf")
    )
    parameter_refs = {
        cast(str, parameter["$ref"])
        for parameter in cast(list[dict[str, object]], logout["parameters"])
    }
    assert parameter_refs == {
        "#/components/parameters/CsrfToken",
        "#/components/parameters/Origin",
    }


def test_admin_provision_role_and_status_mutations_are_secured_and_typed(
    contract: dict[str, object],
) -> None:
    paths = cast(dict[str, dict[str, dict[str, object]]], contract["paths"])
    operations = [
        paths["/admin/users"]["post"],
        paths["/admin/users/{user_id}/role"]["patch"],
        paths["/admin/users/{user_id}/status"]["patch"],
    ]

    for operation in operations:
        assert operation["security"] == [{"sessionCookie": []}]
        responses = cast(dict[str, object], operation["responses"])
        assert {"401", "403"} <= set(responses)
        assert "requestBody" in operation

    assert "409" in cast(dict[str, object], operations[0]["responses"])
    assert "409" in cast(dict[str, object], operations[1]["responses"])


def test_domain_mapping_crud_contract_is_admin_secured_and_csrf_explicit(
    contract: dict[str, object],
) -> None:
    paths = cast(dict[str, dict[str, dict[str, object]]], contract["paths"])
    collection = paths["/admin/organization-domain-mappings"]
    item = paths["/admin/organization-domain-mappings/{mapping_id}"]
    assert collection["get"]["security"] == [{"sessionCookie": []}]
    mutations = [collection["post"], item["patch"], item["delete"]]
    for operation in mutations:
        assert operation["security"] == [{"sessionCookie": []}]
        parameter_refs = {
            cast(str, parameter["$ref"])
            for parameter in cast(list[dict[str, object]], operation["parameters"])
            if "$ref" in parameter
        }
        assert {
            "#/components/parameters/CsrfToken",
            "#/components/parameters/Origin",
        } <= parameter_refs
        assert {"401", "403"} <= set(cast(dict[str, object], operation["responses"]))
    assert "requestBody" in collection["post"]
    assert "requestBody" in item["patch"]
