from __future__ import annotations

import fitz
from fastapi.testclient import TestClient
import pytest

from immcad_api.main import create_app


def _pdf_payload(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


def _new_client() -> TestClient:
    return TestClient(create_app())


@pytest.mark.parametrize(
    ("forum", "expected_profile_id"),
    [
        ("federal_court_jr", "federal_court_jr_leave"),
        ("rpd", "rpd"),
        ("rad", "rad"),
        ("id", "id"),
        ("iad", "iad"),
        ("ircc_application", "ircc_pr_card_renewal"),
    ],
)
def test_document_compilation_intake_assigns_default_profile_by_forum(
    forum: str,
    expected_profile_id: str,
) -> None:
    client = _new_client()
    matter_id = f"matter-compilation-default-{forum}"

    intake_response = client.post(
        "/api/documents/intake",
        data={"forum": forum, "matter_id": matter_id},
        files=[
            (
                "files",
                (
                    "upload.pdf",
                    _pdf_payload("Uploaded filing material."),
                    "application/pdf",
                ),
            ),
        ],
    )

    assert intake_response.status_code == 200
    assert intake_response.json()["compilation_profile_id"] == expected_profile_id


def test_document_compilation_profile_override_persists_to_readiness_and_package() -> None:
    client = _new_client()
    matter_id = "matter-compilation-profile-override"

    intake_response = client.post(
        "/api/documents/intake",
        data={
            "forum": "federal_court_jr",
            "matter_id": matter_id,
            "compilation_profile_id": "federal_court_jr_hearing",
        },
        files=[
            (
                "files",
                (
                    "notice.pdf",
                    _pdf_payload("Notice of Application to commence judicial review."),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "decision.pdf",
                    _pdf_payload("Decision under review by tribunal."),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "affidavit.pdf",
                    _pdf_payload(
                        "Affidavit sworn before the Commissioner for taking affidavits."
                    ),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "memorandum.pdf",
                    _pdf_payload("Memorandum of argument and written representations."),
                    "application/pdf",
                ),
            ),
        ],
    )
    assert intake_response.status_code == 200
    assert intake_response.json()["compilation_profile_id"] == "federal_court_jr_hearing"

    readiness_response = client.get(f"/api/documents/matters/{matter_id}/readiness")
    assert readiness_response.status_code == 200
    readiness_body = readiness_response.json()
    assert readiness_body["compilation_profile"]["id"] == "federal_court_jr_hearing"
    assert readiness_body["compilation_output_mode"] == "metadata_plan_only"

    package_response = client.post(f"/api/documents/matters/{matter_id}/package")
    assert package_response.status_code == 200
    package_body = package_response.json()
    assert package_body["compilation_profile"]["id"] == "federal_court_jr_hearing"
    assert package_body["compilation_output_mode"] == "metadata_plan_only"


def test_document_compilation_iad_subtype_profile_override_is_accepted() -> None:
    client = _new_client()
    matter_id = "matter-compilation-iad-subtype-override"

    intake_response = client.post(
        "/api/documents/intake",
        data={
            "forum": "iad",
            "matter_id": matter_id,
            "compilation_profile_id": "iad_sponsorship",
        },
        files=[
            (
                "files",
                (
                    "appeal-record.pdf",
                    _pdf_payload("IAD appeal record material."),
                    "application/pdf",
                ),
            ),
        ],
    )

    assert intake_response.status_code == 200
    assert intake_response.json()["compilation_profile_id"] == "iad_sponsorship"


def test_document_compilation_happy_path_generates_package() -> None:
    client = _new_client()
    matter_id = "matter-compilation-happy"

    intake_response = client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": matter_id},
        files=[
            (
                "files",
                (
                    "notice.pdf",
                    _pdf_payload("Notice of Application to commence judicial review."),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "decision.pdf",
                    _pdf_payload("Decision under review by tribunal."),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "affidavit.pdf",
                    _pdf_payload(
                        "Affidavit sworn before the Commissioner for taking affidavits."
                    ),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "memorandum.pdf",
                    _pdf_payload("Memorandum of argument and written representations."),
                    "application/pdf",
                ),
            ),
        ],
    )

    assert intake_response.status_code == 200

    package_response = client.post(f"/api/documents/matters/{matter_id}/package")

    assert package_response.status_code == 200
    body = package_response.json()
    assert body["is_ready"] is True
    assert body["forum"] == "federal_court_jr"
    assert len(body["table_of_contents"]) == 4


