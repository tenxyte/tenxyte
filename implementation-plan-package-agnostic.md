# Plan d'implémentation : Make the package agnostic (Core Re-architecture)

## Phase 1 : Préparation et Architecture (Semaine 1)
L'objectif de cette phase est de préparer le terrain pour le refactoring en s'assurant que la structure du projet supporte la nouvelle approche agnostique.
*   **Créer la nouvelle structure de dossiers** : `src/tenxyte/core/`, `src/tenxyte/adapters/django/` et `src/tenxyte/ports/`.
*   **Système de configuration** : Remplacer les appels directs à `django.conf.settings` par une classe `Settings` agnostique (ex: utilisant `pydantic-settings` ou un parseur natif python de dictionnaire/variables d'environnement).
*   **Définition des interfaces (Ports)** : Créer les Abstract Base Classes (ABC) ou Protocoles pour les `UserRepository`, `OrganizationRepository`, `AuditLogRepository`, etc. (Issue 2).

## Phase 2 : Extraction du Core (Semaines 2-3)
C'est le travail principal. Déplacer toute la logique métier vers le nouveau dossier `core/` sans rien casser.
*   **Authentification et JWT** : Déplacer la génération, signature et validation des tokens vers `core/jwt/`.
*   **Sécurité (2FA, WebAuthn, Magic Links)** : Migrer la logique de génération de secrets, validation de codes TOTP et signatures WebAuthn pour quelles prennent de simples paramètres Python (strings, booléens) en entrée et en sortie. (Issue 1).
*   **Tests unitaires du Core** : Créer des tests purs (avec `pytest` sans plugin Django) pour toutes les fonctions de `core/`. (Issue 4).

## Phase 3 : Création de l'Adaptateur Django (Semaines 3-4)
Maintenant que le coeur est pur, il faut s'assurer que l'intégration Django (qui est actuellement l'implémentation par défaut) continue de fonctionner exactement comme avant.
*   **Implémentation des Repositories Django** : Créer les classes (`DjangoUserRepository`, etc.) qui héritent des interfaces définies en Phase 1 et utilisent l'ORM de Django en sous-marin. (Issue 3).
*   **Refonte des Vues et Middlewares** : Modifier les vues et sérialiseurs existants pour qu'ils instancient le Core de Tenxyte avec les Repositories Django et transmettent les requêtes.
*   **Tests d'intégration** : Exécuter l'ancienne suite de tests (qui devient une suite de tests d'intégration) pour valider la non-régression. (Issue 4).

## Phase 4 : Preuve de Concept FastAPI & Documentation (Semaine 5)
Prouver que le package est réellement agnostique.
*   **Adaptateur FastAPI** : Créer un petit package/module `tenxyte.adapters.fastapi` avec quelques routes (Login, Register) pour démontrer la flexibilité de l'architecture. (Issue 5).
*   **Mise à jour de la documentation** : Mettre à jour le README et générer un guide de migration de la `0.9.x` vers la `1.X.X` (Agnostic). (Issue 6).
*   **Release Candidate** : Publier une version `1.0.0-rc.1` sur PyPI.
