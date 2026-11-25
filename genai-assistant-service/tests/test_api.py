"""The HTTP API with Cloud Run IAM identity (E2A v1.11.0): the caller is the Google ID token's email,
granted its tenant and roles by the deployment; four eyes across two people."""
import base64
import json

import pytest
from fastapi.testclient import TestClient

from genai_assistant_service.main import build_app

ANA, BO = "ana@acme.example", "bo@acme.example"


def b64(obj) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")


def as_(email, tenant="acme", iss="https://accounts.google.com"):
    token = f"{b64({'alg': 'RS256'})}.{b64({'iss': iss, 'email': email})}.c2ln"
    return {"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant}


@pytest.fixture
def client(assistant, monkeypatch):
    monkeypatch.setenv("E2A_IDENTITY_SOURCE", "gcp_cloud_run")
    monkeypatch.setenv("E2A_IDENTITY_TRUSTED_ISSUERS", '["https://accounts.google.com", "accounts.google.com"]')
    monkeypatch.setenv("E2A_IDENTITY_SUBJECT_ROLES", json.dumps({
        ANA: ["tenant:acme", "investigator"], BO: ["tenant:acme", "finance-approver"]}))
    return TestClient(build_app(assistant))


def test_health(client):
    assert client.get("/health").json()["status"] == "UP"


def test_ask_propose_and_approve_over_http(client, landscape):
    asked = client.post("/api/v1/ask", headers=as_(ANA), json={"text": "Why is bank line L-1001 unmatched?"})
    assert asked.status_code == 200 and "recon:L-1001" in asked.json()["citations"]
    proposed = client.post("/api/v1/ask", headers=as_(ANA), json={"text": "Propose a write-off for bank line L-1001"})
    approval = proposed.json()["approval_id"]
    assert [a["approval_id"] for a in client.get("/api/v1/approvals", headers=as_(BO)).json()] == [approval]
    assert client.post(f"/api/v1/approvals/{approval}/approve", headers=as_(ANA)).status_code == 403   # not an approver
    done = client.post(f"/api/v1/approvals/{approval}/approve", headers=as_(BO))
    assert done.status_code == 200 and done.json()["receipt"]["read_back"] is True
    detail = client.get(f"/api/v1/approvals/{approval}", headers=as_(BO)).json()
    assert detail["status"] == "APPROVED" and detail["decided_by"] == BO and detail["receipt"]["adjustment_id"]
    assert len(landscape.posted()) == 1


def test_no_token_an_ungranted_tenant_or_a_stranger_is_refused(client, landscape):
    body = {"text": "Why is bank line L-1001 unmatched?"}
    assert client.post("/api/v1/ask", json=body, headers={"X-Tenant-Id": "acme"}).status_code == 401
    assert client.post("/api/v1/ask", json=body, headers=as_(ANA, tenant="globex")).status_code == 403
    assert client.post("/api/v1/ask", json=body, headers=as_("eve@else.example")).status_code == 403
    assert landscape.calls == []


def test_an_unknown_approval_is_404(client):
    assert client.post("/api/v1/approvals/nope/approve", headers=as_(BO)).status_code == 404


def test_a_person_s_google_token_has_the_issuer_without_https(client):
    """gcloud auth print-identity-token for a person carries iss=accounts.google.com (live finding, GCP-01)."""
    body = {"text": "Why is bank line L-1001 unmatched?"}
    assert client.post("/api/v1/ask", json=body, headers=as_(ANA, iss="accounts.google.com")).status_code == 200
