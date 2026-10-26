"""Create a teacher account. Teachers cannot self-register.

    python -m rag_core.create_teacher --name "Ada Rao" --email ada@school.edu --password "a long secret"
"""

import argparse
import asyncio
import sys

from rag_core.auth import hash_password, public_user
from rag_core.mongo import close_mongo
from rag_core.schemas import normalize_email
from rag_core.store import create_user, find_user_by_email


async def create_teacher_account(name: str, email: str, password: str) -> dict:
    cleaned_name = " ".join((name or "").split())
    if not cleaned_name or len(cleaned_name) > 80:
        raise ValueError("name must be 1 to 80 characters")
    try:
        cleaned_email = normalize_email(email)
    except ValueError as exc:
        raise ValueError("invalid email") from exc
    if not isinstance(password, str) or len(password) < 8 or len(password) > 72:
        raise ValueError("password must be 8 to 72 characters")
    if await find_user_by_email(cleaned_email):
        raise ValueError("Email is already registered")
    user = await create_user(
        cleaned_name,
        cleaned_email,
        await hash_password(password),
        role="teacher",
    )
    return public_user(user)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a CodeLens teacher account")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args(argv)

    async def _run() -> dict:
        try:
            return await create_teacher_account(args.name, args.email, args.password)
        finally:
            await close_mongo()

    try:
        user = asyncio.run(_run())
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"Teacher ready: {user['name']} <{user['email']}> id={user['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
