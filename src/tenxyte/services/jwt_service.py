import jwt
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple

from ..conf import auth_settings


class JWTService:
    """
    Service de gestion des tokens JWT
    """

    def __init__(self):
        self.algorithm = auth_settings.JWT_ALGORITHM
        self.is_asymmetric = self.algorithm.startswith(("RS", "PS", "ES"))

        if self.is_asymmetric:
            self.private_key = auth_settings.JWT_PRIVATE_KEY
            self.public_key = auth_settings.JWT_PUBLIC_KEY
            if not self.private_key or not self.public_key:
                from django.core.exceptions import ImproperlyConfigured

                raise ImproperlyConfigured(
                    f"TENXYTE_JWT_PRIVATE_KEY and TENXYTE_JWT_PUBLIC_KEY must be set when using asymmetric algorithm {self.algorithm}."
                )
            self.signing_key = self.private_key
            self.verifying_key = self.public_key
        else:
            self.secret_key = auth_settings.JWT_SECRET_KEY
            self.signing_key = self.secret_key
            self.verifying_key = self.secret_key

        self.access_token_lifetime = timedelta(seconds=auth_settings.JWT_ACCESS_TOKEN_LIFETIME)
        self.refresh_token_lifetime = timedelta(seconds=auth_settings.JWT_REFRESH_TOKEN_LIFETIME)

    def generate_access_token(
        self, user_id: str, application_id: str, extra_claims: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, datetime]:
        """
        Génère un access token JWT avec JTI pour blacklisting.

        Returns:
            Tuple of (token, jti, expires_at)
        """
        now = datetime.now(timezone.utc)
        jti = str(uuid.uuid4())  # Unique token ID for blacklisting
        expires_at = now + self.access_token_lifetime

        payload = {
            "type": "access",
            "jti": jti,
            "user_id": str(user_id),
            "app_id": str(application_id),
            "iat": now,
            "exp": expires_at,
            "nbf": now,
        }

        if extra_claims:
            payload.update(extra_claims)

        token = jwt.encode(payload, self.signing_key, algorithm=self.algorithm)
        return token, jti, expires_at

    def generate_token_pair(
        self, user_id: str, application_id: str, refresh_token_str: str, extra_claims: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Génère une paire access_token + refresh_token
        """
        access_token, jti, expires_at = self.generate_access_token(user_id, application_id, extra_claims)

        return {
            "access_token": access_token,
            "access_token_jti": jti,
            "access_token_expires_at": expires_at,
            "refresh_token": refresh_token_str,
            "token_type": "Bearer",
            "expires_in": int(self.access_token_lifetime.total_seconds()),
        }

    def decode_token(self, token: str, check_blacklist: bool = True) -> Optional[Dict[str, Any]]:
        """
        Décode et valide un token JWT.
        Vérifie aussi si le token est blacklisté.
        """
        try:
            payload = jwt.decode(
                token,
                self.verifying_key,
                algorithms=[self.algorithm],
                options={"require": ["exp", "iat", "user_id", "app_id"]},
            )

            # Check blacklist if enabled
            if check_blacklist and auth_settings.TOKEN_BLACKLIST_ENABLED:
                jti = payload.get("jti")
                if jti:
                    from ..models import BlacklistedToken

                    if BlacklistedToken.is_blacklisted(jti):
                        return None

            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def is_token_valid(self, token: str) -> bool:
        """
        Vérifie si un token est valide
        """
        return self.decode_token(token) is not None

    def get_user_id_from_token(self, token: str) -> Optional[str]:
        """
        Extrait l'ID utilisateur d'un token
        """
        payload = self.decode_token(token)
        if payload:
            return payload.get("user_id")
        return None

    def get_application_id_from_token(self, token: str) -> Optional[str]:
        """
        Extrait l'ID application d'un token
        """
        payload = self.decode_token(token)
        if payload:
            return payload.get("app_id")
        return None

    def blacklist_token(self, token: str, user=None, reason: str = "") -> bool:
        """
        Ajoute un token à la blacklist.

        Args:
            token: Le token JWT à blacklister
            user: L'utilisateur (optionnel)
            reason: La raison du blacklistage

        Returns:
            True si le token a été blacklisté, False sinon
        """
        if not auth_settings.TOKEN_BLACKLIST_ENABLED:
            return False

        # Decode without checking blacklist to get the JTI
        payload = self.decode_token(token, check_blacklist=False)
        if not payload:
            return False

        jti = payload.get("jti")
        if not jti:
            return False

        # Get expiration time
        exp = payload.get("exp")
        if isinstance(exp, (int, float)):
            expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        else:
            expires_at = datetime.now(timezone.utc) + self.access_token_lifetime

        from ..models import BlacklistedToken

        BlacklistedToken.blacklist_token(jti, expires_at, user, reason)
        return True

    def blacklist_all_user_tokens(self, user, reason: str = "logout_all") -> None:
        """
        Note: This doesn't actually blacklist existing tokens since we don't store JTIs.
        For true logout-all functionality, use refresh token revocation.
        This method is a placeholder for future implementation with token storage.
        """
        pass
