# Requirements Document

## Introduction

Cette spécification couvre la **Phase 2 « Le pari IA »** de la feuille de route issue de
`AUDIT.md` : la conversion de l'avance technique AIRS en standard de facto de l'identité des
agents IA. L'implémentation AIRS existe déjà dans Tenxyte (tokens délégués hashés, double RBAC,
HITL, circuit breaker, dead man's switch, budget LLM, trace forensique) — cette phase ne la
réécrit pas : elle la **formalise** (spécification ouverte + suite de conformité), l'**expose**
(endpoint de découverte, connecteurs LangChain et MCP, exemple CrewAI) et la **prouve**
(benchmarks reproductibles).

Huit chantiers :

1. La **spécification AIRS/1.0** — document normatif indépendant du code, licence CC BY 4.0.
2. Un **endpoint de découverte** `.well-known/airs` (seul ajout de code dans `src/tenxyte`).
3. Une **suite de conformité** HTTP boîte noire exécutable contre toute implémentation.
4. Le connecteur **`tenxyte-langchain`** (package PyPI indépendant, client HTTP pur).
5. Le serveur **`tenxyte-mcp-server`** (package PyPI indépendant, transport stdio).
6. Un **exemple CrewAI** exécutable de bout en bout.
7. Des **benchmarks reproductibles** (surcoût de validation, latence HITL).
8. La **distribution communautaire** (article, soumissions aux annuaires — process).

Tout est additif : aucun endpoint, setting, modèle ou comportement AIRS existant ne change.

## Glossary

- **AIRS_Spec** : le document normatif `spec/airs/AIRS-1.0.md` (AI Responsibility & Security,
  version 1.0), rédigé avec le vocabulaire RFC 2119, publié sous licence CC BY 4.0.
- **Delegating_User** : l'utilisateur humain qui émet un Agent_Token et dont les permissions sont
  empruntées (champ `triggered_by` du modèle existant).
- **Agent_Token** : le jeton de délégation défini par le modèle `AgentToken` existant — brut
  transmis une seule fois, seul le hash SHA-256 persisté, statuts `ACTIVE`/`SUSPENDED`/`REVOKED`/
  `EXPIRED`.
- **Double_Validation** : la règle existante imposant que chaque requête d'agent vérifie (a) que
  la permission figure dans les `granted_permissions` du token ET (b) que le Delegating_User
  possède toujours cette permission.
- **HITL_Flow** : le flux Human-in-the-Loop existant — réponse `202` avec `confirmation_token`,
  confirmation/refus humain, rejeu avec l'en-tête `X-Action-Confirmation`.
- **Guardrails** : les garde-fous d'exécution existants — circuit breaker (RPM/total/échecs),
  dead man's switch (heartbeat), budget LLM avec suspension automatique.
- **Conformance_Levels** : les niveaux de conformité définis par l'AIRS_Spec — `core` (tokens
  délégués + Double_Validation + révocation), `hitl`, `guards`, `budget`, `trace`.
- **Discovery_Endpoint** : le nouvel endpoint `GET {API_PREFIX}/auth/ai/.well-known/airs/`
  retournant la version de spec, les Conformance_Levels actifs, la carte des endpoints et les
  limites configurées.
- **Conformance_Suite** : la suite de tests HTTP boîte noire (`spec/airs/conformance/`)
  paramétrée par URL de base et credentials, validant une implémentation contre l'AIRS_Spec.
- **LangChain_Connector** : le package PyPI `tenxyte-langchain` (monorepo
  `integrations/langchain/`) — client HTTP pur pour l'écosystème LangChain/LangGraph.
- **Budget_Callback** : le composant `TenxyteBudgetCallbackHandler` du LangChain_Connector qui
  agrège l'usage LLM (`on_llm_end`) et le rapporte à l'endpoint `report-usage`.
- **HITL_Exception** : l'exception typée `TenxyteHITLPending` (portant `confirmation_token` et
  `expires_at`) levée par le LangChain_Connector sur toute réponse `202`, avec un mécanisme de
  reprise rejouant la requête avec `X-Action-Confirmation`.
