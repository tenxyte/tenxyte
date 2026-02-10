"""
Configuration pytest pour les tests multi-DB.

Usage:
  # SQLite (défaut, toujours disponible)
  pytest tests/multidb/ --db=sqlite

  # PostgreSQL (nécessite psycopg2-binary + serveur PG)
  pytest tests/multidb/ --db=pgsql

  # MySQL (nécessite mysqlclient + serveur MySQL)
  pytest tests/multidb/ --db=mysql

  # MongoDB (nécessite django-mongodb-backend + serveur MongoDB)
  pytest tests/multidb/ --db=mongodb
"""
import pytest
from django.core.cache import cache


# ─── Mapping backend → settings module ───
DB_SETTINGS_MAP = {
    'sqlite': 'tests.multidb.settings_sqlite',
    'pgsql': 'tests.multidb.settings_pgsql',
    'mysql': 'tests.multidb.settings_mysql',
    'mongodb': 'tests.multidb.settings_mongodb',
}


def pytest_addoption(parser):
    """Ajoute l'option --db pour sélectionner le backend."""
    parser.addoption(
        '--db',
        action='store',
        default='sqlite',
        choices=list(DB_SETTINGS_MAP.keys()),
        help='Backend de base de données à tester (défaut: sqlite)',
    )


@pytest.fixture(autouse=True)
def clear_cache():
    """Vider le cache entre chaque test pour éviter les effets de bord throttling."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def db_backend(request):
    """Retourne le nom du backend DB en cours de test."""
    return request.config.getoption('--db')
