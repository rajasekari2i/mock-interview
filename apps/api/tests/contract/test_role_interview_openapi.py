from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

AUTH_CONTRACT = Path("specs/001-user-auth/contracts/auth.openapi.yaml")
FEATURE_CONTRACT = Path("specs/002-role-interview-management/contracts/role-interview.openapi.yaml")


def _load(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def _resolve(document: dict[str, object], reference: str) -> object:
    current: object = document
    for raw_part in reference.removeprefix("#/").split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        assert isinstance(current, dict)
        current = current[part]
    return current


def test_every_feature_contract_reference_resolves() -> None:
    document = _load(FEATURE_CONTRACT)

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if "$ref" in value:
                _resolve(document, cast(str, value["$ref"]))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(document)


def test_auth_and_feature_contracts_share_identity_and_cookie_contracts() -> None:
    auth = _load(AUTH_CONTRACT)
    feature = _load(FEATURE_CONTRACT)

    assert _resolve(auth, "#/components/securitySchemes/sessionCookie") == _resolve(
        feature, "#/components/securitySchemes/sessionCookie"
    )
    assert _resolve(auth, "#/components/schemas/CurrentUserResponse") == _resolve(
        feature, "#/components/schemas/CurrentUserResponse"
    )


def test_auth_contract_allows_every_supported_role_transition() -> None:
    document = _load(AUTH_CONTRACT)
    operation = _resolve(document, "#/paths/~1admin~1users~1{user_id}~1role/patch")
    assert isinstance(operation, dict)
    assert "rejects transitions away from Candidate" not in str(operation.get("description", ""))
    role_schema = _resolve(document, "#/components/schemas/Role")
    assert role_schema == {"type": "string", "enum": ["CANDIDATE", "MANAGER", "ADMIN"]}


def test_candidate_interview_contract_is_self_scoped_and_minimal() -> None:
    document = _load(FEATURE_CONTRACT)
    operation = _resolve(document, "#/paths/~1candidate~1interviews/get")
    assert isinstance(operation, dict)
    parameters = [
        _resolve(document, item["$ref"]) if "$ref" in item else item
        for item in operation["parameters"]
    ]
    assert "candidate" not in {item["name"] for item in parameters}
    schema = _resolve(document, "#/components/schemas/CandidateInterview")
    assert isinstance(schema, dict)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"id", "jobDescription", "scheduledAt", "status"}


def test_manager_jd_contract_is_owned_paginated_and_csrf_protected() -> None:
    document = _load(FEATURE_CONTRACT)
    path = _resolve(document, "#/paths/~1manager~1job-descriptions")
    assert isinstance(path, dict)

    list_operation = path["get"]
    assert isinstance(list_operation, dict)
    list_parameters = [
        _resolve(document, item["$ref"]) for item in list_operation["parameters"]
    ]
    assert {item["name"] for item in list_parameters} == {"page", "pageSize"}
    assert "Manager-owned" in list_operation["responses"]["200"]["description"]

    create_operation = path["post"]
    assert isinstance(create_operation, dict)
    mutation_parameters = [
        _resolve(document, item["$ref"]) for item in create_operation["parameters"]
    ]
    assert {item["name"] for item in mutation_parameters} == {"Origin", "X-CSRF-Token"}
    request_schema = _resolve(
        document,
        create_operation["requestBody"]["content"]["application/json"]["schema"]["$ref"],
    )
    assert request_schema["additionalProperties"] is False
    assert set(request_schema["required"]) == {"title", "content"}
    assert set(create_operation["responses"]) == {"201", "400", "401", "403"}


def test_manager_jd_upload_contract_is_bounded_multipart_with_safe_errors() -> None:
    document = _load(FEATURE_CONTRACT)
    operation = _resolve(document, "#/paths/~1manager~1job-descriptions~1upload/post")
    assert isinstance(operation, dict)
    content = operation["requestBody"]["content"]
    assert set(content) == {"multipart/form-data"}
    schema = content["multipart/form-data"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"title", "document"}
    assert schema["properties"]["document"] == {"type": "string", "format": "binary"}
    assert set(operation["responses"]) == {"201", "400", "401", "403", "413", "415"}
    assert "5 MiB" in operation["description"]


def test_manager_scheduling_contract_is_scoped_idempotent_and_csrf_protected() -> None:
    document = _load(FEATURE_CONTRACT)
    candidate_list = _resolve(document, "#/paths/~1manager~1candidates/get")
    assert isinstance(candidate_list, dict)
    assert candidate_list["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ManagerCandidatePage"
    }
    operation = _resolve(document, "#/paths/~1manager~1interviews/post")
    assert isinstance(operation, dict)
    parameters = [_resolve(document, item["$ref"]) for item in operation["parameters"]]
    assert {item["name"] for item in parameters} == {
        "Origin",
        "X-CSRF-Token",
        "Idempotency-Key",
    }
    assert set(operation["responses"]) == {"200", "201", "400", "401", "403", "404", "409"}
    request = _resolve(
        document,
        operation["requestBody"]["content"]["application/json"]["schema"]["$ref"],
    )
    assert request["additionalProperties"] is False
    assert set(request["required"]) == {"candidateId", "jobDescriptionId", "scheduledAt"}


def test_admin_contract_has_independent_pages_detail_and_all_role_updates() -> None:
    document = _load(FEATURE_CONTRACT)
    for path in ("/admin/users", "/admin/job-descriptions"):
        operation = _resolve(document, f"#/paths/{path.replace('/', '~1')}/get")
        assert isinstance(operation, dict)
        parameters = [_resolve(document, item["$ref"]) for item in operation["parameters"]]
        assert {item["name"] for item in parameters} == {"page", "pageSize"}
        assert set(operation["responses"]) == {"200", "401", "403"}
    detail = _resolve(document, "#/paths/~1admin~1users~1{user_id}/get")
    assert isinstance(detail, dict)
    assert "404" in detail["responses"]
    role_update = _resolve(document, "#/paths/~1admin~1users~1{user_id}~1role/patch")
    parameters = [_resolve(document, item["$ref"]) for item in role_update["parameters"]]
    assert {item["name"] for item in parameters} == {"Origin", "X-CSRF-Token"}
    assert _resolve(document, "#/components/schemas/Role")["enum"] == [
        "CANDIDATE",
        "MANAGER",
        "ADMIN",
    ]
