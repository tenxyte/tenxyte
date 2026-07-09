#### Plan : Phase 3 « Multi-framework réel » — FastAPI à parité + Core async + UI (z_aud_3)

  Objectif : rendre la promesse « framework-agnostic » vérifiable (AUDIT.md
  F3/F7) et combler l'écart time-to-market frontend vs Clerk (composants UI).
  Trois chantiers : async de bout en bout, parité FastAPI prouvée, UI headless.

---------------------------------------------------------------------------

  État mesuré dans le code (v0.9.6.4)

  Adapter FastAPI (src/tenxyte/adapters/fastapi/) — TRÈS partiel :
    * routers.py : 2 endpoints seulement — POST /auth/login (avec check
      bcrypt INLINE dans le handler, application_id="fastapi-app" codé en
      dur, pas d'app-auth, pas de lockout, pas de 2FA, pas d'anti-énum
      complète) et POST /auth/magic-link (ip="0.0.0.0" codé en dur).
    * DI : get_user_repository/get_jwt_service/get_magic_link_service
      lèvent NotImplementedError — l'intégrateur DOIT tout fournir.
    * models.py + repositories.py : base SQLAlchemy présente (sync).
    * services/ : répertoire VIDE. task_service.py : présent.
    * Tests : 4 fichiers (models, repositories, routers, task_service),
      non collectables sans extra [fastapi].
    → Django : 93 routes, 128 settings, throttles, middleware app-auth,
      anti-énumération systématique. Écart : ~91 endpoints.

  Async du Core — plus avancé que ne le dit l'audit :
    * core/jwt_service.py : API duale COMPLÈTE — AsyncTokenBlacklistProtocol
      (is_blacklisted_async, is_user_revoked_async, revoke_all_user_tokens_
      async, blacklist_token_async), wrapper via asyncio.to_thread,
      decode_token_async, blacklist_token_async, blacklist_token_by_jti_
      async, revoke_all_user_tokens_async, refresh_tokens_async. Détection
      hasattr(service, "*_async") avec repli to_thread. ← PATTERN DE
      RÉFÉRENCE à généraliser.
    * ports/repositories.py : 0 async — UserRepository est 100 % sync.
    * totp/magic_link/session/webauthn services : 0 async.
    → Le chantier async = généraliser le pattern jwt_service aux ports
      et aux services restants, PAS une réécriture.

  SDK JS :
    * Docs présentes (docs/en/integration/javascript/: core, react, vue) ;
      packages @tenxyte/core, @tenxyte/react, @tenxyte/vue dans le monorepo
      JS externe. Aucun composant UI (hooks/logique seulement).

