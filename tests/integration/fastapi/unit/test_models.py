import pytest
from datetime import datetime
from tenxyte.ports.repositories import UserStatus, MFAType
from tenxyte.adapters.fastapi.models import UserDB

def test_generate_uuid():
    from tenxyte.adapters.fastapi.models import generate_uuid
    uuid_str = generate_uuid()
    assert isinstance(uuid_str, str)
    assert len(uuid_str) == 36

def test_userdb_to_port_model():
    now = datetime.utcnow()
    db_user = UserDB(
        id="test-id",
        email="test@example.com",
        password_hash="hashed_pw",
        first_name="John",
        last_name="Doe",
        is_active=True,
        is_superuser=False,
        is_staff=True,
        status=UserStatus.ACTIVE,
        mfa_type=MFAType.NONE,
        mfa_secret=None,
        email_verified=True,
        created_at=now,
        updated_at=now,
        last_login=None,
        user_metadata={"custom": "value"}
    )
    
    port_model = db_user.to_port_model()
    
    assert port_model.id == "test-id"
    assert port_model.email == "test@example.com"
    assert port_model.password_hash == "hashed_pw"
    assert port_model.first_name == "John"
    assert port_model.last_name == "Doe"
    assert port_model.is_active is True
    assert port_model.is_superuser is False
    assert port_model.is_staff is True
    assert port_model.status == UserStatus.ACTIVE
    assert port_model.mfa_type == MFAType.NONE
    assert port_model.mfa_secret is None
    assert port_model.email_verified is True
    assert port_model.created_at == now
    assert port_model.updated_at == now
    assert port_model.last_login is None
    assert port_model.metadata == {"custom": "value"}

def test_userdb_to_port_model_empty_metadata():
    db_user = UserDB(
        id="test-id",
        email="test@example.com",
        user_metadata=None
    )
    
    port_model = db_user.to_port_model()
    assert port_model.metadata == {}
