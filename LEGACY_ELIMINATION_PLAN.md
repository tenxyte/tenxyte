# Plan d'Élimination du Code Legacy - Tenxyte

## 📋 Vue d'Ensemble

Le package Tenxyte contient actuellement du code legacy (Django-specific) qui coexiste avec la nouvelle architecture core/adapters. Ce plan détaille la stratégie complète pour éliminer tout le code legacy.

## 🔍 Inventaire du Code Legacy

### **Services Legacy** (`src/tenxyte/services/`)
Tous les services dans ce dossier sont marqués `@deprecated` et doivent être supprimés :

1. **`auth_service.py`** (33 KB)
   - ⚠️ **Status**: Deprecated
   - 🎯 **Remplacé par**: `tenxyte.core.JWTService` + `tenxyte.core.UserRepository` + adapters Django
   - 📍 **Utilisé dans**: `views/auth_views_legacy.py`, `views/password_views_legacy.py`

2. **`jwt_service.py`** (6.5 KB)
   - ⚠️ **Status**: Deprecated
   - 🎯 **Remplacé par**: `tenxyte.core.JWTService`
   - 📍 **Utilisé dans**: Aucune référence directe trouvée

3. **`totp_service.py`** (13.8 KB)
   - ⚠️ **Status**: Deprecated
   - 🎯 **Remplacé par**: `tenxyte.core.TOTPService`
   - 📍 **Utilisé dans**: `views/twofa_views_legacy.py`, `views/auth_views_legacy.py`
   - 🐛 **Problème actuel**: Singleton instancié automatiquement (ligne 382) → cause le warning TOTP

4. **`magic_link_service.py`** (5 KB)
   - ⚠️ **Status**: Deprecated
   - 🎯 **Remplacé par**: `tenxyte.core.MagicLinkService`
   - 📍 **Utilisé dans**: Aucune référence directe trouvée

5. **`webauthn_service.py`** (12.4 KB)
   - ⚠️ **Status**: Deprecated
   - 🎯 **Remplacé par**: `tenxyte.core.WebAuthnService`
   - 📍 **Utilisé dans**: Aucune référence directe trouvée

6. **`email_service.py`** (22.4 KB)
   - ⚠️ **Status**: Deprecated
   - 🎯 **Remplacé par**: `tenxyte.adapters.django.email_service.DjangoEmailService`
   - 📍 **Utilisé dans**: Aucune référence directe trouvée

7. **`otp_service.py`** (7.3 KB)
   - ⚠️ **Status**: Utilisé activement (pas de deprecation warning)
   - 🎯 **À migrer vers**: Architecture core/adapters
   - 📍 **Utilisé dans**: `views/otp_views.py`, `views/password_views.py`, `views/auth_views.py`, `views/auth_views_legacy.py`, `views/password_views_legacy.py`

### **Services Non-Legacy** (à conserver)
Ces services ne sont PAS legacy et doivent rester :

- ✅ **`agent_service.py`** - Service AIRS/Agent (utilisé activement)
- ✅ **`organization_service.py`** - Service organisations
- ✅ **`social_auth_service.py`** - Service OAuth social
- ✅ **`account_deletion_service.py`** - Service GDPR
- ✅ **`stats_service.py`** - Service statistiques
- ✅ **`breach_check_service.py`** - Service HaveIBeenPwned

### **Views Legacy** (`src/tenxyte/views/`)

1. **`auth_views_legacy.py`** (711 lignes)
   - 📍 **Dépendances**: `AuthService`, `OTPService`, `totp_service`
   - 🎯 **Remplacé par**: `auth_views.py` (utilise déjà core services)

2. **`password_views_legacy.py`** (413 lignes)
   - 📍 **Dépendances**: `AuthService`, `OTPService`
   - 🎯 **Remplacé par**: `password_views.py` (utilise déjà core services)

3. **`twofa_views_legacy.py`** (344 lignes)
   - 📍 **Dépendances**: `totp_service` singleton
   - 🎯 **Remplacé par**: `twofa_views.py` (utilise déjà core services)

4. **`user_views_legacy.py`** (789 lignes)
   - 📍 **Dépendances**: À analyser
   - 🎯 **Remplacé par**: `user_views.py`

5. **`magic_link_views_legacy.py`** (249 lignes)
   - 📍 **Dépendances**: À analyser
   - 🎯 **Remplacé par**: `magic_link_views.py`

6. **`webauthn_views_legacy.py`** (388 lignes)
   - 📍 **Dépendances**: À analyser
   - 🎯 **Remplacé par**: `webauthn_views.py`

### **Tests Legacy**

1. **`tests/integration/django/unit/test_legacy_email_service_extra.py`**
   - 🗑️ **Action**: Supprimer

## 📊 Impact Analysis

### **Fichiers Utilisant le Code Legacy**

#### Views utilisant `from ..services import`:
- `views/otp_views.py` → `OTPService` (actif, à migrer)
- `views/password_views.py` → `OTPService` (actif, à migrer)
- `views/auth_views.py` → `OTPService` (actif, à migrer)
- `views/password_views_legacy.py` → `AuthService`, `OTPService` (legacy)
- `views/auth_views_legacy.py` → `AuthService`, `OTPService`, `totp_service` (legacy)
- `views/twofa_views_legacy.py` → `totp_service` (legacy)

