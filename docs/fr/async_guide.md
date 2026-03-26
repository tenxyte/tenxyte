# Guide Async/Await

Les services Tenxyte Core offrent un support de premier ordre pour les opérations asynchrones via les modèles `async`/`await`. Ce guide explique comment utiliser efficacement les méthodes asynchrones dans les applications FastAPI et Django.

## Sommaire

- [Présentation](#présentation)
- [Référence des méthodes asynchrones](#référence-des-méthodes-asynchrones)
  - [CacheService](#cacheservice)
  - [JWTService](#jwtservice)
  - [TOTPService](#totpservice)
  - [MagicLinkService](#magiclinkservice)
  - [SessionService](#sessionservice)
  - [TaskService](#taskservice)
- [Quand utiliser l'asynchrone vs le synchrone](#quand-utiliser-lasynchrone-vs-le-synchrone)
- [Modèles spécifiques aux frameworks](#modèles-spécifiques-aux-frameworks)
  - [FastAPI (Asynchrone natif)](#fastapi-asynchrone-natif)
  - [Django (Compatible asynchrone)](#django-compatible-asynchrone)
- [Considérations de performance](#considérations-de-performance)
- [Pièges courants](#pièges-courants)

---

## Présentation

Tous les services Tenxyte Core fournissent des versions synchrones et asynchrones de leurs méthodes :

```python
# Synchrone (bloque jusqu'à la fin)
token = jwt_service.generate_access_token(user_id="123")

# Asynchrone (cède le contrôle à la boucle d'événements)
token = await jwt_service.generate_access_token_async(user_id="123")
```

**Principaux avantages de l'asynchrone :**
- Opérations d'E/S non bloquantes
- Meilleure gestion de la concurrence
- Débit amélioré pour les opérations liées aux E/S
- Intégration native avec FastAPI et les frameworks asynchrones modernes

---

## Référence des méthodes asynchrones

### CacheService

Toutes les opérations de cache ont des variantes asynchrones qui délèguent au backend de cache de manière asynchrone :

```python
from tenxyte.core.cache_service import InMemoryCacheService

cache = InMemoryCacheService()

# Opérations de base
await cache.set_async("key", "value", timeout=3600)
value = await cache.get_async("key")
exists = await cache.exists_async("key")
await cache.delete_async("key")

# Opérations de compteur
count = await cache.increment_async("counter", delta=1)

# Limitation de débit (renvoie : allowed, remaining, reset_time)
allowed, remaining, reset = await cache.check_rate_limit_async(
    key="rate:user:123",
    max_requests=100,
    window_seconds=60
)

# Mise sur liste noire de jetons (révocation JWT)
await cache.add_to_blacklist_async(jti="token-id", expires_in=3600)
is_blacklisted = await cache.is_blacklisted_async("token-id")
```

### JWTService

Les opérations sur les jetons prennent en charge l'asynchrone pour la validation et la mise sur liste noire non bloquantes :

```python
from tenxyte.core.jwt_service import JWTService

jwt_svc = JWTService(settings=settings, blacklist_service=cache)

# Générer des jetons (synchrone uniquement - opérations cryptographiques)
access_token, jti, exp = jwt_svc.generate_access_token(user_id="123")
refresh_token = jwt_svc.generate_refresh_token(user_id="123")

# Décoder et valider (asynchrone)
decoded = await jwt_svc.decode_token_async(token)
if decoded and decoded.is_valid:
    print(f"Utilisateur : {decoded.user_id}")

# Mise sur liste noire (E/S asynchrones)
await jwt_svc.blacklist_token_async(token, user_id="123")
await jwt_svc.blacklist_token_by_jti_async(jti="token-id", expires_at=datetime)

# Rafraîchir les jetons (asynchrone)
new_tokens = await jwt_svc.refresh_tokens_async(refresh_token)
if new_tokens:
    print(f"Nouveau jeton d'accès : {new_tokens.access_token}")

# Révocation au niveau utilisateur (asynchrone)
await jwt_svc.revoke_all_user_tokens_async(user_id="123")
```

### TOTPService

Authentification à deux facteurs avec adaptateurs de stockage asynchrones :

```python
from tenxyte.core.totp_service import TOTPService

totp_svc = TOTPService(settings=settings)

# Configuration 2FA (asynchrone avec stockage)
result = await totp_svc.setup_2fa_async(
    user_id="123",
    email="user@example.com",
    storage=async_storage_adapter
)
# Renvoie : secret, qr_code (base64), backup_codes

# Confirmer la configuration avec le code initial
ok, error = await totp_svc.confirm_2fa_setup_async(
    user_id="123",
    code="123456",
    storage=async_storage_adapter
)

# Vérifier lors de la connexion
ok, error = await totp_svc.verify_2fa_async(
    user_id="123",
    code="123456",
    storage=async_storage_adapter
)
# Renvoie (True, "") pour un code valide
# Renvoie (True, "") si la 2FA n'est pas activée (passage direct)
# Renvoie (False, "message d'erreur") si invalide

# Désactiver la 2FA
ok, error = await totp_svc.disable_2fa_async(
    user_id="123",
    code="123456",
    storage=async_storage_adapter
)

# Régénérer les codes de secours
ok, new_codes, error = await totp_svc.regenerate_backup_codes_async(
    user_id="123",
    code="123456",  # TOTP actuel ou code de secours
    storage=async_storage_adapter
)

# Vérifier un code autonome (pour des vérifications ponctuelles)
is_valid = await totp_svc.verify_code_async(
    secret=decrypted_secret,
    code="123456",
    user_id="123"  # Optionnel : pour la protection contre le rejeu
)
```

### MagicLinkService

Authentification sans mot de passe avec opérations asynchrones :

```python
from tenxyte.core.magic_link_service import MagicLinkService

magic_svc = MagicLinkService(
    settings=settings,
    email_service=email_service,
    repo=async_repo,
    user_lookup=async_user_lookup
)

# Demander un lien magique (envoie un e-mail de manière asynchrone)
success, error = await magic_svc.request_magic_link_async(
    email="user@example.com",
    application_id="app-123",
    ip_address="1.2.3.4",
    user_agent="Mozilla/5.0..."
)

# Vérifier le jeton du lien
result = await magic_svc.verify_magic_link_async(
    token="token-from-url",
    application_id="app-123",
    ip_address="1.2.3.4",
    require_same_device=True  # Optionnel : correspondance d'IP
)
# Renvoie MagicLinkResult avec :
# - success : bool
# - user_id : str (si succès)
# - error : str (si échec)
```

### SessionService

Gestion des sessions avec opérations asynchrones sur le cache et le repository :

```python
from tenxyte.core.session_service import SessionService

session_svc = SessionService(
    settings=settings,
    cache_service=async_cache,
    session_repository=async_repo
)

# Créer une session
session_data = await session_svc.create_session_async(
    user=user,
    device_id="device-123",
    ip_address="1.2.3.4",
    user_agent="Mozilla/5.0...",
    application_id="app-123"
)
# Renvoie un dictionnaire avec session_id, device_fingerprint, etc.

# Valider une session
session = await session_svc.validate_session_async(session_id)
if session:
    print(f"Session valide pour l'utilisateur : {session['user_id']}")

# Révoquer une session unique
await session_svc.revoke_session_async(session_id)

# Révoquer toutes les sessions d'un utilisateur
revoked_count = await session_svc.revoke_all_sessions_async(
    user_id="123",
    except_session_id="garder-celle-ci"  # Optionnel
)
```

### TaskService

Exécution de tâches en arrière-plan avec support asynchrone :

```python
from tenxyte.adapters.fastapi.task_service import AsyncIOTaskService

task_svc = AsyncIOTaskService()

# Ajouter une fonction synchrone à la file (s'exécute dans un pool de threads)
task_id = await task_svc.enqueue_async(send_email, user_id, message)

# Ajouter une fonction asynchrone à la file (s'exécute comme une tâche asyncio)
task_id = await task_svc.enqueue_async(async_webhook_call, payload)

# L'implémentation de base utilise to_thread pour les adaptateurs synchrones
# Les adaptateurs asynchrones natifs (AsyncIOTaskService) gèrent les deux de manière optimale
```

---

## Quand utiliser l'asynchrone vs le synchrone

### Utilisez l'asynchrone quand :

| Scénario | Raison |
|----------|--------|
| Points de terminaison FastAPI | Framework asynchrone natif ; les appels synchrones bloquants nuisent aux performances |
| Opérations d'E/S (cache, base de données, e-mail) | Ne bloquez pas la boucle d'événements en attendant le réseau ou le disque |
| Validation de jetons concurrente | Traitez plusieurs requêtes simultanément |
| Vérifications de limitation de débit | Consultations rapides du cache asynchrone |
| Mise sur liste noire de jetons | Écriture non bloquante dans le cache/la base de données |

### Utilisez le synchrone quand :

| Scénario | Raison |
----------|--------|
| Opérations cryptographiques | `jwt.encode()` est lié au CPU, pas aux E/S ; l'asynchrone ajoute une surcharge |
| Génération de code TOTP | `pyotp` est synchrone et rapide ; pas d'E/S |
| Hachage de mot de passe | `bcrypt` est lié au CPU ; utilisez le synchrone |
| Scripts monothreadés | Plus simple, aucune boucle d'événements nécessaire |
| Vues Django (non asynchrones) | Django traditionnel est orienté synchrone |

### Exemple : Choisir la bonne méthode

```python
from tenxyte.core.jwt_service import JWTService

jwt_svc = JWTService(settings=settings)

# Point de terminaison FastAPI - utilisez l'asynchrone
def create_access_token_async(user_id: str) -> str:
    # generate_access_token est synchrone (crypto), mais c'est correct
    # C'est rapide et lié au CPU
    token, _, _ = jwt_svc.generate_access_token(user_id)
    return token

# Point de terminaison FastAPI - validez avec l'asynchrone
def validate_token_async(token: str) -> Optional[DecodedToken]:
    # decode_token_async permet aux autres requêtes de continuer
    # pendant que nous vérifions la liste noire (opération d'E/S)
    return await jwt_svc.decode_token_async(token)

# Tâche en arrière-plan - envoyer une notification de révocation
def notify_logout_async(user_id: str, token: str):
    # La vérification et l'ajout à la liste noire sont des E/S
    await jwt_svc.blacklist_token_async(token, user_id)
```

---

## Modèles spécifiques aux frameworks

### FastAPI (Asynchrone natif)

FastAPI est conçu pour l'asynchrone. Utilisez `async def` pour tous les points de terminaison et préférez les méthodes asynchrones de Tenxyte :

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer

app = FastAPI()
security = HTTPBearer()

# Initialiser les services
jwt_svc = JWTService(settings=settings, blacklist_service=cache)

@app.post("/auth/login")
async def login(credentials: LoginCredentials):
    # Le synchrone convient pour les opérations crypto
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(401, "Identifiants invalides")
    
    access_token, _, _ = jwt_svc.generate_access_token(str(user.id))
    return {"access": access_token}

@app.get("/protected")
async def protected_route(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    
    # Utilisez la validation asynchrone pour ne pas bloquer les autres requêtes
    decoded = await jwt_svc.decode_token_async(token)
    
    if not decoded or not decoded.is_valid:
        raise HTTPException(401, "Jeton invalide")
    
    if decoded.is_blacklisted:
        raise HTTPException(401, "Jeton révoqué")
    
    return {"user_id": decoded.user_id}

@app.post("/auth/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    
    # Mise sur liste noire asynchrone
    await jwt_svc.blacklist_token_async(token)
    
    return {"status": "logged_out"}
```

### Django (Compatible asynchrone)

Django 4.2+ prend en charge les vues asynchrones. Utilisez `async def` avec les méthodes asynchrones de Tenxyte :

```python
# views.py
from django.http import JsonResponse
from django.views import View
from asgiref.sync import sync_to_async

from tenxyte.core.jwt_service import JWTService

jwt_svc = JWTService(settings=settings)

# Vue asynchrone basée sur une classe
class AsyncProtectedView(View):
    async def get(self, request):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "")
        
        # Validation de jeton asynchrone
        decoded = await jwt_svc.decode_token_async(token)
        
        if not decoded or not decoded.is_valid:
            return JsonResponse({"error": "Non autorisé"}, status=401)
        
        # Pour les opérations ORM, enveloppez les appels synchrones
        user = await sync_to_async(User.objects.get)(id=decoded.user_id)
        
        return JsonResponse({"user": user.email})

# Vue asynchrone basée sur une fonction
async def async_logout(request):
    token = extract_token_from_request(request)
    
    # Mise sur liste noire asynchrone
    await jwt_svc.blacklist_token_async(token)
    
    return JsonResponse({"status": "logged_out"})
```

**Note :** L'ORM de Django est toujours principalement synchrone. Utilisez l'enveloppe `sync_to_async` :

```python
from asgiref.sync import sync_to_async

# Envelopper les appels ORM
user = await sync_to_async(User.objects.get)(id=user_id)
sessions = await sync_to_async(list)(UserSession.objects.filter(user_id=user_id))
```

---

## Considérations de performance

### Pool de threads vs Asynchrone natif

| Adaptateur | `enqueue()` | `enqueue_async()` | Idéal pour |
|---------|-------------|-------------------|----------|
| `AsyncIOTaskService` | `run_in_executor` (thread pool) | `create_task` pour coroutines | FastAPI, pur asynchrone |
| `CeleryTaskService` | Worker Celery | Fallback `to_thread` | Tâches distribuées et lourdes |
| `RQTaskService` | Worker RQ | Fallback `to_thread` | File d'attente basée sur Redis |
| `SyncThreadTaskService` | `Thread` | Fallback `to_thread` | Dév, sans dépendances |

### Détails d'implémentation des méthodes asynchrones

```python
# Méthodes asynchrones de CacheService :
# - InMemoryCacheService : Utilise to_thread (les verrous sont synchrones)
# - RedisCacheService : Utilise le client asynchrone redis-py (E/S véritablement asynchrones)

# Méthodes asynchrones de JWTService :
# - decode_token_async : Vérification de liste noire asynchrone (E/S)
# - blacklist_token_async : Écriture en cache asynchrone (E/S)
# - refresh_tokens_async : Opérations DB/cache asynchrones

# Toutes les autres opérations crypto restent synchrones (liées au CPU)
```

### Banc d'essai : Vérification de liste noire Synchrone vs Asynchrone

```python
import asyncio
import time

# Simulation de 100 validations de jetons simultanées
async def benchmark():
    tokens = [generate_test_token() for _ in range(100)]
    
    # Version synchrone (bloquante)
    start = time.time()
    for token in tokens:
        jwt_svc.decode_token(token)  # E/S bloquantes
    sync_time = time.time() - start
    
    # Version asynchrone (concurrente)
    start = time.time()
    await asyncio.gather(*[
        jwt_svc.decode_token_async(token) for token in tokens
    ])
    async_time = time.time() - start
    
    print(f"Synchrone : {sync_time:.2f}s, Asynchrone : {async_time:.2f}s")
    # Résultat typique : Asynchrone 5 à 10 fois plus rapide pour les opérations liées aux E/S

asyncio.run(benchmark())
```

---

## Pièges courants

### 1. Oublier `await`

```python
# FAUX : Renvoie un objet coroutine, pas le résultat
decoded = jwt_svc.decode_token_async(token)  # await manquant !
if decoded.is_valid:  # AttributeError: 'coroutine' object has no attribute 'is_valid'
    ...

# CORRECT :
decoded = await jwt_svc.decode_token_async(token)
```

### 2. Appeler de l'asynchrone dans un contexte synchrone sans boucle d'événements

```python
# FAUX : Impossible d'utiliser await en dehors d'une fonction async
def sync_function():
    result = await cache.get_async("key")  # SyntaxError

# CORRECT : Utilisez asyncio.run() ou async def
async def async_function():
    result = await cache.get_async("key")

# Ou pour des scripts rapides :
import asyncio
result = asyncio.run(cache.get_async("key"))
```

### 3. Bloquer la boucle d'événements dans un contexte asynchrone

```python
# FAUX : Bloque toute la boucle d'événements
async def bad_endpoint():
    time.sleep(5)  # Bloque TOUTES les requêtes simultanées !
    return {"done": True}

# CORRECT : Utilisez async sleep ou exécutez dans un exécuteur
async def good_endpoint():
    await asyncio.sleep(5)  # Cède la place aux autres requêtes
    # OU pour les E/S synchrones :
    await asyncio.to_thread(blocking_io_function)
    return {"done": True}
```

### 4. Utiliser des méthodes synchrones dans FastAPI sans précaution

```python
# FAUX dans FastAPI : Bloque la boucle d'événements
@app.get("/slow")
def slow_endpoint():  # Note : def, pas async def
    time.sleep(10)  # Bloque toutes les autres requêtes !
    return {"done": True}

# CORRECT :
@app.get("/slow")
async def fast_endpoint():
    await asyncio.sleep(10)  # Les autres requêtes continuent
    return {"done": True}
```

### 5. Mélanger asynchrone et ORM Django incorrectement

```python
# FAUX : Appel direct à l'ORM dans une vue asynchrone
async def bad_view(request):
    user = User.objects.get(id=1)  # E/S synchrones dans un contexte asynchrone !

# CORRECT : Enveloppez l'ORM avec sync_to_async
from asgiref.sync import sync_to_async

async def good_view(request):
    user = await sync_to_async(User.objects.get)(id=1)
    # OU pour les requêtes renvoyant plusieurs objets :
    users = await sync_to_async(list)(User.objects.all())
```

---

## Référence rapide : Aide-mémoire des méthodes asynchrones

```python
# CacheService
await cache.get_async(key)
await cache.set_async(key, value, timeout)
await cache.delete_async(key)
await cache.exists_async(key)
await cache.increment_async(key, delta)
await cache.expire_async(key, timeout)
await cache.ttl_async(key)
await cache.add_to_blacklist_async(jti, expires_in)
await cache.is_blacklisted_async(jti)
await cache.remove_from_blacklist_async(jti)
await cache.check_rate_limit_async(key, max_requests, window_seconds)
await cache.reset_rate_limit_async(key)

# JWTService
decoded = await jwt_svc.decode_token_async(token)
await jwt_svc.blacklist_token_async(token, user_id)
await jwt_svc.blacklist_token_by_jti_async(jti, expires_at, user_id)
tokens = await jwt_svc.refresh_tokens_async(refresh_token)
await jwt_svc.revoke_all_user_tokens_async(user_id)

# TOTPService
setup = await totp_svc.setup_2fa_async(user_id, email, storage)
ok, err = await totp_svc.confirm_2fa_setup_async(user_id, code, storage)
ok, err = await totp_svc.verify_2fa_async(user_id, code, storage)
ok, err = await totp_svc.disable_2fa_async(user_id, code, storage)
ok, codes, err = await totp_svc.regenerate_backup_codes_async(user_id, code, storage)
is_valid = await totp_svc.verify_code_async(secret, code, user_id)

# MagicLinkService
ok, err = await magic_svc.request_magic_link_async(email, ...)
result = await magic_svc.verify_magic_link_async(token, ...)

# SessionService
session = await session_svc.create_session_async(user, ...)
session = await session_svc.validate_session_async(session_id)
await session_svc.revoke_session_async(session_id)
count = await session_svc.revoke_all_sessions_async(user_id)

# TaskService
task_id = await task_svc.enqueue_async(func, *args, **kwargs)
```

---

## Prochaines étapes

- [Task Service](task_service.md) — Traitement des tâches en arrière-plan
- [Démarrage rapide FastAPI](fastapi_quickstart.md) — Configuration complète de FastAPI
- [Architecture](architecture.md) — Comprendre les Ports et Adaptateurs
