"""Run untrusted student code in a subprocess with a timeout and resource limits.

The child is a fresh Python process. It does not inherit API keys. Memory and
CPU are capped with setrlimit when the host provides the resource module.
Nothing here uses exec or eval in the API process.
"""

import logging
import os
import signal
import subprocess
import sys
import tempfile

logger = logging.getLogger("codelens.sandbox")

DEFAULT_TIMEOUT = 2.0
MAX_TIMEOUT = 5.0
MAX_CODE_CHARS = 20_000
MAX_OUTPUT_CHARS = 8_000
MEMORY_BYTES = 768 * 1024 * 1024

_BOOT = """
import runpy
import sys

def _limits():
    cpu = int(sys.argv[1])
    mem = int(sys.argv[2])
    try:
        import resource
    except ImportError:
        return
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    try:
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    except (ValueError, OSError):
        pass
    resource.setrlimit(resource.RLIMIT_FSIZE, (1_000_000, 1_000_000))

if __name__ == "__main__":
    student = sys.argv[3]
    _limits()
    sys.argv = [student]
    runpy.run_path(student, run_name="__main__")
"""


def _clip(data: bytes | str | None) -> str:
    if data is None:
        return ""
    text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + "\n...[truncated]"
    return text


def _empty(stderr: str, exit_code: int = 1) -> dict:
    return {"stdout": "", "stderr": stderr, "exit_code": exit_code, "timed_out": False}


def run_code(
    code: str,
    language: str = "python",
    stdin: str = "",
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """Execute Python and return stdout, stderr, exit_code, and timed_out.

    Other languages are rejected. They are never passed to a shell.
    """
    language = (language or "python").strip().lower()
    if language not in {"python", "py", "python3"}:
        return _empty(f"Unsupported language: {language}. Only python can be run here.")
    if code is None or not str(code).strip():
        return _empty("No code was provided.")
    if len(code) > MAX_CODE_CHARS:
        return _empty(f"Code exceeds the {MAX_CODE_CHARS} character limit.")

    timeout = min(max(float(timeout), 0.1), MAX_TIMEOUT)
    cpu_seconds = max(1, int(timeout + 0.999))
    env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "LANG": "C.UTF-8",
    }

    with tempfile.TemporaryDirectory(prefix="codelens-") as tmp:
        student_path = os.path.join(tmp, "main.py")
        boot_path = os.path.join(tmp, "boot.py")
        with open(student_path, "w", encoding="utf-8") as handle:
            handle.write(code)
        with open(boot_path, "w", encoding="utf-8") as handle:
            handle.write(_BOOT)
        env["HOME"] = tmp
        env["TMPDIR"] = tmp

        proc = subprocess.Popen(
            [sys.executable, "-I", boot_path, str(cpu_seconds), str(MEMORY_BYTES), student_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=tmp,
            env=env,
            start_new_session=True,
        )
        timed_out = False
        try:
            stdout, stderr = proc.communicate(stdin.encode("utf-8"), timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                proc.kill()
            stdout, stderr = proc.communicate()
            stderr = (stderr or b"") + b"\nExecution timed out."
            logger.info("sandbox timeout after %.2fs", timeout)

    return {
        "stdout": _clip(stdout),
        "stderr": _clip(stderr),
        "exit_code": -1 if timed_out else proc.returncode,
        "timed_out": timed_out,
    }
