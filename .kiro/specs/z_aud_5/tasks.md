# Implementation Plan: Phase 5 « Go-to-Market » (z_aud_5)

## Overview

L'implémentation suit le jalonnement du design : **positionnement** (tout en dépend), puis
**fondations de preuve et de mesure** (Claims_Registry + lint, télémétrie, gouvernance —
installées AVANT toute exposition publique), puis **surfaces publiques** (README, site,
Demo_Instance), puis **launch** (après dry-run obligatoire), enfin **business** (design
partners → études de cas → pricing). Les livrables hors-repo (site, Discord, campagne, CRM)
sont cochés ici sur preuve (lien + ligne au registre de `manual_tests.md`), comme les tâches
monorepo JS de z_aud_3. Les vérifications non automatisables portent le marqueur `[MT-x]`.

## Tasks

- [ ] 1. Positionnement (socle de toute la phase)
  - [ ] 1.1 Rédiger `marketing/positioning.md` `[MT-1]`
    - ICP primaire (équipes Python déployant des agents IA en production) + ≤ 2 secondaires
      (SaaS B2B self-hosted, secteurs régulés §3.3), avec canaux/douleurs/objections ;
      Message_House (toit = Positioning_Statement §5.5 recentré AIRS, 3 piliers adossés à
      §6.2/§5.4/§3.2+3.5) ; matrice objections/réponses (allauth, Keycloak/Authentik,
      Clerk/Auth0, « petit projet ») avec concessions explicites
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ] 1.2 Définir la règle de revue AIRS_First
    - Checklist de revue d'asset public (toit du message, Positioning_Statement verbatim,
      chiffres depuis le Claims_Registry) intégrée au template de PR des fichiers publics
    - **Property 9 (processus)** · _Requirements: 1.2, 4.5_

- [ ] 2. Fondations de preuve : Claims_Registry et lint
  - [ ] 2.1 Créer `marketing/claims.yml` et peupler les claims existants
    - Chaque chiffre public actuel ou prévu (tests, couverture, endpoints, « 2 minutes »,
      benchmarks HITL z_aud_2, chiffres d'audit z_aud_1) : valeur, pointeur de preuve
      résolvable, date de vérification
    - _Requirements: 8.1_

  - [ ] 2.2 Implémenter `scripts/check_claims.py` + job CI
    - Échec si pointeur non résolvable, chiffre public hors registre (motifs sur README +
      pages marketing trackées), ou preuve recalculable dérivée ; warning J-30 puis échec à
      échéance pour les Dated_Comparisons ; cas de test du lint (un claim faux introduit ⇒
      échec)
    - **Property 7: Traçabilité des claims** · **Property 8: Datation des comparatifs**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4**

- [ ] 3. Fondations de mesure : télémétrie opt-in
  - [ ] 3.1 Implémenter le Telemetry_Module à schéma fermé
    - `tenxyte/telemetry.py` : enum d'évènements (`setup_completed`, heartbeat de version,
      flags de features actives en booléens) et champs typés énumérés, Install_ID aléatoire
      stable, aucune API à valeur libre ; setting `TELEMETRY_ENABLED` (défaut False, préfixe
      auto de `_get()`) ; émission fire-and-forget hors chemin de requête (thread détaché,
      timeout ≤ 2 s, backoff plafonné, échec silencieux)
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ] 3.2 Write property tests for telemetry privacy and inertness
    - **Property 1: Inertie par défaut** (séquences d'usage générées ⇒ zéro réseau/thread/fichier)
    - **Property 2: Kill switch total** (désactivé ≡ jamais activé)
    - **Property 3: Confidentialité structurelle** (aucune séquence ne produit de payload
      hors schéma ; Install_ID non dérivé)
    - **Property 4: Innocuité d'émission** (endpoint down/lent/500 ⇒ aucun impact)
    - **Property 5: Isolement du chemin d'auth** (analyse d'imports)
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 9.2, 9.3**

  - [ ] 3.3 Publier la Transparency_Doc générée et monter le North_Star_Dashboard `[MT-6]`
    - Doc EN/FR générée depuis le Closed_Schema (payload exact, déclencheurs, rétention,
      opt-out) + test de fraîcheur CI ; dashboard agrégeant PyPI/GitHub/Discord/télémétrie
      selon readme.md §Métriques ; rituel de revue mensuel documenté
    - **Property 6: Cohérence doc/schéma** · _Requirements: 5.5, 5.6_

