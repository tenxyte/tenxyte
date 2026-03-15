# Service de Tâches — Jobs en Arrière-plan

Tenxyte fournit une abstraction unifiée pour l'exécution de tâches en arrière-plan via le port `TaskService`. Cela permet à votre application de mettre des jobs en file d'attente sans se coupler à des implémentations spécifiques comme Celery, RQ ou les `BackgroundTasks` de FastAPI.

## Table des Matières

- [Le Port TaskService](#le-port-taskservice)
- [Adaptateurs Disponibles](#adaptateurs-disponibles)
  - [Adaptateurs Django](#adaptateurs-django)
  - [Adaptateur FastAPI](#adaptateur-fastapi)
- [Exemples d'Utilisation](#exemples-dutilisation)
  - [Mise en File d'Attente de Tâches Synchrones](#mise-en-file-dattente-de-taches-synchrones)
  - [Mise en File d'Attente de Tâches Asynchrones](#mise-en-file-dattente-de-taches-asynchrones)
- [Configuration par Framework](#configuration-par-framework)
  - [Configuration Django](#configuration-django)
  - [Configuration FastAPI](#configuration-fastapi)
- [Création d'Adaptateurs TaskService Personnalisés](#creation-dadaptateurs-taskservice-personnalises)

---

## Le Port TaskService

La classe de base abstraite `TaskService` est définie dans `tenxyte.core.task_service` et propose deux méthodes :

| Méthode | Description |
|--------|-------------|
| `enqueue(func, *args, **kwargs)` | Met en file d'attente une fonction synchrone pour une exécution en arrière-plan. Retourne une chaîne d'ID de tâche. |
| `enqueue_async(func, *args, **kwargs)` | Met en file d'attente une fonction (sync ou async) de manière non bloquante. Détecte automatiquement les coroutines et les gère nativement. |

L'implémentation de la classe de base pour `enqueue_async` délègue dynamiquement à une méthode asynchrone native (`_enqueue_async_native`) si elle est disponible, ou se rabat sur l'exécution du `enqueue` synchrone dans un pool de threads via `asyncio.to_thread()`.

---

## Adaptateurs Disponibles

### Adaptateurs Django

Situés dans `tenxyte.adapters.django.task_service` :

| Adaptateur | Description | Quand l'utiliser |
|---------|-------------|-------------|
| `SyncThreadTaskService` | Exécute les tâches dans un thread d'arrière-plan à l'aide du module `threading` de Python. | Développement, tests, ou quand vous ne voulez pas de dépendances externes. Zéro configuration requise. |
| `CeleryTaskService` | Délègue à la file d'attente de tâches Celery. | Django en production avec Celery déjà configuré. |
| `RQTaskService` | Délègue à Django-RQ. | Django en production avec Redis Queue (RQ). |

#### SyncThreadTaskService

```python
from tenxyte.adapters.django.task_service import SyncThreadTaskService

task_service = SyncThreadTaskService()

# Envoi d'un e-mail de bienvenue en arrière-plan
def send_welcome_email(user_id):
    user = User.objects.get(id=user_id)
    # ... logique d'envoi d'e-mail

task_id = task_service.enqueue(send_welcome_email, user.id)
print(f"Tâche démarrée : {task_id}")  # Retourne le nom du thread
```

#### CeleryTaskService

```python
from tenxyte.adapters.django.task_service import CeleryTaskService
from celery import shared_task

task_service = CeleryTaskService()

# Option 1 : Utiliser une tâche Celery existante
@shared_task
def process_report(report_id):
    # ... traitement lourd
    pass

task_id = task_service.enqueue(process_report, report_id=123)

# Option 2 : Utiliser une fonction classique (emballée automatiquement dans une tâche Celery)
def cleanup_old_sessions():
    Session.objects.filter(expires__lt=timezone.now()).delete()

task_id = task_service.enqueue(cleanup_old_sessions)
```

**Prérequis :**
```bash
pip install tenxyte[django] celery
```

#### RQTaskService

```python
from tenxyte.adapters.django.task_service import RQTaskService

task_service = RQTaskService(queue_name="high")  # ou "default"

def generate_pdf(invoice_id):
    # ... logique de génération de PDF
    pass

task_id = task_service.enqueue(generate_pdf, invoice_id=456)
```

**Prérequis :**
```bash
pip install tenxyte[django] django-rq
```

---

### Adaptateur FastAPI

Situé dans `tenxyte.adapters.fastapi.task_service` :

| Adaptateur | Description | Quand l'utiliser |
|---------|-------------|-------------|
| `AsyncIOTaskService` | Exécution en arrière-plan basée sur asyncio natif via `asyncio.create_task()` et des pools de threads. | Applications FastAPI ou toute application Python purement asynchrone. |

#### AsyncIOTaskService

```python
from tenxyte.adapters.fastapi.task_service import AsyncIOTaskService
from fastapi import FastAPI

app = FastAPI()
task_service = AsyncIOTaskService()

# Fonction synchrone - s'exécute dans un pool de threads
def send_sms_notification(phone_number: str, message: str):
    # ... appel synchrone à une API SMS
    pass

# Fonction asynchrone - s'exécute comme une tâche asyncio
async def process_webhook(data: dict):
    # ... appels HTTP asynchrones vers des services externes
    async with httpx.AsyncClient() as client:
        await client.post("https://partner-api.example.com/webhook", json=data)

@app.post("/orders/")
async def create_order(order: OrderCreate):
    # Sauvegarde de la commande (appel DB synchrone)
    order_id = await save_order(order)
    
    # Mise en file d'attente de tâches de fond sans bloquer la réponse
    await task_service.enqueue_async(send_sms_notification, order.customer_phone, "Commande reçue !")
    await task_service.enqueue_async(process_webhook, {"order_id": order_id, "status": "created"})
    
    return {"order_id": order_id, "status": "created"}
```

**Caractéristiques clés :**
- Détecte automatiquement si la fonction est sync ou async
- Les fonctions async s'exécutent comme des `asyncio.Task` (non bloquant, même boucle d'événements)
- Les fonctions sync s'exécutent dans `loop.run_in_executor()` (pool de threads)
- Gestion des exceptions intégrée avec journalisation (logging)

**Prérequis :**
```bash
pip install tenxyte[fastapi]
```

---

## Exemples d'Utilisation

### Mise en File d'Attente de Tâches Synchrones

Tous les adaptateurs supportent la méthode synchrone `enqueue()` :

```python
from tenxyte.core.task_service import TaskService

def heavy_computation(data: list) -> dict:
    """Un travail intensif pour le CPU."""
    results = []
    for item in data:
        results.append(process_item(item))
    return {"processed": len(results)}

# Dans votre vue/endpoint
job_id = task_service.enqueue(heavy_computation, large_dataset)
# Retourne immédiatement, le calcul s'exécute en arrière-plan
```

### Mise en File d'Attente de Tâches Asynchrones

Utilisez `enqueue_async()` pour une exécution non bloquante, en particulier dans des contextes asynchrones :

```python
# Dans un endpoint asynchrone
async def handle_request(request):
    # Ceci ne bloquera pas la réponse même si la tâche est synchrone
    await task_service.enqueue_async(send_notification, user_id, message)
    return {"status": "accepted"}
```

**Comportement par adaptateur :**
- **AsyncIOTaskService** : Les fonctions async s'exécutent comme des `asyncio.Task` natives ; les fonctions sync utilisent le pool de threads.
- **CeleryTaskService/RQTaskService/SyncThreadTaskService** : Se rabat sur `asyncio.to_thread(self.enqueue, ...)`.

---

## Configuration par Framework

### Configuration Django

Ajoutez le service de tâches à vos réglages ou utilisez l'injection de dépendances :

```python
# settings.py
TENXYTE_TASK_SERVICE_CLASS = "tenxyte.adapters.django.task_service.CeleryTaskService"
TENXYTE_TASK_SERVICE_QUEUE = "default"  # Pour RQTaskService

# Ou dans votre couche de service
from tenxyte.adapters.django.task_service import CeleryTaskService
from tenxyte.core.email_service import EmailService

class AuthService:
    def __init__(self):
        self.task_service = CeleryTaskService()
        self.email_service = EmailService()
    
    def send_magic_link(self, user_id: str, email: str):
        # Génération du lien magique de manière synchrone
        token = self.generate_magic_token(user_id)
        
        # Envoi de l'e-mail de manière asynchrone
        self.task_service.enqueue(
            self.email_service.send_magic_link,
            to_email=email,
            magic_link_url=f"https://app.example.com/magic?token={token}",
            expires_in_minutes=15
        )
```

### Configuration FastAPI

Avec FastAPI, instanciez le service et injectez-le via une dépendance :

```python
# dependencies.py
from tenxyte.adapters.fastapi.task_service import AsyncIOTaskService

task_service = AsyncIOTaskService()

async def get_task_service() -> AsyncIOTaskService:
    return task_service

# main.py
from fastapi import Depends
from dependencies import get_task_service

@app.post("/auth/magic-link/")
async def request_magic_link(
    email: str,
    task_service: AsyncIOTaskService = Depends(get_task_service)
):
    # Validation de l'existence de l'e-mail
    user = await find_user_by_email(email)
    if not user:
        return {"status": "sent_if_exists"}  # Ne pas révéler si l'e-mail existe
    
    # Envoi du lien magique en arrière-plan (appel asynchrone du service e-mail)
    await task_service.enqueue_async(
        email_service.send_magic_link_async,
        to_email=email,
        magic_link_url=generate_magic_link(user.id),
        expires_in_minutes=15
    )
    
    return {"status": "sent_if_exists"}
```

---

## Création d'Adaptateurs TaskService Personnalisés

Pour intégrer un autre système de file d'attente (ex: Huey, ARQ, ou une file personnalisée), implémentez l'ABC `TaskService` :

```python
from tenxyte.core.task_service import TaskService
from typing import Any, Callable
import my_custom_queue

class CustomQueueTaskService(TaskService):
    """
    Adaptateur pour un système de file d'attente personnalisé.
    """
    
    def __init__(self, queue_url: str):
        self.client = my_custom_queue.Client(queue_url)
    
    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """
        Met en file d'attente une fonction synchrone.
        """
        # Sérialisation de l'appel de fonction
        job = self.client.submit(func, args=args, kwargs=kwargs)
        return job.id
    
    # Optionnel : Implémenter le support async natif pour de meilleures performances
    async def _enqueue_async_native(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> str:
        """
        Implémentation async native optionnelle.
        Si fournie, enqueue_async() l'utilisera à la place de to_thread().
        """
        # Si votre file possède un client async
        job = await self.client.async_submit(func, args=args, kwargs=kwargs)
        return job.id
```

Puis utilisez-le :

```python
task_service = CustomQueueTaskService("https://queue.example.com")

# Les utilisations sync et async fonctionnent toutes deux
task_service.enqueue(sync_function, arg1, arg2)
await task_service.enqueue_async(async_or_sync_function, arg1, arg2)
```

---

## Étapes Suivantes

- [Guide Async](async_guide.md) — Plongée au cœur des patterns async/await avec Tenxyte
- [Démarrage Rapide FastAPI](fastapi_quickstart.md) — Guide complet de configuration FastAPI
- [Adaptateurs Personnalisés](custom_adapters.md) — Création d'adaptateurs pour d'autres services (Cache, E-mail, etc.)
