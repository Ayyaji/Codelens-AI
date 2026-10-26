"""CORS_ORIGINS is applied for the S3 alternative and stays open for local dev."""

import re

from rag_core.config import cors_origin_regex, cors_origins

# Same pattern deploy/simple/backend-setup.sh writes. A Vercel production
# host and a preview host match; a lookalike host does not.
VERCEL_ORIGIN_REGEX = r"https://([A-Za-z0-9-]+\.)*vercel\.app"


def test_cors_origins_default_is_open(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("CORS_ORIGIN_REGEX", raising=False)
    assert cors_origins() == ["*"]
    assert cors_origin_regex() is None


def test_cors_origins_lists_the_cloudfront_site(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://d111.cloudfront.net/")
    origins = cors_origins()
    assert origins[0] == "https://d111.cloudfront.net"
    assert "http://localhost:5173" in origins
    assert "*" not in origins


def test_vercel_regex_allows_vercel_hosts_only(monkeypatch):
    monkeypatch.setenv("CORS_ORIGIN_REGEX", VERCEL_ORIGIN_REGEX)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    origins = cors_origins()
    assert "*" not in origins
    assert "http://localhost:5173" in origins
    assert cors_origin_regex() == VERCEL_ORIGIN_REGEX
    assert re.fullmatch(VERCEL_ORIGIN_REGEX, "https://codelens-ai.vercel.app")
    assert re.fullmatch(VERCEL_ORIGIN_REGEX, "https://codelens-git-main-user.vercel.app")
    assert not re.fullmatch(VERCEL_ORIGIN_REGEX, "https://evil.com")
    assert not re.fullmatch(VERCEL_ORIGIN_REGEX, "https://evilvercel.app")
    assert not re.fullmatch(VERCEL_ORIGIN_REGEX, "https://codelens.vercel.app.evil.com")
    assert not re.fullmatch(VERCEL_ORIGIN_REGEX, "http://codelens.vercel.app")


def test_frontend_origin_is_listed_beside_the_vercel_regex(monkeypatch):
    monkeypatch.setenv("CORS_ORIGIN_REGEX", VERCEL_ORIGIN_REGEX)
    monkeypatch.setenv("CORS_ORIGINS", "https://codelens.example.edu/")
    origins = cors_origins()
    assert origins[0] == "https://codelens.example.edu"
    assert "http://127.0.0.1:5173" in origins
    assert "*" not in origins
