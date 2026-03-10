# Milestone: Make the package agnostic (Core Re-architecture)

- [ ] **Issue 1 : Extraire la logique métier (Core) hors de Django**
  - [ ] Sub-issue 1.1 : Extraire la génération et la validation des tokens JWT dans un module pur Python.
  - [ ] Sub-issue 1.2 : Extraire la logique de validation et de génération (TOTP, WebAuthn/Passkeys, Magic Links) pour qu'elle ne dépende que de variables simples (dictionnaires, dataclasses).
  - [ ] Sub-issue 1.3 : Remplacer la dépendance à `django.conf.settings` par un système de configuration propre au package (ex: `tenxyte.config.Settings`).

- [ ] **Issue 2 : Créer des interfaces d'abstraction (Ports/Repositories) pour la Base de données**
  - [ ] Sub-issue 2.1 : Définir les interfaces de gestion des utilisateurs (`UserRepository`, `AbstractUser`).
  - [ ] Sub-issue 2.2 : Définir les interfaces pour le RBAC (Role-Based Access Control) et les organisations B2B (`OrganizationRepository`, `RoleRepository`).
  - [ ] Sub-issue 2.3 : Définir une interface pour générer et écrire les Audit Logs sans dépendre du modèle Django.

- [ ] **Issue 3 : Isoler l'implémentation Django dans un module "Adapter"**
  - [ ] Sub-issue 3.1 : Déplacer et renommer les Vues (Views) et Sérialiseurs (Serializers) actuels vers le dossier adaptateur de Django.
  - [ ] Sub-issue 3.2 : Implémenter les Repositories définis dans l'Issue 2 en utilisant l'ORM Django (ex: `DjangoUserRepository`).
  - [ ] Sub-issue 3.3 : Vérifier que les points d'entrées actuels de l'API sont rétrocompatibles pour les utilisateurs existants.

- [ ] **Issue 4 : Refonte de la suite de Tests**
  - [ ] Sub-issue 4.1 : Mettre en place des tests unitaires purs pour le `tenxyte.core` (sans `pytest-django`).
  - [ ] Sub-issue 4.2 : Déplacer les tests actuels (qui dépendent de la BDD et de l'API) dans un sous-dossier `tests/integration/django/`.

- [ ] **Issue 5 : [Preuve de concept] Développer un deuxième adaptateur (FastAPI)**
  - [ ] Sub-issue 5.1 : Créer un modèle de données abstrait (ex: Pydantic ou SQLAlchemy) pour représenter les utilisateurs dans le cadre de FastAPI.
  - [ ] Sub-issue 5.2 : Implémenter les `Repositories` pour l'adaptateur FastAPI.
  - [ ] Sub-issue 5.3 : Exposer 1 ou 2 routes (ex: Login, Magic Link) via FastAPI + le "Core" de Tenxyte.

- [ ] **Issue 6 : Mettre à jour la documentation (Readme & Docs)**
  - [ ] Sub-issue 6.1 : Mettre à jour le `README.md` (changer "Complete Django authentication" par "Agnostic Python Authentication").
  - [ ] Sub-issue 6.2 : Ajouter une section à la documentation expliquant l'architecture (Core vs Adapters).
  - [ ] Sub-issue 6.3 : Rédiger un "Migration Guide" pour les projets Django actuels afin qu'ils effectuent la transition de la v0.9 à la v1.0 en douceur.
