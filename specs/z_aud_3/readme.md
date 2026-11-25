# Spec z_aud_3 — Phase 3 « Multi-framework réel » (FastAPI à parité + Core async + UI headless)

> **Source :** `AUDIT.md` (racine du projet), §9 « Feuille de route recommandée », Phase 3 (T+4 → T+10 mois)
> **Statut :** 📋 Spécifié — prêt pour implémentation
> **Prérequis conseillé :** Phase 1 (`z_aud_1`) livrée — le packaging inversé (`tenxyte[fastapi]`
> sans Django) et le contrat de stabilité conditionnent la crédibilité de cette phase
> **Durée cible :** 6 mois, la plus lourde des quatre phases

---

## Contexte

L'audit stratégique (`AUDIT.md`) identifie la promesse « framework-agnostic » comme non tenue :

| Constat (AUDIT.md) | Réalité mesurée dans le code |
|---|---|
| F3 — Adapter FastAPI partiel | **2 endpoints** (`POST /auth/login`, `POST /auth/magic-link`) contre **93 routes** Django ; stubs DI levant `NotImplementedError` ; `application_id` codé en dur ; vérification bcrypt inline dans le router |
| F7 — Core synchrone | **Partiellement faux** : `jwt_service` possède déjà une API duale sync/async complète (protocole blacklist async, `decode_token_async`, `refresh_tokens_async`, pont `asyncio.to_thread`). Mais `ports/repositories.py` est **0 % async**, et les autres services Core n'ont pas de variantes async |
| Écart vs Clerk : composants UI | SDKs JS documentés (`@tenxyte/core`, `@tenxyte/react`, `@tenxyte/vue`) mais **aucun composant UI** — chaque intégrateur reconstruit ses écrans |

Cette phase rend la promesse multi-framework **vérifiable** : parité d'endpoints prouvée par une
matrice automatique, contrat filaire identique prouvé par des tests partagés entre adapters,
couverture ≥ 90 % sur l'adapter FastAPI, et composants UI headless puis stylés côté JS.

## Périmètre de la phase

1. **Ports async** — interfaces async des repositories (`AsyncUserRepository`…) en dual avec les
   interfaces sync existantes (jamais modifiées), suivant le pattern déjà établi par
   `jwt_service` (méthodes `*_async`, détection `hasattr`, pont `asyncio.to_thread`).
2. **Complétion async du Core** — variantes async des services Core utilisés sur les chemins de
   requête (`magic_link_service`, `session_service`, `totp_service` pour les accès storage) ;
   l'API sync existante reste intouchée.
3. **Socle FastAPI production** — app factory `create_tenxyte_app()` / router montable,
   implémentations par défaut SQLAlchemy 2.0 async (fin des stubs `NotImplementedError`),
   middleware d'authentification d'application (`X-Access-Key`/`X-Access-Secret`), provider de
   settings par variables d'env (parité `TENXYTE_*`), format d'erreur `{error, code, details}`,
   throttling, migrations Alembic du stack de référence.
4. **Parité d'endpoints** — les 7 groupes du contrat public documenté (`endpoints.md`), livrés en
   vagues : **A** Auth de base · **B** Password · **C** OTP + Magic Link + Login OTP + 2FA ·
   **D** RBAC + Applications + Admin · **E** Organisations · **F** AIRS (+ découverte z_aud_2) ·
   **G** WebAuthn + Social. Parité = mêmes chemins (sous préfixe), mêmes formes de
   requêtes/réponses, mêmes codes d'erreur, mêmes comportements anti-énumération et feature-flags.
5. **Preuve de parité** — matrice de parité automatique (diff routes Django ↔ routes FastAPI avec
   liste d'exclusions explicite), suite de tests de contrat **partagée** exécutée contre les deux
   adapters, seuil de couverture ≥ 90 % appliqué à `adapters/fastapi` en CI.
6. **SDK JS : réalignement du contrat, puis composants UI headless et stylés** — d'abord
   `@tenxyte/core` remis sur le Wire_Contract (13 méthodes visant des routes inexistantes,
   17 routes du contrat inatteignables, `apple` non typable, `must_change_password` absent —
   mesuré le 2026-09-22, cf. D9) ; ensuite `@tenxyte/ui-headless` (logique + a11y, zéro CSS)
   puis `@tenxyte/ui` (couche stylée thémable) couvrant les parcours clés (SignIn, SignUp,
   OTPInput, TwoFactorSetup, PasskeyButton, ForcedPasswordChange, OrgSwitcher).
   Implémentation dans le monorepo JS existant ; ce repo fournit le backend de contrat
   (export OpenAPI + backend démo docker) consommé par la CI JS.
7. **Documentation** — `fastapi_quickstart.md` réécrit en zéro-config réel, tableau de parité
   publié, guide async.

## Hors périmètre (backlog ou phases ultérieures)

- Adapters au-delà de FastAPI (Java, Node, PHP — mentionnés dans le README) → backlog.
- Réécriture async de l'adapter Django (l'ORM Django reste sync ; le pont existant suffit).
- Mode OIDC Provider / SAML / SCIM → Phase 4.
- Composants UI Vue/Svelte (headless d'abord, React stylé ensuite ; autres frameworks au
  backlog). À dire franchement : `@tenxyte/vue` 0.5.5 est publié au même rang que
  `@tenxyte/react` dans le monorepo et son README, et cette phase ne lui livre **aucun**
  composant — un utilisateur Vue reste à égalité avec aujourd'hui.
