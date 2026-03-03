import os
import django
from datetime import timedelta
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
django.setup()

from django.test.utils import override_settings
from unittest.mock import patch
from tenxyte.services.auth_service import AuthService
from tenxyte.models import User, Application, RefreshToken
from django.utils import timezone

def run_test():
    import datetime
    tbase = datetime.datetime.now(datetime.timezone.utc)
    user = User.objects.create(email="zom@test.com")
    user.set_password("pass")
    user.save()
    application = Application.objects.create(name="App Zom")
    
    rt = RefreshToken.generate(user=user, application=application, ip_address="127.0.0.1")
    RefreshToken.objects.filter(id=rt.id).update(expires_at=tbase + timedelta(seconds=1))

    qs1 = RefreshToken.objects.filter(expires_at__gt=tbase).count()
    qs2 = RefreshToken.objects.filter(expires_at__lte=tbase + timedelta(seconds=2)).update(is_revoked=True)
    
    print(f"QS1 (active): {qs1}")
    print(f"QS2 (purged): {qs2}")

if __name__ == "__main__":
    run_test()
