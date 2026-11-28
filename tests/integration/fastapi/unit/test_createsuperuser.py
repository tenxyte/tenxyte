"""
Tests for `tenxyte.adapters.fastapi.createsuperuser` (follow-up to `quickstart.py`) — the
counterpart of Django's `createsuperuser` / `python -m tenxyte.adapters.django.createsuperuser` —
against a real ephemeral aiosqlite database (no mocks): real bcrypt hashing, real uniqueness
check, real `is_superuser`/`is_staff` flags.
"""

import pytest
from sqlalchemy import select

from tenxyte.adapters.fastapi import db as db_module
from tenxyte.adapters.fastapi.createsuperuser import create_superuser
from tenxyte.adapters.fastapi.models_sa import UserDB
from tenxyte.core.auth_service import verify_password


@pytest.mark.anyio
async def test_create_superuser_end_to_end(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'createsuperuser_test.db'}"
    await create_superuser(url, "admin@example.com", "Correct-Horse-Battery-1!")

    engine = db_module.create_engine(url)
    session_factory = db_module.create_session_factory(engine)
    async with session_factory() as session:
        user = (await session.execute(select(UserDB).where(UserDB.email == "admin@example.com"))).scalar_one()
        assert user.is_superuser is True
        assert user.is_staff is True
        assert user.is_active is True
        assert verify_password("Correct-Horse-Battery-1!", user.password_hash)
    await engine.dispose()


@pytest.mark.anyio
async def test_create_superuser_rejects_duplicate_email(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'createsuperuser_dup_test.db'}"
    await create_superuser(url, "admin@example.com", "Correct-Horse-Battery-1!")

    with pytest.raises(ValueError, match="already exists"):
        await create_superuser(url, "admin@example.com", "Another-Password-2!")


@pytest.mark.anyio
async def test_create_superuser_rejects_password_over_72_bytes(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'createsuperuser_long_pw_test.db'}"
    too_long = "x" * 73

    with pytest.raises(ValueError, match="72 bytes"):
        await create_superuser(url, "admin@example.com", too_long)
