# Implementation Plan: Phase 2 « Le pari IA » (z_aud_2)

## Overview

Cette implémentation suit l'ordre de dépendance naturel du pari : la **spec d'abord** (elle est la
source de vérité que tout le reste consomme), puis la **découverte** (seul code serveur, prérequis
des connecteurs), puis la **suite de conformité** (verrou spec ↔ implémentation, prérequis de
confiance des connecteurs), puis les **deux connecteurs en parallèle**, puis l'**exemple CrewAI**
(qui consomme le connecteur LangChain), les **benchmarks**, et enfin la **distribution**.

Côté `src/tenxyte`, une seule tâche de code (2.1) ; tout le reste vit dans `spec/`,
`integrations/`, `examples/` et `benchmarks/`. Les vérifications non automatisables portent le
marqueur `[MT-x]` renvoyant à `manual_tests.md`.

## Tasks

- [ ] 1. Spécification AIRS/1.0
  - [ ] 1.1 Rédiger le document normatif `spec/airs/AIRS-1.0.md`
    - Structure en 11 sections (cf. `base.md` §1) : terminologie, modèle de délégation, machine à
      états du token (transitions + 5 raisons de suspension), protocole filaire (AgentBearer,
      X-Action-Confirmation, X-Prompt-Trace-ID), contrat HITL 202, sémantique des Guardrails,
      endpoints REST normatifs, codes d'erreur, découverte, niveaux de conformité, considérations
      de sécurité — chaque clause MUST/SHOULD avec identifiant stable `[AIRS-<NIVEAU>-n]`
    - Vérification de fidélité clause par clause contre le code existant (`models/agent.py`,
      `services/agent_service.py`, `decorators.py`, `conf/airs.py`)
    - Aucune référence normative à Django/Tenxyte ; annexe non normative « implémentations »
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [ ] 1.2 Ajouter la licence CC BY 4.0 de la spec
    - `spec/airs/LICENSE` + mention dans le document ; le code du repo reste MIT
    - _Requirements: 1.2_

  - [ ] 1.3 Write spec-fidelity unit tests
    - Tests côté serveur vérifiant que chaque valeur normative citée par la spec existe dans le
      code : les 4 statuts et 5 raisons de suspension de `AgentToken`, l'expiration par défaut des
      pending actions (10 min), le schéma `AgentBearer`, la forme du 202
    - _Requirements: 1.7_

- [ ] 2. Endpoint de découverte AIRS
  - [ ] 2.1 Implémenter `AIRSDiscoveryView` et sa route
    - Ajouter la vue à `src/tenxyte/views/agent_views.py` (AllowAny, gating `AIRS_ENABLED` → 404
      `FEATURE_DISABLED`), le helper `_build_endpoint_map()` basé sur `reverse()`, la route
      `ai/.well-known/airs/` dans `urls.py` (section `# Agent / AIRS`), l'export dans
      `views/__init__.py`, le schéma drf-spectacular
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ] 2.2 Write property test for discovery shape and conformance gating
    - **Property 1: Forme et exactitude de la découverte** (combinatoire
      `AIRS_CIRCUIT_BREAKER_ENABLED` × `AIRS_BUDGET_TRACKING_ENABLED` via `override_settings`)
    - **Validates: Requirements 2.1, 2.2**

  - [ ] 2.3 Write property test for disabled-feature behavior
    - **Property 2: Effet nul de la découverte quand AIRS est désactivé**
    - **Validates: Requirements 2.3**

  - [ ] 2.4 Write property test for zero data disclosure
    - **Property 3: La découverte ne divulgue jamais de données** (états de base générés)
    - **Validates: Requirements 2.4**

  - [ ] 2.5 Documenter la découverte
    - `docs/en/endpoints.md` + `docs/fr/endpoints.md` (section AIRS) et `docs/en/airs.md` +
      `docs/fr/airs.md` ; passer `scripts/validate_endpoints.py`
    - _Requirements: 2.6_

- [ ] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Suite de conformité
  - [ ] 4.1 Implémenter le socle de la suite (`spec/airs/conformance/`)
    - `conftest.py` : options `--airs-base-url`, `--airs-user-jwt`, `--airs-app-key/secret` ;
      fixture de session appelant la découverte ; marqueur `airs_level` avec skip automatique des
      niveaux non annoncés ; fixture d'émission d'un Agent_Token de test
    - _Requirements: 3.1, 3.2_

  - [ ] 4.2 Implémenter les modules de test par niveau
    - `test_core.py` (émission, transmission unique du brut, AgentBearer, Double_Validation dans
      les deux sens, révocation, expiration), `test_hitl.py` (202, confirm, deny, expiration,
      rejeu), `test_guards.py` (suspension RPM, heartbeat manquant), `test_budget.py` (report,
      accumulation, `BUDGET_EXCEEDED`), `test_trace.py` (persistance du trace ID) — chaque test
      référencé `[AIRS-*-n]`
    - _Requirements: 3.3_

  - [ ] 4.3 Implémenter le mock négatif et son test wrapper
    - `negative_mock/` : serveur minimal violant 3 clauses identifiées ; test automatisé
      vérifiant que la suite échoue contre lui
    - **Property 4 (moitié négative)**
    - _Requirements: 3.5_

  - [ ] 4.4 Câbler la conformité en CI contre un Tenxyte éphémère
    - Job CI : instance sqlite seedée → suite complète tous niveaux activés (**Property 4, moitié
      positive**) ; puis mock négatif → échec attendu
    - **Validates: Requirements 3.4, 3.6**

