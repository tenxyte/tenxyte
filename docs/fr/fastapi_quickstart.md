# Démarrage Rapide avec FastAPI

Obtenez un premier appel API authentifié contre l'adaptateur FastAPI de Tenxyte en environ cinq
minutes, grâce à l'**App_Factory** intégrée — aucun câblage manuel de services requis.

## Table des Matières

- [1. Installation](#1-installation)
- [2. Créer l'application](#2-creer-lapplication)
- [3. La lancer](#3-la-lancer)
- [4. Créer une Application (identifiants API)](#4-creer-une-application-identifiants-api)
- [5. Votre premier appel API](#5-votre-premier-appel-api)
- [Étapes suivantes](#etapes-suivantes)
- [Considérations pour la production](#considerations-pour-la-production)

---

## 1. Installation

```bash
pip install "tenxyte[fastapi]"
```

Ceci installe FastAPI, uvicorn, SQLAlchemy 2.0 (async), aiosqlite (le pilote de base de données de
développement par défaut), Alembic, et httpx — tout ce dont l'adaptateur a besoin. Django n'est
**pas** installé ; les deux adaptateurs sont entièrement indépendants (`pip freeze | grep -i
django` reste vide).

Extras disponibles :
- `[fastapi]` — tout ce qui précède.
- `[webauthn]` — à ajouter pour le support Passkeys/FIDO2 (endpoints `webauthn/*`).
- `[postgres]` / `[mysql]` — si vous n'utilisez pas le pilote SQLite de développement par défaut,
  installez vous-même le pilote async de votre base de données (par exemple `asyncpg` pour
  Postgres) — ce n'est pas une dépendance obligatoire de `[fastapi]`, puisqu'elle varie selon le
  déploiement.

## 2. Créer l'application

```python
# main.py
from tenxyte.adapters.fastapi.app import create_tenxyte_app

app = create_tenxyte_app()
```

C'est tout — `create_tenxyte_app()` renvoie une application `FastAPI` entièrement câblée et
exécutable : chaque endpoint de chaque Parity_Group porté (inscription, connexion, réinitialisation
de mot de passe, OTP, 2FA, liens magiques, passkeys, connexion sociale, RBAC, applications,
organisations, RGPD, délégation d'agent AIRS, routes admin), adossée à une vraie couche ORM
SQLAlchemy async (le **Reference_Stack**) dont les tables sont créées automatiquement au démarrage
— aucun `NotImplementedError` nulle part, aucune dépendance à fournir vous-même au préalable.

Les réglages sont lus depuis les variables d'environnement `TENXYTE_*` par défaut (via
`EnvSettingsProvider` — voir [Référence des réglages](settings.md) pour la chaîne de priorité
complète `Adapter_Custom > OS env > .env > préréglage > défaut` partagée par les deux
adaptateurs). Le seul réglage que vous devez fournir est le secret de signature JWT. Un fichier
`.env` dans ce répertoire est le plus simple — chargé automatiquement, aucun flag requis :

```bash
# .env
TENXYTE_JWT_SECRET_KEY=a-changer-pour-un-vrai-secret-d-au-moins-32-caracteres
```

Une vraie variable d'environnement OS fonctionne aussi (et gagne toujours face au `.env` si les
deux sont définis), mais seulement pour la session shell où elle a été définie — rouvrir un
terminal la fait disparaître, la raison la plus fréquente pour laquelle une configuration qui
« marchait » se plaint soudain que le secret manque :

```bash
export TENXYTE_JWT_SECRET_KEY="a-changer-pour-un-vrai-secret-d-au-moins-32-caracteres"
# PowerShell : $env:TENXYTE_JWT_SECRET_KEY = "..."
```

## 3. La lancer

```bash
uvicorn main:app --reload
```

La documentation interactive (Swagger UI) est à `http://localhost:8000/api/v1/docs/` — sous le
même préfixe API que tous les autres endpoints, pas le `/docs` racine par défaut de FastAPI lui-
même, donc exempte de l'authentification applicative (étape 4) de la même façon que la convention
de documentation de Django elle-même.

## 4. Créer une Application (identifiants API)

L'authentification au niveau application (`X-Access-Key`/`X-Access-Secret`) est **activée par
défaut** (`TENXYTE_APPLICATION_AUTH_ENABLED=true`), comme le propre défaut de l'adaptateur Django
— chaque requête vers un chemin non exempté a besoin de ces deux en-têtes. Créez une application
une seule fois, en amont :

```python
# create_application.py — à exécuter une fois contre la base de votre app en cours d'exécution
import asyncio

from tenxyte.adapters.fastapi import db
from tenxyte.adapters.fastapi.application_auth import create_application


async def main():
    engine = db.create_engine()  # même fichier SQLite par défaut que main.py vient de créer
    session_factory = db.create_session_factory(engine)
    async with session_factory() as session:
        app, raw_secret = await create_application(session, name="Mon App")
        print(f"X-Access-Key: {app.access_key}")
        print(f"X-Access-Secret: {raw_secret}")  # affiché une seule fois — à conserver maintenant
    await engine.dispose()


asyncio.run(main())
```

```bash
python create_application.py
```

Exécutez ceci *après* qu'`uvicorn` ait démarré au moins une fois (pour que les tables existent).
Pour du développement local uniquement, vous pouvez sauter complètement cette étape en réglant
`TENXYTE_APPLICATION_AUTH_ENABLED=false` à la place — chaque fixture de test de la propre suite de
tests de ce repo fait exactement ça. Gardez-la activée si vous voulez exercer la vraie forme de
requête par défaut.

## 5. Votre premier appel API

```bash
export ACCESS_KEY="<X-Access-Key de l'étape 4>"
export ACCESS_SECRET="<X-Access-Secret de l'étape 4>"

# Inscription
curl -X POST http://localhost:8000/api/v1/register/ \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: $ACCESS_KEY" \
  -H "X-Access-Secret: $ACCESS_SECRET" \
  -d '{"email": "vous@example.com", "password": "Correct-Horse-Battery-1!"}'

# Connexion
curl -X POST http://localhost:8000/api/v1/login/email/ \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: $ACCESS_KEY" \
  -H "X-Access-Secret: $ACCESS_SECRET" \
  -d '{"email": "vous@example.com", "password": "Correct-Horse-Battery-1!"}'
# -> {"access_token": "...", "refresh_token": "...", "user": {...}, ...}

# Appeler un endpoint authentifié
curl http://localhost:8000/api/v1/me/ \
  -H "X-Access-Key: $ACCESS_KEY" \
  -H "X-Access-Secret: $ACCESS_SECRET" \
  -H "Authorization: Bearer <access_token de la connexion>"
```

Chaque réponse d'erreur — mauvais mot de passe, champ manquant, token expiré — revient dans la
même forme canonique que l'adaptateur Django :

```json
{ "error": "Invalid email or password", "code": "LOGIN_FAILED" }
```

C'est la boucle complète : installer, créer l'application, la lancer, obtenir un vrai token
d'accès, appeler un endpoint protégé. Tout le reste — 2FA, liens magiques, passkeys, connexion
sociale, organisations, RBAC, RGPD, délégation d'agent AIRS — c'est le même `create_tenxyte_app()`,
déjà câblé ; voir la [table de parité](parity_table.md) pour la liste complète des endpoints.

## Étapes suivantes

- [Guide Async](async_guide.md) — le motif `Async_Ports` et comment les services Core résolvent
  automatiquement sync vs async.
- [Référence des réglages](settings.md) — chaque variable d'environnement `TENXYTE_*`.
- [Architecture](architecture.md) — Ports et Adapters, et la place du Reference_Stack.
- [Adaptateurs personnalisés](custom_adapters.md) — remplacez les pièces du Reference_Stack
  (cache, email, file de tâches) par votre propre infrastructure.
- [Table de parité](parity_table.md) — chaque endpoint, les deux adaptateurs, régénérée par la CI.

## Considérations pour la production

Les défauts de `create_tenxyte_app()` visent à vous faire démarrer immédiatement, pas un
déploiement en production tel quel :

- **Des migrations, pas des tables auto-créées** : passez `auto_create_schema=False` et appliquez
  les migrations Alembic sous `migrations/` dans le cadre de votre propre processus de déploiement,
  plutôt que de compter sur la création de tables depuis les métadonnées ORM.
- **Un vrai backend de cache/blacklist** : les défauts `InMemoryCacheService`/
  `InMemoryTokenBlacklistService` ne partagent pas d'état entre plusieurs processus ou instances.
  Construisez un adaptateur adossé à Redis (voir [Adaptateurs personnalisés](custom_adapters.md))
  pour tout ce qui dépasse un seul processus.
- **Un vrai backend d'email** : `ConsoleEmailService` affiche au lieu d'envoyer — les liens
  magiques, codes OTP et réinitialisations de mot de passe ont besoin d'un vrai fournisseur câblé
  avant la mise en production.
- **Un algorithme JWT asymétrique** : le défaut `HS256` (symétrique) partage un seul secret entre
  chaque service qui doit vérifier un token. Passez à `RS256`/`PS256`/`EdDSA`
  (`TENXYTE_JWT_ALGORITHM`) si plus d'un service doit un jour vérifier des tokens qu'il n'a pas
  émis.
- **CORS**, si l'API est appelée depuis un navigateur sur une autre origine :

  ```python
  from fastapi.middleware.cors import CORSMiddleware

  app.add_middleware(
      CORSMiddleware,
      allow_origins=["https://yourdomain.com"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

Les deux adaptateurs partagent les mêmes services Core en dessous — la logique d'authentification
elle-même est portable entre eux ; seule la couche App_Factory/câblage diffère.