- Tests des bindings `@tenxyte/react` / `@tenxyte/vue` eux-mêmes : les deux paquets n'ont
  aujourd'hui aucun test (la CI JS n'y fait que `typecheck` + `build`). Cette phase crée
  l'infrastructure de test pour les paquets UI, pas rétroactivement pour les bindings.
- Toute modification du contrat filaire existant — la parité copie le contrat Django, elle ne le
  renégocie pas.

## Fichiers de cette spec

| Fichier | Rôle |
|---|---|
| `readme.md` | Ce document — vue d'ensemble, contexte, statut, journal de décisions |
| `base.md` | Plan initial issu de l'audit + état des lieux mesuré du code |
| `requirements.md` | Exigences formelles EARS avec glossaire et critères d'acceptation |
| `design.md` | Conception : architecture, ports async, socle FastAPI, matrice de parité, propriétés de correction |
| `tasks.md` | Plan d'implémentation traçable (vagues A→G, tâches ↔ requirements, graphe de dépendances) |
| `manual_tests.md` | Procédures de tests manuels (quickstart chrono, parcours Postman croisés, charge async, revue UI/a11y) |
| `.config.kiro` | Métadonnées de la spec |

## Décisions structurantes (journal)

| # | Décision | Justification |
|---|---|---|
| D1 | **Dual sync/async par extension, jamais par modification** : les interfaces sync des ports restent intouchées ; les interfaces async sont de nouvelles classes (`AsyncUserRepository`), consommées via détection `hasattr`/`isinstance` avec pont `asyncio.to_thread` en repli | C'est le pattern déjà en production dans `jwt_service` (protocole blacklist async) — cohérence + zéro régression Django |
| D2 | **La parité est un artefact testé, pas une déclaration** : un manifeste machine-readable des endpoints (dérivé des routes Django) est diffé contre les routes FastAPI en CI, avec liste d'exclusions explicite et justifiée | Sans gate automatique, la parité régresse silencieusement à chaque nouvel endpoint Django |
| D3 | **Le contrat filaire de référence est celui de l'adapter Django** (`endpoints.md` + snapshots existants) : les tests de contrat partagés sont paramétrés par adapter et doivent passer à l'identique sur les deux | Un client (SDK JS inclus) doit pouvoir changer de backend sans changer de code |
| D4 | **Stack de référence FastAPI : SQLAlchemy 2.0 async + Alembic**, avec `aiosqlite` (dev) et `asyncpg` (prod) ; les repositories restent remplaçables par DI | Standard de l'écosystème FastAPI ; la DI existante (stubs) devient « surchargeable » au lieu d'« obligatoire » |
| D5 | **Interdiction d'I/O sync dans les handlers FastAPI**, vérifiée par un check AST automatisé (liste de motifs interdits : appels repo sync, `requests.`, `time.sleep`) | Le blocage de l'event loop est le bug n°1 des adapters async ; on le rend impossible à merger |
| D6 | **Les composants UI vivent dans le monorepo JS existant** (`@tenxyte/*`) ; ce repo Python livre le contrat (export OpenAPI versionné + backend démo docker) que la CI JS consomme | Un seul endroit pour le code JS ; le contrat croisé empêche la dérive entre SDK et backend |
| D7 | **Headless d'abord, stylé ensuite** : `@tenxyte/ui-headless` (hooks + composants sans style, ARIA complet) est une dépendance de `@tenxyte/ui` (thème par défaut + tokens CSS) | Réutilisabilité maximale (design systems clients) et testabilité a11y indépendante du visuel |
| D9 | **Le SDK JS est réaligné sur le Wire_Contract avant toute ligne d'UI** (tâche 15.0 bloque 15.1/15.2), et un gate de conformité des chemins contre l'export OpenAPI est ajouté à la CI JS | Les composants headless orchestrent `@tenxyte/core` : construire sur un SDK qui vise des routes inexistantes donnerait des composants verts en tests et cassés en production. Les 14 fichiers de tests JS mockent le client HTTP et assertent l'URL que le module vient de produire — auto-référentiels, donc aveugles à la dérive ; c'est ainsi qu'elle s'est installée |
| D10 | **Un seul oracle de contrat, deux backends démo** : `examples/js-contract-backend/` (FastAPI, seed déterministe) gate la CI JS ; `tenxyte-js/examples/server-django/` (Django+MongoDB+Celery, préexistant) reste la vitrine d'intégration | Découvert au réalignement : un backend démo existait déjà côté JS. Ne pas le supprimer (il démontre l'intégration réelle), ne pas le promouvoir oracle (seed non déterministe, mauvaise pile), et l'écrire dans les deux README pour qu'aucun troisième ne soit fabriqué |
| D8 | Les groupes de parité sont livrés dans l'ordre **A → B → C → F → D → E → G** | A–C = cœur d'usage FastAPI ; F (AIRS) avancé car c'est le différenciateur stratégique (Phase 2) ; G en dernier car WebAuthn/Social ont le plus de dépendances externes |

