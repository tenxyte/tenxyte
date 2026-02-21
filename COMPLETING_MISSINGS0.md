# Tenxyte — Analyse des Lacunes API & Plan d'Implémentation

## 1. État des Lieux Actuel

### Endpoints existants (41 routes)

| Module | Endpoints existants | CRUD complet ? | Filtres ? | Pagination ? |
|---|---|:---:|:---:|:---:|
| **Auth** | `register`, `login/email`, `login/phone`, `google`, `refresh`, `logout`, `logout/all` | ✅ (auth flow) | ❌ | ❌ |
| **User** | `me/` (GET, PATCH), `me/roles/` (GET) | ❌ **Admin CRUD manquant** | ❌ | ❌ |
| **OTP** | `otp/request`, `otp/verify/email`, `otp/verify/phone` | ✅ (action-based) | ❌ | ❌ |
| **Password** | `reset/request`, `reset/confirm`, `change`, `strength`, `requirements` | ✅ | ❌ | ❌ |
| **2FA** | `status`, `setup`, `confirm`, `disable`, `backup-codes` | ✅ | ❌ | ❌ |
| **RBAC** | Permissions (list/detail), Roles (list/detail/perms), User roles/perms | ✅ | ❌ | ❌ |
| **Applications** | list, detail, regenerate | ✅ | ❌ | ❌ |
| **GDPR** | request/confirm/cancel deletion, status, export | ✅ | ❌ | ❌ |
| **Organizations** | CRUD, tree, members, invitations, roles | ✅ | ❌ | ❌ |
| **Security** | ❌ Aucun endpoint AuditLog, BlacklistedToken, LoginAttempt | ❌ | ❌ | ❌ |
| **Dashboard** | ❌ Aucun endpoint stats/agrégats | ❌ | ❌ | ❌ |

---

## 2. Lacunes Identifiées

### 2.1 ❌ CRUD Manquants

