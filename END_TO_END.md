# Guide Tests End-to-End — Tenxyte v0.0.8

**Date :** 10 février 2026
**Objectif :** Valider l'intégralité des flux Tenxyte Auth via des tests E2E manuels (API Postman) puis via une application frontend Vue 3.

---

## Table des Matières

1. [Prérequis](#1-prérequis)
2. [Partie 1 — Préparation des apps_showcase](#2-partie-1--préparation-des-apps_showcase)
3. [Partie 2 — Tests API avec Postman](#3-partie-2--tests-api-avec-postman)
4. [Partie 3 — Application Frontend Vue 3](#4-partie-3--application-frontend-vue-3)

---

## 1. Prérequis

### Outils requis

| Outil | Version | Usage |
|-------|---------|-------|
| Python | 3.10+ | Backend Django |
| Docker Desktop | Latest | PostgreSQL, MySQL, MongoDB |
| Postman | Latest | Tests API manuels |
| Node.js | 18+ | Frontend Vue 3 |
| pnpm / npm | Latest | Package manager JS |

### Installation du package Tenxyte (mode dev)

```bash
cd tenxyte/
pip install -e ".[dev,postgres,mysql,mongodb]"
```

### Démarrage des bases de données (Docker)

```bash
# PostgreSQL
docker run -d --name tenxyte_pg_e2e \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=tenxyte_pgsql \
  -p 5432:5432 postgres:16

# MySQL
docker run -d --name tenxyte_mysql_e2e \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=tenxyte_mysql \
  -p 3306:3306 mysql:8

# MongoDB
docker run -d --name tenxyte_mongo_e2e \
  -p 27017:27017 mongo:8
```

---

## 2. Partie 1 — Préparation des apps_showcase

Chaque app showcase est un projet Django autonome dans `apps_showcase/`. Avant de tester, il faut **corriger les URLs** (tenxyte.urls manquant) et **appliquer les migrations**.

### 2.1 Correction commune : ajouter les URLs Tenxyte

Chaque fichier `apps_showcase/test_<db>/config/urls.py` ne contient que `admin/`. Il faut ajouter les endpoints Tenxyte :

```python
# apps_showcase/test_<db>/config/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("tenxyte.urls")),
]
```

> Appliquer cette modification dans les 4 apps : `test_sqlite`, `test_pgsql`, `test_mysql`, `test_mongodb`.

### 2.2 Correction MongoDB : ajouter MIGRATION_MODULES

Le fichier `apps_showcase/test_mongodb/config/settings.py` doit également inclure :

```python
# Après la ligne DEFAULT_AUTO_FIELD
MIGRATION_MODULES = {
    "contenttypes": None,
    "auth": None,
}
```

Et retirer `"django.contrib.admin"` de `INSTALLED_APPS` (incompatible avec ObjectIdAutoField).

### 2.3 Lancer chaque app showcase

#### SQLite

```bash
cd apps_showcase/test_sqlite
python manage.py migrate
python manage.py tenxyte_seed
python manage.py runserver 8001
```

#### PostgreSQL

```bash
cd apps_showcase/test_pgsql
python manage.py migrate
python manage.py tenxyte_seed
python manage.py runserver 8002
```

#### MySQL

```bash
cd apps_showcase/test_mysql
python manage.py migrate
python manage.py tenxyte_seed
python manage.py runserver 8003
```

#### MongoDB

```bash
cd apps_showcase/test_mongodb
python manage.py migrate
python manage.py tenxyte_seed
python manage.py runserver 8004
```

### 2.4 Créer une Application (credentials API)

Pour chaque serveur lancé, ouvrir un shell Django et créer une Application :

```bash
python manage.py shell -c "
from tenxyte.models import Application
app, secret = Application.create_application(name='Postman E2E', description='Tests Postman')
print(f'X-Access-Key: {app.access_key}')
print(f'X-Access-Secret: {secret}')
"
```

> **Sauvegarder** les `access_key` et `access_secret` — le secret ne sera plus affiché.

---

## 3. Partie 2 — Tests API avec Postman

### 3.1 Configuration Postman

#### Variables d'environnement Postman

Créer un environnement par backend (SQLite, PgSQL, MySQL, MongoDB) avec ces variables :

| Variable | Valeur (SQLite) | Valeur (PgSQL) | Valeur (MySQL) | Valeur (MongoDB) |
|----------|-----------------|----------------|----------------|------------------|
| `base_url` | `http://localhost:8001` | `http://localhost:8002` | `http://localhost:8003` | `http://localhost:8004` |
| `access_key` | *(from shell)* | *(from shell)* | *(from shell)* | *(from shell)* |
| `access_secret` | *(from shell)* | *(from shell)* | *(from shell)* | *(from shell)* |
| `access_token` | *(auto-rempli)* | | | |
| `refresh_token` | *(auto-rempli)* | | | |
| `user_id` | *(auto-rempli)* | | | |

#### Headers communs (onglet Collection > Pre-request)

```
X-Access-Key: {{access_key}}
X-Access-Secret: {{access_secret}}
Content-Type: application/json
```

Pour les requêtes authentifiées, ajouter :
```
Authorization: Bearer {{access_token}}
```

### 3.2 Scénario E2E complet

Exécuter les requêtes **dans l'ordre** ci-dessous. Chaque étape indique le verbe HTTP, l'URL, le body, les tests Postman à écrire, et les variables à capturer.

---

#### FLUX 1 — Inscription & Authentification

##### 1.1 Register

```
POST {{base_url}}/api/auth/register/
```

**Body :**
```json
{
  "email": "e2e@tenxyte.test",
  "password": "E2e@Str0ng!Pass",
  "first_name": "E2E",
  "last_name": "Tester"
}
```

**Tests Postman :**
```javascript
pm.test("Status 201", () => pm.response.to.have.status(201));
const body = pm.response.json();
pm.test("Has access_token", () => pm.expect(body.access_token).to.be.a("string"));
pm.test("Has refresh_token", () => pm.expect(body.refresh_token).to.be.a("string"));
pm.test("Has user object", () => pm.expect(body.user).to.have.property("email"));

// Capture tokens
pm.environment.set("access_token", body.access_token);
pm.environment.set("refresh_token", body.refresh_token);
pm.environment.set("user_id", body.user.id);
```

##### 1.2 Login Email

```
POST {{base_url}}/api/auth/login/email/
```

**Body :**
```json
{
  "email": "e2e@tenxyte.test",
  "password": "E2e@Str0ng!Pass"
}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
const body = pm.response.json();
pm.test("Has tokens", () => {
    pm.expect(body.access_token).to.be.a("string");
    pm.expect(body.refresh_token).to.be.a("string");
});
pm.test("Has expires_in", () => pm.expect(body.expires_in).to.be.above(0));

pm.environment.set("access_token", body.access_token);
pm.environment.set("refresh_token", body.refresh_token);
```

##### 1.3 Get Profile (Me)

```
GET {{base_url}}/api/auth/me/
Authorization: Bearer {{access_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
const body = pm.response.json();
pm.test("Email matches", () => pm.expect(body.email).to.eql("e2e@tenxyte.test"));
pm.test("First name matches", () => pm.expect(body.first_name).to.eql("E2E"));
```

##### 1.4 Update Profile

```
PATCH {{base_url}}/api/auth/me/
Authorization: Bearer {{access_token}}
```

**Body :**
```json
{
  "first_name": "E2E_Updated"
}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
pm.test("Name updated", () => pm.expect(pm.response.json().first_name).to.eql("E2E_Updated"));
```

##### 1.5 Refresh Token

```
POST {{base_url}}/api/auth/refresh/
```

**Body :**
```json
{
  "refresh_token": "{{refresh_token}}"
}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
const body = pm.response.json();
pm.test("New access_token", () => pm.expect(body.access_token).to.be.a("string"));
pm.test("New refresh_token", () => pm.expect(body.refresh_token).to.be.a("string"));

pm.environment.set("access_token", body.access_token);
pm.environment.set("refresh_token", body.refresh_token);
```

---

#### FLUX 2 — Gestion des Mots de Passe

##### 2.1 Password Requirements

```
GET {{base_url}}/api/auth/password/requirements/
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
pm.test("Has min_length", () => pm.expect(pm.response.json().min_length).to.be.a("number"));
```

##### 2.2 Password Strength Check

```
POST {{base_url}}/api/auth/password/strength/
```

**Body :**
```json
{
  "password": "E2e@Str0ng!Pass"
}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
const body = pm.response.json();
pm.test("Has score", () => pm.expect(body.score).to.be.a("number"));
pm.test("Has strength label", () => pm.expect(body.strength).to.be.a("string"));
```

##### 2.3 Change Password

```
POST {{base_url}}/api/auth/password/change/
Authorization: Bearer {{access_token}}
```

**Body :**
```json
{
  "old_password": "E2e@Str0ng!Pass",
  "new_password": "NewE2e@Str0ng!Pass2"
}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
```

> **Important :** Après le changement, se reconnecter avec le nouveau mot de passe.

##### 2.4 Re-login avec nouveau password

```
POST {{base_url}}/api/auth/login/email/
```

**Body :**
```json
{
  "email": "e2e@tenxyte.test",
  "password": "NewE2e@Str0ng!Pass2"
}
```

**Tests Postman :** Capturer les nouveaux tokens (même script que 1.2).

##### 2.5 Password Reset Request

```
POST {{base_url}}/api/auth/password/reset/request/
```

**Body :**
```json
{
  "email": "e2e@tenxyte.test"
}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
```

> **Note :** L'OTP sera affiché dans la console du serveur (ConsoleBackend). Récupérer le code pour l'étape suivante.

##### 2.6 Password Reset Confirm

```
POST {{base_url}}/api/auth/password/reset/confirm/
```

**Body :**
```json
{
  "email": "e2e@tenxyte.test",
  "code": "<CODE_FROM_CONSOLE>",
  "new_password": "ResetE2e@Str0ng!Pass3"
}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
```

---

#### FLUX 3 — OTP Verification

##### 3.1 Request OTP (email verification)

```
POST {{base_url}}/api/auth/otp/request/
Authorization: Bearer {{access_token}}
```

**Body :**
```json
{
  "type": "email_verification"
}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
```

> Récupérer le code OTP dans la console du serveur.

##### 3.2 Verify Email OTP

```
POST {{base_url}}/api/auth/otp/verify/email/
Authorization: Bearer {{access_token}}
```

**Body :**
```json
{
  "code": "<CODE_FROM_CONSOLE>"
}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
```

---

#### FLUX 4 — Two-Factor Authentication (TOTP)

##### 4.1 Get 2FA Status

```
GET {{base_url}}/api/auth/2fa/status/
Authorization: Bearer {{access_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
pm.test("2FA not enabled", () => pm.expect(pm.response.json().is_2fa_enabled).to.be.false);
```

##### 4.2 Setup 2FA

```
POST {{base_url}}/api/auth/2fa/setup/
Authorization: Bearer {{access_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
const body = pm.response.json();
pm.test("Has secret", () => pm.expect(body.secret).to.be.a("string"));
pm.test("Has QR code", () => pm.expect(body.qr_code).to.include("data:image"));
pm.test("Has backup codes", () => pm.expect(body.backup_codes).to.be.an("array"));
pm.test("Has provisioning URI", () => pm.expect(body.provisioning_uri).to.include("otpauth://"));

pm.environment.set("totp_secret", body.secret);
pm.environment.set("backup_codes", JSON.stringify(body.backup_codes));
```

> **Sauvegarder** le `secret` pour générer des codes TOTP. Utiliser un outil comme https://totp.app/ ou une extension Postman TOTP.

##### 4.3 Confirm 2FA

```
POST {{base_url}}/api/auth/2fa/confirm/
Authorization: Bearer {{access_token}}
```

**Body :**
```json
{
  "code": "<TOTP_CODE_FROM_AUTHENTICATOR>"
}
```

> Générer le code TOTP à partir du `secret` capturé à l'étape 4.2.

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
```

##### 4.4 Verify 2FA Status (now enabled)

```
GET {{base_url}}/api/auth/2fa/status/
Authorization: Bearer {{access_token}}
```

**Tests Postman :**
```javascript
pm.test("2FA now enabled", () => pm.expect(pm.response.json().is_2fa_enabled).to.be.true);
```

##### 4.5 Login with 2FA

```
POST {{base_url}}/api/auth/login/email/
```

**Body :**
```json
{
  "email": "e2e@tenxyte.test",
  "password": "ResetE2e@Str0ng!Pass3",
  "totp_code": "<TOTP_CODE>"
}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
pm.test("Has tokens", () => pm.expect(pm.response.json().access_token).to.be.a("string"));
pm.environment.set("access_token", pm.response.json().access_token);
pm.environment.set("refresh_token", pm.response.json().refresh_token);
```

##### 4.6 Regenerate Backup Codes

```
POST {{base_url}}/api/auth/2fa/backup-codes/
Authorization: Bearer {{access_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
pm.test("Has backup codes", () => pm.expect(pm.response.json().backup_codes).to.be.an("array"));
```

##### 4.7 Disable 2FA

```
POST {{base_url}}/api/auth/2fa/disable/
Authorization: Bearer {{access_token}}
```

**Body :**
```json
{
  "code": "<TOTP_CODE>"
}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
```

---

#### FLUX 5 — RBAC (Rôles & Permissions)

> Les requêtes RBAC nécessitent un utilisateur admin. Créer un super_admin via le shell :
> ```bash
> python manage.py shell -c "
> from tenxyte.models import get_user_model, get_role_model
> User = get_user_model()
> Role = get_role_model()
> admin = User.objects.create_user(email='admin@tenxyte.test', password='Admin@Str0ng!Pass')
> admin.is_staff = True
> admin.save()
> sa_role = Role.objects.get(code='super_admin')
> admin.roles.add(sa_role)
> "
> ```
> Puis se connecter avec `admin@tenxyte.test` et capturer le token dans `admin_token`.

##### 5.1 List Permissions

```
GET {{base_url}}/api/auth/permissions/
Authorization: Bearer {{admin_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
pm.test("Has permissions", () => pm.expect(pm.response.json()).to.be.an("array"));
pm.test("At least 28 permissions (from seed)", () => pm.expect(pm.response.json().length).to.be.at.least(28));
```

##### 5.2 List Roles

```
GET {{base_url}}/api/auth/roles/
Authorization: Bearer {{admin_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
pm.test("Has roles", () => pm.expect(pm.response.json()).to.be.an("array"));
pm.test("At least 4 roles (from seed)", () => pm.expect(pm.response.json().length).to.be.at.least(4));
```

##### 5.3 Create Role

```
POST {{base_url}}/api/auth/roles/
Authorization: Bearer {{admin_token}}
```

**Body :**
```json
{
  "name": "E2E Test Role",
  "code": "e2e_tester",
  "description": "Role created during E2E testing"
}
```

**Tests Postman :**
```javascript
pm.test("Status 201", () => pm.response.to.have.status(201));
pm.environment.set("test_role_id", pm.response.json().id);
```

##### 5.4 Get Role Detail

```
GET {{base_url}}/api/auth/roles/{{test_role_id}}/
Authorization: Bearer {{admin_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
pm.test("Code matches", () => pm.expect(pm.response.json().code).to.eql("e2e_tester"));
```

##### 5.5 Assign Role to User

```
POST {{base_url}}/api/auth/users/{{user_id}}/roles/
Authorization: Bearer {{admin_token}}
```

**Body :**
```json
{
  "role_id": "{{test_role_id}}"
}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
```

##### 5.6 Get User Roles

```
GET {{base_url}}/api/auth/users/{{user_id}}/roles/
Authorization: Bearer {{admin_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
pm.test("User has e2e_tester role", () => {
    const roles = pm.response.json();
    const hasTester = roles.some(r => r.code === "e2e_tester");
    pm.expect(hasTester).to.be.true;
});
```

##### 5.7 Get My Roles (as e2e user)

```
GET {{base_url}}/api/auth/me/roles/
Authorization: Bearer {{access_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
```

##### 5.8 Remove Role from User

```
DELETE {{base_url}}/api/auth/users/{{user_id}}/roles/
Authorization: Bearer {{admin_token}}
```

**Body :**
```json
{
  "role_id": "{{test_role_id}}"
}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
```

##### 5.9 Delete Role

```
DELETE {{base_url}}/api/auth/roles/{{test_role_id}}/
Authorization: Bearer {{admin_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 204 or 200", () => {
    pm.expect(pm.response.code).to.be.oneOf([200, 204]);
});
```

---

#### FLUX 6 — Applications Management

##### 6.1 List Applications

```
GET {{base_url}}/api/auth/applications/
Authorization: Bearer {{admin_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
pm.test("At least 1 app", () => pm.expect(pm.response.json().length).to.be.at.least(1));
```

##### 6.2 Create Application

```
POST {{base_url}}/api/auth/applications/
Authorization: Bearer {{admin_token}}
```

**Body :**
```json
{
  "name": "E2E Test App",
  "description": "Application created during E2E"
}
```

**Tests Postman :**
```javascript
pm.test("Status 201", () => pm.response.to.have.status(201));
const body = pm.response.json();
pm.test("Has access_key", () => pm.expect(body.access_key).to.be.a("string"));
pm.test("Has access_secret", () => pm.expect(body.access_secret).to.be.a("string"));
pm.environment.set("test_app_id", body.id);
```

##### 6.3 Get Application Detail

```
GET {{base_url}}/api/auth/applications/{{test_app_id}}/
Authorization: Bearer {{admin_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
pm.test("Name matches", () => pm.expect(pm.response.json().name).to.eql("E2E Test App"));
```

##### 6.4 Regenerate Application Credentials

```
POST {{base_url}}/api/auth/applications/{{test_app_id}}/regenerate/
Authorization: Bearer {{admin_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
pm.test("New credentials generated", () => {
    pm.expect(pm.response.json().access_key).to.be.a("string");
    pm.expect(pm.response.json().access_secret).to.be.a("string");
});
```

##### 6.5 Delete Application

```
DELETE {{base_url}}/api/auth/applications/{{test_app_id}}/
Authorization: Bearer {{admin_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 204 or 200", () => {
    pm.expect(pm.response.code).to.be.oneOf([200, 204]);
});
```

---

#### FLUX 7 — Sécurité & Edge Cases

##### 7.1 Accès sans token

```
GET {{base_url}}/api/auth/me/
(pas de header Authorization)
```

**Tests Postman :**
```javascript
pm.test("Status 401", () => pm.response.to.have.status(401));
```

##### 7.2 Token invalide

```
GET {{base_url}}/api/auth/me/
Authorization: Bearer invalid.token.here
```

**Tests Postman :**
```javascript
pm.test("Status 401", () => pm.response.to.have.status(401));
```

##### 7.3 Credentials Application invalides

```
POST {{base_url}}/api/auth/login/email/
X-Access-Key: wrong_key
X-Access-Secret: wrong_secret
```

**Tests Postman :**
```javascript
pm.test("Status 401", () => pm.response.to.have.status(401));
```

##### 7.4 Login avec mauvais password

```
POST {{base_url}}/api/auth/login/email/
```

**Body :**
```json
{
  "email": "e2e@tenxyte.test",
  "password": "WrongPassword!"
}
```

**Tests Postman :**
```javascript
pm.test("Status 401", () => pm.response.to.have.status(401));
```

##### 7.5 Logout

```
POST {{base_url}}/api/auth/logout/
Authorization: Bearer {{access_token}}
```

**Body :**
```json
{
  "refresh_token": "{{refresh_token}}"
}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
```

##### 7.6 Verify refresh token is now blacklisted

```
POST {{base_url}}/api/auth/refresh/
```

**Body :**
```json
{
  "refresh_token": "{{refresh_token}}"
}
```

**Tests Postman :**
```javascript
pm.test("Status 401 (blacklisted)", () => pm.response.to.have.status(401));
```

##### 7.7 Logout All Devices

Se reconnecter d'abord, puis :

```
POST {{base_url}}/api/auth/logout/all/
Authorization: Bearer {{access_token}}
```

**Tests Postman :**
```javascript
pm.test("Status 200", () => pm.response.to.have.status(200));
```

---

### 3.3 Exécution par backend

Exécuter la collection Postman **4 fois** en changeant d'environnement :

| Run | Environnement | Port | Backend |
|-----|---------------|------|---------|
| 1 | SQLite | 8001 | `django.db.backends.sqlite3` |
| 2 | PostgreSQL | 8002 | `django.db.backends.postgresql` |
| 3 | MySQL | 8003 | `django.db.backends.mysql` |
| 4 | MongoDB | 8004 | `django_mongodb_backend` |

Utiliser le **Collection Runner** de Postman pour exécuter tous les tests séquentiellement.

### 3.4 Résumé des requêtes Postman

| # | Flux | Requests | Endpoints testés |
|---|------|----------|------------------|
| 1 | Auth | 5 | register, login, me, me/patch, refresh |
| 2 | Password | 6 | requirements, strength, change, re-login, reset/request, reset/confirm |
| 3 | OTP | 2 | otp/request, otp/verify/email |
| 4 | 2FA | 7 | 2fa/status, setup, confirm, status, login+totp, backup-codes, disable |
| 5 | RBAC | 9 | permissions, roles, roles/create, roles/detail, users/roles (assign, get, remove), me/roles, roles/delete |
| 6 | Apps | 5 | applications (list, create, detail, regenerate, delete) |
| 7 | Security | 7 | no-auth, bad-token, bad-credentials, bad-password, logout, blacklisted-refresh, logout-all |
| | **Total** | **41** | |

---

## 4. Partie 3 — Application Frontend Vue 3

### 4.1 Objectif

Créer une application Vue 3 qui consomme les APIs Tenxyte et démontre les flux suivants :
- Inscription / Connexion / Déconnexion
- Profil utilisateur (affichage + modification)
- Gestion du mot de passe (changement, force)
- Configuration 2FA (QR code, activation, désactivation)
- Administration RBAC (rôles, permissions) — pour les admins
- Gestion des Applications — pour les admins

### 4.2 Stack technique recommandé

| Outil | Rôle |
|-------|------|
| **Vue 3** (Composition API) | Framework frontend |
| **Vue Router 4** | Routing SPA |
| **Pinia** | State management (auth store) |
| **Axios** | HTTP client avec interceptors |
| **TailwindCSS** | Styling |
| **Lucide Vue** | Icônes |
| **vue-qrcode** | Affichage QR code 2FA |

### 4.3 Structure du projet

```
tenxyte-e2e-app/
├── public/
├── src/
│   ├── api/
│   │   └── client.ts          # Axios instance + interceptors
│   ├── stores/
│   │   └── auth.ts            # Pinia store (user, tokens, roles)
│   ├── composables/
│   │   ├── useAuth.ts         # login, register, logout
│   │   ├── useProfile.ts      # me, update profile
│   │   ├── usePassword.ts     # change, reset, strength
│   │   ├── useTwoFactor.ts    # setup, confirm, disable
│   │   └── useRbac.ts         # roles, permissions, assign
│   ├── router/
│   │   └── index.ts           # Routes + guards
│   ├── views/
│   │   ├── LoginView.vue
│   │   ├── RegisterView.vue
│   │   ├── DashboardView.vue
│   │   ├── ProfileView.vue
│   │   ├── PasswordView.vue
│   │   ├── TwoFactorView.vue
│   │   ├── RolesView.vue      # Admin
│   │   ├── PermissionsView.vue # Admin
│   │   └── ApplicationsView.vue # Admin
│   ├── components/
│   │   ├── AppHeader.vue
│   │   ├── AppSidebar.vue
│   │   ├── PasswordStrength.vue
│   │   ├── QRCodeDisplay.vue
│   │   └── RoleTag.vue
│   ├── App.vue
│   └── main.ts
├── .env                        # VITE_API_BASE_URL, VITE_ACCESS_KEY, VITE_ACCESS_SECRET
├── package.json
├── tailwind.config.js
├── vite.config.ts
└── tsconfig.json
```

### 4.4 Configuration Axios (client.ts)

```typescript
// src/api/client.ts
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/auth',
  headers: {
    'Content-Type': 'application/json',
    'X-Access-Key': import.meta.env.VITE_ACCESS_KEY,
    'X-Access-Secret': import.meta.env.VITE_ACCESS_SECRET,
  },
})

// Interceptor: inject access_token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor: auto-refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const { data } = await api.post('/refresh/', { refresh_token: refreshToken })
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`
          return api(originalRequest)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api
```

### 4.5 Auth Store (Pinia)

```typescript
// src/stores/auth.ts
import { defineStore } from 'pinia'
import api from '@/api/client'

interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  is_2fa_enabled: boolean
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    isAuthenticated: false,
  }),
  actions: {
    async login(email: string, password: string, totp_code?: string) {
      const { data } = await api.post('/login/email/', { email, password, totp_code })
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      this.isAuthenticated = true
      await this.fetchProfile()
      return data
    },
    async register(payload: { email: string; password: string; first_name: string; last_name: string }) {
      const { data } = await api.post('/register/', payload)
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      this.isAuthenticated = true
      await this.fetchProfile()
      return data
    },
    async fetchProfile() {
      const { data } = await api.get('/me/')
      this.user = data
    },
    async logout() {
      const refreshToken = localStorage.getItem('refresh_token')
      try {
        await api.post('/logout/', { refresh_token: refreshToken })
      } finally {
        localStorage.clear()
        this.user = null
        this.isAuthenticated = false
      }
    },
  },
})
```

### 4.6 Router avec Guards

```typescript
// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { guest: true } },
  { path: '/register', name: 'register', component: () => import('@/views/RegisterView.vue'), meta: { guest: true } },
  { path: '/', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { auth: true } },
  { path: '/profile', name: 'profile', component: () => import('@/views/ProfileView.vue'), meta: { auth: true } },
  { path: '/password', name: 'password', component: () => import('@/views/PasswordView.vue'), meta: { auth: true } },
  { path: '/2fa', name: 'twofactor', component: () => import('@/views/TwoFactorView.vue'), meta: { auth: true } },
  { path: '/roles', name: 'roles', component: () => import('@/views/RolesView.vue'), meta: { auth: true } },
  { path: '/permissions', name: 'permissions', component: () => import('@/views/PermissionsView.vue'), meta: { auth: true } },
  { path: '/applications', name: 'applications', component: () => import('@/views/ApplicationsView.vue'), meta: { auth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.auth && !auth.isAuthenticated) return { name: 'login' }
  if (to.meta.guest && auth.isAuthenticated) return { name: 'dashboard' }
})

export default router
```

### 4.7 Fichier .env

```env
VITE_API_BASE_URL=http://localhost:8001/api/auth
VITE_ACCESS_KEY=<votre_access_key>
VITE_ACCESS_SECRET=<votre_access_secret>
```

### 4.8 Pages clés à implémenter

#### LoginView.vue
- Champs : email, password, totp_code (conditionnel)
- Bouton "Se connecter"
- Lien vers Register
- Gestion de l'erreur `2FA required` → afficher champ TOTP

#### RegisterView.vue
- Champs : email, password, first_name, last_name
- Indicateur de force du mot de passe en temps réel (appel `/password/strength/`)
- Bouton "S'inscrire"

#### DashboardView.vue
- Affiche les infos utilisateur
- Liens vers Profil, Password, 2FA
- Si admin : liens vers Roles, Permissions, Applications

#### ProfileView.vue
- Affichage des infos (GET `/me/`)
- Formulaire de modification (PATCH `/me/`)

#### PasswordView.vue
- Affichage des règles (`/password/requirements/`)
- Changement de mot de passe (`/password/change/`)
- Indicateur de force en temps réel

#### TwoFactorView.vue
- Statut 2FA (`/2fa/status/`)
- Setup : affichage QR code + secret + backup codes
- Confirmation : champ code TOTP
- Désactivation
- Régénération des backup codes

#### RolesView.vue (Admin)
- Liste des rôles
- Création / modification / suppression
- Assignation de permissions

#### ApplicationsView.vue (Admin)
- Liste des applications
- Création / suppression
- Régénération des credentials

### 4.9 Commandes de lancement

```bash
# Créer le projet
npm create vue@latest tenxyte-e2e-app -- --typescript
cd tenxyte-e2e-app

# Installer les dépendances
npm install axios pinia vue-router@4
npm install -D tailwindcss @tailwindcss/vite lucide-vue-next

# Lancer en dev
npm run dev
```

### 4.10 Test par backend

Changer `VITE_API_BASE_URL` dans `.env` pour pointer vers chaque backend :

| Backend | URL |
|---------|-----|
| SQLite | `http://localhost:8001/api/auth` |
| PostgreSQL | `http://localhost:8002/api/auth` |
| MySQL | `http://localhost:8003/api/auth` |
| MongoDB | `http://localhost:8004/api/auth` |

> **Note CORS :** Ajouter `django-cors-headers` et `CORS_ALLOW_ALL_ORIGINS = True` dans les settings de chaque app_showcase pour le développement.

---

## Checklist de Validation E2E

### Par backend (×4)

| # | Flux | Postman | Vue 3 |
|---|------|---------|-------|
| 1 | Register | ☐ | ☐ |
| 2 | Login | ☐ | ☐ |
| 3 | Get Profile | ☐ | ☐ |
| 4 | Update Profile | ☐ | ☐ |
| 5 | Refresh Token | ☐ | ☐ |
| 6 | Password Requirements | ☐ | ☐ |
| 7 | Password Strength | ☐ | ☐ |
| 8 | Change Password | ☐ | ☐ |
| 9 | Password Reset Request | ☐ | ☐ |
| 10 | Password Reset Confirm | ☐ | ☐ |
| 11 | OTP Request | ☐ | ☐ |
| 12 | OTP Verify Email | ☐ | ☐ |
| 13 | 2FA Status | ☐ | ☐ |
| 14 | 2FA Setup (QR) | ☐ | ☐ |
| 15 | 2FA Confirm | ☐ | ☐ |
| 16 | 2FA Login | ☐ | ☐ |
| 17 | 2FA Backup Codes | ☐ | ☐ |
| 18 | 2FA Disable | ☐ | ☐ |
| 19 | List Permissions | ☐ | ☐ |
| 20 | List Roles | ☐ | ☐ |
| 21 | Create Role | ☐ | ☐ |
| 22 | Assign Role | ☐ | ☐ |
| 23 | Get User Roles | ☐ | ☐ |
| 24 | Remove Role | ☐ | ☐ |
| 25 | Delete Role | ☐ | ☐ |
| 26 | List Applications | ☐ | ☐ |
| 27 | Create Application | ☐ | ☐ |
| 28 | Regenerate Credentials | ☐ | ☐ |
| 29 | Delete Application | ☐ | ☐ |
| 30 | Unauthenticated Access → 401 | ☐ | ☐ |
| 31 | Invalid Token → 401 | ☐ | ☐ |
| 32 | Bad App Credentials → 401 | ☐ | ☐ |
| 33 | Wrong Password → 401 | ☐ | ☐ |
| 34 | Logout | ☐ | ☐ |
| 35 | Blacklisted Refresh → 401 | ☐ | ☐ |
| 36 | Logout All Devices | ☐ | ☐ |
