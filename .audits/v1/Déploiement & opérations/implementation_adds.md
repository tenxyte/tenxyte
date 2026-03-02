# Résumé des Implémentations — Déploiement & Opérations

Suite à l'audit de Déploiement et Opérations, voici les actions entreprises pour sécuriser le flux d'authentification et l'infrastructure sous-jacente :

## 1. Sécurité Applicative
* **Révocation de Tokens (Redis)** : Le modèle `BlacklistedToken` a été mis à jour pour interroger le cache en mémoire (Redis) en premier, permettant un contrôle d'accès instantané en O(1) sans solliciter la base de données.
* **Rate Limiting** : Des classes de rate limiting strictes (Throttle APIs) ont été implémentées et rattachées aux vues d'authentification sensibles (Register, Login, Refresh, Password Reset).
* **MFA Administrateur** : Le MFA (via Authenticator ou autres) est dorénavant imposé (mandatory) au niveau de l'API (dans `LoginEmailView` et `LoginPhoneView`) pour les utilisateurs à profil élevé (`is_staff`, `is_superuser`).

## 2. Infrastructure et CI/CD
* **GitHub Actions** : Le pipeline d'intégration `security.yml` a été révisé en profondeur pour remplacer Bandit par `Semgrep` (SAST amélioré).
* **Configuration Docker Sécurisée** : Création d'un `Dockerfile` de référence multi-étapes qui exécute l'application avec un compte `tenxyte` sans privilèges (non-root) et copie les requirements compilés de façon indépendante.
* **Docker Compose** : Un exemple `docker-compose.yml` robuste a été ajouté, incluant Redis, Postgres, des contraintes de réseaux fermés et des liveness-probes/health-checks stricts.

## 3. Observabilité et Résilience
* **Logging JSON Structuré** : La méthode `AuditLog.log()` produit dorénavant des logs formés en JSON standardisés avec l'horodatage, le niveau, l'IP, et le contexte.
* **Simulation de Monte en Charge** : Un premier script `k6_load_test.js` a été écrit pour tester les limites de l'API d'authentification sur le P95 en deçà de 500ms.
* **Procédures (Runbooks)** :
  * Déploiement (`docs/runbooks/deployment.md`)
  * Rollback (`docs/runbooks/rollback.md`)
  * Réponse aux Incidents (`docs/runbooks/incident_response.md`)