#### A. User Management (Admin)
**Problème critique** : Seul `MeView` existe (profil de l'utilisateur connecté). Aucun endpoint pour qu'un admin puisse gérer les utilisateurs.

| Action | Endpoint attendu | Existe ? |
|---|---|:---:|
| Lister les utilisateurs | `GET /users/` | ❌ |
| Détails d'un utilisateur | `GET /users/<id>/` | ❌ |
| Modifier un utilisateur (admin) | `PATCH /users/<id>/` | ❌ |
| Bannir un utilisateur | `POST /users/<id>/ban/` | ❌ |
| Débannir un utilisateur | `POST /users/<id>/unban/` | ❌ |
| Verrouiller un compte | `POST /users/<id>/lock/` | ❌ |
| Déverrouiller un compte | `POST /users/<id>/unlock/` | ❌ |
| Soft delete (admin) | `DELETE /users/<id>/` | ❌ |
| Sessions actives | `GET /users/<id>/sessions/` | ❌ |

#### B. Security / Monitoring (Admin)
Aucun endpoint pour consulter les données de sécurité critiques.

| Action | Endpoint attendu | Existe ? |
|---|---|:---:|
| Lister les audit logs | `GET /audit-logs/` | ❌ |
| Détails d'un audit log | `GET /audit-logs/<id>/` | ❌ |
| Lister les tokens blacklistés | `GET /blacklisted-tokens/` | ❌ |
| Nettoyer tokens expirés | `POST /blacklisted-tokens/cleanup/` | ❌ |
| Lister les tentatives de connexion | `GET /login-attempts/` | ❌ |
| Lister les refresh tokens | `GET /refresh-tokens/` | ❌ |
| Révoquer refresh token (admin) | `POST /refresh-tokens/<id>/revoke/` | ❌ |

#### C. GDPR Admin
| Action | Endpoint attendu | Existe ? |
|---|---|:---:|
| Lister les demandes de suppression | `GET /admin/deletion-requests/` | ❌ |
| Traiter une demande | `POST /admin/deletion-requests/<id>/process/` | ❌ |
| Exécuter les demandes expirées | `POST /admin/deletion-requests/process-expired/` | ❌ |

---

### 2.2 ❌ Filtres et Pagination Manquants

**Aucun** des endpoints `list` n'utilise de filtres ni de pagination. Problème en production avec des volumes > 100 enregistrements.

#### Filtres nécessaires par endpoint

| Endpoint | Filtres attendus |
|---|---|
| `GET /users/` | `search` (email, name), `is_active`, `is_locked`, `is_banned`, `is_deleted`, `is_email_verified`, `is_2fa_enabled`, `role`, `created_after`, `created_before`, `ordering` |
| `GET /permissions/` | `search` (code, name), `parent` (null/id), `ordering` |
| `GET /roles/` | `search` (code, name), `is_default`, `ordering` |
| `GET /applications/` | `search` (name), `is_active`, `ordering` |
| `GET /audit-logs/` | `user_id`, `action`, `ip_address`, `date_from`, `date_to`, `application_id`, `ordering` |
| `GET /login-attempts/` | `identifier`, `ip_address`, `success`, `date_from`, `date_to`, `ordering` |
| `GET /blacklisted-tokens/` | `user_id`, `reason`, `expired`, `ordering` |
| `GET /refresh-tokens/` | `user_id`, `application_id`, `is_revoked`, `expired`, `ordering` |
| `GET /organizations/list/` | `search` (name, slug), `is_active`, `parent` (null/id), `ordering` |
| `GET /organizations/members/` | `search` (name, email), `role`, `status`, `ordering` |
| `GET /admin/deletion-requests/` | `user_id`, `status`, `date_from`, `date_to`, `ordering` |

#### Pagination standard
Tous les endpoints `list` doivent supporter :
```json
{
  "count": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8,
  "results": [...]
}
```

---

### 2.3 ❌ Dashboard & Statistiques

#### A. Dashboard Global — `GET /dashboard/stats/`

Agrégats cross-modules pour un admin panel.

```json
{
  "users": {
    "total": 1250,
    "active": 1180,
    "locked": 15,
    "banned": 5,
    "deleted": 50,
    "verified_email": 1100,
    "verified_phone": 800,
    "with_2fa": 350,
    "new_today": 12,
    "new_this_week": 45,
    "new_this_month": 180
  },
  "auth": {
    "total_logins_today": 320,
    "failed_logins_today": 25,
    "active_refresh_tokens": 890,
    "active_sessions_now": 45
  },
  "applications": {
    "total": 8,
    "active": 7
  },
  "security": {
    "blacklisted_tokens": 42,
    "suspicious_activity_24h": 3,
    "rate_limited_ips_today": 2
  },
  "gdpr": {
    "pending_deletions": 3,
    "confirmed_deletions": 1,
    "grace_period_expiring_soon": 1
  },
  "organizations": {
    "total": 25,
    "active": 23,
    "total_members": 450,
    "pending_invitations": 12
  }
}
```

#### B. Auth Stats — `GET /dashboard/auth/`

```json
{
  "login_stats": {
    "today": { "total": 320, "success": 295, "failed": 25 },
    "this_week": { "total": 2100, "success": 1980, "failed": 120 },
    "this_month": { "total": 8500, "success": 8100, "failed": 400 }
  },
  "login_by_method": {
    "email": 280,
    "phone": 30,
    "google": 10
  },
  "registration_stats": {
    "today": 12,
    "this_week": 45,
    "this_month": 180,
    "by_method": { "email": 150, "phone": 20, "google": 10 }
  },
  "token_stats": {
    "active_refresh_tokens": 890,
    "tokens_refreshed_today": 450,
    "tokens_revoked_today": 15
  },
  "top_login_failure_reasons": [
    { "reason": "invalid_password", "count": 300 },
    { "reason": "account_locked", "count": 50 },
    { "reason": "account_banned", "count": 10 }
  ],
  "charts": {
    "logins_per_day_7d": [
      { "date": "2026-02-13", "success": 280, "failed": 15 },
      ...
    ]
  }
}
```

#### C. Security Stats — `GET /dashboard/security/`

```json
{
  "audit_summary_24h": {
    "total_events": 500,
    "by_action": {
      "login": 295,
      "login_failed": 25,
      "password_change": 10,
      ...
    }
  },
  "blacklisted_tokens": {
    "total_active": 42,
    "by_reason": { "logout": 20, "password_change": 12, "security": 10 },
    "expired_pending_cleanup": 15
  },
  "rate_limiting": {
    "currently_limited_identifiers": 2,
    "limited_today": 5
  },
  "suspicious_activity": {
    "last_24h": 3,
    "last_7d": 12,
    "top_ips": [
      { "ip": "192.168.1.1", "events": 50 }
    ]
  },
  "account_security": {
    "locked_accounts": 15,
    "banned_accounts": 5,
    "2fa_adoption_rate": 28.0,
    "password_changes_today": 10
  }
}
```

#### D. GDPR Stats — `GET /dashboard/gdpr/`

```json
{
  "deletion_requests": {
    "total": 50,
    "by_status": {
      "pending": 3,
      "confirmation_sent": 1,
      "confirmed": 2,
      "completed": 40,
      "cancelled": 4
    },
    "grace_period_expiring_7d": 1,
    "avg_processing_time_days": 32.5
  },
  "data_exports": {
    "total_today": 2,
    "total_this_month": 15
  }
}
```

#### E. Organizations Stats — `GET /dashboard/organizations/`

```json
{
  "total_organizations": 25,
  "active": 23,
  "with_sub_orgs": 8,
  "members": {
    "total": 450,
    "avg_per_org": 18,
    "by_role": { "owner": 25, "admin": 40, "member": 385 }
  },
  "invitations": {
    "pending": 12,
    "accepted_this_month": 30,
    "expired": 5,
    "declined": 3
  },
  "top_organizations": [
    { "name": "Acme Corp", "slug": "acme-corp", "members": 45 }
  ]
}
```

---

## 3. Plan d'Implémentation

### Phase 1 : Infrastructure (pagination + filtres)

| Fichier | Action | Priorité |
|---|---|:---:|
| [NEW] `src/tenxyte/pagination.py` | Classe `TenxytePagination` (cursor + page) | 🔴 P0 |
| [NEW] `src/tenxyte/filters.py` | Classes de filtres par modèle | 🔴 P0 |
| [MODIFY] `src/tenxyte/views/rbac_views.py` | Ajouter pagination + filtres aux list views | 🔴 P0 |
| [MODIFY] `src/tenxyte/views/application_views.py` | Ajouter pagination + filtres | 🔴 P0 |
| [MODIFY] `src/tenxyte/views/organization_views.py` | Ajouter pagination + filtres | 🔴 P0 |

### Phase 2 : User Management CRUD (Admin)

| Fichier | Action | Priorité |
|---|---|:---:|
| [NEW] `src/tenxyte/serializers/user_serializers.py` | `AdminUserSerializer`, `UserListSerializer`, `UserUpdateSerializer` | 🔴 P0 |
| [MODIFY] `src/tenxyte/views/user_views.py` | `UserListView`, `UserDetailView`, `UserBanView`, `UserLockView`, `UserSessionsView` | 🔴 P0 |
| [MODIFY] `src/tenxyte/urls.py` | Ajouter les routes `/users/` admin | 🔴 P0 |

### Phase 3 : Security Admin Views

| Fichier | Action | Priorité |
|---|---|:---:|
| [NEW] `src/tenxyte/views/security_views.py` | `AuditLogListView`, `LoginAttemptListView`, `BlacklistedTokenListView`, `RefreshTokenListView` | 🟡 P1 |
| [NEW] `src/tenxyte/serializers/security_serializers.py` | Serializers pour AuditLog, LoginAttempt, BlacklistedToken, RefreshToken | 🟡 P1 |
| [MODIFY] `src/tenxyte/urls.py` | Ajouter routes security | 🟡 P1 |

### Phase 4 : GDPR Admin Views

| Fichier | Action | Priorité |
|---|---|:---:|
| [NEW] `src/tenxyte/views/gdpr_admin_views.py` | `DeletionRequestListView`, `ProcessDeletionView`, `ProcessExpiredView` | 🟡 P1 |
| [MODIFY] `src/tenxyte/urls.py` | Ajouter routes GDPR admin | 🟡 P1 |

### Phase 5 : Dashboard Stats

| Fichier | Action | Priorité |
|---|---|:---:|
| [NEW] `src/tenxyte/views/dashboard_views.py` | `DashboardGlobalView`, `DashboardAuthView`, `DashboardSecurityView`, `DashboardGDPRView`, `DashboardOrganizationsView` | 🟢 P2 |
| [NEW] `src/tenxyte/services/stats_service.py` | Service d'agrégation pour les stats | 🟢 P2 |
| [MODIFY] `src/tenxyte/urls.py` | Ajouter routes dashboard | 🟢 P2 |

### Phase 6 : Tests & Documentation

| Fichier | Action | Priorité |
|---|---|:---:|
| [NEW] `tests/test_user_admin.py` | Tests User CRUD admin | 🟡 P1 |
| [NEW] `tests/test_security_views.py` | Tests Security views | 🟡 P1 |
| [NEW] `tests/test_dashboard.py` | Tests Dashboard stats | 🟢 P2 |
| [NEW] `tests/test_filters.py` | Tests filtres et pagination | 🟡 P1 |

---

## 4. Résumé des Estimations

| Phase | Fichiers | Lignes estimées | Effort |
|---|:---:|:---:|:---:|
| Phase 1 — Pagination + Filtres | 5 | ~400 | 🟡 Moyen |
| Phase 2 — User Admin CRUD | 3 | ~500 | 🟡 Moyen |
| Phase 3 — Security Admin | 3 | ~400 | 🟡 Moyen |
| Phase 4 — GDPR Admin | 2 | ~200 | 🟢 Léger |
| Phase 5 — Dashboard Stats | 3 | ~600 | 🔴 Lourd |
| Phase 6 — Tests | 4 | ~800 | 🔴 Lourd |
| **Total** | **20** | **~2900** | — |

---

## 5. Notes Architecturales

### Permissions recommandées
Tous les endpoints admin doivent être protégés par `@require_permission`:
- `users.view`, `users.update`, `users.ban`, `users.lock`, `users.delete`
- `audit.view`, `security.view`
- `gdpr.admin`, `gdpr.process`
- `dashboard.view`

### Convention de pagination
Utiliser `PageNumberPagination` de DRF avec override :
- `?page=1&page_size=20` (défaut: 20, max: 100)
- Headers: `X-Total-Count`, `X-Total-Pages`

### Convention de filtres
- Filtres via query params: `?search=john&is_active=true&ordering=-created_at`
- Support multi-valeurs: `?action=login,login_failed`
- Date ranges: `?date_from=2026-01-01&date_to=2026-02-01`
