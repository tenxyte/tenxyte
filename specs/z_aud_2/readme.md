# Spec z_aud_2 — Phase 2 « Le pari IA » (AIRS ouvert + écosystème agents)

> **Source :** `AUDIT.md` (racine du projet), §6 « Le pari game-changer » et §9 Phase 2 (T+2 → T+8 mois)
> **Statut :** 📋 Spécifié — prêt pour implémentation
> **Prérequis conseillé :** Phase 1 (`z_aud_1`) au moins entamée — la spec AIRS référence la 1.0
> **Peut s'exécuter en parallèle de la Phase 1** (aucune dépendance de code bloquante)

---

## Contexte

L'audit stratégique (`AUDIT.md`) a établi que le seul front sur lequel Tenxyte peut devenir un
game-changer est **l'identité et la gouvernance des agents IA**. L'implémentation AIRS existe et
est unique sur le marché (délégation scopée, double RBAC, HITL, budget LLM, circuit breaker, dead
man's switch, trace forensique) — mais elle est **invisible** : pas de spécification citable, pas
de connecteurs vers les écosystèmes où vivent les builders d'agents (LangChain, MCP, CrewAI), pas
de preuves de performance publiables.

Cette phase convertit l'avance technique en **standard de facto**, selon les trois conditions de
l'audit (§6.3) :

| Condition (AUDIT.md §6.3) | Adressée par |
|---|---|
| 1. Nommer et standardiser — publier AIRS comme spécification ouverte | Requirement 1 (spec AIRS/1.0), Requirement 2 (endpoint de découverte), Requirement 3 (suite de conformité) |
| 2. Intégrations agents-first — LangChain, MCP, CrewAI | Requirements 4, 5, 6 (`tenxyte-langchain`, `tenxyte-mcp-server`, exemple CrewAI) |
| 3. Vitesse — capter la communauté dans la fenêtre 12–24 mois | Requirement 7 (benchmarks publiables), Requirement 8 (distribution communautaire, tracée dans `manual_tests.md`) |

## Périmètre de la phase

1. **Spécification AIRS/1.0** — document normatif indépendant du code (`spec/airs/AIRS-1.0.md`),
   vocabulaire RFC 2119, licence CC BY 4.0, protocole filaire complet (headers, endpoints,
   machine à états, codes d'erreur), niveaux de conformité. Tenxyte devient *l'implémentation de
   référence*, pas *la définition*.
2. **Endpoint de découverte AIRS** — `GET /ai/.well-known/airs/` (code additif) : version de
   spec, niveaux de conformité actifs, carte des endpoints — l'introspection dont les connecteurs
   ont besoin.
3. **Suite de conformité** — tests HTTP boîte noire exécutables contre **n'importe quelle**
   implémentation (paramétrés par URL) ; Tenxyte doit la passer intégralement.
4. **`tenxyte-langchain`** — package PyPI séparé (monorepo `integrations/langchain/`) : gestion du
   cycle de vie AgentToken, callback de budget LLM, gestion HITL compatible interrupts LangGraph,
   propagation de trace.
5. **`tenxyte-mcp-server`** — package PyPI séparé (monorepo `integrations/mcp-server/`) : serveur
   MCP exposant les primitives AIRS comme tools/resources (statut, heartbeat, budget, actions en
   attente), transport stdio.
6. **Exemple CrewAI** — `examples/crewai/` exécutable et documenté (crew complet avec HITL et
   suspension budget démontrées).
7. **Benchmarks reproductibles** — `benchmarks/airs/` : surcoût de la validation AgentBearer +
   double RBAC vs JWT nu ; latence du round-trip HITL. Scripts + gabarit de résultats publiables.
8. **Distribution communautaire** — article technique de lancement, soumissions aux annuaires
   (LangChain integrations, awesome-mcp-servers) — actions process tracées dans `manual_tests.md`.

## Hors périmètre (phases ultérieures ou backlog)

- Standardisation externe formelle (IETF/OpenID) — la spec ouverte en est le préalable.
- Connecteurs au-delà de LangChain/MCP/CrewAI (AutoGen, Semantic Kernel, Haystack) → backlog,
  la suite de conformité les rendra triviaux à valider.
- Dashboard HITL managé (offre commerciale) → Phase 4.
- Toute modification du comportement AIRS existant — cette phase **expose et documente**,
  elle ne réécrit pas.

## Fichiers de cette spec

| Fichier | Rôle |
|---|---|
| `readme.md` | Ce document — vue d'ensemble, contexte, statut, journal de décisions |
| `base.md` | Plan initial issu de l'audit (notes brutes de cadrage) |
| `requirements.md` | Exigences formelles EARS avec glossaire et critères d'acceptation |
| `design.md` | Conception : architecture, contrats des connecteurs, propriétés de correction, stratégie de test |
| `tasks.md` | Plan d'implémentation traçable (tâches ↔ requirements, graphe de dépendances) |
| `manual_tests.md` | Procédures de tests manuels (MCP/Claude Desktop, LangChain E2E, publication PyPI, soumissions communautaires) |
| `.config.kiro` | Métadonnées de la spec |

## Décisions structurantes (journal)

| # | Décision | Justification |
|---|---|---|
| D1 | Les connecteurs vivent dans le monorepo (`integrations/langchain/`, `integrations/mcp-server/`) mais sont des **packages PyPI indépendants** avec leur propre versionnage | Un seul repo à maintenir en Phase 2 ; extraction en repos dédiés possible plus tard sans casser PyPI |
| D2 | Les connecteurs sont des **clients HTTP purs** : interdiction d'importer `tenxyte` | Dogfooding de la spec — si le connecteur a besoin d'un import interne, la spec est incomplète. Testable (Property 11) |
| D3 | Le serveur MCP ne détient **jamais** de JWT utilisateur — uniquement un AgentToken déjà émis | Le MCP tourne côté agent : lui confier un JWT humain serait une amplification de privilèges contraire au modèle AIRS |
| D4 | La spec AIRS est publiée sous **CC BY 4.0** dans `spec/airs/` ; le code reste MIT | Une spec doit être librement réimplémentable, y compris par des concurrents — c'est le but |
| D5 | Le HITL côté LangChain est modélisé en **exception typée + reprise** (`TenxyteHITLPending` portant le `confirmation_token`), compatible avec le pattern `interrupt()` de LangGraph | Les deux modes d'usage (try/except simple, graphe interrompu/resumé) partagent la même primitive |
| D6 | L'endpoint de découverte suit le style `.well-known` (`GET {API_PREFIX}/ai/.well-known/airs/`), non authentifié mais gated par `AIRS_ENABLED` | Convention d'introspection standard ; ne révèle que des capacités, jamais de données |
| D7 | Suite de conformité en pytest paramétré par `--airs-base-url` + credentials, livrée dans `spec/airs/conformance/` | Réutilisable par tout implémenteur tiers ; sert aussi de test d'intégration interne |

## Definition of Done de la phase

- [ ] `spec/airs/AIRS-1.0.md` publié (CC BY 4.0), relu, sans référence normative à Django/Tenxyte.
- [ ] `GET /ai/.well-known/airs/` livré, testé, documenté (EN/FR), 100 % additif.
- [ ] Suite de conformité verte contre Tenxyte ; contrôle négatif (mock non conforme) rouge.
- [ ] `tenxyte-langchain` et `tenxyte-mcp-server` publiés sur TestPyPI puis PyPI, installables,
      avec leurs suites de tests vertes (backend Tenxyte mocké).
- [ ] Exemple CrewAI exécutable de bout en bout (voir `manual_tests.md` MT-4).
- [ ] Benchmarks exécutés au moins une fois, résultats consignés dans le gabarit.
- [ ] Tous les tests Tenxyte existants passent sans modification (non-régression).
- [ ] Article de lancement publié + soumissions annuaires effectuées (registre MT-7).

## Suivi

Consulter `tasks.md` pour l'avancement tâche par tâche et `manual_tests.md` pour le registre
d'exécution des validations manuelles (E2E MCP/Claude Desktop, publication PyPI, communauté).
