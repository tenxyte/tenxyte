# base.md — Phase 5 « Go-to-Market » : état des lieux et plan brut

## 1. Ce que dit l'audit (la phase est dérivée, pas copiée)

`AUDIT.md` §9 s'arrête à la Phase 4. Mais le **verdict §10** est sans ambiguïté :

> « Le code est déjà au niveau (c'est rare). Ce qui manque est entièrement dans la
> distribution : audit externe, 1.0, spec AIRS ouverte, connecteurs LangChain/MCP, et une
> communauté construite chez les *builders d'agents* plutôt que chez les développeurs Django.
> […] le pari se gagne dans les 18 prochains mois, et il se gagne en dehors du dépôt Git. »

Les phases 1–4 couvrent audit/1.0/spec/connecteurs/multi-framework/enterprise. Cette phase 5
couvre **tout le reste du verdict** : distribution, communauté, notoriété, mesure, business.

Ancrages précis dans l'audit :

- **F5** (critique) : « Communauté embryonnaire — peu de contributeurs visibles, pas de
  Discord/Slack actif documenté, notoriété faible. Un package d'auth vit de la confiance
  communautaire. » Score « Adoption & communauté » : **3/10**, « le chantier n°1 ».
- **F6** (importante) : « Bus factor ≈ 1 — risque de continuité pour tout adopteur sérieux. »
- **§4.3** (mineures mais GTM) : télémétrie d'adoption opt-in inexistante (« impossible de
  savoir qui utilise quoi ») ; « le README compare à 3 concurrents seulement — la vraie carte
  concurrentielle (§5) est plus dure et devrait informer le positionnement ».
- **§3.5** : la rigueur d'ingénierie « doit être rendue visible (badge, page "Engineering
  Practices") ».
- **§3.4** : Shortcut Secure Mode = « pattern produit fort, **sous-exploité dans le marketing
  actuel** ».
- **§6.3** : conditions de conversion — nommer et standardiser (fait en z_aud_2), intégrations
  agents-first (fait en z_aud_2), **vitesse** : « il faut avoir capté la communauté avant » que
  les acteurs financés livrent. Fenêtre : 12–24 mois.
- **§8** : 🟠 P1 « Communauté : Discord, roadmap publique, 2–3 mainteneurs, good-first-issues »
  (effort : continu) ; 🟢 P3 « Offre commerciale » (z_aud_4 a produit la frontière et le
  blueprint — z_aud_5 produit le pipeline : pricing public, design partners, études de cas).
- **§5.5** : la phrase de positionnement existe déjà dans l'audit (« le seul produit du marché
  qui soit à la fois : (1) in-process, (2) comparable à un IAM serveur, (3) gratuit et
  souverain, (4) doté d'une couche agents IA ») — elle n'est utilisée nulle part publiquement.
- **§9 Phase 2** (déborde sur cette phase) : « Contenu technique : "How to give an AI agent a
  credit card limit", benchmarks HITL. Cibler les communautés agents (pas les communautés
  Django). » — les benchmarks existent (z_aud_2), le contenu et le ciblage restent à exécuter.

## 2. État des lieux mesuré

### 2.1 Actifs disponibles (produits par les phases 1–4, prêts à être exploités)

| Actif | Origine | Usage GTM |
|---|---|---|
| Release 1.0 + contrat de stabilité + audit externe publié | z_aud_1 | Signal d'achat n°1 (F1/F2 levées), page « Security » |
| Spec AIRS-1.0 ouverte (CC BY 4.0) + suite de conformité | z_aud_2 | Narratif « standard », posts techniques, SEO du vocabulaire |
| `tenxyte-langchain`, `tenxyte-mcp-server`, exemple CrewAI, benchmarks | z_aud_2 | Canal de distribution natif vers les builders d'agents |
| Parité FastAPI + UI headless/stylée + backend démo docker | z_aud_3 | Crédibilité « framework-agnostic », démos, time-to-market vs Clerk |
| OIDC Provider/SSO/SCIM + dashboard HITL + `editions.md` + blueprint managé | z_aud_4 | Offre enterprise et commerciale à vendre |
| 2 605 tests, PBT, specs formelles, migrations additives, docs bilingues | existant | Matière brute de la page Engineering Practices |
| `docs/en+fr/` complets, Postman, quickstarts validés chronométrés | existant | Activation |

### 2.2 Ce qui n'existe pas (le chantier)

- **Aucun document de positionnement** : pas d'ICP, pas de message house, pas de hiérarchie
  AIRS-d'abord ; le README actuel se compare « gentiment » à 3 concurrents.
- **Aucune présence produit** : pas de site (les docs MkDocs existent mais ne vendent pas),
  pas de page Engineering Practices, pas de page sécurité orientée acheteur.
- **Aucune infrastructure communautaire** : pas de Discord, pas de roadmap publique, pas de
  GOVERNANCE.md ni CODE_OF_CONDUCT.md ; CONTRIBUTING sommaire ; zéro good-first-issue
  étiquetée ; un seul mainteneur.
- **Aucun plan de lancement** : la 1.0 (z_aud_1) et la spec AIRS (z_aud_2) sortiraient sans
  caisse de résonance.