- [ ] 5. Connecteur LangChain (`tenxyte-langchain`)
  - [ ] 5.1 Créer le package et le client bas niveau
    - `integrations/langchain/` : `pyproject.toml` (0.1.0, deps httpx + langchain-core),
      `TenxyteAIRSClient` (découverte auto + cache, en-têtes application, `token_status`,
      `heartbeat`, `report_usage`, `pending_actions`, `request`), hiérarchie d'exceptions typées
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ] 5.2 Implémenter `TenxyteAgentAuth` avec heartbeat de fond
    - AgentBearer + `X-Prompt-Trace-ID` sur chaque requête ; thread daemon de heartbeat
      (intervalle `max(1, required // 2)`, arrêt propre via Event/context manager, échec → log +
      flag, jamais d'exception propagée)
    - _Requirements: 4.3, 4.4, 4.7_

  - [ ] 5.3 Implémenter `TenxyteBudgetCallbackHandler` et le contrat HITL
    - `on_llm_end` → agrégation (`token_usage` et `usage_metadata`) → `report-usage` ;
      `BUDGET_EXCEEDED` → `TenxyteBudgetExceededError` ; 202 → `TenxyteHITLPending` +
      `resume(confirmation_token)` rejouant la requête originale avec `X-Action-Confirmation`
    - _Requirements: 4.5, 4.6_

  - [ ] 5.4 Write property test for per-request authentication headers
    - **Property 5: Le connecteur LangChain authentifie chaque requête**
    - **Validates: Requirements 4.3, 4.7**

  - [ ] 5.5 Write property test for exact budget aggregation
    - **Property 6: Le callback budget rapporte l'agrégation exacte**
    - **Validates: Requirements 4.5**

  - [ ] 5.6 Write property test for the HITL contract
    - **Property 7: Contrat HITL du connecteur**
    - **Validates: Requirements 4.6**

  - [ ] 5.7 Write property test for heartbeat compliance
    - **Property 8: Le heartbeat respecte la contrainte déclarée** (horloge simulée)
    - **Validates: Requirements 4.4**

  - [ ] 5.8 Write property test for fail-safe behavior on terminal token states
    - **Property 9 (volet LangChain)** : 5 raisons de suspension + révoqué + expiré → exception
      typée, zéro retry
    - **Validates: Requirements 4.8**

  - [ ] 5.9 Documentation du connecteur
    - README du package : exemple minimal fonctionnel + recette LangGraph `interrupt()` pour le
      HITL ; lien depuis la section AIRS des READMEs Tenxyte
    - _Requirements: 4.9, 8.3_

- [ ] 6. Serveur MCP (`tenxyte-mcp-server`)
  - [ ] 6.1 Créer le package et le serveur stdio
    - `integrations/mcp-server/` : `pyproject.toml` (0.1.0, deps mcp + httpx, script console),
      `config.py` (validation des 4 variables d'env, échec explicite), `server.py` (FastMCP, les
      5 tools mappés 1:1, resources `airs://token/status` et `airs://budget`)
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ] 6.2 Write unit test locking the MCP tool surface
    - **Property 10: Surface MCP sans amplification de privilèges** (liste exacte des tools,
      aucune option JWT utilisateur)
    - **Validates: Requirements 5.3, 5.4**

  - [ ] 6.3 Write property test for structured errors on terminal token states
    - **Property 9 (volet MCP)** : chaque état terminal → `McpError` structurée portant la
      raison, process vivant
    - **Validates: Requirements 5.5**

  - [ ] 6.4 Tests unitaires et documentation du serveur
    - Schémas d'entrée des tools, démarrage sans env → exit ≠ 0 ; README avec bloc
      `claude_desktop_config.json` et référence des variables d'env `[MT-2]`
    - _Requirements: 5.6, 5.7_

- [ ] 7. Étanchéité des intégrations
  - [ ] 7.1 Write the import-graph check
    - **Property 11: Étanchéité HTTP des intégrations** — test automatisé (AST/`sys.modules`)
      échouant si `tenxyte.*` apparaît dans l'un des deux packages ; vérification des dépendances
      déclarées dans les deux `pyproject.toml`
    - **Validates: Requirements 4.2, 5.2, 9.3**

  - [ ] 7.2 Câbler la matrice CI des intégrations
    - Job `integrations-tests` : {langchain, mcp-server} × Python {3.10–3.13}, backend mocké
    - _Requirements: 4.8, 5.6, 9.3_

