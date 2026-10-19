import pytest

from rag_core.db import init_db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("CODELENS_DB", str(tmp_path / "codelens.db"))
    monkeypatch.setenv("CODELENS_KB", str(tmp_path / "kb"))
    init_db()
