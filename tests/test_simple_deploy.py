"""The beginner deploy is two EC2 instances plus a Vercel frontend."""

import json
import os
import re
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIMPLE = ROOT / "deploy" / "simple"
VERCEL_ORIGIN_REGEX = r"https://([A-Za-z0-9-]+\.)*vercel\.app"


def _bash(script: str) -> str:
    result = subprocess.run(
        ["bash", "-c", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def test_simple_scripts_are_valid_bash():
    for name in ("lib.sh", "mongo-setup.sh", "backend-setup.sh"):
        subprocess.run(["bash", "-n", str(SIMPLE / name)], check=True)
    subprocess.run(["bash", "-n", str(ROOT / "deploy" / "lib.sh")], check=True)


def _warn(version: str, pretty: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            "-c",
            "set -euo pipefail; source deploy/simple/lib.sh; "
            f"warn_ubuntu_release {version} {json.dumps(pretty)}; echo OK",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_ubuntu_26_04_warns_instead_of_exiting():
    for version, pretty in (("24.04", "Ubuntu 24.04 LTS"), ("26.04", "Ubuntu 26.04.1 LTS")):
        known = _warn(version, pretty)
        assert known.stdout.strip() == "OK"
        assert known.stderr == ""
    newer = _warn("28.04", "Ubuntu 28.04 LTS")
    assert newer.stdout.strip() == "OK"
    assert "Ubuntu 28.04 LTS" in newer.stderr
    assert "Continuing" in newer.stderr


def test_docker_install_falls_back_when_the_docker_repo_lacks_the_release():
    text = (ROOT / "deploy" / "lib.sh").read_text(encoding="utf-8")
    assert "docker.io" in text
    assert "docker-compose-v2" in text
    assert "get.docker.com" in text
    for name in ("mongo-setup.sh", "backend-setup.sh"):
        script = (SIMPLE / name).read_text(encoding="utf-8")
        assert "warn_ubuntu_release" in script
        assert "This script expects Ubuntu 24.04" not in script


def test_sslip_host_uses_dashes_and_the_uri_uses_the_private_ip():
    out = _bash(
        "source deploy/simple/lib.sh && "
        "sslip_host 13.234.56.78 && echo && "
        "app_mongo_uri 'abc123' 172.31.10.20"
    )
    lines = out.splitlines()
    assert lines[0] == "13-234-56-78.sslip.io"
    assert lines[1] == (
        "mongodb://codelens:abc123@172.31.10.20:27017/codelens?authSource=admin"
    )


def test_env_file_round_trip_keeps_the_mongo_uri():
    uri = "mongodb://codelens:abc123@172.31.10.20:27017/codelens?authSource=admin"
    out = _bash(
        "source deploy/simple/lib.sh && "
        "file=$(mktemp) && "
        f"write_env MONGODB_URI {json.dumps(uri)} \"$file\" && "
        f"write_env CORS_ORIGIN_REGEX {json.dumps(VERCEL_ORIGIN_REGEX)} \"$file\" && "
        "read_env MONGODB_URI \"$file\" && echo && "
        "read_env CORS_ORIGIN_REGEX \"$file\" && echo && "
        "stat -c %a \"$file\""
    )
    lines = out.splitlines()
    assert lines[0] == uri
    assert lines[1] == VERCEL_ORIGIN_REGEX
    assert lines[2] == "600"
    assert re.fullmatch(VERCEL_ORIGIN_REGEX, "https://codelens-ai.vercel.app")


def test_mongo_setup_binds_the_private_ip_and_prints_a_uri():
    text = (SIMPLE / "mongo-setup.sh").read_text(encoding="utf-8")
    assert "IMAGE=mongo:7.0" in text
    assert "IMAGE=mongo:8" not in text
    assert "/var/lib/codelens-mongo" in text
    assert "--restart unless-stopped" in text
    assert "${PRIVATE_IP}:27017:27017" in text
    assert "MONGO_INITDB_ROOT_USERNAME" in text
    assert "app_mongo_uri" in text
    assert "--wiredTigerCacheSizeGB 0.25" in text
    assert "should_clear_failed_mongo_datadir" in text
    mode = os.stat(SIMPLE / "mongo-setup.sh").st_mode
    assert mode & stat.S_IXUSR
    for compose in (
        ROOT / "docker-compose.yml",
        ROOT / "deploy" / "mongo" / "docker-compose.yml",
    ):
        assert "image: mongo:7.0" in compose.read_text(encoding="utf-8")
        assert "image: mongo:8" not in compose.read_text(encoding="utf-8")


def test_failed_mongo8_datadir_is_cleared_only_when_no_uri_was_saved(tmp_path):
    data = tmp_path / "db"
    data.mkdir()
    (data / "storage.bson").write_bytes(b"\x16featureCompatibilityVersion\x00\x048.0\x00")
    (data / "WiredTiger").write_text("metadata", encoding="utf-8")
    uri = tmp_path / "uri"
    out = _bash(
        "source deploy/simple/lib.sh && "
        f"should_clear_failed_mongo_datadir {json.dumps(str(data))} {json.dumps(str(uri))} mongo:8 "
        "&& echo CLEAR || echo KEEP; "
        f"printf '%s' 'mongodb://kept' > {json.dumps(str(uri))} && "
        f"should_clear_failed_mongo_datadir {json.dumps(str(data))} {json.dumps(str(uri))} mongo:8 "
        "&& echo CLEAR2 || echo KEEP2"
    )
    assert out.splitlines() == ["CLEAR", "KEEP2"]
    guide = (ROOT / "docs" / "DEPLOY_SIMPLE.md").read_text(encoding="utf-8")
    assert "SERVER-121912" in guide
    assert "mongo:7.0" in guide
    assert "sudo rm -rf /var/lib/codelens-mongo" in guide
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    prod = (ROOT / "requirements-prod.txt").read_text(encoding="utf-8")
    assert "motor>=3.6.0" in req and "pymongo>=4.9.0" in req
    assert "motor>=3.6.0" in prod and "pymongo>=4.9.0" in prod


def test_backend_setup_uses_caddy_swap_and_vercel_cors():
    text = (SIMPLE / "backend-setup.sh").read_text(encoding="utf-8")
    compose = (SIMPLE / "docker-compose.yml").read_text(encoding="utf-8")
    caddy = (SIMPLE / "Caddyfile").read_text(encoding="utf-8")
    assert "ensure_swap 4" in text
    assert "JWT_SECRET" in text
    assert "chmod 600" in text
    assert "VERCEL_ORIGIN_REGEX" in text
    assert "sslip_host" in text
    assert "rag_core.build_kb" in text
    assert "rag_core.create_teacher" in text
    assert "unless-stopped" in compose
    assert "127.0.0.1:8000:8000" in compose
    assert '"80:80"' in compose
    assert '"443:443"' in compose
    assert "{$PUBLIC_HOST}" in caddy
    assert "reverse_proxy api:8000" in caddy
    mode = os.stat(SIMPLE / "backend-setup.sh").st_mode
    assert mode & stat.S_IXUSR


def test_vercel_config_rewrites_the_spa_to_index_html():
    config = json.loads((ROOT / "frontend" / "vercel.json").read_text(encoding="utf-8"))
    assert config["rewrites"] == [{"source": "/(.*)", "destination": "/index.html"}]
    guide = (ROOT / "docs" / "DEPLOY_SIMPLE.md").read_text(encoding="utf-8")
    assert "Root Directory" in guide
    assert "VITE_API_URL" in guide
    assert "sslip.io" in guide
    assert "PowerShell" in guide or "powershell" in guide.lower()
    assert "DEPLOY_AWS.md" in guide
