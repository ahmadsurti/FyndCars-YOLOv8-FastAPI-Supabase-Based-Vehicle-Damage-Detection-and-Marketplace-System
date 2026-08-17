"""
fynd(cars) — API Test Suite
Run: pytest tests/test_api.py -v
"""

import io
import struct
import zlib
import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_jpeg(size_kb: int = 5) -> io.BytesIO:
    """Minimal valid JPEG for upload tests."""
    soi    = b'\xff\xd8'
    app0   = b'\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
    dqt    = b'\xff\xdb\x00\x43\x00' + bytes(range(1, 65))
    sof    = b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
    dht    = b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b'
    sos    = b'\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x7b\x40'
    eoi    = b'\xff\xd9'
    core   = soi + app0 + dqt + sof + dht + sos
    padding = b'\x00' * max(0, size_kb * 1024 - len(core) - 2)
    return io.BytesIO(core + padding + eoi)


def make_png() -> io.BytesIO:
    """Minimal valid 1x1 PNG."""
    sig       = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc  = struct.pack('>I', zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff)
    ihdr      = struct.pack('>I', 13) + b'IHDR' + ihdr_data + ihdr_crc
    raw       = zlib.compress(b'\x00\xff\x00\x00')
    idat_crc  = struct.pack('>I', zlib.crc32(b'IDAT' + raw) & 0xffffffff)
    idat      = struct.pack('>I', len(raw)) + b'IDAT' + raw + idat_crc
    # Pad beyond 1000 bytes so the size check passes
    pad_data  = b'\x00' * 1200
    pad_crc   = struct.pack('>I', zlib.crc32(b'tEXt' + pad_data) & 0xffffffff)
    pad_chunk = struct.pack('>I', len(pad_data)) + b'tEXt' + pad_data + pad_crc
    iend_crc  = struct.pack('>I', zlib.crc32(b'IEND') & 0xffffffff)
    iend      = struct.pack('>I', 0) + b'IEND' + iend_crc
    return io.BytesIO(sig + ihdr + idat + pad_chunk + iend)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_returns_200(self):
        assert client.get("/health").status_code == 200

    def test_structure(self):
        data = client.get("/health").json()
        assert {"status", "version", "cv_available", "agent_available", "uptime_seconds"} <= data.keys()

    def test_status_healthy(self):
        assert client.get("/health").json()["status"] == "healthy"

    def test_version_semver(self):
        parts = client.get("/health").json()["version"].split(".")
        assert len(parts) == 3


# ---------------------------------------------------------------------------
# Assessment (only runs when CV model is available)
# ---------------------------------------------------------------------------

def cv_available() -> bool:
    return client.get("/health").json().get("cv_available", False)


@pytest.mark.skipif(not cv_available(), reason="CV model not loaded — skip in CI without best.pt")
class TestAssessment:
    def _post(self, image_io, filename="car.jpg", content_type="image/jpeg"):
        return client.post("/assess", files={"image": (filename, image_io, content_type)})

    def test_accepts_jpeg(self):
        assert self._post(make_jpeg()).status_code == 200

    def test_accepts_png(self):
        assert self._post(make_png(), "car.png", "image/png").status_code == 200

    def test_response_schema(self):
        data = self._post(make_jpeg()).json()
        required = {"assessment_id", "timestamp", "decision", "damages_detected",
                    "total_damages", "decision_trace", "processing_time_ms",
                    "model_version", "policy_version", "cv_backend", "human_review_required"}
        assert required <= data.keys()

    def test_decision_is_valid(self):
        data = self._post(make_jpeg()).json()
        assert data["decision"] in ("AUTO_APPROVE", "HUMAN_REVIEW", "ESCALATE")

    def test_trace_not_empty(self):
        data = self._post(make_jpeg()).json()
        assert len(data["decision_trace"]) > 0

    def test_total_matches_list(self):
        data = self._post(make_jpeg()).json()
        assert data["total_damages"] == len(data["damages_detected"])

    def test_unique_ids(self):
        ids = {self._post(make_jpeg()).json()["assessment_id"] for _ in range(3)}
        assert len(ids) == 3


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_reject_pdf(self):
        r = client.post("/assess", files={"image": ("doc.pdf", io.BytesIO(b"x" * 2000), "application/pdf")})
        assert r.status_code == 400

    def test_reject_too_small(self):
        r = client.post("/assess", files={"image": ("tiny.jpg", io.BytesIO(b'\xff\xd8\xff\xd9'), "image/jpeg")})
        assert r.status_code == 400

    def test_missing_image_422(self):
        assert client.post("/assess").status_code == 422


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

class TestPolicy:
    def test_returns_200(self):
        assert client.get("/policy").status_code == 200

    def test_has_decision_types(self):
        data = client.get("/policy").json()
        assert {"AUTO_APPROVE", "HUMAN_REVIEW", "ESCALATE"} <= set(data["decision_types"])

    def test_has_rules_summary(self):
        assert "rules_summary" in client.get("/policy").json()


# ---------------------------------------------------------------------------
# OpenAPI
# ---------------------------------------------------------------------------

class TestDocs:
    def test_openapi_available(self):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        assert r.json()["info"]["title"] == "fynd(cars) API"

    def test_docs_available(self):
        assert client.get("/docs").status_code == 200


# ---------------------------------------------------------------------------
# Policy Engine & RAG Unit Tests
# ---------------------------------------------------------------------------

class TestPolicyAgent:
    def test_auto_approve_minor_scratch(self):
        from agentic.decision_agent import DecisionAgent
        from agentic.schemas import DamageSignal
        agent = DecisionAgent(policies_dir=Path(__file__).resolve().parent.parent / "policies")
        signal = DamageSignal(damage_type="scratch", confidence=0.92, severity="minor")
        decision = agent.decide(signal)
        assert decision.action == "AUTO_APPROVE"

    def test_low_confidence_human_review(self):
        from agentic.decision_agent import DecisionAgent
        from agentic.schemas import DamageSignal
        agent = DecisionAgent(policies_dir=Path(__file__).resolve().parent.parent / "policies")
        signal = DamageSignal(damage_type="dent", confidence=0.40, severity="moderate")
        decision = agent.decide(signal)
        assert decision.action == "HUMAN_REVIEW"


class TestKnowledgeRetriever:
    def test_simple_retriever_returns_chunks(self, tmp_path):
        from agentic.rag.simple_retriever import SimpleRetriever
        kb = tmp_path / "knowledge"
        kb.mkdir()
        (kb / "a.md").write_text("# Scratch\nMinor scratch info\n", encoding="utf-8")
        r = SimpleRetriever(knowledge_dir=kb)
        out = r.retrieve("scratch minor", top_k=3)
        assert out, "Expected non-empty retrieval"
        assert out[0].source == "a.md"

