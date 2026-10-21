"""GET /health is public and does not leak the MongoDB URI."""


async def test_health_is_ok_when_mongo_answers(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mongo": "ok"}


async def test_health_is_503_and_hides_the_uri(client, monkeypatch):
    async def down(*_args, **_kwargs):
        raise RuntimeError("mongodb://codelens:secret@10.0.2.10:27017")

    monkeypatch.setattr("rag_core.api.ping", down)
    response = await client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "mongo": "error"}
    assert "secret" not in response.text
    assert "27017" not in response.text
