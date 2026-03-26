# Création d'Adaptateurs Personnalisés

L'architecture **Ports et Adaptateurs** de Tenxyte permet d'étendre ou de remplacer extrêmement facilement des parties spécifiques du système sans modifier la logique métier centrale.

Si vous utilisez un framework autre que Django ou FastAPI, ou si vous souhaitez utiliser un ORM de base de données, un système de cache ou un fournisseur SMS différent, vous pouvez écrire vos propres adaptateurs personnalisés.

## Le Concept

La logique du Noyau (Core) repose sur des interfaces abstraites appelées **Ports**. Ceux-ci sont définis à deux endroits :

- **`tenxyte.ports`** — Interfaces de repository (`UserRepository`, `OrganizationRepository`, `RoleRepository`, `AuditLogRepository`) et protocoles de service (`EmailService`, `CacheService`).
- **`tenxyte.core`** — Classes de base abstraites (ABC) des services du noyau (`EmailService`, `CacheService`, `JWTService`, `TOTPService`, etc.) avec des implémentations de base plus riches.

Pour utiliser une implémentation personnalisée, il vous suffit de créer une classe qui hérite de la classe de base abstraite correspondante, d'implémenter les méthodes requises et de passer votre instance d'adaptateur aux services du Noyau.

## Exemple 1 : Service de Cache Personnalisé

L'ABC `CacheService` (définie dans `tenxyte.core.cache_service`) nécessite l'implémentation de sept méthodes abstraites : `get`, `set`, `delete`, `exists`, `increment`, `expire` et `ttl`.

Supposons que vous souhaitiez utiliser Redis :

```python
from tenxyte.core.cache_service import CacheService
from typing import Any, Optional
import redis

class RedisCacheAdapter(CacheService):
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.client = redis.from_url(redis_url)

    def get(self, key: str) -> Optional[Any]:
        val = self.client.get(key)
        return val.decode("utf-8") if val else None

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        self.client.set(key, value, ex=timeout)
        return True

    def delete(self, key: str) -> bool:
        self.client.delete(key)
        return True

    def exists(self, key: str) -> bool:
        return bool(self.client.exists(key))

    def increment(self, key: str, delta: int = 1) -> int:
        return self.client.incr(key, delta)

    def expire(self, key: str, timeout: int) -> bool:
        return bool(self.client.expire(key, timeout))

    def ttl(self, key: str) -> int:
        return self.client.ttl(key)
```

> **Note :** La classe de base `CacheService` fournit également des méthodes utilitaires intégrées `add_to_blacklist`, `is_blacklisted`, `check_rate_limit` et `reset_rate_limit` qui fonctionnent automatiquement une fois les méthodes abstraites implémentées.

## Exemple 2 : Service d'E-mail Personnalisé

L'ABC `EmailService` (définie dans `tenxyte.core.email_service`) nécessite l'implémentation d'une méthode abstraite : `send`. Les méthodes de plus haut niveau comme `send_magic_link`, `send_two_factor_code`, `send_password_reset`, etc. sont déjà implémentées dans la classe de base en appelant `send`.

```python
from tenxyte.core.email_service import EmailService
from typing import List, Optional
import requests

class PostmarkEmailAdapter(EmailService):
    def __init__(self, api_token: str, from_email: str):
        self.api_token = api_token
        self.from_email = from_email

    def send(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments=None,
    ) -> bool:
        response = requests.post(
            "https://api.postmarkapp.com/email",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Postmark-Server-Token": self.api_token
            },
            json={
                "From": from_email or self.from_email,
                "To": to_email,
                "Subject": subject,
                "TextBody": body,
                "HtmlBody": html_body
            }
        )
        return response.status_code == 200
```

## Exemple 3 : Repositories Personnalisés (ORM de Base de Données)

Les repositories sont la manière dont le Noyau lit et écrit les entités (utilisateurs, rôles, organisations) depuis la base de données. L'ABC `UserRepository` est définie dans `tenxyte.ports.repositories` et utilise la dataclass `User` du même module.

```python
from tenxyte.ports.repositories import UserRepository, User
from typing import Any, Dict, List, Optional
from datetime import datetime

class CustomUserRepository(UserRepository):
    def get_by_id(self, user_id: str) -> Optional[User]:
        # logique de base de données personnalisée
        pass

    def get_by_email(self, email: str) -> Optional[User]:
        # logique de base de données personnalisée
        pass

    def create(self, user: User) -> User:
        # logique de base de données personnalisée — reçoit une dataclass User
        pass

    def update(self, user: User) -> User:
        # logique de base de données personnalisée — reçoit une dataclass User
        pass

    def delete(self, user_id: str) -> bool:
        pass

    def list_all(self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None) -> List[User]:
        pass

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        pass

    def update_last_login(self, user_id: str, timestamp: datetime) -> bool:
        pass

    def set_mfa_secret(self, user_id: str, mfa_type, secret: str) -> bool:
        pass

    def verify_email(self, user_id: str) -> bool:
        pass
```

## Exemple 4 : Service de Tâches Personnalisé

