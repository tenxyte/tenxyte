"""
Settings pour tests multi-DB: SQLite (in-memory).
Toujours disponible, pas de dépendances externes.
"""
from .settings_base import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
