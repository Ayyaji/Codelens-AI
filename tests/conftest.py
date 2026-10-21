import pytest


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-for-the-codelens-suite")
    monkeypatch.setenv("BCRYPT_ROUNDS", "4")
    monkeypatch.setenv("CODELENS_MONGO_MOCK", "1")
    monkeypatch.setenv("MONGODB_DB", "codelens_test")
    monkeypatch.setenv("CODELENS_KB", str(tmp_path / "kb"))
    from rag_core.mongo import reset_database

    reset_database()
    yield
    reset_database()


@pytest.fixture
async def client():
    from httpx import ASGITransport, AsyncClient

    from rag_core.api import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def register(client, email="student@example.com", password="password123", name="Student One"):
    response = await client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return body, {"Authorization": f"Bearer {body['token']}"}
