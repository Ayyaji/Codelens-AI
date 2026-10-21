"""CORS_ORIGINS is applied for the S3 alternative and stays open for local dev."""

from rag_core.config import cors_origins


def test_cors_origins_default_is_open(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert cors_origins() == ["*"]


def test_cors_origins_lists_the_cloudfront_site(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://d111.cloudfront.net/")
    origins = cors_origins()
    assert origins[0] == "https://d111.cloudfront.net"
    assert "http://localhost:5173" in origins
    assert "*" not in origins
