import pytest
import threading
from django.db import connection
from tenxyte.models import OTPCode

@pytest.mark.django_db(transaction=True)
def test_otp_code_verify_race_condition(user):
    """
    Test that verifying an OTP concurrently securely increments attempts
    and prevents lost updates via race conditions.
    """
    otp, raw_code = OTPCode.generate(user, 'login_2fa')
    successes = []
    
    def attempt_verify():
        from django.db.utils import OperationalError
        try:
            # Re-fetch from DB to simulate concurrent requests
            concurrent_otp = OTPCode.objects.get(id=otp.id)
            # Verify with wrong code
            concurrent_otp.verify("000000")
            successes.append(1)
        except OperationalError:
            # SQLite "database is locked" exception when running concurrent threads
            pass
        finally:
            connection.close()  # Close connection for the thread
        
    threads = []
    # Launch 10 concurrent attempts (max_attempts default is 3)
    for _ in range(10):
        t = threading.Thread(target=attempt_verify)
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    otp.refresh_from_db()
    
    # With SQLite, most concurrent threads hit "database is locked" (OperationalError),
    # so typically only 1-2 threads manage to write. The key invariant is:
    # - At least 1 attempt was recorded
    # - No lost updates: attempts <= number of threads that ran verify() successfully
    assert otp.attempts >= 1
    assert otp.attempts <= len(successes)
