# Tests Manuels — Phase 3 « Multi-framework réel » (z_aud_3)

> Ce document consigne les procédures de vérification **non automatisables** de la phase, et sert
> de **registre d'exécution** : chaque procédure doit être déroulée et son résultat consigné dans
> le tableau final avant de cocher la tâche correspondante dans `tasks.md`.

**Convention :** chaque section porte un identifiant `MT-x` référencé depuis `tasks.md`.
Un test manuel est **PASS** uniquement si toutes ses étapes de vérification sont satisfaites.

---

## MT-1 — Quickstart FastAPI chronométré (« 5 minutes au premier appel »)

**Couvre :** Requirements 3.1, 3.2, 3.3, 7.1 · **Tâches :** 2.1, 2.2, 16.1
**Prérequis :** venv neuf, Python 3.10+, chronomètre.
**Règle d'or :** suivre `docs/en/fastapi_quickstart.md` **mot à mot, sans aucune connaissance
externe** — le test valide la doc autant que le code.

> **⚠️ Tant que cette branche n'est pas publiée sur PyPI** (dernier release réel : `v0.9.6.4.2`,
> un paquet antérieur à tout ce chantier — vérifié via les tags git et un vrai `pip install`
> pendant l'exécution de ce test le 2026-09-15, qui installe Django/DRF/drf-spectacular en
> dépendances de `[fastapi]` et ne contient pas `create_tenxyte_app` du tout), l'étape 1 ne peut
> **pas** être une « machine vierge » pointant sur le vrai PyPI — installer depuis les sources
> locales de cette branche à la place (`pip install -e "<chemin-vers-le-repo>[fastapi]"`). Ne
> pas retirer cette note avant un vrai `git tag`/release incluant ce travail — c'est un vrai
> `FAIL` de doc, pas une astuce d'environnement de test.

### Procédure

1. Démarrer le chronomètre. Dérouler le quickstart tel qu'écrit :
   ```bash
   python -m venv /tmp/vx-fapi && source /tmp/vx-fapi/bin/activate
   pip install -e "<chemin-vers-le-repo>[fastapi]"   # voir l'avertissement PyPI ci-dessus
                                                       # vérifier : pip freeze | grep -i django → vide
   # créer main.py selon la doc (create_tenxyte_app)
   # créer un fichier .env avec TENXYTE_JWT_SECRET_KEY (voir la doc — chargé automatiquement,
   # pas besoin de --env-file ni de variable d'environnement OS)
   uvicorn main:app --reload
   ```
