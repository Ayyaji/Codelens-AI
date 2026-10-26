"""The production scripts keep the three servers and their security groups apart."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_nginx_proxies_api_to_the_backend_private_ip(tmp_path):
    out = tmp_path / "codelens.conf"
    subprocess.run(
        ["bash", "deploy/frontend/render-nginx.sh"],
        cwd=ROOT,
        check=True,
        env={
            "BACKEND_PRIVATE_IP": "10.0.1.20",
            "CODELENS_DOMAIN": "_",
            "CODELENS_TLS": "0",
            "CODELENS_NGINX_OUT": str(out),
            "CODELENS_NGINX_RENDER_ONLY": "1",
            "CODELENS_WEB_ROOT": "/var/www/codelens",
            "PATH": "/usr/bin:/bin",
        },
    )
    text = out.read_text(encoding="utf-8")
    assert "proxy_pass http://10.0.1.20:8000/;" in text
    assert "location /api/" in text
    assert "try_files $uri $uri/ /index.html;" in text
    assert "return 301" not in text


def test_nginx_https_redirects_port_80(tmp_path):
    out = tmp_path / "codelens.conf"
    subprocess.run(
        ["bash", "deploy/frontend/render-nginx.sh"],
        cwd=ROOT,
        check=True,
        env={
            "BACKEND_PRIVATE_IP": "10.0.1.20",
            "CODELENS_DOMAIN": "app.example.edu",
            "CODELENS_TLS": "1",
            "CODELENS_NGINX_OUT": str(out),
            "CODELENS_NGINX_RENDER_ONLY": "1",
            "PATH": "/usr/bin:/bin",
        },
    )
    text = out.read_text(encoding="utf-8")
    assert "listen 443 ssl http2;" in text
    assert "return 301 https://$host$request_uri;" in text
    assert "/etc/letsencrypt/live/app.example.edu/fullchain.pem" in text


def test_security_groups_match_the_three_tier_rules():
    text = (ROOT / "deploy/vpc/setup-network.sh").read_text(encoding="utf-8")
    assert '--port 8000 --source-group "$be"' not in text
    assert '--port 8000 --source-group "$fe"' in text
    assert '--port 27017 --source-group "$be"' in text
    assert "--port 27017 --cidr" not in text
    assert "--port 80 --cidr 0.0.0.0/0" in text
    assert "--port 443 --cidr 0.0.0.0/0" in text


def test_mongo_init_does_not_embed_a_password():
    text = (ROOT / "deploy/mongo/init/01-app-user.sh").read_text(encoding="utf-8")
    assert "MONGO_APP_PASSWORD" in text
    assert "password123" not in text
    assert "change-me" not in text


def test_iam_documents_are_json():
    for path in (ROOT / "deploy/iam").glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))


def test_backend_compose_has_no_nginx_and_no_mongo():
    text = (ROOT / "deploy/backend/docker-compose.yml").read_text(encoding="utf-8")
    assert "image: nginx" not in text
    assert "image: mongo" not in text
    assert "/data/chroma" in text
    assert "CODELENS_LOW_MEMORY" in text
