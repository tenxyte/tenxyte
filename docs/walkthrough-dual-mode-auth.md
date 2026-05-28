# Walkthrough — Refactoring de l'authentification applicative (Dual-Mode)

## Contexte

Dans la version précédente de Tenxyte, **toute** requête authentifiée par application devait fournir deux headers :

```
X-Access-Key: <clé publique>
X-Access-Secret: <secret privé>
```

**Problème** : dans un contexte navigateur (SPA, frontend), le `X-Access-Secret` est exposé :
1. **Dans le bundle JS** — le string est en clair dans le code source livré au client.
2. **Dans le Network tab** — chaque requête affiche le header en clair dans les DevTools.

**Solution** : implémenter un système d'authentification **dual-mode** :

| Mode | Headers | Cas d'usage |
|------|---------|-------------|
| **Frontend** (navigateur) | `X-Access-Key` + header `Origin` | Web apps, SPAs |
| **Backend** (serveur-à-serveur) | `X-Access-Key` + `X-Access-Secret` | Cron jobs, webhooks, scripts admin |

---

## Phase 1 — Modèle `AbstractApplication`

### Fichier modifié : `src/tenxyte/models/application.py`

**Ajout du champ `allowed_origins`** — un `JSONField` (liste de strings) qui contient les origines autorisées pour l'authentification key-only (frontend).

```python
allowed_origins = models.JSONField(
    default=list,
    blank=True,
    help_text="List of allowed origins for key-only (frontend) auth. Empty list requires secret.",
)
```

**Comportement** :
- Si `allowed_origins` est **vide** (`[]`) → le mode key-only est désactivé, le secret est obligatoire.
- Si `allowed_origins` contient des origines → les requêtes depuis ces origines sont acceptées avec uniquement `X-Access-Key`.

**Ajout de la méthode `is_origin_allowed()`** :

```python
def is_origin_allowed(self, origin: str) -> bool:
    if not self.allowed_origins:
        return False
    return origin in self.allowed_origins
```

**Mise à jour de `create_application()`** pour accepter `allowed_origins` :

```python
@classmethod
def create_application(cls, name, description="", allowed_origins=None):
    # ...
    app = cls(
        name=name,
        description=description,
        access_key=secrets.token_hex(32),
        access_secret=hashed_secret,
        allowed_origins=allowed_origins or [],
    )
```

### Fichier créé : `src/tenxyte/migrations/0014_application_allowed_origins.py`

Migration Django standard qui ajoute le champ `allowed_origins` à la table `application`.

```python
migrations.AddField(
    model_name="application",
    name="allowed_origins",
    field=models.JSONField(blank=True, default=list, help_text="..."),
)
```

---

## Phase 2 — Middleware Django legacy (`middleware.py`)

### Fichier modifié : `src/tenxyte/middleware.py`

**Avant** :
```python
if not access_key or not access_secret:
    return JsonResponse({"error": "...", "code": "APP_AUTH_REQUIRED"}, status=401)
```

**Après** — logique dual-mode :

```python
if not access_key:
    return JsonResponse({"error": "...", "code": "APP_AUTH_REQUIRED"}, status=401)

application = Application.objects.get(access_key=access_key, is_active=True)

if access_secret:
    # Mode serveur : key + secret (inchangé)
    # → vérification bcrypt avec cache anti-DoS
else:
    # Mode frontend : key-only + Origin
    origin = request.META.get("HTTP_ORIGIN")
    if not origin:
        return 401, "APP_AUTH_ORIGIN_REQUIRED"
    if not application.is_origin_allowed(origin):
        return 401, "APP_AUTH_ORIGIN_DENIED"
```

**Nouveaux codes d'erreur** :
- `APP_AUTH_ORIGIN_REQUIRED` — key-only sans header `Origin`
- `APP_AUTH_ORIGIN_DENIED` — Origin pas dans la liste `allowed_origins`

---

## Phase 3 — Core Middleware (`core/middleware.py`)

### Fichier modifié : `src/tenxyte/core/middleware.py`

Même refactoring que Phase 2, appliqué au `ApplicationAuthCoreMiddleware` (framework-agnostic). La logique est identique :

```python
if not access_key:
    return MiddlewareResult.error(401, "APP_AUTH_REQUIRED", "...")

application = self.repository.get_by_access_key(access_key)

if access_secret:
    # Server mode : verify secret (cached)
else:
    # Frontend mode : validate Origin
    origin = request.get_header("Origin")
    if not origin:
        return error(401, "APP_AUTH_ORIGIN_REQUIRED", "...")
    if not application.is_origin_allowed(origin):
        return error(401, "APP_AUTH_ORIGIN_DENIED", "...")
```

---

## Phase 4 — Configuration

### Fichier modifié : `src/tenxyte/conf/security.py`

**Retrait de `X-Access-Secret`** des headers CORS par défaut :

```python
# Avant
CORS_ALLOWED_HEADERS = ["Accept", ..., "X-Access-Key", "X-Access-Secret", "X-Requested-With"]

# Après
CORS_ALLOWED_HEADERS = ["Accept", ..., "X-Access-Key", "X-Requested-With"]
```