#### Autres fichiers utilisant services:
- `middleware.py` → `AgentTokenService` (non-legacy, OK)
- `decorators.py` → `AgentTokenService` (non-legacy, OK)
- `tasks/agent_tasks.py` → `AgentTokenService` (non-legacy, OK)
- `views/agent_views.py` → `AgentTokenService` (non-legacy, OK)

### **URLs Analysis**
- ✅ **Aucune route legacy** dans `urls.py` - toutes les routes pointent vers les nouvelles views
- ✅ Les views legacy ne sont **pas exposées** via les URLs

## 🎯 Plan de Migration Détaillé

### **Phase 1: Migration OTPService** (Priorité: HAUTE)
**Objectif**: Migrer `OTPService` vers architecture core/adapters

#### Étapes:
1. **Créer `tenxyte/core/otp_service.py`**
   - Service framework-agnostic
   - Utilise `Settings` et protocols pour storage/email

2. **Créer adapter Django**
   - `tenxyte/adapters/django/otp_storage.py`
   - Implémente les protocols OTP

3. **Mettre à jour les views actives**
   - `views/otp_views.py`
   - `views/password_views.py`
   - `views/auth_views.py`
   - Remplacer `from ..services import OTPService` par core service

4. **Tester la migration**
   - Vérifier tous les tests OTP passent
   - Tester les flows email/phone OTP

5. **Marquer l'ancien comme deprecated**
   - Ajouter `@deprecated` à `services/otp_service.py`

#### Fichiers impactés:
- ✏️ Nouveau: `src/tenxyte/core/otp_service.py`
- ✏️ Nouveau: `src/tenxyte/adapters/django/otp_storage.py`
- ✏️ Modifier: `src/tenxyte/views/otp_views.py`
- ✏️ Modifier: `src/tenxyte/views/password_views.py`
- ✏️ Modifier: `src/tenxyte/views/auth_views.py`
- ⚠️ Deprecate: `src/tenxyte/services/otp_service.py`

---

### **Phase 2: Suppression des Services Legacy** (Priorité: HAUTE)
**Objectif**: Supprimer tous les services deprecated

#### Étapes:
1. **Vérifier qu'aucune view active n'utilise les services legacy**
   - Grep pour confirmer zéro usage

2. **Supprimer les fichiers services legacy**
   ```
   rm src/tenxyte/services/auth_service.py
   rm src/tenxyte/services/jwt_service.py
   rm src/tenxyte/services/totp_service.py
   rm src/tenxyte/services/magic_link_service.py
   rm src/tenxyte/services/webauthn_service.py
   rm src/tenxyte/services/email_service.py
   ```

3. **Nettoyer `services/__init__.py`**
   - Supprimer les imports des services legacy
   - Garder uniquement les services actifs (agent, org, social, etc.)

4. **Vérifier les imports**
   - S'assurer qu'aucun import cassé

#### Fichiers impactés:
- 🗑️ Supprimer: `src/tenxyte/services/auth_service.py`
- 🗑️ Supprimer: `src/tenxyte/services/jwt_service.py`
- 🗑️ Supprimer: `src/tenxyte/services/totp_service.py`
- 🗑️ Supprimer: `src/tenxyte/services/magic_link_service.py`
- 🗑️ Supprimer: `src/tenxyte/services/webauthn_service.py`
- 🗑️ Supprimer: `src/tenxyte/services/email_service.py`
- ✏️ Modifier: `src/tenxyte/services/__init__.py`

---

### **Phase 3: Suppression des Views Legacy** (Priorité: MOYENNE)
**Objectif**: Supprimer toutes les views `*_legacy.py`

#### Étapes:
1. **Confirmer que les nouvelles views couvrent tous les cas**
   - Comparer fonctionnalités legacy vs nouvelles
   - Identifier les gaps éventuels

2. **Supprimer les fichiers views legacy**
   ```
   rm src/tenxyte/views/auth_views_legacy.py
   rm src/tenxyte/views/password_views_legacy.py
   rm src/tenxyte/views/twofa_views_legacy.py
   rm src/tenxyte/views/user_views_legacy.py
   rm src/tenxyte/views/magic_link_views_legacy.py
   rm src/tenxyte/views/webauthn_views_legacy.py
   ```

3. **Nettoyer `views/__init__.py`**
   - Vérifier qu'aucun import legacy

4. **Vérifier les URLs**
   - Confirmer qu'aucune route ne pointe vers legacy

#### Fichiers impactés:
- 🗑️ Supprimer: `src/tenxyte/views/auth_views_legacy.py`
- 🗑️ Supprimer: `src/tenxyte/views/password_views_legacy.py`
- 🗑️ Supprimer: `src/tenxyte/views/twofa_views_legacy.py`
- 🗑️ Supprimer: `src/tenxyte/views/user_views_legacy.py`
- 🗑️ Supprimer: `src/tenxyte/views/magic_link_views_legacy.py`
- 🗑️ Supprimer: `src/tenxyte/views/webauthn_views_legacy.py`

