"""
Social Login Multi-Provider Service.

Architecture:
- AbstractOAuthProvider: base commune pour tous les providers
- GoogleOAuthProvider: refactored from GoogleAuthService (backward-compatible)
- GitHubOAuthProvider: OAuth2 GitHub
- MicrosoftOAuthProvider: OAuth2 Microsoft/Azure AD
- FacebookOAuthProvider: OAuth2 Facebook
- SocialAuthService: orchestrateur principal (find/create user, generate JWT)
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple

import requests
from django.conf import settings
from django.utils import timezone

from ..models import get_user_model, get_application_model, RefreshToken
from ..models.social import SocialConnection
from .jwt_service import JWTService
from ..device_info import get_device_summary

logger = logging.getLogger(__name__)

User = get_user_model()
Application = get_application_model()


# ===========================================================================
# Abstract Base Provider
# ===========================================================================


class AbstractOAuthProvider(ABC):
    """
    Classe de base pour tous les providers OAuth2.

    Chaque provider doit implémenter:
    - provider_name: identifiant unique (ex: 'github')
    - get_user_info(access_token): retourne un dict normalisé
    - exchange_code(code, redirect_uri): échange un code contre un access_token

    Le dict normalisé retourné par get_user_info doit contenir:
    {
        'provider_user_id': str,   # ID unique chez le provider
        'email': str | None,
        'email_verified': bool,
        'first_name': str,
        'last_name': str,
        'avatar_url': str,
    }
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifiant du provider (ex: 'github', 'microsoft')."""
        ...

    @abstractmethod
    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Récupère les infos utilisateur depuis le provider."""
        ...

    @abstractmethod
    def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """Échange un authorization code contre des tokens."""
        ...

    def _get(self, url: str, access_token: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Helper GET avec Bearer token."""
        try:
            resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=10, **kwargs)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"{self.provider_name} GET {url} returned {resp.status_code}")
            return None
        except Exception as e:
            logger.error(f"{self.provider_name} GET error: {e}")
            return None

    def _post(self, url: str, data: dict, headers: dict = None) -> Optional[Dict[str, Any]]:
        """Helper POST."""
        try:
            resp = requests.post(url, data=data, headers=headers or {}, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"{self.provider_name} POST {url} returned {resp.status_code}")
            return None
        except Exception as e:
            logger.error(f"{self.provider_name} POST error: {e}")
            return None


# ===========================================================================
# Google Provider (refactored, backward-compatible)
# ===========================================================================


class GoogleOAuthProvider(AbstractOAuthProvider):
    """Google OAuth2 provider."""

    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

    @property
    def provider_name(self) -> str:
        return "google"

    def verify_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Vérifie un Google ID token."""
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

            client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
            idinfo = google_id_token.verify_oauth2_token(id_token, google_requests.Request(), client_id)
            if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                return None

            return self._normalize(
                {
                    "sub": idinfo["sub"],
                    "email": idinfo.get("email"),
                    "email_verified": idinfo.get("email_verified", False),
                    "given_name": idinfo.get("given_name", ""),
                    "family_name": idinfo.get("family_name", ""),
                    "picture": idinfo.get("picture", ""),
                }
            )
        except Exception as e:
            logger.error(f"Google ID token verification error: {e}")
            return None

    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        data = self._get(self.GOOGLE_USERINFO_URL, access_token)
        if not data:
            return None
        return self._normalize(data)

    def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        return self._post(
            self.GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": getattr(settings, "GOOGLE_CLIENT_ID", ""),
                "client_secret": getattr(settings, "GOOGLE_CLIENT_SECRET", ""),
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    def _normalize(self, data: dict) -> Dict[str, Any]:
        return {
            "provider_user_id": data.get("sub", ""),
            "email": data.get("email"),
            "email_verified": data.get("email_verified", False),
            "first_name": data.get("given_name", ""),
            "last_name": data.get("family_name", ""),
            "avatar_url": data.get("picture", ""),
        }


# ===========================================================================
# GitHub Provider
# ===========================================================================


class GitHubOAuthProvider(AbstractOAuthProvider):
    """GitHub OAuth2 provider."""

    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_USERINFO_URL = "https://api.github.com/user"
    GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

    @property
    def provider_name(self) -> str:
        return "github"

    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        data = self._get(self.GITHUB_USERINFO_URL, access_token)
        if not data:
            return None

        # GitHub may not expose email in /user — fetch from /user/emails
        email = data.get("email")
        email_verified = False
        if not email:
            emails_data = self._get(self.GITHUB_EMAILS_URL, access_token)
            if emails_data:
                primary = next((e for e in emails_data if e.get("primary") and e.get("verified")), None)
                if primary:
                    email = primary["email"]
                    email_verified = primary.get("verified", False)
        else:
            email_verified = True

        name_parts = (data.get("name") or "").split(" ", 1)
        return {
            "provider_user_id": str(data["id"]),
            "email": email,
            "email_verified": email_verified,
            "first_name": name_parts[0] if name_parts else "",
            "last_name": name_parts[1] if len(name_parts) > 1 else "",
            "avatar_url": data.get("avatar_url", ""),
        }

    def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        return self._post(
            self.GITHUB_TOKEN_URL,
            data={
                "code": code,
                "client_id": getattr(settings, "GITHUB_CLIENT_ID", ""),
                "client_secret": getattr(settings, "GITHUB_CLIENT_SECRET", ""),
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )


# ===========================================================================
# Microsoft Provider
# ===========================================================================


class MicrosoftOAuthProvider(AbstractOAuthProvider):
    """Microsoft OAuth2 / Azure AD provider."""

    MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    MICROSOFT_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"

    @property
    def provider_name(self) -> str:
        return "microsoft"

    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        data = self._get(self.MICROSOFT_USERINFO_URL, access_token)
        if not data:
            return None

        email = data.get("mail") or data.get("userPrincipalName", "")
        return {
            "provider_user_id": data.get("id", ""),
            "email": email if "@" in email else None,
            "email_verified": True,  # Microsoft verifies emails
            "first_name": data.get("givenName", ""),
            "last_name": data.get("surname", ""),
            "avatar_url": "",
        }

    def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        return self._post(
            self.MICROSOFT_TOKEN_URL,
            data={
                "code": code,
                "client_id": getattr(settings, "MICROSOFT_CLIENT_ID", ""),
                "client_secret": getattr(settings, "MICROSOFT_CLIENT_SECRET", ""),
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "scope": "openid email profile",
            },
        )


# ===========================================================================
# Facebook Provider
# ===========================================================================


class FacebookOAuthProvider(AbstractOAuthProvider):
    """Facebook OAuth2 provider."""

    FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
    FACEBOOK_USERINFO_URL = "https://graph.facebook.com/me"

    @property
    def provider_name(self) -> str:
        return "facebook"

    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        try:
            resp = requests.get(
                self.FACEBOOK_USERINFO_URL,
                params={
                    "fields": "id,email,first_name,last_name,picture",
                    "access_token": access_token,
                },
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
        except Exception as e:
            logger.error(f"Facebook user info error: {e}")
            return None

        return {
            "provider_user_id": data.get("id", ""),
            "email": data.get("email"),
            "email_verified": True,  # Facebook verifies emails
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "avatar_url": data.get("picture", {}).get("data", {}).get("url", ""),
        }

    def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        return self._post(
            self.FACEBOOK_TOKEN_URL,
            data={
                "code": code,
                "client_id": getattr(settings, "FACEBOOK_APP_ID", ""),
                "client_secret": getattr(settings, "FACEBOOK_APP_SECRET", ""),
                "redirect_uri": redirect_uri,
            },
        )


# ===========================================================================
# Provider Registry
# ===========================================================================

PROVIDER_REGISTRY: Dict[str, AbstractOAuthProvider] = {
    "google": GoogleOAuthProvider(),
    "github": GitHubOAuthProvider(),
    "microsoft": MicrosoftOAuthProvider(),
    "facebook": FacebookOAuthProvider(),
}


def get_provider(name: str) -> Optional[AbstractOAuthProvider]:
    """Retourne le provider par son nom, ou None si inconnu/désactivé."""
    from ..conf import auth_settings

    # Priorité aux réglages settings.py s'ils existent
    enabled = getattr(settings, "TENXYTE_SOCIAL_PROVIDERS", None)
    if enabled is None:
        # Sinon utiliser les défauts du provider registry filtrés par auth_settings
        enabled = auth_settings.SOCIAL_PROVIDERS

    if name not in enabled:
        return None
    return PROVIDER_REGISTRY.get(name)


# ===========================================================================
# SocialAuthService — orchestrateur principal
# ===========================================================================


class SocialAuthService:
    """
    Orchestrateur pour l'authentification sociale multi-provider.

    Flow:
    1. Récupère les infos utilisateur depuis le provider
    2. Trouve ou crée l'utilisateur local
    3. Crée/met à jour la SocialConnection
    4. Génère les tokens JWT
    """

    def __init__(self):
        self.jwt_service = JWTService()

    def authenticate(
        self, provider_name: str, user_data: Dict[str, Any], application, ip_address: str, device_info: str = ""
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Authentifie ou crée un utilisateur via les données d'un provider social.

        Args:
            provider_name: 'google', 'github', 'microsoft', 'facebook'
            user_data: dict normalisé retourné par provider.get_user_info()
            application: Application instance
            ip_address: IP du client
            device_info: device fingerprint

        Returns:
            (success, data, error)
        """
        provider_user_id = user_data.get("provider_user_id", "")
        email = user_data.get("email")

        if not provider_user_id:
            return False, None, f"Invalid {provider_name} data: missing user ID"

        # 1. Chercher une connexion sociale existante
        connection = (
            SocialConnection.objects.filter(provider=provider_name, provider_user_id=provider_user_id)
            .select_related("user")
            .first()
        )

        if connection:
            user = connection.user
        elif email:
            # 2. Chercher par email (Account Fusion)
            # F-03 Critical Security Fix: Strictly refuse fusion if email is not verified by provider
            from ..conf import auth_settings

            is_verified = user_data.get("email_verified", False)

            if not is_verified:
                return (
                    False,
                    None,
                    f"Email from {provider_name} is not verified. Authentication and account fusion rejected for security.",
                )

            user = User.objects.filter(email__iexact=email).first()

            # R-05 Mitigation: Prevent automatic account merging by default
            auto_merge = getattr(auth_settings, "SOCIAL_AUTO_MERGE_ACCOUNTS", False)
            if user and not auto_merge:
                return (
                    False,
                    None,
                    f"An account with this email already exists. Please login with your email and password to link your {provider_name} account.",
                )
        else:
            user = None

        if not user:
            # 3. Créer un nouvel utilisateur
            user = User.objects.create(
                email=email.lower() if email else None,
                first_name=user_data.get("first_name", ""),
                last_name=user_data.get("last_name", ""),
                is_email_verified=user_data.get("email_verified", False),
                password="",
            )
            user.assign_default_role()

            # Create Default Organization if Multi-Tenancy feature is enabled
            from ..conf import org_settings

            if org_settings.ORGANIZATIONS_ENABLED and getattr(org_settings, "CREATE_DEFAULT_ORGANIZATION", True):
                try:
                    from .organization_service import OrganizationService

                    org_service = OrganizationService()

                    name_part = user_data.get("first_name") or user.email.split("@")[0] if user.email else "Personal"
                    org_name = f"{name_part.capitalize()}'s Workspace"

                    org_service.create_organization(
                        name=org_name,
                        created_by=user,
                        description=f"Default workspace for {user.email or user.full_phone}",
                    )
                except Exception as e:
                    import logging

                    logging.getLogger("tenxyte").error(
                        f"Failed to create default organization for user {user.id} via social auth: {e}"
                    )
        else:
            # Mettre à jour l'email vérifié si nécessaire
            if email and user_data.get("email_verified") and not user.is_email_verified:
                user.is_email_verified = True
                user.save(update_fields=["is_email_verified"])

        if not user.is_active:
            return False, None, "Account is disabled"

        if user.is_account_locked():
            return False, None, "Account is locked"

        # 4. Créer/mettre à jour la SocialConnection
        SocialConnection.get_or_create_for_user(
            user=user,
            provider=provider_name,
            provider_user_id=provider_user_id,
            email=email or "",
            first_name=user_data.get("first_name", ""),
            last_name=user_data.get("last_name", ""),
            avatar_url=user_data.get("avatar_url", ""),
        )

        # 5. Mettre à jour last_login
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        # 6. Générer les tokens JWT
        refresh_token = RefreshToken.generate(
            user=user, application=application, ip_address=ip_address, device_info=device_info
        )

        tokens = self.jwt_service.generate_token_pair(
            user_id=str(user.id),
            application_id=str(application.id),
            refresh_token_str=refresh_token.raw_token,  # valeur brute, jamais persistée
        )

        return (
            True,
            {
                **tokens,
                "device_summary": get_device_summary(device_info) if device_info else None,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_email_verified": user.is_email_verified,
                },
            },
            "",
        )