---------------------------------------------------------------------------

  1. Ports async (tenxyte/ports/)

    * Nouvelles interfaces additives dans ports/repositories.py (ou
      ports/async_repositories.py) : AsyncUserRepository — chaque méthode
      sync X a une variante `async def X` de sémantique identique.
      Idem pour les ports secondaires utilisés en requête : cache (déjà
      couvert côté blacklist), TOTP storage, magic link storage, webauthn
      storage.
    * Adaptateur générique SyncToAsyncRepository(sync_repo) : enveloppe
      to_thread de n'importe quelle implémentation sync (repli universel,
      utilisé par défaut si l'implémentation fournie est sync).
    * RÈGLE : aucune signature sync existante ne change (D1).

  2. Complétion async du Core

    * magic_link_service, session_service : méthodes *_async (to_thread
      sur le storage sync, appel natif si storage async détecté) — même
      logique métier, zéro duplication (extraction des parties pures).
    * totp_service : la crypto est CPU-bound (reste sync) ; seuls les accès
      storage passent par le pont.
    * jwt_service : rien à faire (déjà dual) — sert de gabarit documenté.

  3. Socle FastAPI production (adapters/fastapi/)

    * app.py : create_tenxyte_app(settings) -> FastAPI et
      create_tenxyte_router(settings) -> APIRouter (montable dans une app
      existante). Lifespan : init engine SQLAlchemy async + healthcheck.
    * settings.py : FastAPISettingsProvider (pydantic-settings, env
      TENXYTE_*) — mêmes noms et défauts que le provider Django (réutilise
      la résolution de core/settings.py).
    * repositories_async.py : SQLAlchemyAsyncUserRepository (+ role,
      permission, application, refresh_token, otp, agent...) implémentant
      les ports async ; aiosqlite (dev) / asyncpg (prod).
    * middleware.py : ApplicationAuthMiddleware (X-Access-Key/Secret,
      parité comportement Django incluant APP_AUTH_REQUIRED 401),
      throttling (slowapi ou implémentation maison sur le cache port),
      error handler global au format {error, code, details}.
    * migrations/ : Alembic pour le stack de référence.
    * deps.py : DI par défaut branchée sur le stack de référence,
      surchargeable (fin des NotImplementedError).
    * SUPPRESSION du check bcrypt inline : tout passe par le Core.

  4. Parité d'endpoints — 7 groupes, ordre A→B→C→F→D→E→G (D8)

    A. Auth de base : register, login/email, login/phone, refresh, logout,
       logout/all, me (GET/PATCH), me/roles
    B. Password : reset/request, reset/confirm, change, set-initial,
       strength, requirements (+ force-password-change scope)
    C. OTP & passwordless : otp/request, otp/verify/email|phone,
       login/otp/request|verify, magic-link/request|verify, 2fa/* (5)
    F. AIRS : ai/tokens/* (7), ai/pending-actions/* (3), découverte
       .well-known/airs (z_aud_2)
    D. RBAC & admin : permissions/*, roles/*, users/<id>/roles|permissions,
       applications/*, admin/users/* (ban/unban/lock/unlock), admin
       security (audit-logs, login-attempts, tokens), dashboard/*
    E. Organisations : organizations/* (12), org-roles
    G. WebAuthn (6) + Social (2 par provider) + GDPR user/admin

    Chaque endpoint porté DOIT reproduire : chemin (sous préfixe), corps de
    requête/réponse (endpoints.md = contrat), codes HTTP, codes d'erreur,
    anti-énumération, feature-flags (FEATURE_DISABLED 404), scopes de
    token (2fa_setup_only, password_change_only), throttling équivalent.

  5. Preuve de parité

    * scripts/parity_matrix.py : extrait les routes Django (urls.py) et
      FastAPI (app.routes), normalise, diffe. Sortie : table markdown
      (publiée dans la doc) + exit != 0 si un endpoint documenté manque
      hors liste d'exclusions (parity_exclusions.toml, chaque entrée
      justifiée par un commentaire).
    * Suite de contrat partagée : tests/contract/ paramétrés par une
      fixture `adapter_client` (django | fastapi) — réutilise les
      snapshots de forme existants (test_endpoint_response_shape_
      snapshots) génériques HTTP. Les tests canoniques (test_canonical_
      spec.py) s'appliquent aux deux.
    * CI : job fastapi-tests avec --cov=tenxyte.adapters.fastapi
      --cov-fail-under=90 ; job contract-parity exécutant matrice + suite
      partagée contre les deux adapters.

  6. Anti-blocage event loop (D5)

    * scripts/check_async_purity.py (AST) : dans adapters/fastapi/, tout
      `async def` handler ne doit contenir aucun appel des motifs
      interdits : méthodes des repos sync, requests.*, time.sleep,
      open() hors to_thread... Liste maintenue dans le script.
    * Branché en CI (job lint).

  7. SDK JS — composants UI (monorepo JS externe, contrat fourni ici)

    Côté repo Python (livrables de CE repo) :
    * Export OpenAPI versionné : scripts/export_openapi.py → openapi/
      tenxyte-django.json + tenxyte-fastapi.json (diff = même contrat).
    * Backend démo docker (examples/js-contract-backend/) consommé par la
      CI du monorepo JS pour ses tests E2E.

    Côté monorepo JS (spécifié ici, implémenté là-bas) :
    * @tenxyte/ui-headless : SignIn, SignUp, OTPInput, TwoFactorSetup,
      PasskeyButton, ForcedPasswordChange, OrgSwitcher — hooks + composants
      React sans style, ARIA complet, gestion des états (loading, erreurs
      par code, 2FA requis, must_change_password, HITL le cas échéant).
    * @tenxyte/ui : couche stylée (tokens CSS custom properties, thème
      clair/sombre) au-dessus de ui-headless.
    * Tests : vitest + testing-library + axe-core (a11y) ; E2E Playwright
      contre le backend démo.

  8. Documentation

    * fastapi_quickstart.md : réécriture zéro-config (pip install
      tenxyte[fastapi] → create_tenxyte_app → uvicorn → premier appel).
    * Tableau de parité auto-généré publié (EN/FR).
    * async_guide.md : mise à jour avec les ports async + gabarit
      jwt_service.

---------------------------------------------------------------------------

  Contraintes transverses

  * Zéro modification de l'adapter Django et des signatures sync du Core :
    tout est additif (nouvelles classes, nouvelles méthodes *_async,
    nouveau code FastAPI).
  * Le contrat filaire Django est la référence (D3) — en cas d'ambiguïté
    de la doc, le comportement Django tranche.
  * Chaque vague de parité (A→G) se termine par : matrice partielle verte
    sur le groupe + suite de contrat du groupe verte sur les deux adapters
    + checkpoint.
  * Couverture : le seuil global 90 % du projet s'applique désormais AUSSI
    au sous-arbre adapters/fastapi (gate dédiée).
