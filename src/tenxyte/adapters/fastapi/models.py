"""
Backward-compatible re-exports of the canonical SQLAlchemy models from `models_sa.py`.
"""

from tenxyte.adapters.fastapi.models_sa import Base, DjangoUUID, UserDB, generate_uuid

__all__ = ["Base", "DjangoUUID", "UserDB", "generate_uuid"]
