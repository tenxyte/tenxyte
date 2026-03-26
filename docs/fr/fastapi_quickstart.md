# Démarrage Rapide avec FastAPI

Commencez avec Tenxyte dans une application FastAPI en 2 minutes. Ce guide couvre l'installation de Tenxyte avec le support FastAPI, la configuration des services de base et la mise en place des points de terminaison d'authentification.

## Table des Matières

- [Installation](#1-installation)
- [Configuration](#2-configurez-votre-application-fastapi)
- [Initialisation des Services de Base](#3-initialisation-des-services-de-base)
- [Création des Points de Terminaison](#4-creation-des-points-de-terminaison-dauthentification)
- [Exécution de l'Application](#5-execution-de-lapplication)
- [Exemples d'Utilisation](#exemples-dutilisation)
- [Considérations pour la Production](#considerations-pour-la-production)

---

## 1. Installation

Installez Tenxyte avec les extras FastAPI :

```bash
pip install tenxyte[fastapi,postgres]  # Inclut le support FastAPI + PostgreSQL
```

Extras disponibles pour FastAPI :
- `[fastapi]` — Dépendances de base FastAPI (fastapi, uvicorn, python-multipart)
- `[postgres]` — Support PostgreSQL (psycopg2-binary)
- `[mysql]` — Support MySQL (mysqlclient)
- `[webauthn]` — Support Passkeys/FIDO2
- `[all]` — Tout est inclus

---

## 2. Configurez Votre Application FastAPI

Créez votre fichier d'application principal :

```python
# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from tenxyte.core.settings import Settings, init
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.adapters.fastapi.task_service import AsyncIOTaskService

# Initialiser les paramètres
settings = init(provider=EnvSettingsProvider())

# Initialiser le service de tâches
task_service = AsyncIOTaskService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Événements de cycle de vie de l'application."""
    # Démarrage
    print("Démarrage des services Tenxyte...")
    yield
    # Arrêt
    print("Arrêt des services Tenxyte...")

app = FastAPI(
    title="Mon Application FastAPI avec Tenxyte",
    description="Authentification et sécurité propulsées par Tenxyte",
    version="1.0.0",
    lifespan=lifespan
)
```

### Variables d'Environnement

Créez un fichier `.env` :

```bash
# Requis pour JWT
TENXYTE_JWT_SECRET_KEY=votre-cle-secrete-jwt-super-secrete-dau-moins-32-caracteres

# Optionnel : Durée de vie des jetons
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME=3600
TENXYTE_JWT_REFRESH_TOKEN_LIFETIME=604800

# Optionnel : Paramètres de sécurité
TENXYTE_MAX_LOGIN_ATTEMPTS=5
TENXYTE_LOCKOUT_DURATION=300

# Base de données (exemple avec SQLAlchemy/asyncpg)
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
```

---

## 3. Initialisation des Services de Base

Configurez les services de base de Tenxyte avec vos adaptateurs d'infrastructure :

```python
# services.py
from tenxyte.core.jwt_service import JWTService
from tenxyte.core.cache_service import InMemoryCacheService
from tenxyte.core.email_service import ConsoleEmailService
from tenxyte.core.totp_service import TOTPService
from tenxyte.core.magic_link_service import MagicLinkService
from tenxyte.core.settings import Settings

from tenxyte.adapters.fastapi.task_service import AsyncIOTaskService

# Initialiser les services
settings = Settings(provider=EnvSettingsProvider())
cache_service = InMemoryCacheService()  # Ou adaptateur Redis
email_service = ConsoleEmailService()    # Ou adaptateur SendGrid
task_service = AsyncIOTaskService()

# Services de base
jwt_service = JWTService(
    settings=settings,
    blacklist_service=cache_service
)

totp_service = TOTPService(settings=settings)

magic_link_service = MagicLinkService(
    settings=settings,
    email_service=email_service,
    # repo et user_lookup seraient vos implémentations personnalisées
)
```

---

## 4. Création des Points de Terminaison d'Authentification

### Points de Terminaison d'Authentification JWT

```python
# auth_router.py
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from services import jwt_service, settings

router = APIRouter(prefix="/auth", tags=["Authentification"])

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authentifier l'utilisateur et retourner les jetons JWT."""
    # Vérifier les identifiants (implémentez votre propre vérification d'utilisateur)
    user = await verify_user_credentials(request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    
    # Générer les jetons
    access_token, jti, expires_at = jwt_service.generate_access_token(
        user_id=str(user.id),
        application_id="default"
    )
    refresh_token = jwt_service.generate_refresh_token(
        user_id=str(user.id),
        application_id="default"
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": int(settings.access_token_lifetime.total_seconds())
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """Rafraîchir le jeton d'accès en utilisant le jeton de rafraîchissement."""
    token_pair = await jwt_service.refresh_tokens_async(refresh_token)
    if not token_pair:
        raise HTTPException(status_code=401, detail="Jeton de rafraîchissement invalide")
    
    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "token_type": token_pair.token_type,
        "expires_in": token_pair.expires_in
    }

@router.post("/logout")
async def logout(authorization: str = Header(...)):
    """Se déconnecter et mettre le jeton sur liste noire."""
    token = authorization.replace("Bearer ", "")
    await jwt_service.blacklist_token_async(token)
    return {"status": "deconnecte"}
```

### Dépendance pour les Routes Protégées

```python
# dependencies.py
from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services import jwt_service

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dépendance pour extraire et valider le jeton JWT."""
    token = credentials.credentials
    
    decoded = await jwt_service.decode_token_async(token)
    if not decoded or not decoded.is_valid:
        raise HTTPException(status_code=401, detail="Jeton invalide")
    
    if decoded.is_blacklisted:
        raise HTTPException(status_code=401, detail="Le jeton a été révoqué")
    
    # Charger l'utilisateur depuis la base de données
    user = await get_user_by_id(decoded.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
    
    return user

# Utilisation dans les routes protégées
@app.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}
```

### Points de Terminaison 2FA

```python
# twofa_router.py
from fastapi import APIRouter, Depends, HTTPException
from services import totp_service, settings

router = APIRouter(prefix="/2fa", tags=["2FA"])

class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code: str  # Code QR encodé en Base64
    backup_codes: list[str]

@router.post("/setup", response_model=TOTPSetupResponse)
async def setup_2fa(current_user: User = Depends(get_current_user)):
    """Configurer la 2FA TOTP pour l'utilisateur actuel."""
    # Votre adaptateur de stockage personnalisé
    storage = UserTOTPStorage(user_id=current_user.id)
    
    result = await totp_service.setup_2fa_async(
        user_id=str(current_user.id),
        email=current_user.email,
        storage=storage
    )
    
    return {
        "secret": result.secret,
        "qr_code": result.qr_code,
        "backup_codes": result.backup_codes
    }

@router.post("/confirm")
async def confirm_2fa_setup(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Confirmer la configuration TOTP avec le code de vérification."""
    storage = UserTOTPStorage(user_id=current_user.id)
    
    success, error = await totp_service.confirm_2fa_setup_async(
        user_id=str(current_user.id),
        code=code,
        storage=storage
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    return {"status": "2fa_activee"}

@router.post("/verify")
async def verify_2fa(
    user_id: str,
    code: str
):
    """Vérifier le code TOTP pendant la connexion."""
    storage = UserTOTPStorage(user_id=user_id)
    
    success, error = await totp_service.verify_2fa_async(
        user_id=user_id,
        code=code,
        storage=storage
    )
    
    if not success:
        raise HTTPException(status_code=401, detail=error or "Code invalide")
    
    return {"status": "verifie"}
```

---

## 5. Exécution de l'Application

```bash
uvicorn main:app --reload
```

Visitez `http://localhost:8000/docs` pour la documentation interactive de l'API.

---

## Exemples d'Utilisation

### Flux de Connexion Complet avec 2FA

```python
@app.post("/login/step1")
async def login_step1(request: LoginRequest):
    """Première étape : valider les identifiants."""
    user = await verify_user_credentials(request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    
    # Vérifier si la 2FA est activée
    storage = UserTOTPStorage(user_id=user.id)
    user_data = await storage.load_user_data_async(str(user.id))
    
    if user_data and user_data.is_2fa_enabled:
        # Retourner un jeton temporaire pour l'étape 2FA
        temp_token = jwt_service.generate_access_token(
            user_id=str(user.id),
            application_id="default",
            extra_claims={"2fa_pending": True}
        )[0]
        return {"requires_2fa": True, "temp_token": temp_token}
    
    # Pas de 2FA requise, retourner les jetons complets
    access_token, _, _ = jwt_service.generate_access_token(str(user.id), application_id="default")
    refresh_token = jwt_service.generate_refresh_token(str(user.id), application_id="default")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "requires_2fa": False
    }

@app.post("/login/step2")
async def login_step2(code: str, temp_token: str):
    """Deuxième étape : valider le code 2FA."""
    # Vérifier le jeton temporaire
    decoded = await jwt_service.decode_token_async(temp_token)
    if not decoded or not decoded.extra_claims.get("2fa_pending"):
        raise HTTPException(status_code=401, detail="Session invalide")
    
    # Vérifier le code 2FA
    storage = UserTOTPStorage(user_id=decoded.user_id)
    success, error = await totp_service.verify_2fa_async(
        user_id=decoded.user_id,
        code=code,
        storage=storage
    )
    
    if not success:
        raise HTTPException(status_code=401, detail=error)
    
    # Délivrer les jetons finaux
    access_token, _, _ = jwt_service.generate_access_token(decoded.user_id, application_id="default")
    refresh_token = jwt_service.generate_refresh_token(decoded.user_id, application_id="default")
    
    return {"access_token": access_token, "refresh_token": refresh_token}
```

### Exemple de Tâche en Arrière-plan

```python
from services import task_service, email_service

@app.post("/register")
async def register(request: RegisterRequest):
    """Enregistrer l'utilisateur et envoyer un email de bienvenue en arrière-plan."""
    # Créer l'utilisateur (opération de base de données synchrone)
    user = await create_user(request.email, request.password)
    
    # Envoyer l'email de bienvenue de manière asynchrone
    await task_service.enqueue_async(
        email_service.send_welcome_async,
        to_email=user.email,
        first_name=user.first_name,
        login_url="https://app.example.com/login"
    )
    
    return {"user_id": user.id, "status": "enregistre"}
```

---

## Considérations pour la Production

### 1. Utilisez un Cache de Niveau Production

Remplacez `InMemoryCacheService` par un adaptateur Redis pour les déploiements multi-instances. Tenxyte ne fournit pas d'adaptateur Redis intégré, mais en créer un est simple (voir [Adaptateurs Personnalisés](custom_adapters.md)) :

```python
# Voir custom_adapters.md pour l'implémentation complète de RedisCacheAdapter
from my_adapters.cache import RedisCacheAdapter

cache_service = RedisCacheAdapter(redis_url="redis://localhost:6379/0")

jwt_service = JWTService(settings=settings, blacklist_service=cache_service)
```

### 2. Configurez CORS

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://votredomaine.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Limitation de Débit (Rate Limiting)

```python
from fastapi import Request
from services import cache_service

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client_ip = request.client.host
    allowed, remaining, reset_time = await cache_service.check_rate_limit_async(
        key=f"rate_limit:{client_ip}",
        max_requests=100,  # requêtes
        window_seconds=60  # par minute
    )
    
    if not allowed:
        raise HTTPException(status_code=429, detail="Limite de débit dépassée")
    
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response
```

### 4. Authentification de l'Application

Pour l'authentification au niveau de l'application (clés API), utilisez directement le modèle `Application` :

```python
from fastapi import Security, HTTPException, Header
from tenxyte.models import get_application_model

Application = get_application_model()

async def verify_app_credentials(
    access_key: str = Header(..., alias="X-Access-Key"),
    access_secret: str = Header(..., alias="X-Access-Secret")
):
    from asgiref.sync import sync_to_async
    try:
        app = await sync_to_async(Application.objects.get)(
            access_key=access_key, is_active=True
        )
    except Application.DoesNotExist:
        raise HTTPException(status_code=401, detail="Identifiants d'application invalides")
    
    if not app.verify_secret(access_secret):
        raise HTTPException(status_code=401, detail="Identifiants d'application invalides")
    return app

@app.get("/protected")
async def protected_endpoint(app = Security(verify_app_credentials)):
    return {"message": f"Bonjour de la part de {app.name}"}
```

---

## Prochaines Étapes

- [Service de Tâches](task_service.md) — Traitement des tâches en arrière-plan avec AsyncIOTaskService
- [Guide Async](async_guide.md) — Plongée profonde dans les modèles asynchrones avec Tenxyte
- [Architecture](architecture.md) — Comprendre les Ports et Adaptateurs
- [Référence des Paramètres](settings.md) — Toutes les options de configuration
- [Adaptateurs Personnalisés](custom_adapters.md) — Créez vos propres adaptateurs

---

## Comparaison : Django vs FastAPI

| Fonctionnalité | Django | FastAPI |
|---------|--------|---------|
| Configuration | `tenxyte.setup()` | Initialisation manuelle des services |
| ORM | Django ORM (intégré) | SQLAlchemy, Tortoise, ou n'importe quel ORM async |
| File de Tâches | Celery, RQ, ou threads | Asyncio natif |
| Middleware d'Auth | Automatique | Injection de dépendance manuelle |
| Panneau d'Administration | Intégré | Nécessite une implémentation personnalisée |
| Support Async | Partiel (Django 4.2+) | Natif |

Les deux frameworks utilisent les **mêmes services de base** — votre logique d'authentification est portable !
