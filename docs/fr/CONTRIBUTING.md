# Contribution

Merci de votre intérêt pour la contribution à Tenxyte !

## Sommaire

- [Configuration du développement](#configuration-du-développement)
- [Exécution des tests](#exécution-des-tests)
- [Structure des tests](#structure-des-tests)
- [Style de code](#style-de-code)
- [Effectuer des changements](#effectuer-des-changements)
- [Directives pour les Pull Requests](#directives-pour-les-pull-requests)
- [Documentation](#documentation)
- [Signaler des problèmes](#signaler-des-problèmes)
- [Versions supportées](#versions-supportées)
- [Code de conduite](#code-of-conduct)
- [Des questions ?](#questions)

---

## Configuration du développement

### 1. Fork et Clone

```bash
git clone https://github.com/VOTRE_NOM_UTILISATEUR/tenxyte.git
cd tenxyte
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
```

### 3. Installer les dépendances

```bash
pip install -e ".[dev]"
```

Cela installe le package en mode éditable avec tous les outils de développement :
- **pytest** + pytest-django + pytest-asyncio — framework de test
- **pytest-cov** — rapports de couverture
- **black** — formateur de code
- **ruff** — linter
- **mypy** — vérification de type

### 4. Exécuter les tests

```bash
pytest
```

---

## Exécution des tests

### Tous les tests

```bash
pytest
```

### Tests spécifiques

```bash
# Par répertoire
pytest tests/unit/

# Par fichier
pytest tests/unit/test_jwt.py

# Par classe
pytest tests/unit/test_validators.py::TestPasswordValidator

# Par nom
pytest tests/unit/test_jwt.py::TestJWTService::test_generate_access_token

# Par mot-clé
pytest tests/ -k "password"
```

### Avec couverture

```bash
pytest --cov=tenxyte --cov-report=html --cov-report=term
```

Le rapport HTML est généré dans `htmlcov/index.html`. Le projet impose un **seuil de couverture de 90 %** (configuré dans `pyproject.toml`).

### Cibler un module spécifique

```bash
pytest --cov=tenxyte.services.auth_service tests/unit/test_auth_service.py
```

### Options avancées

```bash
pytest -v              # Sortie verbeuse
pytest -s              # Afficher la sortie de print()
pytest --pdb           # Débogage en cas d'échec
pytest --durations=10  # Afficher les 10 tests les plus lents
pytest --lf            # Réexécuter uniquement les derniers échecs
```

---

## Structure des tests

```
tests/
├── unit/                 # Services Core, Validateurs — rapides et isolés
├── integration/
│   ├── django/           # Adaptateur Django : Modèles, Signaux, Vues, contraintes DB
│   └── fastapi/          # Adaptateur FastAPI : Modèles, Repositories, Routeurs
├── security/             # Attaques temporelles, détection de brèches, limitation de débit
├── multidb/              # Compatibilité des backends multi-bases de données
├── conftest.py           # Fixtures partagées
├── settings.py           # Paramètres de test Django
└── test_dashboard.py     # Tests de la vue Dashboard
```

### Tests multi-bases de données

```bash
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_sqlite"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_pgsql"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_mongodb"
```

---

## Style de code

Nous utilisons **black** pour le formatage et **ruff** pour le peluchage (linting), tous deux configurés avec une longueur de ligne maximale de **120 caractères**.

### Formater le code

```bash
black src/tenxyte/
```

### Vérifier le formatage (mode CI)

```bash
black --check src/tenxyte/
```

### Peluchage (Lint)

```bash
ruff check src/tenxyte/
```

### Vérification de type

```bash
mypy src/tenxyte/
```

### Configuration

Voir `pyproject.toml` pour la configuration de black et ruff :

```toml
[tool.black]
line-length = 120
target-version = ["py310", "py311", "py312"]

[tool.ruff]
line-length = 120
target-version = "py310"
```

---

## Effectuer des changements

### 1. Créer une branche

```bash
git checkout -b feature/nom-de-votre-fonctionnalite
```

### 2. Effectuer vos changements

- Écrivez un code clair et documenté
- Suivez les modèles et conventions existants
- Ajoutez des tests pour les nouvelles fonctionnalités
- Mettez à jour la documentation si nécessaire

### 3. Exécuter les tests et le peluchage

```bash
pytest
black --check src/tenxyte/
ruff check src/tenxyte/
```

### 4. Commiter vos changements

Écrivez des messages de commit clairs :

```bash
git commit -m "Ajout du support pour les claims de jeton personnalisées"
```

### 5. Pousser et créer une Pull Request

```bash
git push origin feature/nom-de-votre-fonctionnalite
```

Ensuite, ouvrez une pull request sur GitHub ciblant la branche `main` ou `develop`.

---

## Directives pour les Pull Requests

### Vérifications CI

Les pull requests sont automatiquement testées par GitHub Actions sur une matrice de :
- **Python** : 3.10, 3.11, 3.12, 3.13
- **Django** : 4.2, 5.0, 5.1, 5.2, 6.0
- **FastAPI** : dernière version stable

La couverture est rapportée via Codecov sur Python 3.12 / Django 6.0.

### Ce que nous recherchons

- [ ] Les tests passent sur toutes les versions Python/Django supportées
- [ ] Le code est formaté avec black (`black --check` passe)
- [ ] Aucune erreur de peluchage (`ruff check` passe)
- [ ] Les nouvelles fonctionnalités incluent des tests
- [ ] La couverture reste supérieure à 90 %
- [ ] La documentation est mise à jour si nécessaire
- [ ] Les messages de commit sont clairs et descriptifs

### Ce qu'il faut inclure

- Description claire du changement
- Lien vers l'issue liée (le cas échéant)
- Captures d'écran pour les changements d'interface utilisateur
- Notes de migration pour les changements majeurs (breaking changes)

---

## Documentation

La documentation est organisée dans le répertoire `docs/` :

| Fichier | Contenu |
|---------|---------|
| `quickstart.md` | Guide de démarrage rapide |
| `settings.md` | Toutes les options de configuration |
| `endpoints.md` | Référence des points de terminaison de l'API REST |
| `rbac.md` | Contrôle d'accès basé sur les rôles |
| `airs.md` | Responsabilité et Sécurité de l'IA |
| `organizations.md` | Organisations multi-locataires |
| `security.md` | Architecture de sécurité |
| `schemas.md` | Schémas de base de données |
| `architecture.md` | Architecture Core & Adapters |
| `custom_adapters.md` | Création d'adaptateurs personnalisés |
| `TESTING.md` | Guide de test |
| `MIGRATION_GUIDE.md` | Migration depuis d'autres packages |
| `troubleshooting.md` | Problèmes courants et solutions |

Lors de l'ajout ou de la modification d'une fonctionnalité, mettez à jour le ou les fichiers de documentation correspondants.

> [!IMPORTANT]
> ### Cohérence des schémas (tous les modèles)
>
> Tenxyte est **agnostique au framework**. Chaque objet de réponse (`User`, `Organization`, `Role`, `TokenPair`, `AuditLog`, etc.) **doit être identique** sur tous les adaptateurs (Django, FastAPI, personnalisé). C'est une valeur fondamentale du projet.
>
> **Règles :**
> - Les schémas canoniques sont définis dans [`schemas.md`](schemas.md) et dans `tenxyte.core.schemas` ([source](../../src/tenxyte/core/schemas.py)). Toute modification de modèle doit commencer par ces fichiers de référence.
> - **Pas de champs alias.** N'ajoutez pas de champs qui dupliquent des champs existants (ex : `is_verified` comme alias de `is_email_verified`, ou `date_joined` comme alias de `created_at`). Chaque information ne doit apparaître qu'une seule fois.
> - **Pas d'état dans les sous-objets de préférences.** Les objets comme `preferences` contiennent uniquement des préférences utilisateur. L'état des fonctionnalités (ex : `is_2fa_enabled`) appartient à des champs dédiés de premier niveau.
> - Lors de la modification d'un modèle, mettez à jour **toutes** les occurrences : `tenxyte.core.schemas.py`, les sérialiseurs adaptateurs (`auth_serializers.py`, etc.), `schemas.md` (EN + FR), et chaque exemple JSON concerné dans `endpoints.md` (EN + FR).
> - **Obligation de test :** après toute modification de modèle, tous les tests impliquant le modèle modifié doivent être repris et **doivent passer sans erreur**. Aucune PR modifiant un schéma ne sera acceptée si des tests échouent.

---

## Signaler des problèmes

### Rapports de bugs

Incluez :
- Version de Tenxyte (`pip show tenxyte`)
- Version de Python
- Version de Django
- Version de Django REST Framework
- Étapes pour reproduire
- Comportement attendu vs comportement réel
- Trace complète (si applicable)

### Demandes de fonctionnalités

- Décrivez le cas d'utilisation
- Expliquez pourquoi cela ne peut pas être fait avec les fonctionnalités actuelles
- Proposez une solution si vous en avez une

---

## Versions supportées

| Composant | Versions |
|-----------|----------|
| Python | 3.10, 3.11, 3.12, 3.13 |
| Django | 4.2, 5.0, 5.1, 5.2, 6.0 |
| DRF | ≥ 3.16 |
| FastAPI | Dernière version stable |

---

## Code de conduite

- Soyez respectueux et inclusif
- Concentrez-vous sur des commentaires constructifs
- Aidez les autres à apprendre et à grandir

---

## Des questions ?

Ouvrez une [Issue GitHub](https://github.com/tenxyte/tenxyte/issues) pour les rapports de bugs et les demandes de fonctionnalités, ou lancez une [Discussion GitHub](https://github.com/tenxyte/tenxyte/discussions) pour les questions générales.
