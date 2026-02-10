from typing import Optional, Dict, Any, Tuple
from django.utils import timezone
from django.db.models import Q

from ..models import Application, User, RefreshToken, LoginAttempt, AuditLog, PasswordHistory
from .jwt_service import JWTService
from ..conf import auth_settings


class AuthService:
    """
    Service principal d'authentification
    """

    def __init__(self):
        self.jwt_service = JWTService()

    @property
    def max_login_attempts(self):
        return auth_settings.MAX_LOGIN_ATTEMPTS

    @property
    def lockout_duration_minutes(self):
        return auth_settings.LOCKOUT_DURATION_MINUTES

    @property
    def rate_limit_window_minutes(self):
        return auth_settings.RATE_LIMIT_WINDOW_MINUTES

    def validate_application(self, access_key: str, access_secret: str) -> Tuple[bool, Optional[Application], str]:
        """
        Valide les credentials de l'application (première couche)
        """
        try:
            application = Application.objects.get(access_key=access_key, is_active=True)
            if application.verify_secret(access_secret):
                return True, application, ''
            return False, None, 'Invalid access_secret'
        except Application.DoesNotExist:
            return False, None, 'Invalid access_key'

    def authenticate_by_email(
        self,
        email: str,
        password: str,
        application: Application,
        ip_address: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Authentification par email + password
        """
        identifier = email.lower()

        # Vérifier le rate limiting (si activé)
        if auth_settings.RATE_LIMITING_ENABLED:
            if LoginAttempt.is_rate_limited(identifier, self.max_login_attempts, self.rate_limit_window_minutes):
                return False, None, 'Too many login attempts. Please try again later.'

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            LoginAttempt.record(identifier, ip_address, application, False, 'user_not_found')
            return False, None, 'Invalid credentials'

        return self._complete_authentication(user, password, application, ip_address, identifier)

    def authenticate_by_phone(
        self,
        country_code: str,
        phone_number: str,
        password: str,
        application: Application,
        ip_address: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Authentification par téléphone + password
        """
        identifier = f"+{country_code}{phone_number}"

        # Vérifier le rate limiting (si activé)
        if auth_settings.RATE_LIMITING_ENABLED:
            if LoginAttempt.is_rate_limited(identifier, self.max_login_attempts, self.rate_limit_window_minutes):
                return False, None, 'Too many login attempts. Please try again later.'

        try:
            user = User.objects.get(
                phone_country_code=country_code,
                phone_number=phone_number
            )
        except User.DoesNotExist:
            LoginAttempt.record(identifier, ip_address, application, False, 'user_not_found')
            return False, None, 'Invalid credentials'

        return self._complete_authentication(user, password, application, ip_address, identifier)

    def _complete_authentication(
        self,
        user: User,
        password: str,
        application: Application,
        ip_address: str,
        identifier: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Finalise l'authentification après avoir trouvé l'utilisateur
        """
        # Vérifier si le compte est verrouillé (si le lockout est activé)
        if auth_settings.ACCOUNT_LOCKOUT_ENABLED and user.is_account_locked():
            LoginAttempt.record(identifier, ip_address, application, False, 'account_locked')
            return False, None, 'Account is locked. Please try again later.'

        # Vérifier si le compte est actif
        if not user.is_active:
            LoginAttempt.record(identifier, ip_address, application, False, 'account_inactive')
            return False, None, 'Account is inactive'

        # Vérifier le mot de passe
        if not user.check_password(password):
            LoginAttempt.record(identifier, ip_address, application, False, 'invalid_password')

            # Vérifier si on doit verrouiller le compte (si le lockout est activé)
            if auth_settings.ACCOUNT_LOCKOUT_ENABLED:
                recent_failures = LoginAttempt.get_recent_failures(identifier, self.rate_limit_window_minutes)
                if recent_failures >= self.max_login_attempts:
                    user.lock_account(self.lockout_duration_minutes)

            return False, None, 'Invalid credentials'

        # Authentification réussie
        LoginAttempt.record(identifier, ip_address, application, True)

        # Enforce session limit
        session_limit_result = self._enforce_session_limit(user, application, ip_address)
        if session_limit_result is not None:
            return session_limit_result

        # Enforce device limit
        device_limit_result = self._enforce_device_limit(user, application, ip_address, device_info='')
        if device_limit_result is not None:
            return device_limit_result

        # Mettre à jour last_login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # Générer les tokens
        refresh_token = RefreshToken.generate(
            user=user,
            application=application,
            ip_address=ip_address
        )

        tokens = self.jwt_service.generate_token_pair(
            user_id=str(user.id),
            application_id=str(application.id),
            refresh_token_str=refresh_token.token
        )

        # Audit log
        self._audit_log('login', user, ip_address, application)

        return True, {
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'token_type': tokens['token_type'],
            'expires_in': tokens['expires_in'],
            'user': {
                'id': str(user.id),
                'email': user.email,
                'phone': user.full_phone,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_email_verified': user.is_email_verified,
                'is_phone_verified': user.is_phone_verified,
                'is_2fa_enabled': user.is_2fa_enabled,
            },
            '_user': user,  # Objet user pour vérification 2FA (non sérialisé)
        }, ''

    def refresh_access_token(
        self,
        refresh_token_str: str,
        application: Application,
        ip_address: str = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Génère un nouveau access_token à partir d'un refresh_token.
        Si la rotation est activée, le refresh token est aussi renouvelé.
        """
        try:
            refresh_token = RefreshToken.objects.select_related('user').get(
                token=refresh_token_str,
                application=application
            )
        except RefreshToken.DoesNotExist:
            return False, None, 'Invalid refresh token'

        if not refresh_token.is_valid():
            return False, None, 'Refresh token expired or revoked'

        user = refresh_token.user

        # Refresh Token Rotation: revoke old token and create new one
        if auth_settings.REFRESH_TOKEN_ROTATION:
            # Revoke the old refresh token
            refresh_token.revoke()

            # Generate a new refresh token
            new_refresh_token = RefreshToken.generate(
                user=user,
                application=application,
                ip_address=ip_address,
                device_info=refresh_token.device_info
            )
            refresh_token_str = new_refresh_token.token
        else:
            # Just update last_used_at
            refresh_token.save()

        # Générer un nouveau access_token
        tokens = self.jwt_service.generate_token_pair(
            user_id=str(user.id),
            application_id=str(application.id),
            refresh_token_str=refresh_token_str
        )

        # Audit log
        self._audit_log('token_refresh', user, ip_address, application)

        return True, {
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'token_type': tokens['token_type'],
            'expires_in': tokens['expires_in'],
        }, ''

    def logout(self, refresh_token_str: str, access_token: str = None,
                ip_address: str = None, application=None) -> bool:
        """
        Révoque un refresh token (logout).
        Optionnellement blacklist l'access token aussi.
        """
        try:
            refresh_token = RefreshToken.objects.select_related('user').get(token=refresh_token_str)
            user = refresh_token.user
            refresh_token.revoke()

            # Blacklist access token if provided
            if access_token and auth_settings.TOKEN_BLACKLIST_ENABLED:
                self.jwt_service.blacklist_token(access_token, user, 'logout')

            # Audit log
            self._audit_log('logout', user, ip_address, application)

            return True
        except RefreshToken.DoesNotExist:
            return False

    def logout_all_devices(self, user: User, ip_address: str = None, application=None) -> int:
        """
        Révoque tous les refresh tokens d'un utilisateur
        """
        count = RefreshToken.objects.filter(
            user=user,
            is_revoked=False
        ).update(is_revoked=True)

        # Audit log
        self._audit_log('logout_all', user, ip_address, application, {'devices_count': count})

        return count

    def register_user(
        self,
        email: Optional[str] = None,
        phone_country_code: Optional[str] = None,
        phone_number: Optional[str] = None,
        password: str = None,
        first_name: str = '',
        last_name: str = ''
    ) -> Tuple[bool, Optional[User], str]:
        """
        Inscription d'un nouvel utilisateur
        """
        # Validation
        if not email and not (phone_country_code and phone_number):
            return False, None, 'Email or phone number is required'

        if not password:
            return False, None, 'Password is required'

        # Vérifier si l'utilisateur existe déjà
        if email:
            if User.objects.filter(email__iexact=email).exists():
                return False, None, 'Email already registered'

        if phone_country_code and phone_number:
            if User.objects.filter(
                phone_country_code=phone_country_code,
                phone_number=phone_number
            ).exists():
                return False, None, 'Phone number already registered'

        # Créer l'utilisateur
        user = User(
            email=email.lower() if email else None,
            phone_country_code=phone_country_code,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name
        )
        user.set_password(password)
        user.save()

        # Assigner le rôle par défaut (user)
        user.assign_default_role()

        # Password history
        if auth_settings.PASSWORD_HISTORY_ENABLED:
            PasswordHistory.add_password(user, user.password, auth_settings.PASSWORD_HISTORY_COUNT)

        # Audit log
        self._audit_log('account_created', user)

        return True, user, ''

    def change_password(
        self,
        user: User,
        old_password: str,
        new_password: str,
        ip_address: str = None,
        application=None
    ) -> Tuple[bool, str]:
        """
        Change le mot de passe d'un utilisateur.
        Vérifie l'ancien mot de passe et l'historique des mots de passe.
        """
        # Vérifier l'ancien mot de passe
        if not user.check_password(old_password):
            return False, 'Invalid current password'

        # Vérifier l'historique des mots de passe
        if auth_settings.PASSWORD_HISTORY_ENABLED:
            if PasswordHistory.is_password_used(user, new_password, auth_settings.PASSWORD_HISTORY_COUNT):
                return False, 'Password has been used recently. Please choose a different password.'

        # Changer le mot de passe
        user.set_password(new_password)
        user.save(update_fields=['password'])

        # Ajouter à l'historique
        if auth_settings.PASSWORD_HISTORY_ENABLED:
            PasswordHistory.add_password(user, user.password, auth_settings.PASSWORD_HISTORY_COUNT)

        # Audit log
        self._audit_log('password_change', user, ip_address, application)

        return True, ''

    def _enforce_session_limit(
        self,
        user: User,
        application,
        ip_address: str
    ) -> Optional[Tuple[bool, Optional[Dict[str, Any]], str]]:
        """
        Vérifie et applique la limite de sessions.
        Retourne None si OK, sinon retourne le tuple d'erreur.
        """
        if not auth_settings.SESSION_LIMIT_ENABLED:
            return None

        # Obtenir la limite de sessions (par utilisateur ou par défaut)
        max_sessions = user.max_sessions if user.max_sessions > 0 else auth_settings.DEFAULT_MAX_SESSIONS

        # 0 = illimité
        if max_sessions == 0:
            return None

        # Compter les sessions actives
        active_sessions = RefreshToken.objects.filter(
            user=user,
            is_revoked=False,
            expires_at__gt=timezone.now()
        ).count()

        if active_sessions >= max_sessions:
            action = auth_settings.SESSION_LIMIT_ACTION

            if action == 'deny':
                # Refuser la nouvelle connexion
                self._audit_log('session_limit_exceeded', user, ip_address, application, {
                    'action': 'denied',
                    'max_sessions': max_sessions,
                    'active_sessions': active_sessions
                })
                return False, None, f'Session limit exceeded. Maximum {max_sessions} session(s) allowed.'

            elif action == 'revoke_oldest':
                # Révoquer les sessions les plus anciennes
                sessions_to_revoke = active_sessions - max_sessions + 1
                oldest_sessions = RefreshToken.objects.filter(
                    user=user,
                    is_revoked=False,
                    expires_at__gt=timezone.now()
                ).order_by('created_at')[:sessions_to_revoke]

                revoked_count = 0
                for session in oldest_sessions:
                    session.revoke()
                    revoked_count += 1

                self._audit_log('session_limit_exceeded', user, ip_address, application, {
                    'action': 'revoked_oldest',
                    'max_sessions': max_sessions,
                    'revoked_count': revoked_count
                })

        return None

    def _enforce_device_limit(
        self,
        user: User,
        application,
        ip_address: str,
        device_info: str = ''
    ) -> Optional[Tuple[bool, Optional[Dict[str, Any]], str]]:
        """
        Vérifie et applique la limite de devices.
        Retourne None si OK, sinon retourne le tuple d'erreur.
        """
        if not auth_settings.DEVICE_LIMIT_ENABLED:
            return None

        # Obtenir la limite de devices (par utilisateur ou par défaut)
        max_devices = user.max_devices if user.max_devices > 0 else auth_settings.DEFAULT_MAX_DEVICES

        # 0 = illimité
        if max_devices == 0:
            return None

        # Compter les devices uniques avec sessions actives
        active_devices = RefreshToken.objects.filter(
            user=user,
            is_revoked=False,
            expires_at__gt=timezone.now()
        ).exclude(
            device_info=''
        ).values('device_info').distinct().count()

        # Si le device actuel est déjà connu, pas de problème
        if device_info:
            existing_device = RefreshToken.objects.filter(
                user=user,
                device_info=device_info,
                is_revoked=False,
                expires_at__gt=timezone.now()
            ).exists()
            if existing_device:
                return None

        if active_devices >= max_devices:
            action = auth_settings.DEVICE_LIMIT_ACTION

            if action == 'deny':
                # Refuser la nouvelle connexion
                self._audit_log('device_limit_exceeded', user, ip_address, application, {
                    'action': 'denied',
                    'max_devices': max_devices,
                    'active_devices': active_devices,
                    'new_device': device_info
                })
                return False, None, f'Device limit exceeded. Maximum {max_devices} device(s) allowed.'

            elif action == 'revoke_oldest':
                # Révoquer toutes les sessions du device le plus ancien
                oldest_device = RefreshToken.objects.filter(
                    user=user,
                    is_revoked=False,
                    expires_at__gt=timezone.now()
                ).exclude(
                    device_info=''
                ).order_by('created_at').values('device_info').first()

                if oldest_device:
                    revoked_count = RefreshToken.objects.filter(
                        user=user,
                        device_info=oldest_device['device_info'],
                        is_revoked=False
                    ).update(is_revoked=True)

                    self._audit_log('device_limit_exceeded', user, ip_address, application, {
                        'action': 'revoked_oldest',
                        'max_devices': max_devices,
                        'revoked_device': oldest_device['device_info'],
                        'revoked_sessions': revoked_count
                    })

        return None

    def _audit_log(
        self,
        action: str,
        user: User = None,
        ip_address: str = None,
        application=None,
        details: Dict[str, Any] = None
    ) -> None:
        """
        Enregistre une entrée dans le journal d'audit.
        """
        if not auth_settings.AUDIT_LOGGING_ENABLED:
            return

        AuditLog.log(
            action=action,
            user=user,
            ip_address=ip_address,
            application=application,
            details=details
        )
