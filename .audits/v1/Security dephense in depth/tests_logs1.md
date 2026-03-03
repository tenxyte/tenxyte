=================================================================================================== FAILURES ===================================================================================================
________________________________________________________________________________________ TestUserCRUD.test_delete_user _________________________________________________________________________________________

self = <tests.multidb.test_db_models.TestUserCRUD object at 0x000002C474B1A810>

    def test_delete_user(self):
        user = User.objects.create_user(email='delete@test.com', password='P@ss123!')
        user_id = user.pk
>       user.delete()

tests\multidb\test_db_models.py:59:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <User: deleted_1_1772510242.562972@anonymized.local>, using = None, keep_parents = False, hard = False

    def delete(self, using=None, keep_parents=False, hard=False):
        """
        Soft delete for GDPR compliance (Art. 17).
        Anonymizes the user data and marks as deleted instead of hard removing.
        Use hard=True for immediate permanent deletion.
        """
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)

        self.is_deleted = True
        self.deleted_at = timezone.now()

        # Anonymize identifiers to prevent reuse conflicts and protect data
        if self.email:
            self.email = f"deleted_{self.id}_{self.deleted_at.timestamp()}@anonymized.local"

        import secrets
        self.anonymization_token = secrets.token_hex(16)

        # Clear sensitive data
        self.first_name = "Deleted"
        self.last_name = "User"
        self.phone_number = None
        self.phone_country_code = None
        self.google_id = None
        self.totp_secret = None
        self.backup_codes = []

        self.is_active = False

        # We don't change passwords so login fails immediately, or we could randomize it
>       self.set_unusable_password()
        ^^^^^^^^^^^^^^^^^^^^^^^^^^
E       AttributeError: 'User' object has no attribute 'set_unusable_password'

src\tenxyte\models\auth.py:297: AttributeError
__________________________________________________________________________ TestRemainingCoverage.test_rate_limit_ip_and_get_client_ip __________________________________________________________________________

self = <tests.unit.test_decorators.TestRemainingCoverage object at 0x000002C474EB4320>

    @override_settings(TENXYTE_TRUSTED_PROXIES=["127.0.0.1"])
    def test_rate_limit_ip_and_get_client_ip(self): # 187, 212-217
        req = MagicMock(META={'HTTP_X_FORWARDED_FOR': '1.2.3.4, 8.8.8.8', 'REMOTE_ADDR': '127.0.0.1'}, method='GET')
        req.user = None
>       assert get_client_ip(req) == '1.2.3.4'
E       AssertionError: assert '127.0.0.1' == '1.2.3.4'
E
E         - 1.2.3.4
E         + 127.0.0.1

tests\unit\test_decorators.py:398: AssertionError
___________________________________________________________________________________ TestCleanupCommand.test_cleanup_dry_run ____________________________________________________________________________________

self = <tests.unit.test_management_commands.TestCleanupCommand object at 0x000002C474FE27E0>, cleanup_data = None

    def test_cleanup_dry_run(self, cleanup_data):
        out = StringIO()
        # Ne doit rien supprimer
>       call_command('tenxyte_cleanup', '--dry-run', stdout=out)

tests\unit\test_management_commands.py:55:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\__init__.py:173: in call_command
    defaults = parser.parse_args(args=parse_args)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\base.py:72: in parse_args
    return super().parse_args(args, namespace)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\argparse.py:1908: in parse_args
    self.error(msg)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = CommandParser(prog=' tenxyte_cleanup', usage=None, description="Nettoie les tokens expirés (JWT Blacklist, Magic Links....", formatter_class=<class 'django.core.management.base.DjangoHelpFormatter'>, conflict_handler='error', add_help=True)
message = 'unrecognized arguments: --dry-run'

    def error(self, message):
        if self.called_from_command_line:
            super().error(message)
        else:
>           raise CommandError("Error: %s" % message)
E           django.core.management.base.CommandError: Error: unrecognized arguments: --dry-run

..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\base.py:78: CommandError
_______________________________________________________________________________ TestCleanupCommand.test_cleanup_normal_execution _______________________________________________________________________________

self = <tests.unit.test_management_commands.TestCleanupCommand object at 0x000002C474FE2C60>, cleanup_data = None

    def test_cleanup_normal_execution(self, cleanup_data):
        out = StringIO()
>       call_command('tenxyte_cleanup', '--login-attempts-days=90', '--audit-log-days=90', stdout=out)

