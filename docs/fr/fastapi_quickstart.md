# Démarrage Rapide avec FastAPI

Obtenez un premier appel API authentifié contre l'adaptateur FastAPI de Tenxyte en environ cinq
minutes, grâce à l'**App_Factory** intégrée — aucun câblage manuel de services requis.

## Table des Matières

- [1. Installation](#1-installation)
- [2. Créer l'application](#2-creer-lapplication)
- [3. La lancer](#3-la-lancer)
- [4. Bootstrap (seed RBAC + identifiants API)](#4-bootstrap-seed-rbac--identifiants-api)
- [5. Votre premier appel API](#5-votre-premier-appel-api)
- [6. Créer un Compte Administrateur](#6-creer-un-compte-administrateur)
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

## 4. Bootstrap (seed RBAC + identifiants API)

`python -m tenxyte.adapters.fastapi.quickstart` est l'équivalent côté FastAPI de la commande
`python manage.py tenxyte_quickstart` de l'adaptateur Django — une seule commande idempotente qui
crée le schéma, seed les rôles/permissions par défaut (`viewer`/`editor`/`admin`/`super_admin`,
mêmes codes et hiérarchie que ceux seedés par l'adaptateur Django), et crée une Application par
défaut :

```bash
python -m tenxyte.adapters.fastapi.quickstart
```

```
Tenxyte Quickstart (FastAPI)

Step 1/3: Creating schema...
  Schema ready
Step 2/3: Seeding roles & permissions...
  Permissions: 47 created, 0 updated
  Roles: 4 created, 0 updated
Step 3/3: Creating default Application...

  ======================================================
  SAVE THESE CREDENTIALS -- shown only once!
  ------------------------------------------------------
  Access Key:    <votre access key>
  Access Secret: <votre access secret>
  ------------------------------------------------------
  ...
```

Le secret est haché en bcrypt dans la base de données et **ne peut plus être récupéré ensuite** —
copiez-le maintenant. L'authentification au niveau application (`X-Access-Key`/`X-Access-Secret`)
est **activée par défaut** (`TENXYTE_APPLICATION_AUTH_ENABLED=true`), comme le propre défaut de
l'adaptateur Django — chaque requête vers un chemin non exempté a besoin de ces deux en-têtes.

Options utiles : `--database-url` (même fichier SQLite par défaut que `create_tenxyte_app()`),
`--no-seed` (sauter le seed RBAC), `--no-app` (sauter la création de l'Application), `--app-name`
(défaut : `"Default App"`). Relancer la commande est sans risque : les Applications sont
identifiées par nom et jamais dupliquées, et relancer le seed **re-synchronise** l'ensemble des
permissions de chaque rôle par défaut (une permission ajoutée dans une version ultérieure de
Tenxyte atteint donc une installation existante à la prochaine exécution) plutôt que de sauter les
rôles/permissions déjà existants — même comportement que la commande `tenxyte_seed` de
l'adaptateur Django.

Pour du développement local uniquement, vous pouvez sauter complètement la création de
l'Application en réglant `TENXYTE_APPLICATION_AUTH_ENABLED=false` à la place — chaque fixture de
test de la propre suite de tests de ce repo fait exactement ça. Gardez-la activée si vous voulez
exercer la vraie forme de requête par défaut.

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

## 6. Créer un Compte Administrateur

`register/` ne définit jamais `is_superuser`/`is_staff` — un endpoint d'inscription public ne
devrait pas pouvoir le faire. Pour un compte avec accès admin complet (nécessaire pour les mêmes
choses que côté Django — configuration RBAC, routes admin), utilisez la commande dédiée à la
place — l'équivalent côté FastAPI de `python manage.py createsuperuser` /
`python -m tenxyte.adapters.django.createsuperuser` :

```bash
python -m tenxyte.adapters.fastapi.createsuperuser
```

Demande un e-mail et un mot de passe (saisie masquée, tapé deux fois pour confirmation), contre la
même base de données que `create_tenxyte_app()` utilise par défaut. Pour le scripting/CI, sans les
invites :

```bash
python -m tenxyte.adapters.fastapi.createsuperuser --email admin@example.com --password "..." --noinput
```

`--database-url` permet de cibler une autre base, même convention que
[la commande de bootstrap du quickstart](#4-bootstrap-seed-rbac--identifiants-api).

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
