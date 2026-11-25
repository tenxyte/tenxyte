#### Plan : Phase 2 « Le pari IA » — AIRS ouvert + écosystème agents (z_aud_2)

  Objectif : convertir l'avance technique AIRS (unique sur le marché, cf.
  AUDIT.md §6.2) en standard de facto avant que les acteurs financés
  (Auth0 AI, Stytch, WorkOS) ne comblent l'écart. Trois leviers : une spec
  ouverte citable, des connecteurs dans les écosystèmes agents, des preuves
  (conformité + benchmarks).

---------------------------------------------------------------------------

  État AIRS constaté dans le code (base de la spec ouverte)

    Modèles (src/tenxyte/models/agent.py) :
    * AgentToken : hash SHA-256 (jamais le brut), agent_id, triggered_by
      (l'humain délégant), application, organization?, granted_permissions
      (M2M Permission), status {ACTIVE, SUSPENDED, REVOKED, EXPIRED},
      suspended_reason {RATE_LIMIT, ANOMALY, MANUAL, HEARTBEAT_MISSING,
      BUDGET_EXCEEDED}, circuit breaker (max_rpm, max_total, max_failures +
      compteurs), dead man's switch (heartbeat_required_every,
      last_heartbeat_at), budget (budget_limit_usd, current_spend_usd).
    * AgentPendingAction : permission_requested, endpoint, payload,
      confirmation_token (unique), expires_at (défaut 10 min),
      confirmed_at/denied_at, prompt_trace_id.

    Service (services/agent_service.py) : create, validate, validate_permission
    (double RBAC), revoke, suspend, revoke_all_for_user/agent, send_heartbeat,
    check_circuit_breaker, create/confirm/deny_pending_action, report_usage.

    Endpoints existants (urls.py, prefix {API_PREFIX}/auth/) :
      GET/POST /ai/tokens/            GET/PUT/DELETE /ai/tokens/<id>/
      POST /ai/tokens/<id>/revoke/    POST /ai/tokens/<id>/suspend/
      POST /ai/tokens/<id>/heartbeat/ POST /ai/tokens/<id>/report-usage/
      POST /ai/tokens/revoke-all/     GET  /ai/pending-actions/
      POST /ai/pending-actions/<token>/confirm/  POST .../deny/

    Protocole filaire existant :
      Authorization: AgentBearer <raw_token>
      X-Action-Confirmation: <confirmation_token>   (rejeu post-HITL)
      X-Prompt-Trace-ID: <trace_id>                 (forensique)
      HITL → 202 {status: pending_confirmation, confirmation_token, expires_at}

    Settings (conf/airs.py) : AIRS_ENABLED (True), AIRS_TOKEN_MAX_LIFETIME
    (86400), AIRS_DEFAULT_EXPIRY (3600), AIRS_REQUIRE_EXPLICIT_PERMISSIONS,
    AIRS_CIRCUIT_BREAKER_ENABLED, AIRS_DEFAULT_MAX_RPM/TOTAL/FAILURES,
    AIRS_CONFIRMATION_REQUIRED (liste de permissions), AIRS_REDACT_PII,
    AIRS_BUDGET_TRACKING_ENABLED.

    → La spec AIRS/1.0 FORMALISE ce protocole ; elle n'invente rien de
      nouveau côté serveur (hors endpoint de découverte).

