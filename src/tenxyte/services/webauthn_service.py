"""
WebAuthn / Passkeys Service (FIDO2).

Requires: pip install py_webauthn

Supports:
- Registration: begin (challenge) + complete (verify + store credential)
- Authentication: begin (challenge) + complete (verify + generate JWT)
"""
import logging
from typing import Optional, Dict, Any, Tuple, List

from django.conf import settings

from ..conf import auth_settings
from ..models.webauthn import WebAuthnCredential, WebAuthnChallenge

logger = logging.getLogger(__name__)


def _get_webauthn():
    """Lazy import of py_webauthn to avoid hard dependency."""
    try:
        import webauthn
        return webauthn
    except ImportError:
        raise ImportError(
            "py_webauthn is required for WebAuthn/Passkeys support. "
            "Install it with: pip install py_webauthn"
        )


class WebAuthnService:
    """
    Gère les opérations WebAuthn (Passkeys) FIDO2.

    Flow d'enregistrement:
    1. begin_registration(user) → challenge + options JSON
    2. complete_registration(user, credential_data, challenge) → WebAuthnCredential

    Flow d'authentification:
    1. begin_authentication(user_or_email) → challenge + options JSON
    2. complete_authentication(credential_data, challenge) → JWT tokens
    """

    def _get_rp_id(self) -> str:
        return getattr(settings, 'TENXYTE_WEBAUTHN_RP_ID', 'localhost')

    def _get_rp_name(self) -> str:
        return getattr(settings, 'TENXYTE_WEBAUTHN_RP_NAME', 'Tenxyte')

    def _get_origin(self) -> str:
        rp_id = self._get_rp_id()
        if rp_id == 'localhost':
            return 'http://localhost'
        return f'https://{rp_id}'

    # =========================================================================
    # Registration
    # =========================================================================

    def begin_registration(self, user) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Génère les options de registration WebAuthn pour l'utilisateur.

        Returns:
            (success, options_dict, error)
        """
        if not auth_settings.WEBAUTHN_ENABLED:
            return False, None, 'WebAuthn is not enabled'

        webauthn = _get_webauthn()

        # Récupérer les credentials existants pour les exclure
        existing_credentials = list(
            WebAuthnCredential.objects.filter(user=user).values_list('credential_id', flat=True)
        )

        challenge_instance, raw_challenge = WebAuthnChallenge.generate(
            operation=WebAuthnChallenge.OPERATION_REGISTER,
            user=user,
            expiry_seconds=300
        )

        try:
            options = webauthn.generate_registration_options(
                rp_id=self._get_rp_id(),
                rp_name=self._get_rp_name(),
                user_id=str(user.id).encode(),
                user_name=user.email,
                user_display_name=f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or user.email,
                challenge=raw_challenge.encode(),
                exclude_credentials=[
                    webauthn.PublicKeyCredentialDescriptor(id=cid.encode())
                    for cid in existing_credentials
                ],
            )
            return True, {
                'challenge_id': challenge_instance.id,
                'options': webauthn.options_to_json(options),
            }, ''
        except Exception as e:
            logger.error(f"WebAuthn begin_registration error: {e}")
            challenge_instance.delete()
            return False, None, str(e)

    def complete_registration(
        self,
        user,
        credential_data: Dict[str, Any],
        challenge_id: int,
        device_name: str = ''
    ) -> Tuple[bool, Optional[WebAuthnCredential], str]:
        """
        Vérifie et enregistre une nouvelle credential WebAuthn.

        Returns:
            (success, WebAuthnCredential | None, error)
        """
        if not auth_settings.WEBAUTHN_ENABLED:
            return False, None, 'WebAuthn is not enabled'

        try:
            challenge_instance = WebAuthnChallenge.objects.get(
                id=challenge_id,
                user=user,
                operation=WebAuthnChallenge.OPERATION_REGISTER
            )
        except WebAuthnChallenge.DoesNotExist:
            return False, None, 'Invalid or expired challenge'

        if not challenge_instance.is_valid():
            return False, None, 'Challenge has expired or already been used'

        webauthn = _get_webauthn()

        try:
            verification = webauthn.verify_registration_response(
                credential=credential_data,
                expected_challenge=challenge_instance.challenge.encode(),
                expected_rp_id=self._get_rp_id(),
                expected_origin=self._get_origin(),
            )
        except Exception as e:
            logger.warning(f"WebAuthn registration verification failed: {e}")
            return False, None, f'Registration verification failed: {e}'

        challenge_instance.consume()

        # Stocker la credential
        credential = WebAuthnCredential.objects.create(
            user=user,
            credential_id=verification.credential_id.decode() if isinstance(verification.credential_id, bytes) else str(verification.credential_id),
            public_key=verification.credential_public_key.decode() if isinstance(verification.credential_public_key, bytes) else str(verification.credential_public_key),
            sign_count=verification.sign_count,
            device_name=device_name or 'Passkey',
            aaguid=str(verification.aaguid) if hasattr(verification, 'aaguid') else '',
        )

        return True, credential, ''

    # =========================================================================
    # Authentication
    # =========================================================================

    def begin_authentication(self, user=None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Génère les options d'authentification WebAuthn.

        Args:
            user: Si fourni, liste les credentials de cet utilisateur.
                  Si None, authentification sans username (usernameless).

        Returns:
            (success, options_dict, error)
        """
        if not auth_settings.WEBAUTHN_ENABLED:
            return False, None, 'WebAuthn is not enabled'

        webauthn = _get_webauthn()

        challenge_instance, raw_challenge = WebAuthnChallenge.generate(
            operation=WebAuthnChallenge.OPERATION_AUTHENTICATE,
            user=user,
            expiry_seconds=300
        )

        allow_credentials = []
        if user:
            credentials = WebAuthnCredential.objects.filter(user=user)
            allow_credentials = [
                webauthn.PublicKeyCredentialDescriptor(id=c.credential_id.encode())
                for c in credentials
            ]

        try:
            options = webauthn.generate_authentication_options(
                rp_id=self._get_rp_id(),
                challenge=raw_challenge.encode(),
                allow_credentials=allow_credentials,
            )
            return True, {
                'challenge_id': challenge_instance.id,
                'options': webauthn.options_to_json(options),
            }, ''
        except Exception as e:
            logger.error(f"WebAuthn begin_authentication error: {e}")
            challenge_instance.delete()
            return False, None, str(e)

    def complete_authentication(
        self,
        credential_data: Dict[str, Any],
        challenge_id: int,
        application=None,
        ip_address: str = None,
        device_info: str = ''
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Vérifie l'assertion WebAuthn et retourne des tokens JWT.

        Returns:
            (success, jwt_data | None, error)
        """
        if not auth_settings.WEBAUTHN_ENABLED:
            return False, None, 'WebAuthn is not enabled'

        try:
            challenge_instance = WebAuthnChallenge.objects.get(
                id=challenge_id,
                operation=WebAuthnChallenge.OPERATION_AUTHENTICATE
            )
        except WebAuthnChallenge.DoesNotExist:
            return False, None, 'Invalid or expired challenge'

        if not challenge_instance.is_valid():
            return False, None, 'Challenge has expired or already been used'

        # Trouver la credential par son ID
        raw_credential_id = credential_data.get('id', '')
        try:
            stored_credential = WebAuthnCredential.objects.select_related('user').get(
                credential_id=raw_credential_id
            )
        except WebAuthnCredential.DoesNotExist:
            return False, None, 'Unknown credential'

        user = stored_credential.user

        if not user.is_active:
            return False, None, 'Account is disabled'

        if user.is_account_locked():
            return False, None, 'Account is locked'

        webauthn = _get_webauthn()

        try:
            verification = webauthn.verify_authentication_response(
                credential=credential_data,
                expected_challenge=challenge_instance.challenge.encode(),
                expected_rp_id=self._get_rp_id(),
                expected_origin=self._get_origin(),
                credential_public_key=stored_credential.public_key.encode() if isinstance(stored_credential.public_key, str) else stored_credential.public_key,
                credential_current_sign_count=stored_credential.sign_count,
            )
        except Exception as e:
            logger.warning(f"WebAuthn authentication verification failed: {e}")
            return False, None, f'Authentication verification failed: {e}'

        challenge_instance.consume()
        stored_credential.update_sign_count(verification.new_sign_count)

        # Générer les tokens JWT
        from .auth_service import AuthService
        jwt_data = AuthService().generate_tokens_for_user(
            user=user,
            application=application,
            ip_address=ip_address,
            device_info=device_info
        )

        return True, jwt_data, ''

    # =========================================================================
    # Credential Management
    # =========================================================================

    def list_credentials(self, user) -> List[Dict[str, Any]]:
        """Liste les passkeys d'un utilisateur."""
        credentials = WebAuthnCredential.objects.filter(user=user).order_by('-created_at')
        return [
            {
                'id': c.id,
                'device_name': c.device_name,
                'created_at': c.created_at.isoformat(),
                'last_used_at': c.last_used_at.isoformat() if c.last_used_at else None,
                'transports': c.transports,
            }
            for c in credentials
        ]

    def delete_credential(self, user, credential_id: int) -> Tuple[bool, str]:
        """Supprime une passkey de l'utilisateur."""
        try:
            credential = WebAuthnCredential.objects.get(id=credential_id, user=user)
            credential.delete()
            return True, ''
        except WebAuthnCredential.DoesNotExist:
            return False, 'Credential not found'