- **MCP_Server** : le package PyPI `tenxyte-mcp-server` (monorepo `integrations/mcp-server/`) —
  serveur Model Context Protocol exposant les primitives AIRS d'entretien de token comme tools.
- **HTTP_Only_Rule** : la règle de conception (D2) interdisant aux connecteurs tout import du
  package `tenxyte` — ils ne communiquent que par le protocole filaire de l'AIRS_Spec.
- **No_Privilege_Amplification_Rule** : la règle de conception (D3) interdisant au MCP_Server de
  détenir un JWT utilisateur, de créer des Agent_Tokens ou de confirmer des actions HITL.
- **CrewAI_Example** : l'exemple exécutable `examples/crewai/` démontrant le cycle complet
  (émission, AgentBearer, HITL, budget) avec un crew CrewAI.
- **Benchmark_Harness** : les scripts reproductibles `benchmarks/airs/` mesurant le surcoût de la
  validation AgentBearer + Double_Validation et la latence du HITL_Flow.
- **Core** : la couche applicative framework-agnostic existante (`tenxyte.core` / `tenxyte.ports`).
- **Django_Adapter** : la couche d'implémentation existante (`tenxyte.adapters.django`,
  `tenxyte.views`, `tenxyte.services`, `tenxyte.models`).
- **Existing_Public_Contract** : l'ensemble des endpoints, formats de requête/réponse, codes
  HTTP, réglages, migrations et comportements déjà documentés ou couverts par des tests avant
  cette phase — incluant la totalité des endpoints `/ai/*` existants.

## Requirements

### Requirement 1: Spécification AIRS/1.0 ouverte

**User Story:** En tant qu'implémenteur tiers ou décideur technique, je veux une spécification
normative, versionnée et librement réutilisable du protocole AIRS, afin de pouvoir l'évaluer,
la citer et l'implémenter sans dépendre du code de Tenxyte.

#### Acceptance Criteria

1. THE System SHALL publish the AIRS_Spec at `spec/airs/AIRS-1.0.md`, versioned `1.0`, using
   RFC 2119 normative vocabulary (MUST / SHOULD / MAY).
2. THE AIRS_Spec SHALL be licensed under CC BY 4.0, with the license stated in the document and a
   `spec/airs/LICENSE` file, independent from the MIT license of the code.
3. THE AIRS_Spec SHALL normatively define: the delegation model (an agent never acts on its own
   authority), the Agent_Token lifecycle state machine (`ACTIVE`, `SUSPENDED` with its five
   reasons, `REVOKED`, `EXPIRED`) and its transitions, the Double_Validation rule, the wire
   protocol (the `AgentBearer` authorization scheme, the `X-Action-Confirmation` and
   `X-Prompt-Trace-ID` headers), the HITL_Flow contract (202 response shape, confirmation token
   expiry, replay), the Guardrails semantics, the normative REST endpoints (as paths relative to
   a discoverable base), and the normative error codes.
4. THE AIRS_Spec SHALL define the five Conformance_Levels (`core`, `hitl`, `guards`, `budget`,
   `trace`) such that `core` is mandatory and each other level is independently claimable.
5. THE AIRS_Spec SHALL contain a Security Considerations section covering at minimum: raw-token
   handling (single transmission, hash-only storage), privilege amplification risks, HITL token
   leakage, and trace-ID PII considerations.
6. THE normative sections of the AIRS_Spec SHALL NOT reference Django, Tenxyte, or any
   implementation detail; Tenxyte SHALL appear only in a non-normative annex as the reference
   implementation.
7. THE AIRS_Spec SHALL be consistent with the existing Tenxyte AIRS implementation: every
   normative endpoint, header, status transition, and error code in the spec SHALL correspond to
   the existing behavior (the spec formalizes, it does not invent server-side behavior beyond the
   Discovery_Endpoint).

### Requirement 2: Endpoint de découverte AIRS

**User Story:** En tant que connecteur ou outil tiers, je veux interroger un endpoint de
découverte standard, afin de connaître la version de spec, les niveaux de conformité actifs et la
carte des endpoints sans configuration manuelle.

#### Acceptance Criteria

