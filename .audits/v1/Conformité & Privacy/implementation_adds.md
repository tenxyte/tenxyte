# Implémentations Audit Conformité & Privacy (v0.9.1.7)

Les recommandations de l'audit relatif à la protection des données et à la conformité RGPD ont été implémentées.

## Changements Majeurs

### 1. Sécurité & Authentification
- **Hachage des Tokens** : Les `refresh_tokens` et `AgentToken` sont hachés en base via SHA-256 (implémenté précédemment, vérifié).
- **Chiffrement TOTP** : Les secrets TOTP sont chiffrés au repos via `django-cryptography`.
- **Politique Social Auth** : 
    - Ajout de `TENXYTE_SOCIAL_REQUIRE_VERIFIED_EMAIL` (défaut: True) pour refuser les logins OAuth avec email non-vérifié.
    - Interdiction de la fusion automatique de comptes avec des emails sociaux non-vérifiés (Prévention du account hijacking).
- **Droit à la Restriction** : Ajout du champ `is_restricted` au modèle `User` (Art. 18 RGPD).

### 2. Droits RGPD & Portabilité
- **Export de Données Étendu** : La vue `export-user-data` inclut désormais :
    - Sessions actives et révoquées.
    - Connexions sociales.
    - Historique des tentatives de login.
    - Tokens d'agents (AIRS).
    - Suppression de la limite arbitraire de 100 logs d'audit.
- **Effacement (Droit à l'oubli)** : 
    - La suppression de compte (soft delete) révoque désormais explicitement TOUS les tokens (Refresh et Agent) associés à l'utilisateur.
    - Anonymisation via token sécurisé unique.

### 3. Rétention des Données
- **Nettoyage Automatique** : La commande `tenxyte_cleanup` a été étendue pour purger les actions d'agents expirées (`AgentPendingAction`) selon `TENXYTE_AGENT_ACTION_RETENTION_DAYS`.
- **Configuration** : Les périodes de rétention pour les logs d'audit et tentatives de login sont configurables.

## Documentation
- Création de `DPA_OBLIGATIONS.md` détaillant les responsabilités concernant les sous-traitants tiers (Google, GitHub, etc.) selon l'Art. 28 RGPD.

---
*Date d'implémentation : 2026-03-02*