> Le secret ne devrait jamais transiter depuis un navigateur. Les backends (serveur-à-serveur) ne sont pas soumis aux restrictions CORS.

### Fichier modifié : `src/tenxyte/conf/modules.py`

Mise à jour de la docstring de `APPLICATION_AUTH_ENABLED` :

```python
"""
Activer/désactiver l'authentification par application.
Deux modes supportés:
- Frontend (navigateur): X-Access-Key + Origin header (validé via allowed_origins)
- Backend (serveur-à-serveur): X-Access-Key + X-Access-Secret
"""
```

---

## Phase 5 — Sérialisation & Vues

### Fichier modifié : `src/tenxyte/serializers/application_serializers.py`

Ajout de `allowed_origins` aux trois serializers :

- **`ApplicationSerializer`** (lecture) : ajouté dans `fields`
- **`ApplicationCreateSerializer`** : nouveau champ `ListField(child=URLField())`
- **`ApplicationUpdateSerializer`** : idem, `required=False`

```python
allowed_origins = serializers.ListField(
    child=serializers.URLField(), required=False, default=list
)
```

### Fichier modifié : `src/tenxyte/views/application_views.py`

Le `POST` de création passe maintenant `allowed_origins` :

```python
app, raw_secret = Application.create_application(
    name=serializer.validated_data["name"],
    description=serializer.validated_data.get("description", ""),
    allowed_origins=serializer.validated_data.get("allowed_origins", []),
)
```

Le `PUT` fonctionne automatiquement (le loop `setattr` parcourt tous les champs validés).

---

## Phase 6 — Documentation

### Fichiers modifiés : `docs/en/applications.md` et `docs/fr/applications.md`

Changements identiques dans les deux langues :

1. **Tableau dual-mode** ajouté dans la section Présentation
2. **Section "Frontend (Key-Only) Mode"** ajoutée avec exemples Python et HTTP
3. **Modèle de données** mis à jour avec `allowed_origins`
4. **Notes** ajoutées expliquant le comportement de `allowed_origins` vide vs rempli

Extrait :
```markdown
| Mode | Headers | Cas d'usage |
|------|---------|-------------|
| **Frontend** (navigateur) | `X-Access-Key` + header `Origin` | Web apps, SPAs |
| **Backend** (serveur-à-serveur) | `X-Access-Key` + `X-Access-Secret` | Cron jobs, webhooks, scripts admin |
```

---

## Phase 7 — Tests

### Fichier modifié : `tests/integration/django/unit/test_middleware_extra.py`

Nouvelle classe `TestApplicationAuthKeyOnlyMode` avec 5 tests :

| Test | Scénario | Résultat attendu |
|------|----------|------------------|
| `test_key_only_valid_origin` | Key + Origin valide | 200, application attachée |
| `test_key_only_invalid_origin` | Key + Origin non autorisée | 401 `APP_AUTH_ORIGIN_DENIED` |
| `test_key_only_no_origin_header` | Key seul, pas de Origin | 401 `APP_AUTH_ORIGIN_REQUIRED` |
| `test_key_only_empty_allowed_origins` | Key + Origin mais `allowed_origins=[]` | 401 `APP_AUTH_ORIGIN_DENIED` |
| `test_key_plus_secret_still_works` | Key + Secret (backward compat) | 200 |

### Fichier modifié : `tests/core/test_core_middleware.py`

Mise à jour du test existant + 3 nouveaux tests :

| Test | Scénario | Résultat attendu |
|------|----------|------------------|
| `test_missing_key` | Aucun header | 401 `APP_AUTH_REQUIRED` |
| `test_key_only_valid_origin` | Key + Origin valide | continue processing |
| `test_key_only_invalid_origin` | Key + Origin invalide | 401 `APP_AUTH_ORIGIN_DENIED` |
| `test_key_only_no_origin` | Key seul, pas d'Origin | 401 `APP_AUTH_ORIGIN_REQUIRED` |

---

## Résumé des fichiers modifiés

| Fichier | Type de changement |
|---------|-------------------|
| `src/tenxyte/models/application.py` | Champ + méthode + factory |
| `src/tenxyte/migrations/0014_application_allowed_origins.py` | **Nouveau** — migration |
| `src/tenxyte/middleware.py` | Logique dual-mode |
| `src/tenxyte/core/middleware.py` | Logique dual-mode (core) |
| `src/tenxyte/conf/security.py` | Retrait `X-Access-Secret` des CORS |
| `src/tenxyte/conf/modules.py` | Docstring |
| `src/tenxyte/serializers/application_serializers.py` | `allowed_origins` dans 3 serializers |
| `src/tenxyte/views/application_views.py` | Passage `allowed_origins` à la création |
| `docs/en/applications.md` | Documentation EN |
| `docs/fr/applications.md` | Documentation FR |
| `tests/integration/django/unit/test_middleware_extra.py` | 5 tests Django |
| `tests/core/test_core_middleware.py` | 3+1 tests core |

## Rétrocompatibilité

- Le mode **key + secret** fonctionne exactement comme avant.
- Les applications existantes ont `allowed_origins = []` par défaut → aucun changement de comportement.
- Pour activer le mode frontend, il suffit de renseigner `allowed_origins` sur l'application.