1. THE System SHALL expose `GET {API_PREFIX}/auth/ai/.well-known/airs/` returning HTTP 200 with a
   JSON body containing: `airs_version` (string `"1.0"`), `conformance` (array of active
   Conformance_Levels), `endpoints` (map of logical names to absolute or prefix-relative paths),
   and `limits` (at minimum `token_max_lifetime` and `default_expiry`).
2. THE `conformance` array SHALL reflect the actual runtime configuration: `budget` SHALL be
   listed only when `AIRS_BUDGET_TRACKING_ENABLED` is true, and `guards` only when
   `AIRS_CIRCUIT_BREAKER_ENABLED` is true; `core`, `hitl`, and `trace` SHALL be listed whenever
   AIRS is enabled.
3. WHERE `AIRS_ENABLED` is false, THE Discovery_Endpoint SHALL respond with HTTP 404 and the
   existing `FEATURE_DISABLED` error shape, without any internal processing.
4. THE Discovery_Endpoint SHALL be unauthenticated (AllowAny) and SHALL never include any token,
   user data, or per-tenant information — capabilities only.
5. THE Discovery_Endpoint SHALL be implemented as a purely additive change: no existing `/ai/*`
   endpoint, serializer, model, or setting is modified.
6. THE System SHALL document the Discovery_Endpoint in `docs/en/endpoints.md`,
   `docs/fr/endpoints.md`, and `docs/en/airs.md` / `docs/fr/airs.md`.

### Requirement 3: Suite de conformité

**User Story:** En tant qu'implémenteur (Tenxyte inclus), je veux une suite de tests boîte noire
exécutable contre n'importe quelle implémentation AIRS, afin de prouver ou vérifier la conformité
à la spec de manière opposable.

#### Acceptance Criteria

1. THE System SHALL provide a Conformance_Suite under `spec/airs/conformance/`, runnable with
   pytest, communicating exclusively over HTTP, parameterized by `--airs-base-url` and the
   required credentials (user JWT, application key/secret).
2. THE Conformance_Suite SHALL begin by calling the Discovery_Endpoint and SHALL automatically
   skip the test modules of Conformance_Levels not announced by the implementation.
3. THE Conformance_Suite SHALL cover, per level: `core` — token issuance, single raw-token
   transmission, AgentBearer authentication, Double_Validation (permission absent from grant →
   403; permission removed from the Delegating_User → 403), revocation and expiry; `hitl` — 202
   contract, confirmation, denial, expiry, replay with `X-Action-Confirmation`; `guards` — RPM
   suspension and heartbeat-missing suspension; `budget` — usage reporting, accumulation, and
   `BUDGET_EXCEEDED` suspension; `trace` — `X-Prompt-Trace-ID` persistence on pending actions.
4. WHEN the Conformance_Suite is executed against the Tenxyte reference implementation with all
   levels enabled, THE suite SHALL pass entirely.
5. THE System SHALL provide a deliberately non-conformant mock server (negative control) and an
   automated check that the Conformance_Suite fails against it.
6. THE Conformance_Suite SHALL be wired into CI against an ephemeral Tenxyte instance, so that a
   server-side regression breaking the spec is detected.

### Requirement 4: Connecteur LangChain (`tenxyte-langchain`)

**User Story:** En tant que développeur d'agents LangChain/LangGraph, je veux un connecteur
officiel gérant le cycle de vie du token, le budget, le HITL et la trace, afin d'intégrer la
gouvernance AIRS sans écrire de plomberie HTTP.

#### Acceptance Criteria

1. THE System SHALL provide the LangChain_Connector as an independently versioned package
   (`integrations/langchain/`, initial version 0.1.0) publishable to PyPI as `tenxyte-langchain`.
2. THE LangChain_Connector SHALL comply with the HTTP_Only_Rule: it SHALL NOT import the `tenxyte`
   package, and its runtime dependencies SHALL be limited to an HTTP client and `langchain-core`.
3. THE LangChain_Connector SHALL provide a low-level `TenxyteAIRSClient` consuming the
   Discovery_Endpoint to resolve endpoint paths, and a high-level `TenxyteAgentAuth` that attaches
   `Authorization: AgentBearer <token>` to every outgoing request.
