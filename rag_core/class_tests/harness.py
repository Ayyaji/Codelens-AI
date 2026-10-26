"""Stdin/stdout wrapper around a student function.

The existing sandbox runs a Python file. Class coding questions keep that
contract: the starter reads a JSON list of arguments and prints the return
value. Students fill in the function and leave the ``__main__`` block alone.
"""


def function_name(signature: str) -> str:
    head = (signature or "").strip()
    if head.startswith("def "):
        head = head[4:]
    name = head.split("(", 1)[0].strip()
    return name or "solve"


def runner_tail(name: str) -> str:
    return (
        "\n\nif __name__ == \"__main__\":\n"
        "    import json\n"
        "    args = json.loads(input() or \"[]\")\n"
        f"    result = {name}(*args)\n"
        "    if isinstance(result, str):\n"
        "        print(result)\n"
        "    else:\n"
        "        print(json.dumps(result, separators=(\",\", \":\")))\n"
    )


def starter_for(signature: str, note: str = "your code here") -> str:
    name = function_name(signature)
    signature = signature.strip()
    if not signature.endswith(":"):
        signature = signature + ":"
    return (
        f"{signature}\n"
        f"    # {note}\n"
        "    raise NotImplementedError\n"
        f"{runner_tail(name)}"
    )
