"""
Tenxyte Models - Application models.

Contains:
- AbstractApplication: Platform identification model (Web/Mobile/Desktop)
- Application: Default concrete implementation (swappable)
"""

import secrets
import bcrypt
import base64
from django.db import models

from .base import AutoFieldClass

# =============================================================================
# ABSTRACT APPLICATION MODEL
# =============================================================================


class AbstractApplication(models.Model):
    """
    Abstract Application model - Extend this to add custom fields.

    Example:
        class CustomApplication(AbstractApplication):
            owner = models.ForeignKey('myapp.User', on_delete=models.CASCADE)
            api_rate_limit = models.IntegerField(default=1000)

            class Meta(AbstractApplication.Meta):
                db_table = 'custom_applications'

        # In settings.py:
        TENXYTE_APPLICATION_MODEL = 'myapp.CustomApplication'
    """

    id = AutoFieldClass(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    access_key = models.CharField(max_length=64, unique=True, db_index=True)
    access_secret = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    redirect_uris = models.JSONField(
        default=list,
        blank=True,
        help_text="List of allowed redirect URIs for OAuth flows. Empty list permits all.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name

    @staticmethod
    def _hash_secret(raw_secret: str) -> str:
        """Hash le secret et encode en base64 pour éviter les problèmes avec MongoDB"""
        hashed = bcrypt.hashpw(raw_secret.encode("utf-8"), bcrypt.gensalt())
        return base64.b64encode(hashed).decode("utf-8")

    @staticmethod
    def _verify_hashed_secret(raw_secret: str, stored_secret: str) -> bool:
        """Vérifie le secret contre le hash stocké en base64"""
        try:
            hashed = base64.b64decode(stored_secret.encode("utf-8"))
            return bcrypt.checkpw(raw_secret.encode("utf-8"), hashed)
        except Exception:
            return False

    def verify_secret(self, raw_secret: str) -> bool:
        if not self.access_secret or not raw_secret:
            return False
        return self._verify_hashed_secret(raw_secret, self.access_secret)

    def is_redirect_uri_allowed(self, redirect_uri: str) -> bool:
        """Check if a redirect URI is in the application's whitelist.

        Returns True if the whitelist is empty (backward compatibility)
        or if the URI exactly matches an entry.
        """
        if not self.redirect_uris:
            return True
        return redirect_uri in self.redirect_uris

    def regenerate_credentials(self):
        """
        Régénère access_key et access_secret
        Retourne le secret brut UNE SEULE FOIS
        """
        raw_secret = secrets.token_hex(32)
        hashed_secret = self._hash_secret(raw_secret)

        self.access_key = secrets.token_hex(32)
        self.access_secret = hashed_secret
        self.save()

        return {"access_key": self.access_key, "access_secret": raw_secret}

    @classmethod
    def create_application(cls, name: str, description: str = ""):
        """
        Crée une nouvelle application et retourne l'instance + le secret brut
        """
        raw_secret = secrets.token_hex(32)
        hashed_secret = cls._hash_secret(raw_secret)
        app = cls(name=name, description=description, access_key=secrets.token_hex(32), access_secret=hashed_secret)
        app.save()
        return app, raw_secret


class Application(AbstractApplication):
    """
    Default Application model. Can be replaced by setting TENXYTE_APPLICATION_MODEL.
    """

    class Meta(AbstractApplication.Meta):
        db_table = "applications"
        swappable = "TENXYTE_APPLICATION_MODEL"