4. WHERE the Agent_Token declares `heartbeat_required_every`, THE `TenxyteAgentAuth` SHALL send
   heartbeats in a background task at an interval strictly smaller than the declared requirement.
5. THE Budget_Callback SHALL implement the LangChain callback interface, aggregate prompt and
   completion tokens and cost on `on_llm_end`, report them to the `report-usage` endpoint, and
   raise a typed `TenxyteBudgetExceededError` when the server responds that the token is suspended
   for `BUDGET_EXCEEDED`.
6. WHEN any request through the connector receives an HTTP 202 HITL response, THE
   LangChain_Connector SHALL raise the HITL_Exception carrying `confirmation_token` and
   `expires_at`, and SHALL provide a `resume(confirmation_token)` mechanism replaying the original
   request with the `X-Action-Confirmation` header.
7. THE LangChain_Connector SHALL propagate a trace identifier (derived from the LangChain run ID
   when available, otherwise generated) as `X-Prompt-Trace-ID` on every request.
8. THE LangChain_Connector SHALL ship its own automated test suite running against a mocked AIRS
   backend, covering criteria 3 through 7, plus an optional integration suite against a local
   Tenxyte instance.
9. THE LangChain_Connector SHALL include documentation with a minimal working example and a
   LangGraph `interrupt()` recipe for the HITL_Flow.

### Requirement 5: Serveur MCP (`tenxyte-mcp-server`)

**User Story:** En tant qu'opérateur d'agents compatibles MCP (Claude Desktop, clients MCP), je
veux un serveur MCP exposant l'entretien du token AIRS comme tools, afin que l'agent puisse gérer
son heartbeat, son budget et consulter son statut sans code spécifique.

#### Acceptance Criteria

1. THE System SHALL provide the MCP_Server as an independently versioned package
   (`integrations/mcp-server/`, initial version 0.1.0) publishable to PyPI as
   `tenxyte-mcp-server`, runnable via `uvx tenxyte-mcp-server` over stdio transport.
2. THE MCP_Server SHALL comply with the HTTP_Only_Rule (no `tenxyte` import) and SHALL be
   configured exclusively through environment variables (`TENXYTE_BASE_URL`,
   `TENXYTE_AGENT_TOKEN`, `TENXYTE_ACCESS_KEY`, `TENXYTE_ACCESS_SECRET`).
3. THE MCP_Server SHALL expose the tools `airs_token_status`, `airs_heartbeat`,
   `airs_report_usage`, `airs_list_pending_actions`, and `airs_discovery`, each mapping to exactly
   one existing AIRS endpoint.
4. THE MCP_Server SHALL comply with the No_Privilege_Amplification_Rule: it SHALL NOT accept or
   store a user JWT, SHALL NOT expose any tool that creates Agent_Tokens, and SHALL NOT expose any
   tool that confirms or denies pending HITL actions.
5. IF the configured Agent_Token is suspended, revoked, or expired, THEN every tool SHALL return a
   structured MCP error carrying the server-provided reason, without crashing the server process.
6. THE MCP_Server SHALL ship an automated test suite against a mocked AIRS backend covering every
   tool, the error paths of criterion 5, and the absence of privilege-amplifying tools.
7. THE MCP_Server SHALL include documentation with a Claude Desktop configuration example
   (`claude_desktop_config.json`) and the environment-variable reference.

### Requirement 6: Exemple CrewAI

**User Story:** En tant que développeur évaluant AIRS, je veux un exemple CrewAI complet et
exécutable, afin de constater en conditions réelles la délégation, le HITL et la suspension
budget.

#### Acceptance Criteria

1. THE System SHALL provide the CrewAI_Example under `examples/crewai/` with a docker-compose (or
   equivalent single-command setup) starting a demo Tenxyte backend with a protected demo API.
2. THE CrewAI_Example SHALL demonstrate, in one documented run: Agent_Token issuance by a human
   user, agent calls authenticated with AgentBearer, an HITL-gated tool (202 → human confirmation
   → replay), and a budget suspension triggered live by reported usage.
