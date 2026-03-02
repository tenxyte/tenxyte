"""
Configuration settings pour Tenxyte (Module factorisé).
"""
from django.conf import settings
from .base import BaseSettingsMixin
from .jwt import JwtSettingsMixin
from .auth import AuthSettingsMixin
from .security import SecuritySettingsMixin
from .social import SocialSettingsMixin
from .communication import CommunicationSettingsMixin
from .modules import ModulesSettingsMixin
from .airs import AirsSettingsMixin
from .presets import SECURE_MODE_PRESETS, VALID_SECURE_MODES

class TenxyteSettings(
    BaseSettingsMixin,
    JwtSettingsMixin,
    AuthSettingsMixin,
    SecuritySettingsMixin,
    SocialSettingsMixin,
    CommunicationSettingsMixin,
    ModulesSettingsMixin,
    AirsSettingsMixin,
):
    """
    Configuration consolidée de Tenxyte.
    """


auth_settings = TenxyteSettings()
org_settings = auth_settings  # Alias pour clarté dans le code org
# Rétrocompatibilité absolue : exposer aussi l'instance dans le module parent
# Note: si quelqu'un importe du code depuis src/tenxyte/conf.py, ça pointera vers __init__.py