- [ ] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass (server + conformance + integrations), ask the user if questions arise.

- [ ] 9. Exemple CrewAI
  - [ ] 9.1 Construire l'exemple exécutable
    - `examples/crewai/` : docker-compose (Tenxyte démo + API métier avec endpoint HITL-gated),
      `crew.py` (2 agents, FakeLLM par défaut, option vrai LLM documentée), scénario complet
      émission → AgentBearer → HITL → confirmation → reprise → suspension budget
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ] 9.2 Rédiger le walkthrough et le valider `[MT-4]`
    - README pas-à-pas aligné sur la procédure MT-4 ; exécution complète consignée au registre
    - _Requirements: 6.4_

- [ ] 10. Benchmarks
  - [ ] 10.1 Implémenter le Benchmark_Harness
    - `benchmarks/airs/` : `bench_validation.py` (3 cibles, warm-up, p50/p95/p99, sortie JSON),
      `bench_hitl.py` (cycle auto-confirmé), environnement figé docker-compose + seed,
      `RESULTS.md` gabarit ; hors suite pytest par défaut (workflow_dispatch)
    - _Requirements: 7.1, 7.2, 7.4_

  - [ ] 10.2 Exécuter la campagne de référence `[MT-6]`
    - Au moins un run complet consigné dans `RESULTS.md` avec specs machine
    - _Requirements: 7.3_

- [ ] 11. Distribution et publication
  - [ ] 11.1 Publier les deux packages `[MT-1]`
    - TestPyPI puis PyPI (`tenxyte-langchain` 0.1.0, `tenxyte-mcp-server` 0.1.0) via le pipeline
      Trusted Publishing (Phase 1) ou workflow dédié équivalent ; installation vérifiée
      (`pip install`, `uvx tenxyte-mcp-server`)
    - _Requirements: 4.1, 5.1_

  - [ ] 11.2 Rédiger l'article de lancement
    - `spec/airs/launch/` : draft « How to give an AI agent a credit card limit » adossé à la
      spec et aux résultats de MT-6
    - _Requirements: 8.1_

  - [ ] 11.3 Effectuer les soumissions communautaires `[MT-7]`
    - Annuaire d'intégrations LangChain, awesome-mcp-servers, annuaires MCP ; consignation au
      registre (l'acceptation par les tiers est hors DoD)
    - _Requirements: 8.2_

  - [ ] 11.4 Mettre à jour les READMEs Tenxyte
    - Sections AIRS de `README.md` + `README.fr.md` : liens spec + connecteurs
    - _Requirements: 8.3_

- [ ] 12. Non-régression finale et validation manuelle
  - [ ] 12.1 Vérifier la non-régression serveur
    - **Property 12: Non-régression du serveur** — routes `/ai/*` et formes de réponses
      inchangées, `migrations/` identique, suite existante verte sans modification
    - **Validates: Requirements 9.1, 9.2, 9.4**

  - [ ] 12.2 Dérouler la campagne de tests manuels
    - Exécuter `manual_tests.md` MT-1 à MT-7 et compléter le registre
    - _Requirements: 5.7, 6.4, 7.3, 8.2_

- [ ] 13. Checkpoint final - Ensure all tests pass
  - Ensure all tests pass, manual test register complete, ask the user before announcing AIRS/1.0.

## Notes

- Les tâches marquées `[MT-x]` ont une contrepartie obligatoire dans `manual_tests.md` : la tâche
  n'est cochable qu'après consignation du résultat dans le registre d'exécution.
- La spec (1.1) est volontairement la première tâche : les identifiants normatifs `[AIRS-*-n]`
  sont référencés par la suite de conformité (4.2) et par l'article (11.2).
- Une seule tâche touche `src/tenxyte` (2.1) ; `tenxyte.core`/`tenxyte.ports` ne sont jamais
  modifiés (Requirement 9.2).
- Les property tests suivent la convention du projet : Hypothesis ≥ 100 exemples, docstring au
  format **Feature: z_aud_2, Property N: <texte>** ; tout le réseau est mocké (`respx`) hors
  suite de conformité (HTTP réel contre instance éphémère).
- L'acceptation des soumissions communautaires par des tiers (11.3) est explicitement hors
  Definition of Done — seule l'exécution des soumissions est exigée.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "2.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "2.5", "4.1"] },
    { "id": 3, "tasks": ["4.2", "4.3", "5.1", "6.1"] },
    { "id": 4, "tasks": ["4.4", "5.2", "5.3", "6.2", "6.3", "6.4", "7.1"] },
    { "id": 5, "tasks": ["5.4", "5.5", "5.6", "5.7", "5.8", "5.9", "7.2"] },
    { "id": 6, "tasks": ["9.1", "9.2", "10.1"] },
    { "id": 7, "tasks": ["10.2", "11.1", "11.2"] },
    { "id": 8, "tasks": ["11.3", "11.4", "12.1", "12.2"] }
  ]
}
```