tests\unit\test_management_commands.py:68:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\__init__.py:173: in call_command
    defaults = parser.parse_args(args=parse_args)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\base.py:72: in parse_args
    return super().parse_args(args, namespace)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\argparse.py:1908: in parse_args
    self.error(msg)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = CommandParser(prog=' tenxyte_cleanup', usage=None, description="Nettoie les tokens expirés (JWT Blacklist, Magic Links....", formatter_class=<class 'django.core.management.base.DjangoHelpFormatter'>, conflict_handler='error', add_help=True)
message = 'unrecognized arguments: --login-attempts-days=90 --audit-log-days=90'

    def error(self, message):
        if self.called_from_command_line:
            super().error(message)
        else:
>           raise CommandError("Error: %s" % message)
E           django.core.management.base.CommandError: Error: unrecognized arguments: --login-attempts-days=90 --audit-log-days=90

..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\base.py:78: CommandError
_______________________________________________________________________________ TestCleanupCommand.test_cleanup_skip_audit_logs ________________________________________________________________________________

self = <tests.unit.test_management_commands.TestCleanupCommand object at 0x000002C474FE3170>, cleanup_data = None

    def test_cleanup_skip_audit_logs(self, cleanup_data):
        out = StringIO()
        # --audit-log-days=0 indique de tout garder
>       call_command('tenxyte_cleanup', '--audit-log-days=0', stdout=out)

tests\unit\test_management_commands.py:87:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\__init__.py:173: in call_command
    defaults = parser.parse_args(args=parse_args)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\base.py:72: in parse_args
    return super().parse_args(args, namespace)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\argparse.py:1908: in parse_args
    self.error(msg)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = CommandParser(prog=' tenxyte_cleanup', usage=None, description="Nettoie les tokens expirés (JWT Blacklist, Magic Links....", formatter_class=<class 'django.core.management.base.DjangoHelpFormatter'>, conflict_handler='error', add_help=True)
message = 'unrecognized arguments: --audit-log-days=0'

    def error(self, message):
        if self.called_from_command_line:
            super().error(message)
        else:
>           raise CommandError("Error: %s" % message)
E           django.core.management.base.CommandError: Error: unrecognized arguments: --audit-log-days=0

..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\base.py:78: CommandError
_________________________________________________________________________________________ test_tenxyte_cleanup_normal __________________________________________________________________________________________

cleanup_data = (<User: cleanup@test.com>, <Application: Cleanup App>)

    @pytest.mark.django_db
    def test_tenxyte_cleanup_normal(cleanup_data):
        out = StringIO()
        call_command('tenxyte_cleanup', stdout=out)
        output = out.getvalue()

>       assert 'Cleanup completed' in output
E       assert 'Cleanup completed' in "Demarrage du nettoyage des tokens expirés...\nSuccessfully deleted 1 expired blacklisted JWT tokens.\nSuccessfully de...d Magic Link tokens.\nError cleaning OTP codes: No module named 'tenxyte.models.otp'\nNettoyage termine avec succes.\n"

tests\unit\test_tenxyte_cleanup.py:51: AssertionError
_________________________________________________________________________________________ test_tenxyte_cleanup_dry_run _________________________________________________________________________________________

cleanup_data = (<User: cleanup@test.com>, <Application: Cleanup App>)

    @pytest.mark.django_db
    def test_tenxyte_cleanup_dry_run(cleanup_data):
        out = StringIO()
>       call_command('tenxyte_cleanup', '--dry-run', stdout=out)

tests\unit\test_tenxyte_cleanup.py:61:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\__init__.py:173: in call_command
    defaults = parser.parse_args(args=parse_args)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\base.py:72: in parse_args
    return super().parse_args(args, namespace)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\argparse.py:1908: in parse_args
    self.error(msg)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = CommandParser(prog=' tenxyte_cleanup', usage=None, description="Nettoie les tokens expirés (JWT Blacklist, Magic Links....", formatter_class=<class 'django.core.management.base.DjangoHelpFormatter'>, conflict_handler='error', add_help=True)
message = 'unrecognized arguments: --dry-run'

    def error(self, message):
        if self.called_from_command_line:
            super().error(message)
        else:
>           raise CommandError("Error: %s" % message)
E           django.core.management.base.CommandError: Error: unrecognized arguments: --dry-run