- **Aucune mesure** : pas de télémétrie, pas de tableau de bord d'adoption, pas de funnel.
- **Aucun pipeline commercial** : `editions.md` (z_aud_4) définit QUOI vendre, rien ne définit
  À QUI ni COMMENT (pas de pricing public, pas de design partners, pas d'études de cas).
- **Aucun garde-fou d'intégrité marketing** : rien n'empêche un claim public de dériver du
  code réel.

## 3. Plan brut des chantiers

1. **Positionnement** — `marketing/positioning.md` : ICP primaire (équipes Python déployant
   des agents IA en production, 5–200 devs, contrainte souveraineté/coût) et secondaires
   (SaaS B2B self-hosted, secteurs régulés — §3.3) ; message house (toit = phrase §5.5
   recentrée AIRS ; piliers = gouvernance d'agents / souveraineté+coût / largeur+rigueur) ;
   matrice objections/réponses (dont « pourquoi pas allauth/Keycloak/Clerk » — réponses tirées
   de §5.2–5.4) ; naming du narratif (AIRS = le vocabulaire du problème, §6.3-1).
2. **Présence** — site produit (hors-repo, tracé ici) : home AIRS-first, pages solutions par
   ICP, page Engineering Practices (chiffres CI en continu), page Security (audit z_aud_1,
   SECURITY.md), comparatifs datés avec concessions explicites (D4), pricing (chantier 7).
   Dans le repo : README repositionné (hiérarchie D1, vraie carte concurrentielle), badges.
3. **Communauté** — GOVERNANCE.md (rôles, processus de décision, chemin vers mainteneur),
   CODE_OF_CONDUCT.md (Contributor Covenant), CONTRIBUTING.md réécrit (setup dev Windows/Linux,
   conventions specs `.kiro`, PBT), 20+ good-first-issues calibrées (petites, testables,
   mentorées), Discord structuré (canaux : help, agents/AIRS, contrib, annonces), roadmap
   publique (GitHub Projects, alimentée par les specs `.kiro`), SLA de réponse public,
   programme 2ᵉ mainteneur (critères objectifs, délégation progressive des droits).
4. **Lancement & contenu** — plan de launch 1.0+AIRS : séquencement (teasing → show HN →
   communautés agents → récap), assets préparés (démo vidéo 90 s, post technique, FAQ
   objections), présence 48 h planifiée, bilan J+7 chiffré ; 3 contenus piliers : « How to
   give an AI agent a credit card limit » (§9), « Anatomy of a HITL approval » (benchmarks
   z_aud_2), « Self-hosted auth without running an identity server » (§5.3) ; calendrier
   éditorial 6 mois ciblant les canaux D2 ; 2 propositions de talks (PyCon/conf IA).
5. **Télémétrie opt-in** — module `tenxyte/telemetry.py` : évènements fermés (schéma énuméré :
   `setup_completed`, versions, framework adapter, flags de features actives — jamais de
   valeurs), anonymat structurel (ID d'installation aléatoire, pas de PII possible par
   construction), `TELEMETRY_ENABLED=False` par défaut, activation explicite documentée,
   endpoint de collecte hors chemin de requête (thread/task fire-and-forget, échec silencieux),
   doc de transparence publique (payload exact, rétention) ; dashboard interne des métriques
   nord (PyPI, GitHub, Discord, télémétrie).
6. **Produit démontrable** — instance démo publique (backend démo z_aud_3 + UI z_aud_3 +
   dashboard HITL z_aud_4, seed déterministe, reset périodique, rate-limited) ; vérification
   chronométrée du « 2 minutes au premier login » (§5.3) sur les deux frameworks ; templates
   de départ référencés depuis le site.
7. **GTM commercial** — programme design partners (charte : gratuité offre managée contre
   feedback structuré + étude de cas nominative, 5–10 équipes issues des communautés agents),
   pricing public dérivé d'`editions.md` (z_aud_4) publié APRÈS validation partners (D7),
   2 études de cas publiées, CRM léger de suivi du pipeline.
8. **Intégrité des claims** — `marketing/claims.yml` : chaque claim quantifié public (« 2 605
   tests », « 2 minutes », « HITL p95 < X ms », « 93 endpoints »…) avec sa source de preuve
   (chemin de test, script, MT au registre, rapport) ; `scripts/check_claims.py` en CI :
   claim sans preuve résolvable ⇒ échec ; règle éditoriale : tout chiffre public vient de
   `claims.yml`, jamais d'un texte libre.

## 4. Contraintes héritées

- **Zéro impact sur le package** : hors module télémétrie (opt-in, défaut off), aucun
  changement de comportement ; suite existante verte sans modification ; le lint des claims
  et la télémétrie sont additifs.
- La télémétrie ne touche JAMAIS le chemin d'une requête d'authentification (D5) et ne peut
  structurellement pas transporter de PII (schéma fermé, property-testé).
- Les livrables hors-repo (site, Discord, campagne, CRM) sont tracés dans `tasks.md` et
  prouvés au registre de `manual_tests.md` (même mécanisme que les tâches monorepo JS de
  z_aud_3 et dashboard de z_aud_4).
- Cohérence des engagements publics : SLA de réponse, gouvernance et frontière open-core
  (z_aud_4) sont des promesses — ne publier que ce qui est tenable par l'équipe réelle.
