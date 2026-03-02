=================================================================================================== FAILURES ===================================================================================================
___________________________________________________________________________ TestConfirmDeletion.test_confirm_deletion_general_error ____________________________________________________________________________

self = <tests.unit.test_account_deletion.TestConfirmDeletion object at 0x0000012B565FED50>

    @pytest.mark.django_db
    def test_confirm_deletion_general_error(self):
        from tenxyte.services.account_deletion_service import AccountDeletionService
        service = AccountDeletionService()

        with patch.object(AccountDeletionRequest.objects, 'get', side_effect=Exception("DB Error")):
            success, data, error = service.confirm_deletion(token="some-token")

        assert success is False
>       assert error == "Error confirming deletion request: DB Error"
E       AssertionError: assert 'An unexpecte...tion request.' == 'Error confir...est: DB Error'
E
E         - Error confirming deletion request: DB Error
E         + An unexpected error occurred while confirming the deletion request.

tests\unit\test_account_deletion.py:201: AssertionError
--------------------------------------------------------------------------------------------- Captured stderr call ---------------------------------------------------------------------------------------------
Error confirming deletion request: DB Error
Traceback (most recent call last):
  File "C:\Users\bobop\Documents\own\tenxyte\src\tenxyte\services\account_deletion_service.py", line 121, in confirm_deletion
    deletion_request = AccountDeletionRequest.objects.get(
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1198, in _execute_mock_call
    raise effect
Exception: DB Error
---------------------------------------------------------------------------------------------- Captured log call -----------------------------------------------------------------------------------------------
ERROR    tenxyte.services.account_deletion_service:account_deletion_service.py:154 Error confirming deletion request: DB Error
Traceback (most recent call last):
  File "C:\Users\bobop\Documents\own\tenxyte\src\tenxyte\services\account_deletion_service.py", line 121, in confirm_deletion
    deletion_request = AccountDeletionRequest.objects.get(
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1198, in _execute_mock_call
    raise effect
Exception: DB Error
_____________________________________________________________________________________ test_send_confirmation_email_failure _____________________________________________________________________________________

user = <User: gdpr_test@test.com>

    @pytest.mark.django_db
    def test_send_confirmation_email_failure(user):
        req = AccountDeletionRequest.create_request(user=user)
        with patch("tenxyte.services.email_service.EmailService") as MockService:
            MockService.return_value.send_account_deletion_confirmation.side_effect = Exception("Email failed")
            result = req.send_confirmation_email()
            assert result is False
            assert req.status == 'confirmation_sent'

            from tenxyte.models.security import AuditLog
            log = AuditLog.objects.get(action='deletion_confirmation_email_failed', user=user)
>           assert log.details['error'] == "Email failed"
E           AssertionError: assert 'Internal server error' == 'Email failed'
E
E             - Email failed
E             + Internal server error

tests\unit\test_models_gdpr.py:37: AssertionError
--------------------------------------------------------------------------------------------- Captured stderr call ---------------------------------------------------------------------------------------------
Error sending deletion confirmation email: Email failed
Traceback (most recent call last):
  File "C:\Users\bobop\Documents\own\tenxyte\src\tenxyte\models\gdpr.py", line 115, in send_confirmation_email
    email_service.send_account_deletion_confirmation(self)
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1198, in _execute_mock_call
    raise effect
Exception: Email failed
---------------------------------------------------------------------------------------------- Captured log call -----------------------------------------------------------------------------------------------
ERROR    tenxyte.models.gdpr:gdpr.py:119 Error sending deletion confirmation email: Email failed
Traceback (most recent call last):
  File "C:\Users\bobop\Documents\own\tenxyte\src\tenxyte\models\gdpr.py", line 115, in send_confirmation_email
    email_service.send_account_deletion_confirmation(self)
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1198, in _execute_mock_call
    raise effect
Exception: Email failed
_________________________________________________________________________________ test_execute_deletion_success_email_failure __________________________________________________________________________________

user = <User: gdpr_test@test.com>

    @pytest.mark.django_db
    def test_execute_deletion_success_email_failure(user):
        req = AccountDeletionRequest.create_request(user=user)
        req.confirm_request()

        with patch.object(user, 'soft_delete', return_value=True):
            with patch("tenxyte.services.email_service.EmailService") as MockService:
                MockService.return_value.send_account_deletion_completed.side_effect = Exception("Failed")
                result = req.execute_deletion()
                assert result is True
                assert req.status == 'completed'

                from tenxyte.models.security import AuditLog
                log = AuditLog.objects.get(action='deletion_completion_email_failed', user=user)
>               assert log.details['error'] == "Failed"
E               AssertionError: assert 'Internal server error' == 'Failed'
E
E                 - Failed
E                 + Internal server error

tests\unit\test_models_gdpr.py:70: AssertionError
--------------------------------------------------------------------------------------------- Captured stderr call ---------------------------------------------------------------------------------------------
Error sending deletion completion email: Failed
Traceback (most recent call last):
  File "C:\Users\bobop\Documents\own\tenxyte\src\tenxyte\models\gdpr.py", line 159, in execute_deletion
    email_service.send_account_deletion_completed(self)
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1198, in _execute_mock_call
    raise effect
Exception: Failed
---------------------------------------------------------------------------------------------- Captured log call -----------------------------------------------------------------------------------------------
ERROR    tenxyte.models.gdpr:gdpr.py:162 Error sending deletion completion email: Failed
Traceback (most recent call last):
  File "C:\Users\bobop\Documents\own\tenxyte\src\tenxyte\models\gdpr.py", line 159, in execute_deletion
    email_service.send_account_deletion_completed(self)
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1198, in _execute_mock_call
    raise effect
Exception: Failed
____________________________________________________________________________ TestCreateOrganization.test_create_exception_handling _____________________________________________________________________________

self = <tests.unit.test_organization_service.TestCreateOrganization object at 0x0000012B56A264E0>, service = <tenxyte.services.organization_service.OrganizationService object at 0x0000012B5893D6A0>
owner = <User: owner@test.com>, system_roles = [<OrganizationRole: Owner (owner)>, <OrganizationRole: Admin (admin)>, <OrganizationRole: Member (member)>, <OrganizationRole: Viewer (viewer)>]

    @pytest.mark.django_db
    def test_create_exception_handling(self, service, owner, system_roles):
        from unittest import mock
        with mock.patch.object(service.Organization.objects, 'create', side_effect=Exception("DB Error")):
            success, org, error = service.create_organization(name="Crash", created_by=owner)
            assert success is False
>           assert "Error creating organization: DB Error" in error
E           AssertionError: assert 'Error creating organization: DB Error' in 'An unexpected error occurred while creating the organization.'

tests\unit\test_organization_service.py:214: AssertionError
--------------------------------------------------------------------------------------------- Captured stderr call ---------------------------------------------------------------------------------------------
Error creating organization: DB Error
Traceback (most recent call last):
  File "C:\Users\bobop\Documents\own\tenxyte\src\tenxyte\services\organization_service.py", line 92, in create_organization
    organization = self.Organization.objects.create(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1198, in _execute_mock_call
    raise effect
Exception: DB Error
---------------------------------------------------------------------------------------------- Captured log call -----------------------------------------------------------------------------------------------
ERROR    tenxyte.services.organization_service:organization_service.py:135 Error creating organization: DB Error
Traceback (most recent call last):
  File "C:\Users\bobop\Documents\own\tenxyte\src\tenxyte\services\organization_service.py", line 92, in create_organization
    organization = self.Organization.objects.create(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1198, in _execute_mock_call
    raise effect
Exception: DB Error
_____________________________________________________________________ TestSocialAuthService.test_authenticate_links_existing_user_by_email _____________________________________________________________________

self = <tests.unit.test_social_auth.TestSocialAuthService object at 0x0000012B56C808F0>

    def test_authenticate_links_existing_user_by_email(self):
        app = _app("SocialSvcApp2")
        existing = _user("github@example.com")
        service = SocialAuthService()
        success, data, error = service.authenticate(
            provider_name='github',
            user_data=GITHUB_USER_DATA,
            application=app,
            ip_address='127.0.0.1',
        )
>       assert success is True
E       assert False is True

tests\unit\test_social_auth.py:439: AssertionError
_____________________________________________________________________ TestSocialAuthService.test_authenticate_multiple_providers_same_user _____________________________________________________________________

self = <tests.unit.test_social_auth.TestSocialAuthService object at 0x0000012B56C82240>

    def test_authenticate_multiple_providers_same_user(self):
        app = _app("SocialSvcApp7")
        service = SocialAuthService()
        # First: GitHub
        service.authenticate(
            provider_name='github',
            user_data={**GITHUB_USER_DATA, 'email': 'multi_provider@example.com'},
            application=app, ip_address='127.0.0.1',
        )
        user = User.objects.get(email='multi_provider@example.com')
        # Second: Google (same email → same user)
        service.authenticate(
            provider_name='google',
            user_data={**GOOGLE_USER_DATA, 'email': 'multi_provider@example.com'},
            application=app, ip_address='127.0.0.1',
        )
>       assert SocialConnection.objects.filter(user=user).count() == 2
E       assert 1 == 2
E        +  where 1 = count()
E        +    where count = <QuerySet [<SocialConnection: multi_provider@example.com — github:gh_123>]>.count
E        +      where <QuerySet [<SocialConnection: multi_provider@example.com — github:gh_123>]> = filter(user=<User: multi_provider@example.com>)
E        +        where filter = <django.db.models.manager.Manager object at 0x0000012B5872C140>.filter
E        +          where <django.db.models.manager.Manager object at 0x0000012B5872C140> = SocialConnection.objects

tests\unit\test_social_auth.py:518: AssertionError
_____________________________________________________________________________ TestWebAuthnService.test_begin_authentication_error ______________________________________________________________________________

self = <tests.unit.test_webauthn.TestWebAuthnService object at 0x0000012B56D85100>

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_begin_authentication_error(self):
        user = _user("svc_begin_auth_err@example.com")
        service = WebAuthnService()
        mock_webauthn = MagicMock()
        mock_webauthn.generate_authentication_options.side_effect = Exception("auth err")
        mock_webauthn.PublicKeyCredentialDescriptor = MagicMock()
        with patch('tenxyte.services.webauthn_service._get_webauthn', return_value=mock_webauthn):
            success, data, error = service.begin_authentication(user)
        assert success is False
>       assert 'auth err' in error
E       AssertionError: assert 'auth err' in 'An unexpected error occurred during WebAuthn authentication.'

tests\unit\test_webauthn.py:448: AssertionError
--------------------------------------------------------------------------------------------- Captured stderr call ---------------------------------------------------------------------------------------------
WebAuthn begin_authentication error: auth err
Traceback (most recent call last):
  File "C:\Users\bobop\Documents\own\tenxyte\src\tenxyte\services\webauthn_service.py", line 197, in begin_authentication
    options = webauthn.generate_authentication_options(
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1198, in _execute_mock_call
    raise effect
Exception: auth err
---------------------------------------------------------------------------------------------- Captured log call -----------------------------------------------------------------------------------------------
ERROR    tenxyte.services.webauthn_service:webauthn_service.py:207 WebAuthn begin_authentication error: auth err
Traceback (most recent call last):
  File "C:\Users\bobop\Documents\own\tenxyte\src\tenxyte\services\webauthn_service.py", line 197, in begin_authentication
    options = webauthn.generate_authentication_options(
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bobop\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py", line 1198, in _execute_mock_call
    raise effect
Exception: auth err
_____________________________________________________________________________________ test_otp_code_verify_race_condition ______________________________________________________________________________________

user = <User: test@example.com>

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

        # If using atomic updates (F('attempts') + 1), it should record exactly len(successes) attempts.
>       assert otp.attempts == len(successes)
E       assert 3 == 8
E        +  where 3 = <OTPCode: OTPCode object (1)>.attempts
E        +  and   8 = len([1, 1, 1, 1, 1, 1, ...])

tests\security\test_race_conditions.py:42: AssertionError
__________________________________________________________________________ TestPresetDefinitions.test_development_cors_allow_all_true __________________________________________________________________________

self = <tests.unit.test_secure_mode.TestPresetDefinitions object at 0x0000012B56B91700>

    def test_development_cors_allow_all_true(self):
>       assert SECURE_MODE_PRESETS['development']['CORS_ALLOW_ALL_ORIGINS'] is True
E       assert False is True

tests\unit\test_secure_mode.py:106: AssertionError
____________________________________________________________________________ TestDevelopmentPreset.test_development_cors_allow_all _____________________________________________________________________________

self = <tests.unit.test_secure_mode.TestDevelopmentPreset object at 0x0000012B56BA9B50>

    def test_development_cors_allow_all(self):
>       assert _get_with_mode('CORS_ALLOW_ALL_ORIGINS', 'development') is True
E       AssertionError: assert False is True
E        +  where False = _get_with_mode('CORS_ALLOW_ALL_ORIGINS', 'development')

tests\unit\test_secure_mode.py:201: AssertionError
================================================================================================ tests coverage ================================================================================================






=========================================================================================== short test summary info ============================================================================================
FAILED tests/unit/test_account_deletion.py::TestConfirmDeletion::test_confirm_deletion_general_error - AssertionError: assert 'An unexpecte...tion request.' == 'Error confir...est: DB Error'
FAILED tests/unit/test_models_gdpr.py::test_send_confirmation_email_failure - AssertionError: assert 'Internal server error' == 'Email failed'
FAILED tests/unit/test_models_gdpr.py::test_execute_deletion_success_email_failure - AssertionError: assert 'Internal server error' == 'Failed'
FAILED tests/unit/test_organization_service.py::TestCreateOrganization::test_create_exception_handling - AssertionError: assert 'Error creating organization: DB Error' in 'An unexpected error occurred while creating the organization.'
FAILED tests/unit/test_social_auth.py::TestSocialAuthService::test_authenticate_links_existing_user_by_email - assert False is True
FAILED tests/unit/test_social_auth.py::TestSocialAuthService::test_authenticate_multiple_providers_same_user - assert 1 == 2
FAILED tests/unit/test_webauthn.py::TestWebAuthnService::test_begin_authentication_error - AssertionError: assert 'auth err' in 'An unexpected error occurred during WebAuthn authentication.'
FAILED tests/security/test_race_conditions.py::test_otp_code_verify_race_condition - assert 3 == 8
FAILED tests/unit/test_secure_mode.py::TestPresetDefinitions::test_development_cors_allow_all_true - assert False is True
FAILED tests/unit/test_secure_mode.py::TestDevelopmentPreset::test_development_cors_allow_all - AssertionError: assert False is True
================================================================================= 10 failed, 1418 passed in 407.26s (0:06:47) ==================================================================================




