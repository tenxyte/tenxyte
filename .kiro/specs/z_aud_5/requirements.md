# Requirements Document — Phase 5 « Go-to-Market » (z_aud_5)

## Introduction

Cette phase convertit l'actif technique produit par les phases 1–4 en **produit distribué,
mesuré et monétisé** : positionnement AIRS-first, présence produit, communauté gouvernée,
lancement orchestré, télémétrie opt-in respectueuse, instance démo, pipeline commercial et
garde-fou d'intégrité des claims. Elle est majoritairement hors-code ; ses livrables in-repo
(télémétrie, lint des claims, docs de gouvernance, README) sont additifs et sans effet sur le
comportement du package.

## Glossaire

| Terme | Définition |
|---|---|
| **ICP** | Ideal Customer Profile — profil d'équipe cible d'un message et d'un canal |
| **Message_House** | Hiérarchie de messages : toit (positionnement), piliers (preuves), fondations (features) |
| **Positioning_Statement** | La phrase §5.5 de l'audit recentrée AIRS-first, utilisée partout à l'identique |
| **AIRS_First** | Règle D1 : tout support public mène par la gouvernance d'agents IA ; l'auth humaine est preuve de support |
| **Engineering_Practices_Page** | Page publique rendant visibles les métriques de rigueur (§3.5), alimentée par la CI |
| **Dated_Comparison** | Comparatif concurrentiel public portant sa date d'évaluation et ses concessions explicites |
| **Claim** | Toute affirmation quantifiée ou vérifiable publiée (README, site, posts, pricing) |
| **Claims_Registry** | `marketing/claims.yml` — source unique de tout Claim, avec pointeur de preuve |
| **Claims_Lint** | `scripts/check_claims.py` — job CI échouant si un Claim n'a pas de preuve résolvable |
| **Governance_Docs** | GOVERNANCE.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md |
| **Good_First_Issue** | Issue étiquetée, autoportante (contexte, fichiers, critère d'acceptation), réalisable < 4 h par un externe |
| **Maintainer_Path** | Critères objectifs et publics de progression contributeur → mainteneur (attaque F6) |
| **Launch_Plan** | Artefact décrivant séquencement, assets, FAQ objections et plan de présence du lancement 1.0+AIRS |
| **Pillar_Content** | Les 3 contenus techniques de référence (dont « How to give an AI agent a credit card limit », §9) |
| **Telemetry_Module** | `tenxyte/telemetry.py` — collecte opt-in d'évènements anonymes à schéma fermé |
| **Closed_Schema** | Énumération exhaustive des évènements et champs télémétrie ; aucun champ à valeur libre |
| **Install_ID** | Identifiant d'installation aléatoire, non dérivé d'aucune donnée du déploiement |
| **Transparency_Doc** | Page publique décrivant payload exact, déclencheurs, rétention et opt-out de la télémétrie |
| **North_Star_Dashboard** | Tableau de bord des métriques de pilotage (readme.md §Métriques) |
| **Demo_Instance** | Instance publique seedée (backend z_aud_3 + UI + dashboard HITL z_aud_4), reset périodique |
| **Design_Partner** | Équipe utilisant l'offre managée gratuitement contre feedback structuré et étude de cas |
| **Case_Study** | Étude de cas nominative publiée, validée par le partner |

## Requirements

### Requirement 1 — Positionnement et message

**User Story:** En tant que mainteneur, je veux un positionnement unique et hiérarchisé, afin
que Tenxyte soit comparé sur le terrain où il n'a pas de concurrent (AIRS) et non sur celui où
il est challenger.

#### Acceptance Criteria

1. WHEN `marketing/positioning.md` is published, THEN it SHALL define one primary ICP (Python
   teams shipping AI agents to production) and at most two secondary ICPs, each with channels,
   pains, and objections, grounded in AUDIT.md §3.3, §5, §6.
2. WHEN the Message_House is defined, THEN its roof SHALL be the Positioning_Statement
   (AIRS_First), its pillars SHALL each map to audit-documented proof (AIRS §6.2 table,
   sovereignty+cost §5.4, breadth+rigor §3.2/§3.5), and no public asset SHALL invert the
   hierarchy (auth-first messaging).
3. WHEN the objections matrix is written, THEN it SHALL cover at minimum "why not allauth",
   "why not Keycloak/Authentik", "why not Clerk/Auth0", "why trust a small project", with
   answers derived from §5.2–§5.4 including conceded points.
4. WHEN the repository README is repositioned, THEN it SHALL lead AIRS_First, use the
   Positioning_Statement verbatim, and replace the current 3-competitor table with
   Dated_Comparisons.

### Requirement 2 — Présence produit et preuve visible

**User Story:** En tant qu'acheteur technique, je veux vérifier en cinq minutes ce que
Tenxyte est, prouve et concède, afin de décider d'un essai sans creuser le code.

#### Acceptance Criteria

1. WHEN the product site is live, THEN it SHALL include: AIRS-first home, per-ICP solution
   pages, a Security page (external audit report z_aud_1, SECURITY.md path), and the
   Engineering_Practices_Page.
2. WHEN the Engineering_Practices_Page is rendered, THEN its figures (tests count, coverage
   gate, endpoints, property tests) SHALL be sourced from the Claims_Registry, not hand-written.
3. WHEN a Dated_Comparison is published, THEN it SHALL carry its evaluation date, its
   methodology reference, and explicit conceded points (social providers vs allauth, UI
   time-to-market vs Clerk, ecosystem maturity), per D4.
4. WHEN documentation quickstarts are referenced from the site, THEN the advertised
   time-to-first-login SHALL match the last chronometered verification (z_aud_1/z_aud_3 MTs or
   MT-7 of this phase).

### Requirement 3 — Communauté et gouvernance

**User Story:** En tant que contributeur potentiel, je veux comprendre comment participer,
qui décide et comment on devient mainteneur, afin d'investir mon temps en confiance.

#### Acceptance Criteria

1. WHEN Governance_Docs are published, THEN GOVERNANCE.md SHALL define roles, decision
   process, and the Maintainer_Path with objective criteria; CODE_OF_CONDUCT.md SHALL adopt a
   recognized covenant; CONTRIBUTING.md SHALL cover dev setup (Windows and Linux), the
   `.kiro/specs` process, and property-based testing conventions.
2. WHEN the community launch happens, THEN a structured Discord (help, AIRS/agents, contrib,
   announcements) and a public roadmap (fed from `.kiro/specs`) SHALL be live and linked from
   README and site.
3. WHEN Good_First_Issues are published, THEN at least 20 SHALL exist, each self-contained
   (context, files, acceptance criteria), and the contributor journey SHALL have been
   validated end-to-end by at least one external tester (MT-5).
4. WHEN a public response SLA is stated, THEN it SHALL be sustainable by the actual team and
   measured monthly.
5. WHEN the phase completes, THEN a second maintainer SHALL be named or a candidate SHALL be
   in the documented Maintainer_Path with delegated rights in progress (F6).

### Requirement 4 — Programme de lancement et contenu

**User Story:** En tant que mainteneur, je veux que la sortie 1.0+AIRS atteigne les builders
d'agents avec une exécution répétée, afin de convertir la fenêtre de marché (§6.3) en adoption.

#### Acceptance Criteria

1. WHEN the Launch_Plan is written, THEN it SHALL define sequencing (teaser → Show HN →
   agent communities → recap), prepared assets (90s demo video, technical post, objections
   FAQ), a 48h presence plan with named responders, and a J+7 quantified debrief template.
2. WHEN the launch is executed, THEN it SHALL have been preceded by a dry-run (MT-4) and the
   J+7 debrief SHALL be filed with metrics against the North_Star_Dashboard.
3. WHEN Pillar_Content is published, THEN the three pieces SHALL exist, technically reviewed,
   including "How to give an AI agent a credit card limit" backed by z_aud_2 benchmarks, and
   SHALL target the channels of the primary ICP (D2), not Django communities.
4. WHEN the editorial calendar is defined, THEN it SHALL cover 6 months with owners and
   channels, and include at least two conference talk proposals.
5. WHEN any content includes a Claim, THEN the Claim SHALL come from the Claims_Registry.

### Requirement 5 — Télémétrie opt-in respectueuse

**User Story:** En tant que mainteneur, je veux savoir ce qui est utilisé sans jamais trahir
la promesse de souveraineté, afin de piloter le produit avec des données.

#### Acceptance Criteria

1. WHEN Tenxyte runs with default settings, THEN the Telemetry_Module SHALL be fully inert:
   no network call, no file, no thread (`TELEMETRY_ENABLED` default False).
2. WHEN telemetry is enabled, THEN only Closed_Schema events SHALL be emittable: enumerated
   event names and enumerated fields (versions, adapter, active feature flags as booleans,
   Install_ID); free-form values SHALL be structurally impossible.
3. WHEN any event is emitted, THEN it SHALL carry no PII, no hostname, no IP-derived data, no
   setting values; the Install_ID SHALL be random and stable per install.
4. WHEN the collection endpoint is unreachable or slow, THEN authentication behavior SHALL be
   unaffected: emission is fire-and-forget outside any auth request path, failures silent,
   and the kill switch (`TELEMETRY_ENABLED=False`) SHALL restore full inertness.
5. WHEN the Transparency_Doc is published, THEN it SHALL show the exact payload, triggers,
   retention, and opt-out, and the documented payload SHALL match the Closed_Schema
   (single source).
6. WHEN the North_Star_Dashboard is set up, THEN it SHALL aggregate PyPI, GitHub, Discord and
   telemetry metrics per readme.md §Métriques with a monthly review ritual.

### Requirement 6 — Produit démontrable

**User Story:** En tant que prospect, je veux toucher le produit sans rien installer, afin de
me convaincre en minutes.

#### Acceptance Criteria

1. WHEN the Demo_Instance is live, THEN it SHALL expose the demo backend (z_aud_3), the UI
   components and the HITL dashboard (z_aud_4) with a deterministic seed, periodic reset, and
   rate limiting; no real user data SHALL ever be present.
2. WHEN the demo showcases AIRS, THEN a scripted scenario SHALL let a visitor trigger an
   agent action, see the 202 HITL hold, and approve it in the dashboard.
3. WHEN "time to first login" is advertised, THEN it SHALL have been re-verified by
   chronometered run on both Django and FastAPI quickstarts (MT-7) and recorded in the
   Claims_Registry.
4. WHEN starter templates are referenced from the site, THEN each SHALL be runnable as
   documented (verified in MT-7).

### Requirement 7 — GTM commercial et design partners

**User Story:** En tant que mainteneur, je veux valider l'offre commerciale avec de vraies
équipes avant tout pricing public, afin de vendre un produit prouvé et non une hypothèse.

#### Acceptance Criteria

1. WHEN the Design_Partner program launches, THEN a public charter SHALL define the exchange
   (free managed offer vs structured feedback + named Case_Study), targeting 5–10 teams from
   agent-builder communities.
2. WHEN public pricing is published, THEN it SHALL derive from `editions.md` (z_aud_4), SHALL
   occur only after at least 5 active Design_Partners (D7), and SHALL NOT contradict the
   Open_Core_Boundary.
3. WHEN Case_Studies are published, THEN at least two SHALL be live, partner-validated, with
   quantified outcomes sourced through the Claims_Registry.
4. WHEN the pipeline is tracked, THEN a lightweight CRM SHALL record partner status, feedback
   themes, and conversion intent, reviewed monthly with the North_Star_Dashboard.

### Requirement 8 — Intégrité des claims

**User Story:** En tant que mainteneur d'un produit de sécurité, je veux qu'aucune
affirmation publique ne puisse dériver de la réalité du code, afin qu'un démenti ne détruise
pas la confiance (le risque « un CVE mal géré » de l'audit vaut aussi pour un claim faux).

#### Acceptance Criteria

1. WHEN the Claims_Registry exists, THEN every quantified public Claim (tests count,
   time-to-login, benchmark figures, endpoints, coverage) SHALL have an entry with a
   resolvable proof pointer (test path, script output, MT registry line, audit report).
2. WHEN Claims_Lint runs in CI, THEN a Claim whose proof pointer does not resolve, or a
   tracked public file (README, marketing docs pages) containing a quantified claim absent
   from the registry, SHALL fail the build.
3. WHEN a proof becomes stale (e.g., tests count changed), THEN the lint SHALL flag the
   drift so the public figure is updated, not the reverse.
4. WHEN comparisons are published, THEN each SHALL carry its evaluation date
   (Dated_Comparison) and be re-reviewed at least every 6 months (tracked as a recurring
   task).

### Requirement 9 — Non-régression et innocuité

**User Story:** En tant qu'utilisateur existant, je veux que toute cette phase soit invisible
dans mon déploiement, afin que le GTM n'introduise aucun risque produit.

#### Acceptance Criteria

1. WHEN the full existing test suite runs after this phase, THEN it SHALL pass without any
   modification to existing tests.
2. WHEN all new settings are at defaults, THEN the package SHALL make zero network calls
   attributable to this phase and the OpenAPI schema SHALL be unchanged.
3. WHEN the Telemetry_Module code paths are inspected, THEN none SHALL be reachable from any
   authentication, token, or AIRS request handler.
4. WHEN in-repo additions land (marketing/, Governance_Docs, telemetry, scripts), THEN no
   existing public API, model, or migration SHALL be modified.