---------------------------------------------------------------------------

  1. Spécification AIRS/1.0 (spec/airs/AIRS-1.0.md, CC BY 4.0)

    * Vocabulaire normatif RFC 2119 (MUST/SHOULD/MAY).
    * Sections :
      1. Terminologie (Delegating User, Agent, Agent Token, Guardrail...)
      2. Modèle de délégation (jamais d'autorité propre ; double validation)
      3. Cycle de vie du token : machine à états ACTIVE → SUSPENDED
         (5 raisons) / REVOKED / EXPIRED ; règles de transition
      4. Protocole filaire : schéma d'auth AgentBearer, en-têtes
         X-Action-Confirmation et X-Prompt-Trace-ID, formats de réponses
      5. HITL : contrat 202, confirmation_token, expiration, rejeu
      6. Guardrails : circuit breaker, dead man's switch, budget —
         sémantique et priorités des suspensions
      7. Endpoints REST normatifs (chemins relatifs à une base découvrable)
      8. Codes d'erreur normatifs
      9. Découverte (.well-known/airs)
      10. Niveaux de conformité :
          AIRS-Core   (tokens délégués + double validation + révocation)
          AIRS-HITL   (Core + actions en attente)
          AIRS-Guards (Core + circuit breaker + dead man's switch)
          AIRS-Budget (Core + budget)
          AIRS-Trace  (Core + prompt trace)
      11. Considérations de sécurité
    * AUCUNE référence normative à Django/Tenxyte ; Tenxyte cité uniquement
      en annexe « implémentations connues » comme implémentation de référence.

  2. Endpoint de découverte (code additif)

    GET {API_PREFIX}/auth/ai/.well-known/airs/  (AllowAny, gated AIRS_ENABLED)
    → 200 {
        "airs_version": "1.0",
        "conformance": ["core", "hitl", "guards", "budget", "trace"],
          // reflète les settings réels (ex: budget absent si
          // AIRS_BUDGET_TRACKING_ENABLED=False)
        "endpoints": { "tokens": ".../ai/tokens/", ... },
        "limits": { "token_max_lifetime": 86400, ... }
      }
    → 404 FEATURE_DISABLED si AIRS_ENABLED=False (cohérent avec les
      patterns feature-flag existants, cf. OTP_LOGIN).
    Jamais de données (aucun token, aucun user) — capacités uniquement.

  3. Suite de conformité (spec/airs/conformance/)

    * pytest boîte noire, HTTP pur (httpx), paramétrée :
      --airs-base-url, --airs-user-jwt, --airs-app-key/secret
    * Un module par niveau de conformité ; skip automatique des niveaux
      non annoncés par la découverte.
    * Contrôle négatif : un mock serveur volontairement non conforme
      (ex : accepte un token révoqué) DOIT faire échouer la suite.
    * Doublement utilisée : test d'intégration interne CI (contre un
      Tenxyte éphémère) + outil public pour implémenteurs tiers.

  4. tenxyte-langchain (integrations/langchain/, package PyPI)

    * Client HTTP pur (httpx) — IMPORT DE tenxyte INTERDIT (D2).
    * Composants :
      - TenxyteAIRSClient : bas niveau (create/validate/heartbeat/
        report_usage/pending_actions), découverte automatique
      - TenxyteAgentAuth : cycle de vie haut niveau — création du token
        depuis un JWT utilisateur (au setup, côté humain), header
        AgentBearer auto, heartbeat en tâche de fond (thread) si le token
        a heartbeat_required_every
      - TenxyteBudgetCallbackHandler(BaseCallbackHandler) : on_llm_end →
        agrège tokens/coût → POST report-usage ; suspension budget →
        TenxyteBudgetExceededError
      - Gestion HITL : réponse 202 → lève TenxyteHITLPending(
        confirmation_token, expires_at) ; helper resume(confirmation_token)
        qui rejoue avec X-Action-Confirmation ; recette LangGraph
        interrupt() documentée
      - Trace : run_id LangChain → X-Prompt-Trace-ID sur chaque requête
    * Dépendances : httpx, langchain-core (léger). Tests sur backend mocké
      (respx) + suite d'intégration optionnelle contre Tenxyte local.

  5. tenxyte-mcp-server (integrations/mcp-server/, package PyPI)

    * SDK MCP Python officiel (mcp), transport stdio (uvx-runnable :
      `uvx tenxyte-mcp-server`).
    * Config par env : TENXYTE_BASE_URL, TENXYTE_AGENT_TOKEN,
      TENXYTE_ACCESS_KEY/SECRET.
    * Tools exposés (lecture/entretien du token — JAMAIS de création,
      cf. D3) :
      - airs_token_status()        → statut, expiration, budget restant
      - airs_heartbeat()           → maintient le dead man's switch
      - airs_report_usage(cost_usd, prompt_tokens, completion_tokens)
      - airs_list_pending_actions() → actions HITL en attente de l'agent
      - airs_discovery()           → capacités du serveur
    * Resources : airs://token/status, airs://budget
    * Le serveur ne détient jamais de JWT humain ; la confirmation HITL
      reste une action humaine hors MCP (lien retourné dans la réponse).

  6. Exemple CrewAI (examples/crewai/)

    * Crew 2 agents (chercheur + rédacteur financier) : outils custom
      appelant une API démo protégée par @require_agent_clearance.
    * Démontre : émission du token par l'humain, AgentBearer, HITL sur
      l'outil « émettre une facture » (202 → pause → confirmation →
      reprise), suspension budget en direct.
    * README pas-à-pas + docker-compose du backend démo.

  7. Benchmarks (benchmarks/airs/)

    * bench_validation.py : p50/p95/p99 du middleware AgentBearer +
      double RBAC vs JWT nu vs sans auth (baseline), N configurable.
    * bench_hitl.py : latence du cycle 202 → confirm → rejeu.
    * Environnement figé (docker-compose, seed identique), RESULTS.md
      gabarit avec specs machine — publiable dans l'article de lancement.

  8. Distribution (process, tracé manual_tests.md)

    * Article de lancement (« How to give an AI agent a credit card
      limit ») s'appuyant sur spec + benchmarks.
    * Soumissions : LangChain integrations docs, awesome-mcp-servers,
      annuaire MCP. Registre MT-7.

---------------------------------------------------------------------------

  Contraintes transverses

  * 100 % additif côté tenxyte : seul l'endpoint de découverte touche
    src/ ; aucun endpoint/setting/modèle AIRS existant ne change.
  * Les connecteurs parlent HTTP uniquement (D2) — vérifié par test
    d'import-graph (Property 11).
  * Le MCP server n'amplifie jamais les privilèges (D3) : pas de création
    de token, pas de confirmation HITL côté agent.
  * Versionnage indépendant des packages d'intégration (0.1.0 initial).
