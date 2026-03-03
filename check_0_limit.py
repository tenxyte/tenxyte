import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
django.setup()

from django.test.utils import override_settings
from tenxyte.services.auth_service import AuthService
from tenxyte.models import User, Application
from tenxyte.conf import auth_settings
import pytest

def run_test():
    with override_settings(TENXYTE_AUTH={'SESSION_LIMIT_ENABLED': True, 'DEFAULT_MAX_SESSIONS': 0}):
        user = User.objects.create(email="zlimit@test.com")
        user.set_password("pass")
        user.save()
        app = Application.objects.create(name="App Zero")
        
        print(f"SESSION_LIMIT_ENABLED in test: {auth_settings.SESSION_LIMIT_ENABLED}")
        print(f"DEFAULT_MAX_SESSIONS in test: {auth_settings.DEFAULT_MAX_SESSIONS}")
        
        service = AuthService()
        res = service._enforce_session_limit(user, app, "127.0.0.1")
        print(f"Result: {res}")

if __name__ == "__main__":
    run_test()
