# z_aud_5 — Phase 5 « Go-to-Market » : marketing, business et produit

> Source : cette phase n'est **pas** dans la feuille de route `AUDIT.md` §9 — elle est dérivée
> directement du **verdict §10** : *« Ce qui manque est entièrement dans la distribution […]
> le pari se gagne dans les 18 prochains mois, et il se gagne en dehors du dépôt Git. »*
> Elle opérationnalise les écarts hors-code : F5 (communauté quasi nulle, score adoption 3/10),
> F6 (bus factor ≈ 1), §4.3 (télémétrie d'adoption inexistante, README comparatif trop tendre),
> §3.5 (rigueur d'ingénierie invisible), §6.3 (conditions de conversion de l'avance AIRS).
> Prérequis : z_aud_1 (crédibilité 1.0), z_aud_2 (spec AIRS + connecteurs), z_aud_3
> (multi-framework + UI), z_aud_4 (enterprise + frontière open-core).

## Le problème que cette phase résout

Les phases 1 à 4 rendent le produit **achetable**. Aucune ne le rend **connu, cru et acheté** :

1. **Personne ne sait que Tenxyte existe.** Adoption & communauté : 3/10 — la pire note de
   l'audit, qualifiée de « chantier n°1 ». Un package d'auth vit de la confiance communautaire
   (revues par des pairs) ; sans elle, même un audit externe ne convertit pas.
2. **Le message est dispersé.** Tenxyte chevauche 3 segments (packages, IAM, SaaS — §5.1) :
   c'est sa force et « son risque (dispersion du message) ». Sans hiérarchie de messages, il
   sera comparé à allauth et perdra ; comparé sur AIRS, il n'a pas de concurrent.
3. **La fenêtre se referme.** §6.3 : 12–24 mois avant qu'Auth0/Okta/Clerk livrent HITL+budget.
   La vitesse de captation de la communauté *builders d'agents* est LA variable du scénario
   « game-changer de niche » (~50 %) vs « excellent outil, adoption modeste » (~35 %).
4. **On pilote à l'aveugle.** Aucune télémétrie d'adoption : « impossible de savoir qui
   utilise quoi » (§4.3). Aucune métrique = aucune boucle d'apprentissage GTM.
5. **Le projet n'est pas encore un produit.** Pas de site, pas de démo, pas de programme
   design partners, pas de pipeline pour l'offre commerciale définie en z_aud_4.

## Ce que la phase livre

| # | Livrable | Nature | Localisation |
|---|----------|--------|--------------|
| 1 | **Positionnement** : ICP, message house, phrase de positionnement (§5.5 : « seul produit cochant les 4 cases »), narratif AIRS comme vocabulaire du problème | Doc stratégique | `marketing/` (repo) |
| 2 | **Présence produit** : site, page « Engineering Practices » (rendre visibles les 2 605 tests/PBT/specs), comparatifs honnêtes et datés, README repositionné | Site + docs | hors-repo + repo |
| 3 | **Communauté & gouvernance** : Discord, roadmap publique, good-first-issues, CONTRIBUTING/GOVERNANCE/CODE_OF_CONDUCT, onboarding d'un 2ᵉ mainteneur | Process + docs repo | repo + hors-repo |
| 4 | **Programme de lancement** : launch 1.0+AIRS (HN, r/MachineLearning, communautés agents), 3 contenus piliers (dont « How to give an AI agent a credit card limit » — §9 Phase 2), calendrier éditorial 6 mois | Campagne | hors-repo |
| 5 | **Télémétrie opt-in** : module anonyme, désactivé par défaut, zéro PII, kill switch, doc transparente ; north-star metrics et funnel | Code + doc | repo |
| 6 | **Produit démontrable** : instance démo publique seedée, « deploy in 2 minutes » vérifié, templates de départ | Code + infra | repo + hors-repo |
| 7 | **GTM commercial** : page pricing (adossée à `editions.md` z_aud_4), programme design partners (5–10 équipes), 2 études de cas publiées | Business | hors-repo |
| 8 | **Intégrité des claims** : traçabilité claim marketing ↔ preuve dans le code, garde-fou anti-vaporware outillé | Code (lint CI) | repo |

## Décisions structurantes

- **D1 — Un seul message d'attaque : AIRS.** Le positionnement principal est « l'infrastructure
  d'identité open source pour agents IA » ; l'auth humaine complète est le *supporting proof*
  (« et il remplace aussi vos 6–8 packages d'auth »), jamais l'inverse. C'est la traduction
  directe du verdict : challenger sur l'auth classique, game-changer sur les agents.
- **D2 — Cibler les builders d'agents, pas les développeurs Django.** Canaux prioritaires :
  communautés LangChain/CrewAI/MCP, HN, r/MachineLearning (§6.3, §9 Phase 2). Les canaux
  Django sont secondaires (allauth y est le réflexe par défaut — on ne gagne pas là).
- **D3 — La preuve avant la promesse.** Chaque claim quantifié du site/README doit tracer vers
  une preuve versionnée (test, benchmark z_aud_2, rapport d'audit z_aud_1, MT au registre).
  Garde-fou outillé : lint CI des claims (`marketing/claims.yml` ↔ preuves). Un produit de
  sécurité ne survit pas à un claim démenti.
- **D4 — Comparatifs durs et datés.** Le README actuel « compare à 3 concurrents seulement »
  (§4.3) ; la vraie carte (§5) est plus dure et plus crédible. Les tableaux publics reprennent
  la méthodologie de l'audit, citent leurs dates, et concèdent explicitement les points perdus
  (providers sociaux vs allauth, UI vs Clerk, SSO vs Keycloak — avant z_aud_4).
- **D5 — Télémétrie : opt-in explicite ou rien.** Pour un package d'auth self-hosted vendu sur
  la souveraineté, une télémétrie silencieuse serait un suicide de confiance. Défaut
  `TELEMETRY_ENABLED=False`, activation explicite, payload anonyme documenté publiquement,
  zéro PII structurellement impossible (schéma fermé), kill switch, et **jamais dans le chemin
  d'une requête d'auth**.
- **D6 — La communauté se construit sur des rails.** Pas de « on ouvre un Discord et on
  verra » : gouvernance écrite (GOVERNANCE.md : rôles, décision, chemin mainteneur), 20
  good-first-issues calibrées et testées sur un cobaye externe, SLA de réponse public,
  objectif contractuel : un 2ᵉ mainteneur avec droits de merge sous 6 mois (attaque F6).
- **D7 — Design partners avant pricing public.** L'offre commerciale (z_aud_4) est validée par
  5–10 équipes design partners (gratuit contre feedback + étude de cas) AVANT toute grille
  tarifaire publique. Les études de cas sont le contenu de vente n°1 d'un produit sans marque.
- **D8 — Le lancement est un artefact, pas un événement.** Le launch 1.0+AIRS est spécifié
  (séquencement, assets, réponses préparées aux objections type HN, plan de présence 48 h)
  et répété à blanc (dry-run MT-4). Un launch HN raté ne se rejoue pas.

## Métriques de pilotage (north star et funnel)

| Niveau | Métrique | Source | Cible T+6 mois |
|---|---|---|---|
| North star | Installations actives opt-in (proxy : téléchargements PyPI hebdo dédupliqués) | PyPI stats + télémétrie | tendance ×4 vs T0 |
| Acquisition | Étoiles GitHub, trafic site, inscriptions Discord | GitHub/analytics/Discord | 2 000 ⭐ · 500 membres |
| Activation | Quickstarts réussis (télémétrie opt-in `setup_completed`) | télémétrie | mesurable (T0 = 0) |
| Adoption AIRS | Backends exposant `/ai/.well-known/airs/` connus, connecteurs installés (npm/PyPI) | télémétrie + registres | 50 déploiements identifiés |
| Communauté | Contributeurs externes mergés, good-first-issues résolues par des externes | GitHub | 15 contributeurs · 2ᵉ mainteneur |
| Business | Design partners actifs, études de cas publiées, pipeline offre managée | CRM léger | 5 partners · 2 études |

## Definition of Done de la phase

1. Positionnement, message house et ICP approuvés par le mainteneur (MT-1) ; README et site
   alignés dessus.
2. Site produit en ligne avec page Engineering Practices et comparatifs datés (MT-2, MT-3).
3. Launch 1.0+AIRS exécuté après dry-run ; bilan chiffré à J+7 consigné (MT-4).
4. Discord ouvert avec gouvernance publiée ; ≥ 20 good-first-issues ; parcours contributeur
   validé par un cobaye externe (MT-5) ; 2ᵉ mainteneur identifié ou nommé.
5. Télémétrie opt-in livrée : les 3 propriétés de confidentialité passent, revue de la doc
   de transparence (MT-6) ; dashboard des métriques de pilotage opérationnel.
6. Instance démo publique fonctionnelle ; « 2 minutes au premier login » re-vérifié
   chronomètre en main (MT-7).
7. Programme design partners lancé : ≥ 5 équipes signées, 2 études de cas en pipeline (MT-8).
8. Lint des claims vert en CI ; zéro claim public sans preuve tracée.
9. Zéro changement de comportement du package hors module télémétrie (flags off = invisible) ;
   suite existante verte sans modification.

## Fichiers de la spec

| Fichier | Rôle |
|---|---|
| `base.md` | État des lieux (ce que l'audit mesure hors-code) + plan brut des chantiers |
| `requirements.md` | 9 requirements EARS + glossaire |
| `design.md` | Stratégie, décisions justifiées, 10 Correctness Properties, gestion des risques, stratégie de validation |
| `tasks.md` | Plan d'implémentation en vagues + Task Dependency Graph |
| `manual_tests.md` | MT-1 → MT-8 + registre d'exécution + critère de sortie |