- [ ] 4. Fondations communautaires : gouvernance
  - [ ] 4.1 Publier les Governance_Docs
    - GOVERNANCE.md (rôles, décision, Maintainer_Path à critères objectifs),
      CODE_OF_CONDUCT.md (Contributor Covenant), CONTRIBUTING.md réécrit (setup Windows +
      Linux, processus `.kiro/specs`, conventions PBT et mots de passe concaténés)
    - _Requirements: 3.1_

  - [ ] 4.2 Rédiger et étiqueter 20+ Good_First_Issues
    - Chacune autoportante (contexte, fichiers, critère d'acceptation, estimation < 4 h),
      mentorat déclaré ; vivier issu des chantiers réels (docs, providers SMS F10, DX §4.3)
    - _Requirements: 3.3_

  - [ ] 4.3 Ouvrir le Discord structuré et la roadmap publique `[MT-5]`
    - Canaux help / AIRS-agents / contrib / annonces ; roadmap GitHub Projects alimentée
      depuis `.kiro/specs` ; SLA de réponse public tenable ; liens depuis README et site
    - _Requirements: 3.2, 3.4_

- [ ] 5. Checkpoint - Ensure all tests pass
  - Fondations vertes (propriétés télémétrie, Claims_Lint, snapshot OpenAPI/réseau intacts),
    gouvernance publiée ; ask the user if questions arise.

- [ ] 6. Surfaces publiques
  - [ ] 6.1 Repositionner le README `[MT-3]`
    - AIRS_First, Positioning_Statement verbatim, Dated_Comparisons remplaçant le tableau à
      3 concurrents, chiffres exclusivement via Claims_Registry, liens communauté ; passage
      de la checklist 1.2
    - _Requirements: 1.4, 2.3_

  - [ ] 6.2 Livrer le site produit `[MT-2]`
    - Home AIRS-first, pages solutions par ICP, page Security (rapport z_aud_1 +
      SECURITY.md), Engineering_Practices_Page alimentée par le Claims_Registry,
      comparatifs datés avec concessions — hors-repo, sources trackées pour le lint
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ] 6.3 Déployer la Demo_Instance `[MT-7]`
    - Assemblage backend démo z_aud_3 + UI z_aud_3 + dashboard HITL z_aud_4 ; seed
      déterministe, reset périodique, rate-limiting agressif, zéro donnée réelle ni email
      sortant réel ; scénario scripté AIRS (action agent → 202 → approbation dashboard)
    - _Requirements: 6.1, 6.2_

  - [ ] 6.4 Re-vérifier les temps annoncés et les templates `[MT-7]`
    - Chronométrage « time to first login » Django ET FastAPI, consignation au
      Claims_Registry ; chaque template de départ référencé exécuté tel que documenté
    - _Requirements: 6.3, 6.4_