def test_document_compilation_package_returns_compiled_artifact_when_flag_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMMCAD_ENABLE_COMPILED_PDF", "1")
    client = _new_client()
    matter_id = "matter-compilation-compiled-pdf"

    intake_response = client.post(
        "/api/documents/intake",
        data={"forum": "rpd", "matter_id": matter_id},
        files=[
            (
                "files",
                (
                    "disclosure.pdf",
                    _pdf_payload("Document disclosure package for tribunal review."),
                    "application/pdf",
                ),
            )
        ],
    )
    assert intake_response.status_code == 200

    package_response = client.post(f"/api/documents/matters/{matter_id}/package")

    assert package_response.status_code == 200
    body = package_response.json()
    assert body["compilation_output_mode"] == "compiled_pdf"
    assert body["compiled_artifact"] is not None
    assert body["compiled_artifact"]["filename"] == f"{matter_id}-compiled-binder.pdf"
    assert body["compiled_artifact"]["byte_size"] > 0
    assert body["compiled_artifact"]["page_count"] >= 1
    assert len(body["compiled_artifact"]["sha256"]) == 64


def test_document_compilation_download_returns_pdf_when_flag_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMMCAD_ENABLE_COMPILED_PDF", "1")
    client = _new_client()
    matter_id = "matter-compilation-download-pdf"

    intake_response = client.post(
        "/api/documents/intake",
        data={"forum": "rpd", "matter_id": matter_id},
        files=[
            (
                "files",
                (
                    "disclosure.pdf",
                    _pdf_payload("Document disclosure package for tribunal review."),
                    "application/pdf",
                ),
            )
        ],
    )
    assert intake_response.status_code == 200

    download_response = client.get(f"/api/documents/matters/{matter_id}/package/download")

    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("application/pdf")
    assert "attachment;" in download_response.headers["content-disposition"]
    assert f"{matter_id}-compiled-binder.pdf" in download_response.headers["content-disposition"]
    assert download_response.content.startswith(b"%PDF")


def test_document_compilation_blocked_path_returns_policy_blocked() -> None:
    client = _new_client()
    matter_id = "matter-compilation-blocked"

    intake_response = client.post(
        "/api/documents/intake",
        data={"forum": "federal_court_jr", "matter_id": matter_id},
        files=[
            (
                "files",
                (
                    "notice.pdf",
                    _pdf_payload("Notice of Application to commence judicial review."),
                    "application/pdf",
                ),
            )
        ],
    )

    assert intake_response.status_code == 200

    package_response = client.post(f"/api/documents/matters/{matter_id}/package")

    assert package_response.status_code == 409
    assert package_response.json()["error"]["code"] == "POLICY_BLOCKED"
    assert (
        package_response.json()["error"]["policy_reason"]
        == "document_package_not_ready"
    )


def test_document_compilation_translation_requirement_is_conditional() -> None:
    client = _new_client()

    base_matter_id = "matter-compilation-rpd-base"
    base_intake = client.post(
        "/api/documents/intake",
        data={"forum": "rpd", "matter_id": base_matter_id},
        files=[
            (
                "files",
                (
                    "disclosure.pdf",
                    _pdf_payload("Document disclosure package for tribunal review."),
                    "application/pdf",
                ),
            )
        ],
    )
    assert base_intake.status_code == 200

    base_package = client.post(f"/api/documents/matters/{base_matter_id}/package")
    assert base_package.status_code == 200
    assert base_package.json()["is_ready"] is True

    translated_matter_id = "matter-compilation-rpd-translation"
    translated_intake = client.post(
        "/api/documents/intake",
        data={"forum": "rpd", "matter_id": translated_matter_id},
        files=[
            (
                "files",
                (
                    "disclosure.pdf",
                    _pdf_payload("Document disclosure package for tribunal review."),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "translation.pdf",
                    _pdf_payload("Translation prepared for hearing."),
                    "application/pdf",
                ),
            ),
        ],
    )
    assert translated_intake.status_code == 200

    readiness_response = client.get(
        f"/api/documents/matters/{translated_matter_id}/readiness"
    )
    assert readiness_response.status_code == 200
    assert "translator_declaration" in readiness_response.json()["missing_required_items"]

    translated_package = client.post(
        f"/api/documents/matters/{translated_matter_id}/package"
    )
    assert translated_package.status_code == 409
    assert (
        translated_package.json()["error"]["policy_reason"]
        == "document_package_not_ready"
    )
