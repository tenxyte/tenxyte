# Guide de Test pour Tenxyte

## Installation des Dépendances de Test

```bash
pip install -e ".[dev]"
```

Ceci installera :
- **pytest** : Le framework de test principal
- **pytest-django** : Intégration Django
- **pytest-cov** : Génération de rapports de couverture
- **pytest-asyncio** : Support pour les tests asynchrones
- **black, ruff, mypy** : Outils de linting et de vérification de types

## Exécution des Tests

### Tous les Tests

```bash
pytest
```

### Tests avec Rapport de Couverture

```bash
pytest --cov=tenxyte --cov-report=html --cov-report=term
```

Le rapport HTML sera généré dans `htmlcov/index.html`. Le seuil de couverture de référence du projet est de **90%** (configuré dans `pyproject.toml`).

### Tests Spécifiques

```bash
# Répertoire de test spécifique
pytest tests/core/

# Fichier de test spécifique
pytest tests/core/test_core_jwt_service.py

# Classe de test spécifique
pytest tests/core/test_core_jwt_service.py::TestJWTService

# Test spécifique
pytest tests/core/test_core_jwt_service.py::TestJWTService::test_generate_access_token

# Tests correspondant à un motif (pattern)
pytest tests/ -k "password"
```

### Options Avancées

```bash
pytest -v              # Mode verbeux
pytest -s              # Affiche la sortie de print()
pytest --pdb           # Débogage en cas d'échec
pytest -n auto         # Tests en parallèle (nécessite pytest-xdist)
pytest --durations=10  # Affiche les 10 tests les plus lents
pytest --lf            # Réexécute uniquement les derniers échecs
```

## Structure des Tests

Tenxyte organise les tests par catégorie :

```
tests/
├── core/                       # Tests des services Core (JWT, Cache, E-mail, TOTP, Sessions, etc.)
│   └── conftest.py             # Fixtures de test Core (mocks, sans DB)
├── integration/
│   ├── django/                 # Tests d'intégration de l'adaptateur Django (Modèles, Signaux, Vues)
│   │   ├── conftest.py         # Fixtures Django partagées (DB, clients API, utilisateurs)
│   │   ├── multidb/            # Tests du support multi-bases de données
│   │   ├── test_dashboard.py   # Tests de la vue tableau de bord
│   │   └── settings.py         # Paramètres de test Django
│   └── fastapi/                # Tests de l'adaptateur FastAPI (Modèles, Répertoires, Routeurs)
└── test_canonical_spec.py      # Validation de la spécification canonique
```

## Fixtures Disponibles

Définies dans `tests/integration/django/conftest.py` :

- `api_client` : Client API standard REST Framework
- `app_api_client` : Client avec les en-têtes `X-Access-Key` / `X-Access-Secret`
- `authenticated_client` : Client avec JWT + En-têtes d'application
- `authenticated_admin_client` : Client administrateur avec JWT + En-têtes d'application
- `application` : Instance du modèle Application de test
- `user` : Utilisateur de test standard (test@example.com)
- `admin_user` : Utilisateur avec le rôle "admin"
- `user_with_phone` : Utilisateur avec numéro de téléphone (pour les tests OTP)
- `user_with_2fa` : Utilisateur avec TOTP activé
- `permission`/`role` : Instances des modèles RBAC de test

## Catégories de Tests

### 1. Tests Core (`tests/core/`)
Tests de la logique de la couche de service Core (JWT, OTP, TOTP, Cache, E-mail, Session, Magic Link, WebAuthn). Rapides, isolés et agnostiques au framework. Inclut également des tests spécifiques à la sécurité (atténuation des attaques temporelles).

### 2. Tests d'Intégration (`tests/integration/`)

#### Django (`tests/integration/django/`)
Test des composants de l'adaptateur Django : interactions avec les modèles, contraintes de base de données, signaux, vues, sérialiseurs et tableau de bord.

#### FastAPI (`tests/integration/fastapi/`)
Test des composants de l'adaptateur FastAPI : modèles Pydantic, répertoires (repositories) et routeurs.

### 3. Tests Multi-DB (`tests/integration/django/multidb/`)
Garantit la compatibilité avec plusieurs backends :
```bash
pytest tests/integration/django/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.integration.django.multidb.settings_sqlite"
pytest tests/integration/django/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.integration.django.multidb.settings_pgsql"
pytest tests/integration/django/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.integration.django.multidb.settings_mongodb"
```

## Couverture Attendue

Tenxyte impose un **seuil de couverture de 90%**. Pour vérifier la couverture d'un module spécifique :
```bash
pytest --cov=tenxyte.core.jwt_service tests/core/test_core_jwt_service.py
```

## Meilleures Pratiques

1. **Isolation** : Ne laissez jamais les tests dépendre les uns des autres. Utilisez la fixture `db` pour l'isolation de la base de données.
2. **Mocking** : Simulez (mock) les services externes (E-mail, passerelles SMS) sauf si vous testez spécifiquement les backends.
3. **Nommage** : Utilisez des noms descriptifs : `test_<fonctionnalité>_<scénario>_<résultat_attendu>`.
4. **Cas Limites (Edge Cases)** : Testez toujours les entrées vides, les formats invalides et les valeurs aux limites.

## Dépannage

### `ImportError: No module named 'tenxyte'`
Assurez-vous d'avoir installé le package en mode éditable : `pip install -e .`

### `Database errors`
Les tests utilisent par défaut une base de données SQLite en mémoire (`--create-db --reuse-db` sont activés dans `pytest.ini`). Pour d'autres bases de données, assurez-vous que les variables d'environnement `DB_HOST`, `DB_USER`, etc., sont correctement configurées.

### `Django settings not configured`
Vérifiez que `DJANGO_SETTINGS_MODULE` pointe vers `tests.settings` ou un fichier de paramètres valide.