3. THE CrewAI_Example SHALL run with a fake/deterministic LLM by default (no API key required) and
   SHALL document the option to switch to a real LLM.
4. THE CrewAI_Example README SHALL provide a step-by-step walkthrough whose successful completion
   is recorded in `manual_tests.md` (MT-4).

### Requirement 7: Benchmarks reproductibles

**User Story:** En tant que mainteneur préparant le contenu de lancement, je veux des benchmarks
reproductibles du surcoût AIRS, afin de publier des chiffres opposables (« la gouvernance ne coûte
que X ms »).

#### Acceptance Criteria

1. THE System SHALL provide the Benchmark_Harness under `benchmarks/airs/` with a pinned,
   documented environment (docker-compose, identical seed) so results are reproducible.
2. THE Benchmark_Harness SHALL measure at minimum: (a) p50/p95/p99 request latency of an
   AgentBearer-authenticated endpoint with Double_Validation versus the same endpoint with plain
   user JWT versus unauthenticated baseline; (b) the end-to-end HITL round-trip latency (request →
   202 → confirm → replay → response), excluding human think-time.
3. THE Benchmark_Harness SHALL emit machine-readable results (JSON) plus a `RESULTS.md` template
   including machine specifications, and at least one executed run SHALL be recorded.
4. THE Benchmark_Harness SHALL NOT be part of the default test suite (separate invocation), and
   SHALL NOT affect any runtime code.

### Requirement 8: Distribution communautaire

**User Story:** En tant que porteur du projet, je veux que la spec et les connecteurs atteignent
les communautés d'agents (pas les communautés Django), afin de capter l'adoption dans la fenêtre
de marché identifiée par l'audit.

#### Acceptance Criteria

1. THE System SHALL produce a launch technical article draft (working title « How to give an AI
   agent a credit card limit ») grounded in the AIRS_Spec and the executed benchmark results,
   stored under `spec/airs/launch/`.
2. THE community submissions (LangChain integrations directory, awesome-mcp-servers, MCP server
   directories) SHALL be performed and recorded in the `manual_tests.md` execution register
   (MT-7); their acceptance by third parties is outside the Definition of Done.
3. THE README (EN and FR) SHALL link the AIRS_Spec and both connectors from the AIRS section.

### Requirement 9: Compatibilité ascendante et respect de l'architecture

**User Story:** En tant que mainteneur, je veux que cette phase soit purement additive côté
Tenxyte et étanche côté connecteurs, afin de ne créer ni régression ni couplage caché.

#### Acceptance Criteria

1. THE System SHALL implement every capability of Requirements 1 through 8 as additive changes:
   no existing endpoint (including all `/ai/*` routes), serializer field, response shape, setting
   default, model field, or migration is modified or removed.
2. THE only change inside `src/tenxyte` SHALL be the Discovery_Endpoint (view, route, docs, tests);
   `tenxyte.core` and `tenxyte.ports` SHALL NOT be modified.
3. THE HTTP_Only_Rule SHALL be enforced by an automated check (import-graph test) failing if any
   integration package imports `tenxyte`.
4. THE System SHALL ensure that all automated tests passing before this phase continue to pass
   after it; non-automatable verifications SHALL be recorded in `manual_tests.md`.

## Notes de conception ouvertes

- Le chemin exact de découverte (`/ai/.well-known/airs/` sous le prefix API vs racine du domaine)
  est arrêté en conception — contrainte : joignable sans authentification utilisateur, cohérent
  avec le routage existant de `tenxyte.urls`.
- La stratégie de heartbeat en tâche de fond du LangChain_Connector (thread daemon vs boucle
  asyncio selon le contexte d'exécution) est précisée en conception ; contrainte : jamais bloquant
  pour l'agent, arrêt propre à la fermeture.
- Le versionnage des packages d'intégration est indépendant de celui de Tenxyte (0.1.0 initial) ;
  la matrice de compatibilité (connector ↔ airs_version découverte) est définie en conception.
- La publication PyPI des deux connecteurs réutilise le pipeline Trusted Publishing mis en place
  en Phase 1 (`z_aud_1`) si disponible, sinon un workflow équivalent dédié.
