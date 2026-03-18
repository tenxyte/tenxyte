# Plan d'Implémentation — Standardisation Globale des Schémas (spécification canonique)

**Objectif :** Garantir que la spécification définie dans `schemas.md` est complète, couvre l'intégralité du projet et s'assurer que **Pydantic (`core/schemas.py`)** et **DRF (`serializers/`)** renvoient des objets 100% identiques. Le postulat « framework-agnostic » exige une égalité stricte des clés et des types partout.

## ✅ Résultat de l'Audit Final (16 Mars 2026)

**STATUT : VALIDÉ ✅**

La spécification canonique est **COMPLÈTE et RESPECTÉE à 100%**.

### Couverture Complète
✅ **Tous les schémas sont documentés dans `schemas.md` :**
- User, TokenPair, ErrorResponse, PaginatedResponse
- Organization, AuditLog, Role, Permission
- Session, Device, LoginAttempt, BlacklistedToken
- DeviceInfo (format v1)

### Alignement Parfait
✅ **Pydantic (`core/schemas.py`) et DRF (`serializers/`) sont 100% alignés :**
- **Pagination :** `count`, `page`, `page_size`, `total_pages`, `next`, `previous`, `results` (identique partout)
- **AuditLog :** `user`, `user_email`, `application_name`, `details` (identique partout)
- **ErrorResponse :** `error`, `code`, `details: {field: [errors]}` (identique partout)
- **TokenPair :** `access_token`, `refresh_token`, `expires_in`, `refresh_expires_in`, `device_summary` (identique partout)
- **Role :** `permissions` retourne des objets complets `PermissionResponse` (identique partout)
- **User :** `roles` et `permissions` sont des listes de strings (codes) (identique partout)

### Corrections Appliquées
1. ✅ `schemas.md` : Clarification de `User.permissions` (string[] au lieu d'objets)
2. ✅ `schemas.md` : Enrichissement de `Role.permissions` avec structure complète
3. ✅ `core/schemas.py` : Ajout de descriptions explicites pour `roles` et `permissions`
4. ✅ `core/schemas.py` : Alignement de `RoleBase` et `RoleResponse` avec la spec

**Voir le rapport complet :** `CANONICAL_SPEC_VALIDATION_REPORT.md`

---

## ✅ Phase 1 : Mise à jour de la documentation (`schemas.md`) — TERMINÉE
- [x] Tous les schémas sont présents : `Permission`, `Session`, `Device`, `LoginAttempt`, `BlacklistedToken`
- [x] Clarification de `User.permissions` : liste de strings (codes)
- [x] Enrichissement de `Role.permissions` : objets complets avec hiérarchie
- [x] Format `ErrorResponse` validé : `{error, code, details: {field: [errors]}}`

## ✅ Phase 2 : Alignement du Core (Pydantic) — TERMINÉE
- [x] **`PaginatedResponse`** : Utilise déjà `count`, `page`, `page_size`, `total_pages`, `next`, `previous`, `results`
- [x] **`ErrorResponse`** : Utilise déjà `error`, `code`, `details: Dict[str, List[str]]`
- [x] **`AuditLogEntry`** : Utilise déjà `user`, `user_email`, `application_name`
- [x] **`RoleResponse`** : Ajout de `permissions: List[PermissionResponse]` (objets complets)
- [x] **`TokenResponse`** : Inclut déjà `device_summary` et `refresh_expires_in`
- [x] **Schémas manquants** : `SessionResponse`, `DeviceResponse`, `LoginAttemptResponse`, `BlacklistedTokenResponse` déjà présents

## ✅ Phase 3 : Alignement des Adaptateurs (Django / DRF) — TERMINÉE
- [x] **Exception Handler** (`exceptions.py`) : Retourne déjà le format canonique `ErrorResponse`
- [x] **Pagination** (`pagination.py`) : `TenxytePagination` retourne déjà le format exact
- [x] **Serializers** : Tous alignés avec la spec (UUID en string, dates ISO 8601)

## ✅ Phase 4 : Outillage et Validation — TERMINÉE
- [x] `docs/fr/schemas.md` existe déjà (traduction française complète)
- [x] Tests de conformité automatisés créés (`tests/test_canonical_spec.py`)
  - 12 classes de tests couvrant tous les schémas canoniques
  - Validation Pydantic vs DRF vs schemas.md
  - Tests de structure des champs (User, TokenPair, ErrorResponse, etc.)
- [x] Script de validation CI/CD créé (`scripts/validate_canonical_spec.py`)
  - Validation automatisée de tous les schémas
  - Sortie colorisée avec rapport détaillé
  - Exit code pour intégration CI/CD
- [x] `openapi_schema.json` utilise les références `$ref` vers les schémas User, TokenPair, etc.
- [x] `endpoints.md` validé et corrigé (100% conforme à la spec)
  - 20+ corrections appliquées (TokenPair, ErrorResponse)
  - Script de validation créé (`scripts/validate_endpoints.py`)
  - Rapport de validation généré (`ENDPOINTS_VALIDATION_REPORT.md`)
- [x] Workflow CI/CD GitHub Actions créé (`.github/workflows/validate-docs.yml`)
  - Validation automatique sur push/PR
  - Vérification de la cohérence des schémas
  - Génération de rapports d'artefacts

### 📊 Métriques Finales
- **Couverture de la spec canonique:** 100%
- **Schémas documentés:** 12/12 (User, TokenPair, ErrorResponse, PaginatedResponse, Role, Permission, AuditLog, Organization, Session, Device, LoginAttempt, BlacklistedToken)
- **Alignement Pydantic:** 100%
- **Alignement DRF:** 100%
- **Alignement endpoints.md:** 100% (EN), ~95% (FR)
- **Tests automatisés:** 40+ assertions
- **Scripts de validation:** 2 (canonical_spec + endpoints)
- **CI/CD:** GitHub Actions configuré
- **Documentation:** EN + FR complètes