L'ABC `TaskService` (définie dans `tenxyte.core.task_service`) fournit une interface pour l'exécution de tâches en arrière-plan. Elle nécessite l'implémentation de la méthode `enqueue` pour l'exécution synchrone, et optionnellement `_enqueue_async_native` pour un support asynchrone natif.

### Adaptateur Basique Synchrone Uniquement

```python
from tenxyte.core.task_service import TaskService
from typing import Any, Callable
import my_task_queue

class CustomTaskService(TaskService):
    """
    Adaptateur pour une file de tâches personnalisée (ex : Huey, ARQ ou implémentation maison).
    """
    
    def __init__(self, queue_url: str):
        self.client = my_task_queue.Client(queue_url)
    
    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """
        Ajouter une fonction synchrone à la file pour exécution en arrière-plan.
        Doit retourner une chaîne d'ID de tâche.
        """
        job = self.client.submit(func, args=args, kwargs=kwargs)
        return job.id
```

### Adaptateur Asynchrone Complet

Pour des performances optimales dans les applications asynchrones (FastAPI), implémentez le support asynchrone natif :

```python
from tenxyte.core.task_service import TaskService
from typing import Any, Callable, Coroutine, Union
import asyncio

class AsyncCustomTaskService(TaskService):
    """
    Adaptateur de service de tâches entièrement asynchrone avec support natif des coroutines.
    """
    
    def __init__(self, queue_url: str):
        self.sync_client = my_task_queue.Client(queue_url)
        self.async_client = my_task_queue.AsyncClient(queue_url)
    
    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """Ajout synchrone — s'exécute dans un worker en arrière-plan."""
        job = self.sync_client.submit(func, args=args, kwargs=kwargs)
        return job.id
    
    async def _enqueue_async_native(
        self, 
        func: Union[Callable[..., Coroutine[Any, Any, Any]], Callable[..., Any]], 
        *args: Any, 
        **kwargs: Any
    ) -> str:
        """
        Ajout asynchrone natif — utilisé automatiquement par enqueue_async().
        Cette méthode est appelée par la classe de base lorsqu'elle est disponible.
        """
        if asyncio.iscoroutinefunction(func):
            # C'est une fonction asynchrone — créer la coroutine et soumettre
            coro = func(*args, **kwargs)
            job = await self.async_client.submit_coro(coro)
        else:
            # C'est une fonction synchrone — soumettre au client asynchrone
            job = await self.async_client.submit(func, args=args, kwargs=kwargs)
        return job.id
```

### Exemple d'Utilisation

```python
# Initialisez votre adaptateur personnalisé
task_service = AsyncCustomTaskService("https://queue.example.com")

# Ajouter une fonction synchrone
job_id = task_service.enqueue(send_email, user_id=123, subject="Bienvenue")

# Ajouter une fonction asynchrone (fonctionne dans un contexte asynchrone)
await task_service.enqueue_async(async_webhook_call, payload=data)

# Les deux fonctionnent de manière transparente avec les services Tenxyte
from tenxyte.core.magic_link_service import MagicLinkService

magic_link_service = MagicLinkService(
    settings=settings,
    email_service=email_service,
    repo=repo,
    user_lookup=user_lookup,
    task_service=task_service  # Injecté pour l'envoi d'e-mails asynchrone
)
```

> **Note :** Si vous n'implémentez que `enqueue()`, la méthode `enqueue_async()` de la classe de base se repliera automatiquement sur l'exécution de `enqueue()` dans un pool de threads en utilisant `asyncio.to_thread()`. L'implémentation de `_enqueue_async_native()` est facultative mais recommandée pour de meilleures performances dans les applications asynchrones.

---

## Assemblage Final

Une fois que vous avez vos adaptateurs personnalisés, vous les passez aux services du Noyau lors de l'initialisation de votre application. Chaque service du Noyau (ex : `JWTService`, `TOTPService`, `MagicLinkService`) accepte des dépendances spécifiques dans son constructeur.

```python
from tenxyte.core.settings import Settings, init
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.jwt_service import JWTService

# 1. Initialisez vos adaptateurs personnalisés
my_cache = RedisCacheAdapter()
my_email = PostmarkEmailAdapter(api_token="...", from_email="...")
my_user_repo = CustomUserRepository()

# 2. Configurez les paramètres du noyau avec un fournisseur
#    (lit les variables TENXYTE_* de l'environnement)
settings = init(provider=EnvSettingsProvider())

# 3. Instanciez les services du noyau
jwt_service = JWTService(settings=settings)

# 4. Utilisez les services du noyau dans les points de terminaison de votre framework !
# token_pair = jwt_service.generate_token_pair(user_id="123", ...)
```

> **Conseil :** Pour les projets Django, l'adaptateur `DjangoSettingsProvider` lit automatiquement les paramètres `TENXYTE_*` depuis `django.conf.settings`. Pour FastAPI, utilisez `EnvSettingsProvider` ou passez les paramètres directement.

En implémentant les méthodes abstraites définies dans `tenxyte.core` et `tenxyte.ports`, vos adaptateurs personnalisés sont garantis d'être entièrement compatibles avec la logique de sécurité interne, la 2FA, la génération de JWT et les systèmes RBAC de Tenxyte.