2. Bootstrap — seed RBAC + Application par défaut (l'auth applicative est active par défaut, il
   faut de vrais identifiants `X-Access-Key`/`X-Access-Secret` pour l'étape 3) :
   ```bash
   python -m tenxyte.adapters.fastapi.quickstart
   ```
3. Premier cycle API selon la doc (credentials d'application inclus) :
   ```bash
   curl -X POST .../register/  -H "X-Access-Key: ..." -H "X-Access-Secret: ..." -d '{...}'
   curl -X POST .../login/email/ -H "X-Access-Key: ..." -H "X-Access-Secret: ..." ...
   curl .../me/ -H "X-Access-Key: ..." -H "X-Access-Secret: ..." -H "Authorization: Bearer <access_token>"
   ```
4. Arrêter le chronomètre au premier `GET /me/` réussi.
5. Vérifier : Swagger accessible **sans** identifiants d'application à l'URL préfixée
   `{base_url}/api/v1/docs/` (avec le slash final — c'est la vraie URL que `create_tenxyte_app()`
   monte ; `/docs` nu à la racine n'existe pas et renvoie 401), erreurs au format
   `{error, code, details}` (tester un login faux), aucun `NotImplementedError` rencontré.

✅ Attendu : cycle complet ≤ **5 minutes** sans sortir de la doc ; Django absent de
l'environnement (une fois installé depuis les sources locales de cette branche) ; toute étape
ambiguë de la doc = FAIL de la doc (corriger puis re-tester).

**Historique de correction (2026-09-15)** : la première exécution réelle de ce test a échoué à
plusieurs reprises avant de réussir — chaque échec corrigé dans le code ou la doc, pas contourné
dans le test :
- `pip install "tenxyte[fastapi]"` installait un vieux paquet PyPI (Django inclus,
  `create_tenxyte_app` absent) → étape 1 corrigée ci-dessus, install locale de la branche.
- La création d'une Application était absente de la procédure alors que l'étape suivante exigeait
  déjà `X-Access-Key`/`X-Access-Secret` — impossible à suivre « mot à mot » → étape 2 ajoutée.
- `TENXYTE_JWT_SECRET_KEY` fixée via `$env:`/`export` disparaissait à chaque nouveau terminal →
  fonctionnalité `.env` ajoutée au Core (`Adapter_Custom > OS env > .env > preset > default`,
  `python-dotenv` maintenant dépendance Core) et recommandée en premier dans la doc et ici.
- `/docs` (Swagger natif de FastAPI) restait 401 même sans aucune bonne raison documentée — bug
  réel dans `create_tenxyte_app()` (aucun `docs_url` explicite, donc hors du chemin exempté par
  défaut) corrigé dans `app.py` ; étape 5 corrigée avec la vraie URL.

**Historique de correction (2026-09-16)** : en testant manuellement le `register/`, l'utilisateur
a observé un `201 "Registration successful"` systématique et s'est demandé si SQLite recréait
l'utilisateur à chaque appel — en fait un comportement voulu (anti-énumération, Property 3) : un
email déjà pris renvoie un faux `User` de même forme sans rien persister (`routers/auth.py`). Dans
la foulée, deux vrais manques ont été trouvés et corrigés :
- Les tables de l'adaptateur Django n'étaient pas préfixées `tenxyte_` (contrairement à
  l'adaptateur FastAPI) → 19 tables + leurs tables de jointure M2M implicites renommées
  (migration `0020_rename_tables_tenxyte_prefix.py`).
- Il n'existait **aucun équivalent FastAPI** de `python manage.py tenxyte_quickstart` : les tables
  `RoleDB`/`PermissionDB` existaient (Wave D) mais rien ne les peuplait, et la création
  d'Application n'était qu'un script à écrire soi-même → `python -m
  tenxyte.adapters.fastapi.quickstart` ajouté (idempotent : schéma + seed RBAC + Application par
  défaut), étape 2 ci-dessus corrigée pour l'utiliser au lieu du script `create_application.py`
  fait main.

En poursuivant l'uniformisation, l'utilisateur a demandé que l'adaptateur Django suive le même
principe de seeding que FastAPI et que `python -m tenxyte.adapters.fastapi.quickstart` ait un
équivalent Django symétrique. Trois corrections supplémentaires :
- `DEFAULT_PERMISSIONS`/`DEFAULT_ROLES` étaient dupliquées littéralement entre `tenxyte_seed.py`
  (Django) et `quickstart.py` (FastAPI) → extraites dans `tenxyte.core.rbac_defaults`, source
  unique importée par les deux.
- `seed_rbac()` (FastAPI) sautait silencieusement tout rôle/permission déjà existant — cassait le
  chemin de mise à jour (une permission ajoutée à un rôle dans une version ultérieure de Tenxyte
  n'atteignait jamais une installation existante) → réécrit pour re-synchroniser à chaque run,
  comme `tenxyte_seed.py` le fait déjà côté Django (`__all__` résolu dynamiquement sur toutes les
  permissions présentes en base, pas une liste figée).
- `python -m tenxyte.adapters.django.quickstart` ajouté (fin wrapper autour de
  `call_command("tenxyte_quickstart", ...)`), symétrique à l'entrée FastAPI. En le testant
  directement, un vrai bug préexistant est apparu : `tenxyte_quickstart.py` utilisait des emojis
  (🚀, ✅, ⚠) et des caractères de dessin de boîte (║╔╗╚╝) dans sa sortie console, qui plantent
  (`UnicodeEncodeError`) dès que stdout n'est pas un vrai terminal UTF-8 — reproductible sur
  Windows avec l'encodage console par défaut (cp1252). Cassait `python manage.py tenxyte_quickstart`
  aussi, pas seulement le nouveau wrapper → remplacés par de l'ASCII pur.

En testant `python -m tenxyte.adapters.django.quickstart` sans base réelle sous la main,
l'utilisateur a dû fixer `$env:DJANGO_SETTINGS_MODULE` à la main avant chaque appel — étape jugée
à éliminer. Auto-détection ajoutée (`_settings_discovery.py`, ordre : OS env > `.env` >
`manage.py` du répertoire courant, parsé jamais exécuté), donc plus besoin de la fixer
explicitement pour le cas courant (lancé depuis la racine d'un vrai projet).

L'utilisateur a ensuite demandé le même traitement pour `python manage.py createsuperuser`
(symétrie complète avec les deux commandes `quickstart`), ce qui a aussi comblé un vrai manque
côté FastAPI — anticipé par le prérequis de MT-2 ci-dessous (« seed identique : application +
admin ») mais jamais construit :
- `python -m tenxyte.adapters.django.createsuperuser` ajouté (fin wrapper, `DJANGO_SETTINGS_MODULE`
  auto-détecté comme le quickstart ; `createsuperuser` lui-même n'est pas du code Tenxyte, il vient
  de `django.contrib.auth` et fonctionne déjà tel quel avec le `User` custom de Tenxyte).
- `python -m tenxyte.adapters.fastapi.createsuperuser` ajouté — aucun équivalent n'existait avant
  (`register/` ne positionne jamais `is_superuser`/`is_staff`) : prompts interactifs (saisie
  masquée, confirmation) ou `--email`/`--password`/`--noinput` pour le scripting. Vérifié
  bout-en-bout avec un vrai login : le superuser créé déclenche bien le flux de bootstrap 2FA admin
  existant (`2fa_setup_only`), preuve qu'il est reconnu comme un vrai superuser par tout le système,
  pas juste un champ en base.

En se connectant pour de vrai à travers une application cliente avec ce superuser fraîchement créé
(donc sans 2FA configurée), l'utilisateur a reçu le token bootstrap `2fa_setup_only` et a demandé
pourquoi son client ne pouvait pas se déconnecter avec. Vérifié contre le vrai code Django avant
toute correction (source de vérité) :
- Élargir le scope à `GET /2fa/status/` et `POST /logout/all/` aurait été une régression de
  sécurité, pas un correctif — ni l'un ni l'autre n'autorise `2fa_setup_only` dans Django, et c'est
  voulu (le token bootstrap de 15 minutes doit rester minimal).
- Le vrai bug était que `POST /logout/` exigeait `refresh_token` de façon inconditionnelle — que
  le bootstrap n'émet jamais — alors que blacklister l'access token seul (via l'en-tête
  `Authorization`) est une opération bien définie en soi. Corrigé dans les deux adaptateurs :
  `refresh_token` n'est requis que si aucun des deux (lui ou l'en-tête) n'est fourni.
- En écrivant un test réel (non mocké) pour vérifier ce correctif côté Django, un bug plus grave
  et déjà présent est apparu : `LogoutView`/`LogoutAllView` appelaient
  `jwt_service.blacklist_token(jti=..., expires_at=...)` — mauvaise méthode (la vraie signature
  prend le token brut en argument positionnel, pas `jti`/`expires_at`), levant systématiquement
  une `TypeError` avalée silencieusement par un `except Exception`. **Les access tokens n'ont
  jamais été réellement blacklistés au logout côté Django** — le test existant qui aurait dû le
  détecter mockait cette même méthode buguée et ne vérifiait que « appelée », restant vert tout du
  long. Corrigé (`blacklist_token_by_jti` au lieu de `blacklist_token`, sur les 3 sites concernés),
  tests réécrits pour vérifier l'état réel du token après logout plutôt qu'un appel mocké.

Deux signalements distincts de l'utilisateur le 2026-09-20 :
- **2FA (non résolu, en attente de détails)** : `is_2fa_enabled` resterait à `false` après avoir
  configuré la 2FA, donc le login avec `totp_code` ne renverrait toujours que le token bootstrap
  `2fa_setup_only`. Reproduit bout-en-bout sur Django ET FastAPI avec un code TOTP réellement
  frais : le mécanisme fonctionne correctement dans les deux cas (`is_2fa_enabled` se persiste,
  login avec un code valide renvoie un token complet). Deux causes plausibles identifiées mais pas
  confirmées : (a) collision de fenêtre TOTP (réutiliser le même code entre confirm et le login
  suivant est rejeté à raison par l'anti-rejeu — comportement normal, pas un bug) ; (b) un bug réel
  trouvé en creusant, `TOTPService.setup_2fa()` ne vérifie jamais l'existence d'un secret déjà en
  attente — un second appel à `/2fa/setup/` écrase silencieusement le premier secret, invalidant le
  QR code déjà scanné. L'utilisateur a confirmé un seul appel à `/2fa/setup/`, éliminant la piste
  (b) pour son cas précis. En attente des réponses JSON exactes de `/2fa/setup/`, `/2fa/confirm/`
  et du login suivant pour identifier la vraie cause.
- **Incohérence des clés primaires (résolu)** : FastAPI utilise des UUID partout, Django des
  entiers auto-incrémentés — l'utilisateur a demandé de converger vers un seul schéma. Décision :
  Django → UUID (comme FastAPI), malgré le risque de compatibilité ascendante plus élevé que
  l'inverse (accepté explicitement par l'utilisateur), pour la propriété de sécurité que les
  entiers séquentiels n'ont pas (non-énumérabilité). Migration 0021 (PK) + 0022 (suivi :
  `AuditLog.details` plantait sur un UUID sans `DjangoJSONEncoder`), plus une régression d'ordre de
  route que j'ai moi-même introduite (`<str:pk>` avale un segment littéral que `<int:pk>` ne
  pouvait jamais matcher), deux vrais bugs de validation (`AddMemberSerializer`/
  `CreateOrganizationSerializer` en `IntegerField` auraient rejeté tout UUID réel), et plusieurs
  lookups qui ne rattrapaient que `DoesNotExist` sans `ValidationError` (un ID malformé aurait fait
  planter en 500). Tout trouvé et corrigé via la régression Django complète et des reproductions
  réelles, pas par inspection seule. Voir `docs/en+fr/MIGRATION_GUIDE.md` pour le détail communiqué
  aux utilisateurs (breaking change, pas de migration de données automatisée).

En préparant le test manuel du scénario « 2.3 » (compte `must_change_password=true` → token
`password_change_only`, `403 INSUFFICIENT_SCOPE` sur `/2fa/status/`, upgrade full-scope après
`/password/change/`), l'utilisateur a demandé comment créer un tel compte. Vérification du code
réel (pas de la doc) : la fonctionnalité `force_password_change_on_first_login` était **entièrement
implémentée côté Django** (spec dédiée, toutes tâches faites) mais **totalement absente côté
FastAPI**, malgré des indices trompeurs — `UserDB.must_change_password` existait déjà (posé pour
l'endpoint admin `PATCH /admin/users/<id>/`), mais `routers/auth.py`/`routers/login_otp.py`
codaient en dur `"must_change_password": False` dans les réponses de login, et
`routers/password.py` documentait explicitement la branche d'upgrade comme « dead code today ».
Portage complet demandé et livré (commit `feat(fastapi): implement force_password_change_on_first
_login`) : réglage ajouté à `core/settings.py` (partagé, contrairement à Django qui a son propre
`conf/auth.py`), `resolve_forced_password_change_scope` répliqué dans `routers/auth.py` et câblé
dans les 4 points d'émission (login email/phone/OTP + refresh), levée du flag et upgrade full-scope
ajoutés à `routers/password.py` (réutilise `admin_user_service.update_user_async`, déjà utilisé
côté écriture par l'endpoint admin). Vérifié bout-en-bout par reproduction réelle : le scénario
2.3 complet fonctionne exactement comme décrit, la précédence 2FA-bootstrap est respectée, et le
« no-op » quand la feature est désactivée est confirmé. 11 tests réels (no-mock) ajoutés.

---

## MT-2 — Parcours Postman croisés (parité vécue)

**Couvre :** Requirements 4.2, 4.3, 4.4 · **Tâches :** 5.1–12.2
**Prérequis :** la collection Postman du repo ; deux backends up en parallèle — Django
(`:8000`) et FastAPI (`:8001`) — chacun avec un seed identique (application + admin).

### Procédure

1. Configurer deux environnements Postman (`django`, `fastapi`) ne différant que par `base_url`.
2. Dérouler la collection complète sur `django`, puis sur `fastapi`. Pour chaque requête,
   comparer côte à côte : statut, clés de réponse, codes d'erreur.
3. Scénarios de flux transverses à rejouer explicitement sur **fastapi** :
   | # | Scénario | Attendu (identique à Django) |
   |---|---|---|
   | 2.1 | Register d'un email déjà pris | 201 anti-énumération, forme identique au succès |
   | 2.2 | Login admin sans 2FA | token `2fa_setup_only`, `requires_2fa_setup: true` |
   | 2.3 | Compte `must_change_password=true` | token `password_change_only`, 403 `INSUFFICIENT_SCOPE` sur `/2fa/status/`, upgrade full-scope après `/password/change/` |
   | 2.4 | Login OTP feature OFF | 404 `FEATURE_DISABLED` |
   | 2.5 | 5 logins échoués | 423 `ACCOUNT_LOCKED` + `retry_after` |
   | 2.6 | Throttle reset password | 429 avec `retry_after` |
   | 2.7 | Cycle AIRS (token → AgentBearer → HITL 202 → confirm → rejeu) | conforme au contrat |
4. Consigner toute divergence (endpoint, champ, code) — chaque divergence = issue de parité.

✅ Attendu : zéro divergence de contrat sur l'ensemble de la collection et des 7 scénarios.

---

## MT-3 — Tenue en charge async (non-blocage réel)

**Couvre :** Requirements 3.2, 5.4 · **Tâches :** 2.2, 3.3
**Prérequis :** backend FastAPI (Reference_Stack, asyncpg recommandé), outil de charge
(`hey`, `wrk` ou `locust`), un worker uvicorn UNIQUE (pour rendre tout blocage visible).

### Procédure

1. `uvicorn main:app --workers 1`.
2. Charge mixte 2 minutes : 50 connexions concurrentes sur `GET /me/` (JWT valide) + 10/s sur
   `POST /login/email/` + 5/s sur un endpoint AIRS AgentBearer.
3. Pendant la charge, sonde manuelle : `curl` sur `/docs` et sur la découverte AIRS toutes les
   ~5 s — les réponses doivent rester < 1 s (un event loop bloqué se manifeste ici).
4. Relever p95/p99 et erreurs ; vérifier l'absence de timeouts en cascade.
5. Contre-épreuve : introduire volontairement un `time.sleep(2)` dans un handler local, vérifier
   (a) que la sonde manuelle dégénère — preuve que le protocole de test détecte bien le blocage —
   et (b) que `scripts/check_async_purity.py` refuse ce code. Retirer la modification.

✅ Attendu : sonde stable sous charge, zéro erreur 5xx, contre-épreuve concluante dans les deux
directions.

---

## MT-4 — Reference_Stack sur PostgreSQL (asyncpg) et migrations Alembic

**Couvre :** Requirements 3.2 · **Tâche :** 2.2
**Prérequis :** PostgreSQL (docker), `pip install asyncpg`.

### Procédure

1. `TENXYTE_DATABASE_URL=postgresql+asyncpg://...` ; lancer les migrations Alembic depuis zéro
   (`alembic upgrade head`) — vérifier zéro erreur et le schéma attendu.
2. Rejouer le cycle MT-1 étapes 2–4 sur ce backend.
3. `alembic downgrade -1 && alembic upgrade head` — vérifier la réversibilité de la dernière
   migration.
4. Vérifier en base : mots de passe bcrypt (préfixe `$2b$`), tokens refresh hashés (aucune
   valeur brute), secret TOTP chiffré après un setup 2FA.

✅ Attendu : parité d'invariants de sécurité avec le stack Django, migrations propres A/R.

---

## MT-5 — `@tenxyte/ui-headless` dans une app React neuve

**Couvre :** Requirements 6.1, 6.2, 6.3 · **Tâche :** 15.1
**Prérequis :** backend démo (`examples/js-contract-backend/`) up ; Node 20+ ; packages headless
publiés (TestNpm/npm ou `npm pack` local).

### Procédure

1. `npm create vite@latest mt5-app -- --template react-ts && npm i @tenxyte/ui-headless @tenxyte/core`.
2. Monter `<SignIn.Root>` selon le README du package, pointé sur le backend démo. Vérifier :
   - Aucun style injecté (inspecteur : pas de feuille CSS du package, pas de style inline).
   - Le flux complet : erreur `LOGIN_FAILED` affichable, compte 2FA → état `twoFactorRequired`,
     compte `must_change_password` → état `passwordChangeRequired` enchaînant sur
     `<ForcedPasswordChange>`.
3. Monter `OTPInput`, `TwoFactorSetup` (scan QR réel avec une app TOTP), `PasskeyButton`
   (navigateur supportant WebAuthn — passkey de plateforme ou clé), `SignUp`, `OrgSwitcher`
   (backend démo avec 2 orgs seedées).
4. **Clavier uniquement** : dérouler SignIn + OTPInput sans souris (tab/flèches/entrée).
5. Lecteur d'écran (NVDA/VoiceOver) : labels et annonces d'erreurs perceptibles sur SignIn.
6. Lancer l'audit axe DevTools sur chaque écran : zéro violation critique/sérieuse.

✅ Attendu : les 7 composants fonctionnels, zéro CSS émis, navigation clavier complète, axe
propre. Consigner les versions exactes des packages testés.

---

## MT-6 — `@tenxyte/ui` : revue visuelle et thèmes

**Couvre :** Requirement 6.4 · **Tâche :** 15.2
**Prérequis :** MT-5 PASS ; `@tenxyte/ui` publié.

### Procédure

1. Dans l'app MT-5, remplacer les composants headless par leurs équivalents stylés (le README
   doit rendre la substitution triviale — c'est un critère).
2. Revue visuelle des 7 composants en thème clair ET sombre (bascule via l'API documentée) :
   états normal/hover/focus/disabled/erreur/chargement.
3. Personnalisation : surcharger 3 tokens (`--tenxyte-color-primary`, radius, font) et vérifier
   la propagation sans `!important` ni re-style profond.
4. Responsive : 360 px, 768 px, 1280 px — aucun débordement, zones tactiles ≥ 44 px.
5. Contraste : vérifier les paires texte/fond principales aux ratios WCAG AA (outil au choix).
6. Re-passer axe sur les versions stylées : zéro violation critique/sérieuse.

✅ Attendu : rendu professionnel dans les deux thèmes, theming par tokens effectif, AA respecté.
Captures d'écran archivées en preuve.

---

## MT-7 — Revue documentaire et table de parité

**Couvre :** Requirements 4.5, 7.1, 7.2, 7.3, 7.4 · **Tâches :** 16.1, 16.2

### Procédure

1. **Table de parité publiée** (EN/FR) : générée par la CI, datée ; chaque ligne 🚫 exclue porte
   une justification lisible et défendable (relecture critique : « cette exclusion
   survivrait-elle à une question publique ? »).
2. **Quickstart FastAPI** : re-déroulé par une personne différente de MT-1 (validation croisée).
3. **Guide async** : la recette `as_async()` + le gabarit `jwt_service` sont présents ; un
   développeur externe au chantier implémente un mini-repo async en suivant uniquement le guide
   (test de complétude).
4. **Doc UI** : installation, référence des 7 composants, guide de theming — vérifier que chaque
   exemple de code compile tel quel.
5. Synchronisation EN/FR section par section sur les quatre documents.
6. `scripts/validate_endpoints.py` vert sur les deux langues après tous les ajouts.

✅ Attendu : docs auto-suffisantes (validées par des tiers), parité EN/FR, validation CI verte.

---

## Registre d'exécution

> À compléter à chaque exécution. Une ligne par run (garder l'historique en cas de re-run).

| ID | Intitulé | Date | Exécutant | Environnement | Résultat | Notes / lien preuve |
|----|----------|------|-----------|---------------|----------|---------------------|
| MT-1 | Quickstart FastAPI chronométré (run de découverte) | 2026-09-15 | utilisateur | Windows, PowerShell, Python 3.14 | ❌ FAIL (doc corrigée) | Non chronométré, run itératif — 3 blocages réels trouvés et corrigés (PyPI périmé, création d'Application manquante, `/docs` gated) : voir « Historique de correction » ci-dessus. Un run propre et chronométré reste à faire pour PASS officiel. |
| MT-1 | Quickstart FastAPI chronométré | — | — | — | ⬜ À exécuter | temps mesuré : — |
| MT-2 | Parcours Postman croisés (2.1–2.7) | — | — | — | ⬜ À exécuter | |
| MT-3 | Tenue en charge async + contre-épreuve | — | — | — | ⬜ À exécuter | p95/p99 : — |
| MT-4 | PostgreSQL/asyncpg + Alembic A/R | — | — | — | ⬜ À exécuter | |
| MT-5 | ui-headless app React neuve (7 composants) | — | — | — | ⬜ À exécuter | versions : — |
| MT-6 | ui stylé — thèmes, tokens, AA | — | — | — | ⬜ À exécuter | captures : — |
| MT-7 | Revue documentaire + table de parité | — | — | — | ⬜ À exécuter | |

**Légende résultat :** ✅ PASS · ❌ FAIL (ouvrir une issue, référencer ici) · ⚠️ PASS avec réserve
(documenter la réserve) · ⬜ À exécuter

## Critère de sortie de la phase

La phase est validée lorsque : toutes les lignes du registre sont ✅ (ou ⚠️ avec réserve acceptée
par le mainteneur), toutes les gates CI sont vertes (matrice complète, Contract_Suite × 2,
Coverage_Gate ≥ 90 % sur l'adapter FastAPI, Async_Purity_Check, conformité AIRS contre FastAPI,
drift OpenAPI), la suite Django existante passe sans modification, et le checkpoint final de
`tasks.md` est coché. L'annonce « multi-framework GA » n'intervient qu'après.
