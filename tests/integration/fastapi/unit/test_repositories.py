import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tenxyte.adapters.fastapi.models import Base, UserDB
from tenxyte.adapters.fastapi.repositories import FastAPIUserRepository
from tenxyte.ports.repositories import User, UserStatus, MFAType

# Setup in-memory SQLite for testing
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def repo(db_session):
    return FastAPIUserRepository(db_session)

def test_repo_create_user(repo):
    user_in = User(
        id="u1",
        email="test@user.com",
        password_hash="hash",
    )
    user_out = repo.create(user_in)
    assert user_out.id == "u1"
    assert user_out.email == "test@user.com"

def test_repo_get_by_id(repo):
    user_in = User(id="u2", email="get@user.com", password_hash="h")
    repo.create(user_in)
    
    user_out = repo.get_by_id("u2")
    assert user_out is not None
    assert user_out.email == "get@user.com"
    
    assert repo.get_by_id("unknown") is None

def test_repo_get_by_email(repo):
    user_in = User(id="u3", email="get_email@user.com", password_hash="h")
    repo.create(user_in)
    
    user_out = repo.get_by_email("get_email@user.com")
    assert user_out is not None
    assert user_out.id == "u3"
    
    assert repo.get_by_email("unknown@user.com") is None

def test_repo_update(repo):
    user_in = User(id="u4", email="update@user.com", password_hash="h")
    repo.create(user_in)
    
    user_update = User(id="u4", email="new@user.com", password_hash="h2", is_active=False)
    user_out = repo.update(user_update)
    assert user_out.email == "new@user.com"
    assert user_out.is_active is False
    assert user_out.password_hash == "h2"
    
    # Update unknown user
    with pytest.raises(ValueError):
         repo.update(User(id="unknown", email="dne@user.com"))

def test_repo_delete(repo):
    repo.create(User(id="u5", email="del@user.com", password_hash="h"))
    assert repo.delete("u5") is True
    assert repo.get_by_id("u5") is None
    assert repo.delete("u5") is False

def test_repo_list_all(repo):
    repo.create(User(id="l1", email="l1@user.com", is_active=True))
    repo.create(User(id="l2", email="l2@user.com", is_active=False))
    
    all_users = repo.list_all()
    assert len(all_users) == 2
    
    active_users = repo.list_all(filters={"is_active": True})
    assert len(active_users) == 1
    assert active_users[0].id == "l1"
    
    status_users = repo.list_all(filters={"status": UserStatus.ACTIVE})
    assert len(status_users) == 2
    
    email_users = repo.list_all(filters={"email": "l2@user.com"})
    assert len(email_users) == 1

def test_repo_count(repo):
    repo.create(User(id="c1", email="c1@user.com", is_active=True))
    repo.create(User(id="c2", email="c2@user.com", is_active=False))
    
    assert repo.count() == 2
    assert repo.count(filters={"is_active": True}) == 1
    assert repo.count(filters={"status": UserStatus.ACTIVE}) == 2
    assert repo.count(filters={"email": "c1@user.com"}) == 1

def test_repo_update_last_login(repo):
    repo.create(User(id="LL", email="ll@user.com", last_login=None))
    
    now = datetime.now(timezone.utc)
    assert repo.update_last_login("LL", now) is True
    
    updated = repo.get_by_id("LL")
    assert updated.last_login is not None
    assert repo.update_last_login("unknown", now) is False

def test_repo_set_mfa_secret(repo):
    repo.create(User(id="mfa1", email="mfa@user.com"))
    
    assert repo.set_mfa_secret("mfa1", MFAType.TOTP, "sec123") is True
    
    updated = repo.get_by_id("mfa1")
    assert updated.mfa_type == MFAType.TOTP
    assert updated.mfa_secret == "sec123"
    assert repo.set_mfa_secret("unknown", MFAType.SMS, "sec") is False

def test_repo_verify_email(repo):
    repo.create(User(id="ve", email="ve@user.com", email_verified=False))
    
    assert repo.verify_email("ve") is True
    assert repo.get_by_id("ve").email_verified is True
    assert repo.verify_email("unknown") is False
