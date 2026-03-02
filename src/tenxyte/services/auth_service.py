from typing import Optional, Dict, Any, Tuple
from django.utils import timezone
from django.db.models import Q

from ..models import get_application_model, RefreshToken, LoginAttempt, AuditLog, PasswordHistory, get_user_model
from .jwt_service import JWTService
from ..conf import auth_settings
from ..device_info import devices_match, get_device_summary, parse_device_info

User = get_user_model()
Application = get_application_model()


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
        ip_address: str,
        device_info: str = ''
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Authentification par email + password
        """
        identifier = email.lower()

        # Vérifier le rate limiting (si activé)
        if auth_settings.RATE_LIMITING_ENABLED:
            if LoginAttempt.is_rate_limited(identifier, self.max_login_attempts, self.rate_limit_window_minutes):
                # R14: Émettre le signal brute_force_detected
                from tenxyte.signals import brute_force_detected
                brute_force_detected.send(sender=self.__class__, user=None, ip_address=ip_address, attempt_count=self.max_login_attempts)
                return False, None, 'Too many login attempts. Please try again later.'

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            LoginAttempt.record(identifier, ip_address, application, False, 'user_not_found')
            return False, None, 'Invalid credentials'

        return self._complete_authentication(user, password, application, ip_address, identifier, device_info)

    def authenticate_by_phone(
        self,
        country_code: str,
        phone_number: str,
        password: str,
        application: Application,
        ip_address: str,
        device_info: str = ''
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Authentification par téléphone + password
        """
        identifier = f"+{country_code}{phone_number}"

        # Vérifier le rate limiting (si activé)
        if auth_settings.RATE_LIMITING_ENABLED:
            if LoginAttempt.is_rate_limited(identifier, self.max_login_attempts, self.rate_limit_window_minutes):
                # R14: Émettre le signal brute_force_detected
                from tenxyte.signals import brute_force_detected
                brute_force_detected.send(sender=self.__class__, user=None, ip_address=ip_address, attempt_count=self.max_login_attempts)
                return False, None, 'Too many login attempts. Please try again later.'

        try:
            user = User.objects.get(
                phone_country_code=country_code,
                phone_number=phone_number
            )
        except User.DoesNotExist:
            LoginAttempt.record(identifier, ip_address, application, False, 'user_not_found')
            return False, None, 'Invalid credentials'

        return self._complete_authentication(user, password, application, ip_address, identifier, device_info)

    def _complete_authentication(
        self,
        user: User,
        password: str,
        application: Application,
        ip_address: str,
        identifier: str,
        device_info: str = ''
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Finalise l'authentification après avoir trouvé l'utilisateur
        """
        # Vérifier si le compte est banni
        if user.is_account_banned():
            LoginAttempt.record(identifier, ip_address, application, False, 'account_banned')
            return False, None, 'Account is banned'

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
                    # R14: Émettre signal brute force (verrouillage géré via receiver dans signals.py)
                    from tenxyte.signals import brute_force_detected
                    brute_force_detected.send(sender=self.__class__, user=user, ip_address=ip_address, attempt_count=recent_failures)

            return False, None, 'Invalid credentials'

        # Authentification réussie
        LoginAttempt.record(identifier, ip_address, application, True)

        # Enforce session limit
        session_limit_result = self._enforce_session_limit(user, application, ip_address, device_info=device_info)
        if session_limit_result is not None:
            return session_limit_result

        # Enforce device limit
        device_limit_result = self._enforce_device_limit(user, application, ip_address, device_info=device_info)
        if device_limit_result is not None:
            return device_limit_result

        # Détection nouveau device → alerte sécurité
        if device_info:
            is_new = self._check_new_device_alert(user, device_info, ip_address, application)
            if getattr(is_new, 'is_new_device', False) or is_new is True:
                # R14: Émettre le signal public pour intégrateurs
                from tenxyte.signals import suspicious_login_detected
                suspicious_login_detected.send(sender=self.__class__, user=user, ip_address=ip_address, reason='new_device')

        # Mettre à jour last_login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # Générer les tokens
        refresh_token = RefreshToken.generate(
            user=user,
            application=application,
            ip_address=ip_address,
            device_info=device_info
        )

        tokens = self.jwt_service.generate_token_pair(
            user_id=str(user.id),
            application_id=str(application.id),
            refresh_token_str=refresh_token.raw_token  # valeur brute, jamais persistée
        )

        # Audit log
        self._audit_log('login', user, ip_address, application, {
            'device': get_device_summary(device_info)
        } if device_info else None, device_info=device_info)

        return True, {
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'token_type': tokens['token_type'],
            'expires_in': tokens['expires_in'],
            'device_summary': get_device_summary(device_info) if device_info else None,
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
            refresh_token = RefreshToken.get_by_raw_token(refresh_token_str)
            refresh_token = RefreshToken.objects.select_related('user').get(
                pk=refresh_token.pk,
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
            refresh_token_str = new_refresh_token.raw_token  # valeur brute pour le client
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
            refresh_token = RefreshToken.get_by_raw_token(refresh_token_str)
            refresh_token = RefreshToken.objects.select_related('user').get(pk=refresh_token.pk)
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

    def logout_all_devices(self, user: User, access_token: str = None,
                            ip_address: str = None, application=None) -> int:
        """
        Révoque tous les refresh tokens d'un utilisateur.
        Optionnellement blacklist l'access token courant.
        """
        count = RefreshToken.objects.filter(
            user=user,
            is_revoked=False
        ).update(is_revoked=True)

        # Blacklist current access token if provided
        if access_token and auth_settings.TOKEN_BLACKLIST_ENABLED:
            self.jwt_service.blacklist_token(access_token, user, 'logout_all')

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
        last_name: str = '',
        ip_address: str = None,
        application=None,
        device_info: str = ''
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

        # Create Default Organization if Multi-Tenancy feature is enabled
        from ..conf import org_settings
        if org_settings.ORGANIZATIONS_ENABLED and getattr(org_settings, 'CREATE_DEFAULT_ORGANIZATION', True):
            try:
                from .organization_service import OrganizationService
                org_service = OrganizationService()
                
                # Determine a good name based on available info
                name_part = first_name or user.email.split('@')[0] if user.email else "Personal"
                org_name = f"{name_part.capitalize()}'s Workspace"
                
                # The service will automatically make the creator the 'owner'
                org_service.create_organization(
                    name=org_name,
                    created_by=user,
                    description=f"Default workspace for {user.email or user.full_phone}"
                )
            except Exception as e:
                import logging
                logging.getLogger('tenxyte').error(
                    f"Failed to create default organization for user {user.id}: {e}"
                )

        # Password history
        if auth_settings.PASSWORD_HISTORY_ENABLED:
            PasswordHistory.add_password(user, user.password, auth_settings.PASSWORD_HISTORY_COUNT)

        # Audit log
        self._audit_log('account_created', user, ip_address, application, {
            'device': get_device_summary(device_info)
        } if device_info else None, device_info=device_info)

        return True, user, ''

    def generate_tokens_for_user(
        self,
        user: User,
        application: Application,
        ip_address: str = None,
        device_info: str = ''
    ) -> Dict[str, Any]:
        """
        Génère une paire de tokens JWT pour un utilisateur (post-inscription).
        Ne fait pas de vérification d'authentification.
        """
        # Enregistrer la tentative de login (post-inscription)
        identifier = user.email or user.full_phone or str(user.id)
        LoginAttempt.record(identifier, ip_address, application, True)

        # Mettre à jour last_login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        refresh_token = RefreshToken.generate(
            user=user,
            application=application,
            ip_address=ip_address,
            device_info=device_info
        )

        tokens = self.jwt_service.generate_token_pair(
            user_id=str(user.id),
            application_id=str(application.id),
            refresh_token_str=refresh_token.raw_token  # valeur brute, jamais persistée
        )

        # Audit log
        self._audit_log('login', user, ip_address, application, {
            'device': get_device_summary(device_info),
            'method': 'post_registration'
        } if device_info else {'method': 'post_registration'}, device_info=device_info)

        return {
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'token_type': tokens['token_type'],
            'expires_in': tokens['expires_in'],
            'device_summary': get_device_summary(device_info) if device_info else None,
        }

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
        ip_address: str,
        device_info: str = ''
    ) -> Optional[Tuple[bool, Optional[Dict[str, Any]], str]]:
        """
        Vérifie et applique la limite de sessions.
        Retourne None si OK, sinon retourne le tuple d'erreur.
        """
        if not auth_settings.SESSION_LIMIT_ENABLED:
            return None

        # Obtenir la limite de sessions (par utilisateur ou par défaut)
        user_max = getattr(user, 'max_sessions', None)
        max_sessions = user_max if user_max and user_max > 0 else auth_settings.DEFAULT_MAX_SESSIONS

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
            # Purge conditionnelle : révoquer les tokens zombies (expirés mais non révoqués)
            zombies = RefreshToken.objects.filter(
                user=user,
                is_revoked=False,
                expires_at__lte=timezone.now()
            ).update(is_revoked=True)

            if zombies > 0:
                # Recompter après purge
                active_sessions = RefreshToken.objects.filter(
                    user=user,
                    is_revoked=False,
                    expires_at__gt=timezone.now()
                ).count()

                # Si la limite est respectée après purge, on passe
                if active_sessions < max_sessions:
                    return None

            action = auth_settings.DEFAULT_SESSION_LIMIT_ACTION

            if action == 'deny':
                # Refuser la nouvelle connexion
                self._audit_log('session_limit_exceeded', user, ip_address, application, {
                    'action': 'denied',
                    'max_sessions': max_sessions,
                    'active_sessions': active_sessions
                }, device_info=device_info)
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
                }, device_info=device_info)

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
        user_max = getattr(user, 'max_devices', None)
        max_devices = user_max if user_max and user_max > 0 else auth_settings.DEFAULT_MAX_DEVICES

        # 0 = illimité
        if max_devices == 0:
            return None

        # Récupérer TOUS les tokens actifs
        all_active_tokens = RefreshToken.objects.filter(
            user=user,
            is_revoked=False,
            expires_at__gt=timezone.now()
        ).values_list('device_info', flat=True)

        # Regrouper par device identique (matching intelligent)
        # Les tokens avec device_info vide sont chacun comptés comme un device inconnu distinct
        unique_devices = []
        unknown_device_count = 0
        for token_device in all_active_tokens:
            if not token_device:
                unknown_device_count += 1
            elif not any(devices_match(token_device, ud) for ud in unique_devices):
                unique_devices.append(token_device)
        active_devices = len(unique_devices) + unknown_device_count

        # Si le device actuel est déjà connu, pas de problème
        if device_info:
            if any(devices_match(device_info, ud) for ud in unique_devices):
                return None

        if active_devices >= max_devices:
            # Purge conditionnelle : révoquer les tokens zombies (expirés mais non révoqués)
            zombies = RefreshToken.objects.filter(
                user=user,
                is_revoked=False,
                expires_at__lte=timezone.now()
            ).update(is_revoked=True)

            if zombies > 0:
                # Recompter après purge (matching intelligent)
                all_active_tokens = RefreshToken.objects.filter(
                    user=user,
                    is_revoked=False,
                    expires_at__gt=timezone.now()
                ).values_list('device_info', flat=True)

                unique_devices = []
                unknown_device_count = 0
                for token_device in all_active_tokens:
                    if not token_device:
                        unknown_device_count += 1
                    elif not any(devices_match(token_device, ud) for ud in unique_devices):
                        unique_devices.append(token_device)
                active_devices = len(unique_devices) + unknown_device_count

                # Si la limite est respectée après purge, on passe
                if active_devices < max_devices:
                    return None

            action = auth_settings.DEVICE_LIMIT_ACTION

            if action == 'deny':
                # Refuser la nouvelle connexion
                self._audit_log('device_limit_exceeded', user, ip_address, application, {
                    'action': 'denied',
                    'max_devices': max_devices,
                    'active_devices': active_devices,
                    'new_device': get_device_summary(device_info)
                }, device_info=device_info)
                return False, None, f'Device limit exceeded. Maximum {max_devices} device(s) allowed.'

            elif action == 'revoke_oldest':
                # Révoquer les sessions du device le plus ancien
                oldest_token = RefreshToken.objects.filter(
                    user=user,
                    is_revoked=False,
                    expires_at__gt=timezone.now()
                ).order_by('created_at').first()

                if oldest_token:
                    oldest_di = oldest_token.device_info
                    revoked_count = 0

                    if oldest_di:
                        # Device connu → révoquer tous les tokens du même device
                        all_tokens = RefreshToken.objects.filter(
                            user=user,
                            is_revoked=False
                        ).exclude(device_info='')

                        for token in all_tokens:
                            if devices_match(token.device_info, oldest_di):
                                token.is_revoked = True
                                token.save(update_fields=['is_revoked'])
                                revoked_count += 1
                    else:
                        # Device inconnu (device_info vide) → révoquer juste ce token
                        oldest_token.is_revoked = True
                        oldest_token.save(update_fields=['is_revoked'])
                        revoked_count = 1

                    self._audit_log('device_limit_exceeded', user, ip_address, application, {
                        'action': 'revoked_oldest',
                        'max_devices': max_devices,
                        'revoked_device': get_device_summary(oldest_di) if oldest_di else 'unknown',
                        'revoked_sessions': revoked_count
                    }, device_info=device_info)

        return None

    def _check_new_device_alert(
        self,
        user: User,
        device_info: str,
        ip_address: str,
        application=None
    ) -> None:
        """
        Vérifie si le device est nouveau pour cet utilisateur.
        Si oui, envoie une alerte de sécurité par email et log dans l'audit.
        """
        if not device_info:
            return

        # Récupérer tous les device_info connus de l'utilisateur
        known_devices = RefreshToken.objects.filter(
            user=user
        ).exclude(
            device_info=''
        ).values_list('device_info', flat=True).distinct()

        # Vérifier si le device actuel match un device connu
        is_known = any(devices_match(device_info, kd) for kd in known_devices)

        if not is_known:
            summary = get_device_summary(device_info)

            # Audit log
            self._audit_log('new_device_detected', user, ip_address, application, {
                'device': summary,
                'device_info': device_info
            }, device_info=device_info)

            # Envoyer alerte email si l'utilisateur a un email
            if user.email:
                try:
                    from .email_service import EmailService
                    email_service = EmailService()
                    email_service.send_security_alert_email(
                        to_email=user.email,
                        alert_type='new_login',
                        details={
                            'ip': ip_address or 'Inconnue',
                            'device': summary,
                        },
                        first_name=user.first_name
                    )
                except Exception as e:
                    import logging
                    logging.getLogger('tenxyte').warning(
                        f"[DeviceAlert] Failed to send new device alert email: {e}"
                    )

    def _audit_log(
        self,
        action: str,
        user: User = None,
        ip_address: str = None,
        application=None,
        details: Dict[str, Any] = None,
        device_info: str = ''
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
            user_agent=device_info,
            application=application,
            details=details
        )
