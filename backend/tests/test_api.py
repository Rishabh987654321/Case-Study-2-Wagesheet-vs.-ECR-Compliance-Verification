"""API tests. DATA_DIR must be set to an isolated temp dir BEFORE importing app.*,
since app.db creates its SQLite engine at import time from the cached settings."""

import os
import tempfile
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="case2_test_")

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import SessionLocal
from app.main import app
from app.models import VerificationRecord

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample_data" / "input"
WAGESHEET = SAMPLE_DIR / "Sample_Wagesheet_Aug25.xlsx"
PF_ECR = SAMPLE_DIR / "PF ECR AUG-25 SAMPLE.pdf"
ESIC_ECR = SAMPLE_DIR / "ESIC ECR AUG-25 SAMPLE.pdf"

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _upload_sample(client, name=None):
    with open(WAGESHEET, "rb") as ws, open(PF_ECR, "rb") as pf, open(ESIC_ECR, "rb") as esic:
        data = {"name": name} if name else {}
        return client.post(
            "/api/verify",
            files={
                "wagesheet": (WAGESHEET.name, ws, XLSX_MIME),
                "pf_ecr": (PF_ECR.name, pf, "application/pdf"),
                "esic_ecr": (ESIC_ECR.name, esic, "application/pdf"),
            },
            data=data,
        )


@pytest.fixture(scope="module")
def completed_verification_id(client):
    r = _upload_sample(client, name="Phase 2 fixture run")
    assert r.status_code == 201
    return r.json()["verification_id"]


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_config(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    assert body["name_match_threshold"] == 90
    assert body["name_review_threshold"] == 70
    assert body["amount_tolerance"] == 1.0
    assert "max_file_mb" in body


def test_create_verification_success(client):
    r = _upload_sample(client, name="Create test")
    assert r.status_code == 201
    body = r.json()
    assert "verification_id" in body
    assert body["status"] == "processing"
    assert "3 files uploaded" in body["message"]


def test_create_verification_missing_file(client):
    with open(WAGESHEET, "rb") as ws:
        r = client.post("/api/verify", files={"wagesheet": (WAGESHEET.name, ws, XLSX_MIME)})
    assert r.status_code == 400
    assert r.json()["error"] == "INVALID_FILE"


def test_create_verification_wrong_file_type(client, tmp_path):
    bad = tmp_path / "wagesheet.txt"
    bad.write_text("not an excel file")
    with open(bad, "rb") as bad_f, open(PF_ECR, "rb") as pf, open(ESIC_ECR, "rb") as esic:
        r = client.post(
            "/api/verify",
            files={
                "wagesheet": ("wagesheet.txt", bad_f, "text/plain"),
                "pf_ecr": (PF_ECR.name, pf, "application/pdf"),
                "esic_ecr": (ESIC_ECR.name, esic, "application/pdf"),
            },
        )
    assert r.status_code == 400
    assert r.json()["error"] == "INVALID_FILE"


def test_create_verification_oversized_file(client, monkeypatch):
    import app.api.verification as mod

    monkeypatch.setattr(mod, "get_settings", lambda: Settings(max_file_mb=0))
    r = _upload_sample(client)
    assert r.status_code == 400
    assert r.json()["error"] == "FILE_TOO_LARGE"


def test_get_verification_eventually_completed(completed_verification_id, client):
    r = client.get(f"/api/verify/{completed_verification_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["employee_count"] == 12
    assert body["summary"]["pf"]["matched"] == 9
    assert body["summary"]["pf"]["name_mismatch"] == 1
    assert body["summary"]["pf"]["amount_mismatch"] == 1
    assert body["summary"]["pf"]["missing"] == 1
    assert body["summary"]["esic"]["matched"] == 8
    assert body["summary"]["esic"]["missing"] == 2


def test_list_employees_paginated(completed_verification_id, client):
    r = client.get(f"/api/verify/{completed_verification_id}/employees", params={"page_size": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 12
    assert body["page"] == 1
    assert body["page_size"] == 5
    assert body["pages"] == 3
    assert len(body["items"]) == 5


def test_list_employees_filter_by_pf_verdict(completed_verification_id, client):
    r = client.get(
        f"/api/verify/{completed_verification_id}/employees", params={"pf_verdict": "MATCHED"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 9
    assert all(item["pf"]["verdict"] == "MATCHED" for item in body["items"])


def test_list_employees_search(completed_verification_id, client):
    r = client.get(f"/api/verify/{completed_verification_id}/employees", params={"q": "SHARMA"})
    assert r.status_code == 200
    names = {item["name"] for item in r.json()["items"]}
    assert names == {"REKHA SHARMA"}


def test_export_xlsx(completed_verification_id, client):
    r = client.get(f"/api/verify/{completed_verification_id}/export")
    assert r.status_code == 200
    assert r.headers["content-type"] == XLSX_MIME
    assert len(r.content) > 0


def test_export_csv(completed_verification_id, client):
    r = client.get(f"/api/verify/{completed_verification_id}/export", params={"format": "csv"})
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert b"Employee Name" in r.content


def test_export_invalid_format(completed_verification_id, client):
    r = client.get(f"/api/verify/{completed_verification_id}/export", params={"format": "pdf"})
    assert r.status_code == 400
    assert r.json()["error"] == "INVALID_FILE"


def test_unmatched(completed_verification_id, client):
    r = client.get(f"/api/verify/{completed_verification_id}/unmatched")
    assert r.status_code == 200
    body = r.json()
    assert "pf_unmatched" in body
    assert "esic_unmatched" in body


def test_export_blocked_while_processing(completed_verification_id, client):
    db = SessionLocal()
    try:
        v = db.get(VerificationRecord, completed_verification_id)
        v.status = "processing"
        db.commit()
    finally:
        db.close()

    r = client.get(f"/api/verify/{completed_verification_id}/export")
    assert r.status_code == 409
    assert r.json()["error"] == "ALREADY_PROCESSING"

    db = SessionLocal()
    try:
        v = db.get(VerificationRecord, completed_verification_id)
        v.status = "completed"
        db.commit()
    finally:
        db.close()


def test_list_verifications(client):
    r = client.get("/api/verifications")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert body["items"][0]["status"] in ("processing", "completed", "failed")


def test_get_nonexistent_verification_404(client):
    r = client.get("/api/verify/nonexistent")
    assert r.status_code == 404
    assert r.json()["error"] == "NOT_FOUND"


def test_delete_verification(client):
    r = _upload_sample(client, name="Delete me")
    vid = r.json()["verification_id"]

    r = client.delete(f"/api/verify/{vid}")
    assert r.status_code == 204

    r = client.get(f"/api/verify/{vid}")
    assert r.status_code == 404

    data_dir = Path(os.environ["DATA_DIR"])
    assert not (data_dir / "uploads" / vid).exists()