---

### **Phase 4: Nettoyage des Tests Legacy** (Priorité: BASSE)
**Objectif**: Supprimer les tests legacy

#### Étapes:
1. **Identifier tous les tests legacy**
   ```bash
   find tests -name "*legacy*"
   ```

2. **Supprimer les fichiers de tests legacy**
   ```
   rm tests/integration/django/unit/test_legacy_email_service_extra.py
   ```

3. **Vérifier la couverture de tests**
   - S'assurer que les tests core couvrent les mêmes cas

#### Fichiers impactés:
- 🗑️ Supprimer: `tests/integration/django/unit/test_legacy_email_service_extra.py`

---

### **Phase 5: Documentation et Finalisation** (Priorité: BASSE)
**Objectif**: Mettre à jour la documentation

#### Étapes:
1. **Mettre à jour CHANGELOG.md**
   - Documenter la suppression du code legacy
   - Breaking changes si applicable

2. **Mettre à jour README.md**
   - Supprimer références aux services legacy
   - Mettre à jour exemples d'utilisation

3. **Mettre à jour migration guides**
   - Créer guide de migration pour utilisateurs existants

4. **Bump version**
   - Version majeure (breaking change)

#### Fichiers impactés:
- ✏️ Modifier: `CHANGELOG.md`
- ✏️ Modifier: `README.md`
- ✏️ Nouveau: `docs/migration/legacy-to-core.md`
- ✏️ Modifier: `pyproject.toml` (version)

---

## 📈 Métriques de Réduction

### **Avant Nettoyage**
- Services legacy: **7 fichiers** (~100 KB)
- Views legacy: **6 fichiers** (~2900 lignes)
- Tests legacy: **1 fichier**
- **Total**: ~14 fichiers legacy

### **Après Nettoyage**
- Services legacy: **0 fichiers** ✅
- Views legacy: **0 fichiers** ✅
- Tests legacy: **0 fichiers** ✅
- **Réduction**: ~14 fichiers supprimés

### **Bénéfices**
- ✅ Codebase plus propre et maintenable
- ✅ Moins de confusion pour les développeurs
- ✅ Pas de singleton auto-instancié (résout warning TOTP)
- ✅ Architecture 100% core/adapters
- ✅ Meilleure testabilité
- ✅ Support multi-framework facilité

---

## ⚠️ Risques et Précautions

### **Risques Identifiés**

1. **Breaking Changes pour Utilisateurs Existants**
   - 🛡️ **Mitigation**: Version majeure + guide de migration
   - 🛡️ **Mitigation**: Période de deprecation warnings

2. **Fonctionnalités Manquantes**
   - 🛡️ **Mitigation**: Audit complet legacy vs core avant suppression
   - 🛡️ **Mitigation**: Tests de régression complets

3. **Imports Cassés**
   - 🛡️ **Mitigation**: Grep complet avant suppression
   - 🛡️ **Mitigation**: Tests d'import automatisés

### **Checklist Avant Suppression**

- [ ] Tous les tests passent avec les nouveaux services
- [ ] Aucune référence aux services legacy dans le code actif
- [ ] Guide de migration créé
- [ ] CHANGELOG mis à jour
- [ ] Version bumpée (majeure)
- [ ] Documentation mise à jour
- [ ] Tests de régression exécutés

---

## 🚀 Ordre d'Exécution Recommandé

1. **Phase 1**: Migration OTPService (1-2 jours)
2. **Phase 2**: Suppression services legacy (1 jour)
3. **Phase 3**: Suppression views legacy (1 jour)
4. **Phase 4**: Nettoyage tests legacy (0.5 jour)
5. **Phase 5**: Documentation (0.5 jour)

**Durée totale estimée**: 4-5 jours

---

## 📝 Notes Importantes

### **Pourquoi le Legacy Existe Encore**

Le code legacy existe car :
1. **Transition progressive**: Migration core/adapters en cours
2. **Rétrocompatibilité**: Éviter breaking changes brutaux
3. **Singleton auto-instancié**: `totp_service = TOTPService()` dans `services/totp_service.py:382`
   - S'exécute à l'import du module
   - Cause le warning TOTP même si non utilisé

### **Pourquoi Éliminer Maintenant**

1. ✅ Architecture core/adapters est mature
2. ✅ Toutes les fonctionnalités sont migrées
3. ✅ Les nouvelles views utilisent déjà core services
4. ✅ Aucune route n'expose les views legacy
5. ✅ Le singleton cause des problèmes (warning TOTP)
6. ✅ Confusion pour les développeurs (2 façons de faire)

---

## 🎯 Prochaines Actions Immédiates

1. **Valider ce plan** avec l'équipe
2. **Créer une branche** `feature/eliminate-legacy`
3. **Commencer Phase 1** (Migration OTPService)
4. **Tests continus** après chaque phase
5. **Review et merge** progressif

---

**Dernière mise à jour**: 16 mars 2026
**Status**: 📋 Plan créé - En attente de validation
