"""The runner is a subprocess with a wall-clock timeout. It does not exec in-process."""

import os
import time

from rag_core.sandbox.runner import run_code


def test_python_stdout():
    result = run_code("print('hi')\n", "python")
    assert result["stdout"] == "hi\n"
    assert result["stderr"] == ""
    assert result["timed_out"] is False
    assert result["exit_code"] == 0


def test_timeout_kills_a_sleeping_process():
    start = time.perf_counter()
    result = run_code("import time\ntime.sleep(30)\n", "python", timeout=0.4)
    elapsed = time.perf_counter() - start
    assert result["timed_out"] is True
    assert elapsed < 3
    assert "timed out" in result["stderr"].lower()


def test_shell_is_not_used_for_other_languages():
    result = run_code("echo hi", "bash")
    assert result["stdout"] == ""
    assert result["timed_out"] is False
    assert "Unsupported language" in result["stderr"]


def test_parent_secrets_are_not_visible_to_student_code(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "super-secret-key")
    result = run_code("import os\nprint(os.environ.get('GROQ_API_KEY', 'missing'))\n")
    assert "super-secret-key" not in result["stdout"]
    assert result["stdout"].strip() == "missing"


def test_memory_limit_blocks_a_large_allocation():
    result = run_code("x = bytearray(900 * 1024 * 1024)\nprint('allocated')\n", timeout=3)
    assert result["timed_out"] is False
    assert "allocated" not in result["stdout"]
    assert "MemoryError" in result["stderr"]


def test_empty_code_is_rejected_without_a_process():
    result = run_code("   ", "python")
    assert result["timed_out"] is False
    assert "No code" in result["stderr"]
    assert os.environ.get("GROQ_API_KEY") is None or "super" not in result["stderr"]