## Definition of Done de la phase

- [ ] Matrice de parité verte : 100 % des endpoints documentés couverts ou exclus avec justification écrite.
- [ ] Suite de contrat partagée verte contre les deux adapters (mêmes formes, mêmes codes d'erreur).
- [ ] Couverture ≥ 90 % sur `src/tenxyte/adapters/fastapi/` imposée en CI.
- [ ] Check AST anti-blocage vert (aucune I/O sync dans les handlers).
- [ ] API sync existante inchangée (snapshot) ; suite Django complète verte sans modification.
- [ ] `pip install tenxyte[fastapi]` (sans Django) → app démarrable + parcours auth complet en < 5 min (MT-1 chronométré).
- [x] `@tenxyte/core` ≥ 0.10.0 publié : zéro appel vers une route inexistante (gate de conformité
      chemins ↔ `openapi/tenxyte-django.json` vert en CI JS), `apple` typable,
      `must_change_password` exposé, note de migration `b2b` publiée.
      **Fait** (`packages/core/package.json` à 0.10.0 dans `tenxyte-js`, vérifié empiriquement —
      voir tâche 15.0 dans `tasks.md`).
- [x] `@tenxyte/ui-headless` publié avec les 7 composants du périmètre, tests a11y verts (axe).
      **Remplacé, pas publié tel quel** — voir tâche 15 (note de substitution) dans `tasks.md` :
      Registry shadcn (`tenxyte-js/packages/registry/`) + Bindings (`packages/react/`,
      `packages/vue/`) à la place de deux packages npm séparés, décision D3 de
      `tenxyte-js/specs/02-console-runtime`. a11y réelle vérifiée (`a11y-wired.spec.ts` contre le
      vrai Contract_Backend, pas seulement un mock).
- [x] `@tenxyte/ui` publié (thème par défaut), revue visuelle MT-6 consignée.
      **Remplacé, pas publié tel quel** — même substitution que la ligne précédente ; thème par
      défaut clair/sombre livré dans `packages/registry/styles/theme.css`. L'intention de MT-6
      (revue visuelle, thèmes, tokens, AA) est reprise, sous une numérotation différente, par
      `tenxyte-js/specs/02-console-runtime/manual_tests.md` : MT-1 couvre le restylage
      (`--color-primary`, rayon, propagation sans `!important`) et MT-3 couvre l'accessibilité
      réelle (clavier/lecteur d'écran, y compris les états d'erreur réels — `403`, compte
      verrouillé, repli WebAuthn). Ces deux MT restent **à exécuter** (tâche 7.3 de ce fichier,
      campagne manuelle `[MT-1..MT-4]`) — non substitués par la suite automatisée `a11y-wired.
      spec.ts` de cette session, qui vérifie la structure DOM/contraste mais pas la perception
      réelle au lecteur d'écran ni le jugement visuel humain sur le restylage.
- [ ] `fastapi_quickstart.md` réécrit et validé par MT-1 ; tableau de parité publié dans la doc.

## Suivi

Consulter `tasks.md` pour l'avancement par vague (A→G) et `manual_tests.md` pour le registre
d'exécution des validations manuelles (quickstart chronométré, Postman croisé, charge, a11y).
