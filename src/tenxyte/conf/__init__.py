"""
Configuration settings pour Tenxyte (Module factorisé).
"""

from .airs import AirsSettingsMixin
from .auth import AuthSettingsMixin
from .base import BaseSettingsMixin
from .communication import CommunicationSettingsMixin
from .jwt import JwtSettingsMixin
from .modules import ModulesSettingsMixin
from .presets import SECURE_MODE_PRESETS as SECURE_MODE_PRESETS
from .presets import VALID_SECURE_MODES as VALID_SECURE_MODES
from .security import SecuritySettingsMixin
from .social import SocialSettingsMixin


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
