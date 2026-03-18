# 🔧 Tests Nécessitant une Réécriture - Tenxyte v0.10.0.0

## 📋 Contexte

La migration legacy a supprimé les services suivants :
- ❌ `AuthService` (supprimé - pas de remplacement direct)
- ❌ `JWTService` legacy (remplacé par core avec API différente)
- ❌ `TOTPService` legacy (remplacé par core)
- ❌ `MagicLinkService` legacy (remplacé par core)
- ❌ `WebAuthnService` legacy (remplacé par core)
- ❌ `EmailService` legacy (remplacé par DjangoEmailService)

**Problème** : Les tests utilisent l'API legacy qui est incompatible avec l'API core.

---

## ⚠️ Tests Échouant Actuellement

### **1. test_jwt.py** (8/9 tests échouent)

**Problème** : L'ancien `JWTService.generate_access_token()` retournait un tuple `(token, jti, expires_at)`.  
Le nouveau core retourne un objet `TokenPair` avec `.access_token` et `.refresh_token`.

**Tests affectés** :
- `test_generate_access_token` - attend un tuple de 3 éléments
- `test_decode_token` - attend un tuple de 3 éléments
- `test_is_token_valid` - attend un tuple de 3 éléments
- `test_get_user_id_from_token` - attend un tuple de 3 éléments
- `test_get_application_id_from_token` - attend un tuple de 3 éléments
- `test_generate_token_pair` - attend un dict avec `access_token` et `refresh_token`
- `test_extra_claims` - attend un tuple de 3 éléments
- `test_rs256_asymmetric_keys` - vérifie `is_asymmetric` property

**Solution** : Réécrire ces tests pour utiliser l'API core directement.

---

### **2. test_db_auth_flow.py** (7 tests échouent)

**Problème** : Utilise `AuthService` qui n'existe plus.

**Tests affectés** :
```python
# Ligne 36
self.auth_service = AuthService()  # ❌ N'existe plus

# Utilisation dans les tests
success, data, _ = auth_service.authenticate_by_email(...)  # ❌ API supprimée
```

**Solution** : Utiliser directement les vues Django ou créer un helper qui appelle les endpoints.

---

### **3. test_security.py** (Plusieurs tests échouent)

**Problème** : Utilise `AuthService` pour l'authentification dans les tests.

**Tests affectés** :
- `test_tampered_token_rejected` (ligne 47)
- `test_blacklisted_token_rejected` (ligne 143)
- `test_revoked_refresh_token_rejected` (ligne 434)
- `test_logout_invalidates_refresh_token` (ligne 467)
- `test_banned_user_cannot_authenticate_with_jwt` (ligne 576)
- `test_banned_user_cannot_access_any_protected_endpoint` (ligne 722)

**Solution** : Utiliser l'API REST directement via `APIClient`.

---

## ✅ Solutions Recommandées

### **Option 1 : Réécrire les tests (RECOMMANDÉ)**

Adapter les tests pour utiliser l'API core ou les endpoints REST :

```python
# ❌ AVANT (legacy)
from tenxyte.services import AuthService, JWTService

auth_service = AuthService()
success, data, _ = auth_service.authenticate_by_email(
    email=user.email,
    password="password"
)
token = data['access_token']

# ✅ APRÈS (core ou REST)
# Option A: Via REST API
from rest_framework.test import APIClient

client = APIClient()
response = client.post('/api/v1/auth/login/', {
    'email': user.email,
    'password': 'password',
    'application_id': str(app.id),
    'application_secret': app_secret
})
token = response.data['access_token']

# Option B: Via core directement
from tenxyte.core.jwt_service import JWTService
from tenxyte.adapters.django import get_django_settings
from tenxyte.adapters.django.cache_service import DjangoCacheService

jwt_service = JWTService(
    settings=get_django_settings(),
    blacklist_service=DjangoCacheService()
)
token_pair = jwt_service.generate_token_pair(
    user_id=str(user.id),
    application_id=str(app.id),
    refresh_token_str=secrets.token_urlsafe(32)
)
token = token_pair.access_token
```

### **Option 2 : Créer un AuthHelper pour les tests**

Créer un helper qui encapsule la logique d'authentification :

```python
# tests/integration/django/test_helpers.py

def authenticate_user(email, password, app, app_secret):
    """
    Authentifie un utilisateur et retourne les tokens.
    
    Returns:
        dict: {'access_token': str, 'refresh_token': str, 'user': User}
    """
    from rest_framework.test import APIClient
    
    client = APIClient()
    response = client.post('/api/v1/auth/login/', {
        'email': email,
        'password': password,
        'application_id': str(app.id),
        'application_secret': app_secret
    })
    
    if response.status_code == 200:
        return {
            'access_token': response.data['access_token'],
            'refresh_token': response.data['refresh_token'],
            'user': response.data.get('user')
        }
    return None
```

---

## 📊 Statistiques

### **Tests Migrés Automatiquement** ✅
- **25 fichiers** migrés avec succès (imports corrigés)
- Script `migrate_test_imports.py` créé et fonctionnel

### **Tests Nécessitant Réécriture** ⚠️
- **test_jwt.py** : 8/9 tests (API incompatible)
- **test_db_auth_flow.py** : 7 tests (AuthService supprimé)
- **test_security.py** : 6+ tests (AuthService supprimé)
- **Autres tests** : À vérifier individuellement

### **Estimation Temps de Réécriture**
- **test_jwt.py** : ~2h (réécriture complète)
- **test_db_auth_flow.py** : ~1h (remplacer AuthService par REST API)
- **test_security.py** : ~1h (remplacer AuthService par REST API)
- **Total estimé** : ~4-5h

---

## 🎯 Plan d'Action

### **Priorité HAUTE** (Bloquer la release)
1. ✅ Corriger `account_deletion_service.py` (EmailService) - **FAIT**
2. ⚠️ Réécrire `test_jwt.py` pour utiliser l'API core
3. ⚠️ Créer `authenticate_user()` helper pour remplacer AuthService
4. ⚠️ Migrer `test_db_auth_flow.py` et `test_security.py`

### **Priorité MOYENNE** (Amélioration)
5. Vérifier tous les autres tests Django
6. Mettre à jour la documentation des tests
7. Créer des exemples de migration pour les utilisateurs

### **Priorité BASSE** (Optionnel)
8. Supprimer `LegacyJWTServiceWrapper` (inutile si tests réécrits)
9. Nettoyer `migrate_test_imports.py` (garder pour référence)

---

## 📝 Notes Importantes

### **Pourquoi le wrapper ne fonctionne pas**

Le `LegacyJWTServiceWrapper` créé dans `test_helpers.py` ne peut pas fournir une compatibilité 100% car :

1. **API différente** : L'ancien `generate_access_token()` retournait `(token, jti, expires_at)`, le nouveau retourne un objet `TokenPair`
2. **Paramètres différents** : Le core nécessite `refresh_token_str` obligatoire
3. **Types de retour** : Dict vs objets typés (TokenPair, DecodedToken)

**Conclusion** : Il est plus propre de réécrire les tests que de maintenir un wrapper complexe.

---

## ✅ Ce Qui Fonctionne

- ✅ Code source 100% migré (middleware, decorators, authentication, etc.)
- ✅ Services actifs utilisent core/adapters
- ✅ Imports des tests migrés automatiquement (25 fichiers)
- ✅ Application fonctionne normalement (routes, vues, etc.)
- ✅ Tests core passent (non affectés)

---

**Dernière mise à jour** : 16 mars 2026, 22:40  
**Status** : Migration code ✅ | Tests Django ⚠️ (réécriture nécessaire)
