from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from app.auth.errors import AuthError, ErrorCode
from app.jds.documents import parse_document
from app.jds.schemas import ManualJobDescriptionRequest
from pydantic import ValidationError
from pypdf import PdfWriter
from tests.fixtures.jd_documents import (
    BINARY_TXT,
    SAMPLE_TEXT,
    VALID_TXT,
    docx_bytes,
    pdf_bytes,
    traversal_docx_bytes,
)


@pytest.mark.parametrize(
    ("filename", "content_type", "payload", "expected_format"),
    [
        ("role.pdf", "application/pdf", pdf_bytes(), "PDF"),
        (
            "role.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            docx_bytes(),
            "DOCX",
        ),
        ("role.txt", "text/plain", VALID_TXT, "TXT"),
    ],
)
def test_supported_documents_are_bounded_and_normalized(
    filename: str, content_type: str, payload: bytes, expected_format: str
) -> None:
    parsed = parse_document(filename=filename, content_type=content_type, payload=payload)
    assert parsed.source_format == expected_format
    assert SAMPLE_TEXT in parsed.text
    assert parsed.original_filename == filename


def _encrypted_pdf() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("secret")
    writer.write(output)
    return output.getvalue()


def _blank_pdf() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(output)
    return output.getvalue()


def _archive_bomb() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "x" * 1_000_000)
        archive.writestr("word/document.xml", "<w:document />")
    return output.getvalue()


def _zip(entries: dict[str, str]) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, value in entries.items():
            archive.writestr(name, value)
    return output.getvalue()


def _too_many_entries() -> bytes:
    return _zip({f"safe/{index}.xml": "x" for index in range(501)})


def _large_archive() -> bytes:
    return _zip(
        {
            "[Content_Types].xml": "x" * (21 * 1024 * 1024),
            "word/document.xml": "<w:document />",
        }
    )


def _malformed_document_xml() -> bytes:
    return _zip(
        {
            "[Content_Types].xml": (
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Override PartName="/word/document.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                "</Types>"
            ),
            "_rels/.rels": "<Relationships />",
            "word/document.xml": "not xml",
        }
    )


@pytest.mark.parametrize(
    ("filename", "content_type", "payload", "code"),
    [
        ("large.txt", "text/plain", b"x" * (5 * 1024 * 1024 + 1), ErrorCode.UPLOAD_TOO_LARGE),
        ("fake.pdf", "application/pdf", b"not pdf", ErrorCode.UNSUPPORTED_DOCUMENT),
        ("broken.pdf", "application/pdf", b"%PDF-1.4 broken", ErrorCode.UNSUPPORTED_DOCUMENT),
        ("role.pdf", "text/plain", pdf_bytes(), ErrorCode.UNSUPPORTED_DOCUMENT),
        ("encrypted.pdf", "application/pdf", _encrypted_pdf(), ErrorCode.UNSUPPORTED_DOCUMENT),
        ("blank.pdf", "application/pdf", _blank_pdf(), ErrorCode.UNSUPPORTED_DOCUMENT),
        (
            "macro.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            docx_bytes(macro_enabled=True),
            ErrorCode.UNSUPPORTED_DOCUMENT,
        ),
        (
            "traversal.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            traversal_docx_bytes(),
            ErrorCode.UNSUPPORTED_DOCUMENT,
        ),
        (
            "absolute.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            _zip({"/absolute.xml": "x"}),
            ErrorCode.UNSUPPORTED_DOCUMENT,
        ),
        (
            "empty.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            _zip({}),
            ErrorCode.UNSUPPORTED_DOCUMENT,
        ),
        (
            "many.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            _too_many_entries(),
            ErrorCode.UNSUPPORTED_DOCUMENT,
        ),
        (
            "missing.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            _zip({"safe.xml": "x"}),
            ErrorCode.UNSUPPORTED_DOCUMENT,
        ),
        (
            "broken.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            b"PK-not-a-zip",
            ErrorCode.UNSUPPORTED_DOCUMENT,
        ),
        (
            "xml.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            _malformed_document_xml(),
            ErrorCode.UNSUPPORTED_DOCUMENT,
        ),
        (
            "large.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            _large_archive(),
            ErrorCode.UNSUPPORTED_DOCUMENT,
        ),
        (
            "bomb.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            _archive_bomb(),
            ErrorCode.UNSUPPORTED_DOCUMENT,
        ),
        ("binary.txt", "text/plain", BINARY_TXT, ErrorCode.UNSUPPORTED_DOCUMENT),
        ("utf8.txt", "text/plain", b"\xff", ErrorCode.UNSUPPORTED_DOCUMENT),
        ("blank.txt", "text/plain", b"  \n\t", ErrorCode.UNSUPPORTED_DOCUMENT),
        ("role.exe", "application/octet-stream", b"MZ", ErrorCode.UNSUPPORTED_DOCUMENT),
    ],
)
def test_hostile_or_content_free_documents_are_rejected(
    filename: str, content_type: str, payload: bytes, code: ErrorCode
) -> None:
    with pytest.raises(AuthError) as error:
        parse_document(filename=filename, content_type=content_type, payload=payload)
    assert error.value.code is code


def test_filename_is_reduced_to_a_display_only_basename() -> None:
    parsed = parse_document(
        filename="../../private/role.txt", content_type="text/plain", payload=VALID_TXT
    )
    assert parsed.original_filename == "role.txt"


def test_manual_schema_rejects_whitespace_only_fields() -> None:
    with pytest.raises(ValidationError):
        ManualJobDescriptionRequest(title=" ", content="content")