..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\base.py:78: CommandError
_______________________________________________________________________________ test_tenxyte_cleanup_custom_days_and_skip_audit ________________________________________________________________________________

cleanup_data = (<User: cleanup@test.com>, <Application: Cleanup App>)

    @pytest.mark.django_db
    def test_tenxyte_cleanup_custom_days_and_skip_audit(cleanup_data):
        out = StringIO()
        # Skip audit logs by passing --audit-log-days 0
        # Make login attempt cutoff 5 days instead of 90
>       call_command('tenxyte_cleanup', '--audit-log-days', '0', '--login-attempts-days', '5', stdout=out)

tests\unit\test_tenxyte_cleanup.py:78:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\__init__.py:173: in call_command
    defaults = parser.parse_args(args=parse_args)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\base.py:72: in parse_args
    return super().parse_args(args, namespace)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\argparse.py:1908: in parse_args
    self.error(msg)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = CommandParser(prog=' tenxyte_cleanup', usage=None, description="Nettoie les tokens expirés (JWT Blacklist, Magic Links....", formatter_class=<class 'django.core.management.base.DjangoHelpFormatter'>, conflict_handler='error', add_help=True)
message = 'unrecognized arguments: --audit-log-days 0 --login-attempts-days 5'

    def error(self, message):
        if self.called_from_command_line:
            super().error(message)
        else:
>           raise CommandError("Error: %s" % message)
E           django.core.management.base.CommandError: Error: unrecognized arguments: --audit-log-days 0 --login-attempts-days 5

..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\site-packages\django\core\management\base.py:78: CommandError
__________________________________________________________________________ TestUserDetailView.test_delete_already_deleted_returns_400 __________________________________________________________________________

self = <tests.unit.test_user_views.TestUserDetailView object at 0x000002C4753832C0>

    @pytest.mark.django_db
    def test_delete_already_deleted_returns_400(self):
        app = _app("UserDetail6")
        admin = _user("userdetail_admin6@test.com", "users.delete")
        target = _user("userdetail_target6@test.com")
        target.soft_delete()

        resp = _authed_delete(UserDetailView, f"/auth/admin/users/{target.id}/",
                              admin, app, user_id=str(target.id))

>       assert resp.status_code == 400
E       assert 404 == 400
E        +  where 404 = <Response status_code=404, "text/html; charset=utf-8">.status_code

tests\unit\test_user_views.py:302: AssertionError


=========================================================================================== short test summary info ============================================================================================
FAILED tests/multidb/test_db_models.py::TestUserCRUD::test_delete_user - AttributeError: 'User' object has no attribute 'set_unusable_password'
FAILED tests/unit/test_decorators.py::TestRemainingCoverage::test_rate_limit_ip_and_get_client_ip - AssertionError: assert '127.0.0.1' == '1.2.3.4'
FAILED tests/unit/test_management_commands.py::TestCleanupCommand::test_cleanup_dry_run - django.core.management.base.CommandError: Error: unrecognized arguments: --dry-run
FAILED tests/unit/test_management_commands.py::TestCleanupCommand::test_cleanup_normal_execution - django.core.management.base.CommandError: Error: unrecognized arguments: --login-attempts-days=90 --audit-log-days=90
FAILED tests/unit/test_management_commands.py::TestCleanupCommand::test_cleanup_skip_audit_logs - django.core.management.base.CommandError: Error: unrecognized arguments: --audit-log-days=0
FAILED tests/unit/test_tenxyte_cleanup.py::test_tenxyte_cleanup_normal - assert 'Cleanup completed' in "Demarrage du nettoyage des tokens expirés...\nSuccessfully deleted 1 expired blacklisted JWT tokens.\nSuccessfully de...d Magic Link tokens.\nError cleaning OTP codes: No mo...
FAILED tests/unit/test_tenxyte_cleanup.py::test_tenxyte_cleanup_dry_run - django.core.management.base.CommandError: Error: unrecognized arguments: --dry-run
FAILED tests/unit/test_tenxyte_cleanup.py::test_tenxyte_cleanup_custom_days_and_skip_audit - django.core.management.base.CommandError: Error: unrecognized arguments: --audit-log-days 0 --login-attempts-days 5
FAILED tests/unit/test_user_views.py::TestUserDetailView::test_delete_already_deleted_returns_400 - assert 404 == 400
================================================================================== 9 failed, 1419 passed in 444.50s (0:07:24) ==================================================================================