- [ ] 7. Lancement et contenu
  - [ ] 7.1 Rédiger le Launch_Plan et produire les assets
    - Séquencement J-14 → J+7, vidéo 90 s sur la Demo_Instance, post technique, FAQ
      objections (depuis la matrice 1.1), plan de présence 48 h avec répondeurs nommés,
      template de debrief J+7
    - _Requirements: 4.1_

  - [ ] 7.2 Publier les 3 Pillar_Content
    - « How to give an AI agent a credit card limit » (benchmarks z_aud_2), « Anatomy of a
      HITL approval », « Self-hosted auth without running an identity server » — revue
      technique + checklist AIRS_First + claims via registre
    - _Requirements: 4.3, 4.5_

  - [ ] 7.3 Dérouler le dry-run puis exécuter le launch `[MT-4]`
    - Dry-run avec 3 relecteurs externes hostiles (MT-4) ; corrections ; exécution ;
      debrief J+7 chiffré contre le North_Star_Dashboard, consigné
    - _Requirements: 4.2_

  - [ ] 7.4 Établir le calendrier éditorial 6 mois
    - Canaux ordonnés selon D2 (agents d'abord), propriétaires nommés, ≥ 2 propositions de
      talks (PyCon / conf IA)
    - _Requirements: 4.4_

- [ ] 8. Checkpoint - Ensure all tests pass
  - Surfaces en ligne et lintées, launch exécuté et débriefé, suite existante intacte ;
    ask the user if questions arise.

- [ ] 9. Business : design partners → études de cas → pricing
  - [ ] 9.1 Lancer le programme Design_Partner `[MT-8]`
    - Charte publique (offre managée z_aud_4 gratuite vs feedback mensuel structuré +
      Case_Study nominative), sourcing dans les communautés agents, objectif 5–10 équipes ;
      CRM léger (statuts, thèmes de feedback, intention)
    - _Requirements: 7.1, 7.4_

  - [ ] 9.2 Publier 2 Case_Studies
    - Validées par les partners, résultats chiffrés via Claims_Registry
    - _Requirements: 7.3_

  - [ ] 9.3 Publier le pricing `[MT-8]`
    - Dérivé d'`editions.md` (z_aud_4) et des données partners ; publication UNIQUEMENT
      après ≥ 5 partners actifs (D7) ; cohérence Open_Core_Boundary vérifiée
    - _Requirements: 7.2_

- [ ] 10. Vérifications finales et tâches récurrentes
  - [ ] 10.1 Write final non-regression checks
    - **Property 10: Invisibilité totale** — suite existante verte sans modification,
      schéma OpenAPI inchangé aux défauts, zéro connexion sortante attribuable à la phase
      pendant la suite, aucune API/modèle/migration existants modifiés
    - **Validates: Requirements 9.1, 9.2, 9.4**

  - [ ] 10.2 Installer les rituels récurrents
    - Revue semestrielle des Dated_Comparisons (échéances dans le lint), rituel mensuel
      North_Star_Dashboard + SLA communauté + CRM partners ; nomination effective ou
      pipeline documenté du 2ᵉ mainteneur (critère F6)
    - _Requirements: 3.4, 3.5, 8.4, 5.6_

  - [ ] 10.3 Dérouler la campagne de tests manuels
    - Exécuter `manual_tests.md` MT-1 à MT-8 et compléter le registre
    - _Requirements: transverses_

- [ ] 11. Checkpoint final - Ensure all tests pass
  - Toutes gates vertes (propriétés 1–8 automatisées, 9–10 revues), registre manuel complet,
    debrief launch classé, ≥ 5 partners actifs ou dérogation mainteneur motivée ;
    ask the user before declaring the GTM phase complete.

## Notes

- Les tâches `[MT-x]` ont une contrepartie obligatoire dans `manual_tests.md`.
- Le Claims_Lint (2.2) est installé AVANT toute surface publique : aucun chiffre ne part en
  ligne sans preuve — c'est l'équivalent GTM du snapshot OpenAPI de z_aud_4.
- Les tâches 4.3, 6.2, 6.3, 7.3, 9.x s'exécutent partiellement ou totalement hors-repo ;
  elles sont cochées sur preuve (lien + ligne de registre).
- Property tests : Hypothesis ≥ 100 exemples, docstring **Feature: z_aud_5, Property N: <texte>**.
- Le launch (7.3) dépend de la disponibilité réelle des livrables z_aud_1 (1.0 + audit) et
  z_aud_2 (spec AIRS) — ne jamais lancer sur des promesses (D3/D4 s'appliquent au launch
  lui-même).

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "2.1", "3.1", "4.1"] },
    { "id": 2, "tasks": ["2.2", "3.2", "4.2"] },
    { "id": 3, "tasks": ["3.3", "4.3", "6.1"] },
    { "id": 4, "tasks": ["6.2", "6.3"] },
    { "id": 5, "tasks": ["6.4", "7.1", "7.2"] },
    { "id": 6, "tasks": ["7.3", "9.1"] },
    { "id": 7, "tasks": ["7.4", "9.2"] },
    { "id": 8, "tasks": ["9.3", "10.1", "10.2"] },
    { "id": 9, "tasks": ["10.3"] }
  ]
}
```
