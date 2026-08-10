from __future__ import annotations

from app.auth.models import Base


def test_job_description_and_scheduled_interview_metadata_matches_contract() -> None:
    job_descriptions = Base.metadata.tables["job_descriptions"]
    interviews = Base.metadata.tables["scheduled_interviews"]

    assert set(job_descriptions.columns.keys()) == {
        "id",
        "org_id",
        "created_by_user_id",
        "title",
        "source_type",
        "content_text",
        "source_format",
        "created_at",
        "updated_at",
    }
    assert set(interviews.columns.keys()) == {
        "id",
        "org_id",
        "candidate_user_id",
        "job_description_id",
        "scheduling_manager_user_id",
        "scheduled_at",
        "status",
        "idempotency_key_digest",
        "request_fingerprint",
        "created_at",
        "updated_at",
    }
    assert interviews.columns["idempotency_key_digest"].type.length == 32
    assert interviews.columns["request_fingerprint"].type.length == 32
