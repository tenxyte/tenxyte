# Tests Manuels — Phase 5 « Go-to-Market » (z_aud_5)

> Cette phase étant majoritairement hors-code, ce document est son **principal instrument de
> validation** : les revues stratégiques, les tests utilisateurs et les campagnes ne
> s'automatisent pas. Chaque procédure doit être déroulée et son résultat consigné dans le
> registre final avant de cocher la tâche correspondante dans `tasks.md`.

**Convention :** chaque section porte un identifiant `MT-x` référencé depuis `tasks.md`.
Un test manuel est **PASS** uniquement si toutes ses étapes de vérification sont satisfaites.

---

## MT-1 — Validation du positionnement (test des 5 secondes et revue hostile)

**Couvre :** Requirements 1.1, 1.2, 1.3 · **Tâches :** 1.1, 1.2
**Prérequis :** `marketing/positioning.md` rédigé ; 5 personnes externes au projet dont au
moins 2 correspondant à l'ICP primaire (devs travaillant avec des agents IA) et 1 hors cible.

### Procédure

1. **Test des 5 secondes** : montrer uniquement le toit du Message_House (Positioning_Statement
   + sous-titre) pendant 5 secondes à chaque testeur, puis demander : « Que fait ce produit ?
   Pour qui ? En quoi est-il différent ? » — consigner les réponses verbatim.
2. Critère : ≥ 4/5 testeurs restituent « identité/sécurité pour agents IA » (pas « une lib
   d'auth de plus ») ; les testeurs ICP identifient au moins un différenciateur (HITL, budget,
   souverain).
3. **Revue hostile de la matrice d'objections** : un relecteur joue l'avocat du diable sur
   chaque objection (« pourquoi pas allauth/Keycloak/Clerk », « petit projet ») — chaque
   réponse doit contenir sa concession explicite (D4) et tenir sans surpromesse.
4. Vérifier l'ancrage : chaque pilier du Message_House pointe vers sa section d'AUDIT.md et
   ses preuves du Claims_Registry.
5. Approbation finale du mainteneur consignée (le positionnement engage tous les assets).

✅ Attendu : restitution correcte ≥ 4/5, matrice d'objections défendable, approbation datée.

---

## MT-2 — Audit du site produit

**Couvre :** Requirements 2.1, 2.2, 2.3, 2.4 · **Tâche :** 6.2
**Prérequis :** site en ligne (staging accepté), Claims_Registry peuplé.

### Procédure

1. **Parcours acheteur 5 minutes** : un testeur ICP découvre le site sans guidage et doit
   pouvoir répondre à : que fait le produit, qu'est-ce qui est prouvé (audit, tests), qu'est-ce
   qui est concédé, comment j'essaie — chronométrer.
2. Vérifier la hiérarchie AIRS_First sur la home (checklist 1.2) : le premier écran parle
   d'agents IA, pas de login/JWT.
3. **Page Engineering Practices** : recouper chaque chiffre affiché avec `marketing/claims.yml`
   (aucun chiffre écrit à la main) ; vérifier la date de dernière vérification affichée.
4. **Page Security** : le rapport d'audit externe (z_aud_1) est téléchargeable, le chemin de
   signalement (SECURITY.md) est visible.
5. **Comparatifs** : chaque tableau porte sa date d'évaluation et ses concessions (providers
   sociaux vs allauth, UI vs Clerk) — relecture critique : « ce tableau survivrait-il à un
   commentaire HN d'un mainteneur d'allauth ? »
6. Hygiène : liens tous valides, Lighthouse ≥ 90 (performance/a11y/SEO), aucun tracker tiers
   non déclaré (cohérence avec la promesse souveraineté).

✅ Attendu : parcours 5 min concluant, zéro chiffre hors registre, comparatifs datés et
défendables, Lighthouse ≥ 90.

---

## MT-3 — Revue du README repositionné

**Couvre :** Requirements 1.4, 2.3 · **Tâche :** 6.1

### Procédure

1. Passer la checklist AIRS_First (1.2) : premier écran GitHub (titre + badges + premier
   paragraphe) = gouvernance d'agents IA ; Positioning_Statement verbatim présent.
2. Vérifier que l'ancien tableau à 3 concurrents a disparu au profit de Dated_Comparisons
   cohérentes avec le site (mêmes dates, mêmes concessions).
3. Lancer `scripts/check_claims.py` sur le README : vert.
4. Test de fraîcheur externe : montrer le README 30 secondes à 2 testeurs ICP — restitution
   du « pour qui / pourquoi différent » correcte.
5. Vérifier les liens communauté (Discord, roadmap, CONTRIBUTING) et leur réciprocité
   (le site pointe le repo et inversement) — versions EN et FR (`README.fr.md`) synchronisées.

✅ Attendu : checklist verte, lint vert, restitution correcte, parité EN/FR.

---

## MT-4 — Dry-run du lancement puis bilan J+7

**Couvre :** Requirements 4.1, 4.2 · **Tâche :** 7.3
**Prérequis :** Launch_Plan et assets prêts (vidéo 90 s, post technique, FAQ objections) ;
livrables z_aud_1 (1.0 + audit publié) et z_aud_2 (spec AIRS) réellement en ligne.

### Procédure

1. **Vérification de véracité pré-launch** : dérouler la FAQ objections et vérifier que chaque
   réponse repose sur un livrable EN LIGNE (pas « bientôt ») — un launch sur promesse est un
   FAIL immédiat (D3).
2. **Dry-run hostile** : soumettre le post technique et la vidéo à 3 relecteurs externes avec
   pour consigne de jouer les commentateurs HN difficiles (« yet another auth lib », « where's
   the security audit? », « bus factor 1 », « benchmarks or it didn't happen »). Chaque
   objection sans réponse préparée ⇒ itération du plan.
3. Répétition logistique : plan de présence 48 h (répondeurs nommés, fuseaux couverts),
   Demo_Instance testée sous charge de curiosité (MT-7 passé), monitoring en place.
4. **Exécution** : dérouler le séquencement J-14 → J0 → J+1 tel que planifié ; consigner tout
   écart au plan.
5. **Bilan J+7** : remplir le template de debrief avec les chiffres du North_Star_Dashboard
   (trafic, étoiles, Discord, installations, mentions) ; analyse honnête des écarts ;
   décisions d'itération pour le calendrier éditorial.

✅ Attendu : véracité 100 %, dry-run itéré jusqu'à zéro objection sans réponse, launch exécuté,
debrief J+7 classé avec décisions.

---

## MT-5 — Parcours contributeur par cobaye externe

**Couvre :** Requirements 3.1, 3.2, 3.3 · **Tâches :** 4.1, 4.2, 4.3
**Prérequis :** Governance_Docs publiés, Discord ouvert, ≥ 20 Good_First_Issues ; un
développeur externe n'ayant jamais contribué au projet (idéalement sur Windows ET un second
sur Linux, le projet étant développé sous Windows).

### Procédure

1. Le cobaye part du README, rejoint le Discord, choisit une Good_First_Issue et tente de la
   livrer en suivant UNIQUEMENT CONTRIBUTING.md — sans aide privée du mainteneur (les
   questions passent par les canaux publics, comme un vrai contributeur).
2. Mesurer : temps jusqu'au premier `pytest` vert en local, points de friction (consignés un
   par un), temps jusqu'à la PR ouverte.
3. Vérifier que la PR reçoit une première réponse dans le SLA public.
4. Le cobaye évalue GOVERNANCE.md : « est-ce que je comprends comment on devient mainteneur
   et qui décide ? » — réponse libre consignée.
5. Chaque friction identifiée ⇒ correction de CONTRIBUTING.md ou de l'issue, puis re-test
   rapide du point corrigé.
6. Vérifier la roadmap publique : les entrées correspondent aux specs `.kiro` réelles et
   l'état est à jour.

✅ Attendu : PR d'un externe mergée (ou mergeable) sans aide privée, setup dev reproductible
sur Windows et Linux, SLA tenu, frictions corrigées.

---

## MT-6 — Revue de la télémétrie et de la transparence

**Couvre :** Requirements 5.1–5.6, 9.2, 9.3 · **Tâches :** 3.1, 3.3
**Prérequis :** Telemetry_Module livré, propriétés 1–6 vertes, Transparency_Doc publiée.

### Procédure

1. **Vérification réseau à froid** : déploiement quickstart par défaut + capture réseau
   (proxy/Wireshark) pendant 15 minutes d'usage (register, login, refresh, 2FA) → **zéro**
   connexion sortante attribuable à Tenxyte (hors HIBP si activé, documenté).
2. Activer `TELEMETRY_ENABLED=True`, rejouer le même usage, capturer les payloads réels :
   les comparer champ à champ à la Transparency_Doc — toute divergence est un FAIL.
3. Inspecter les payloads en jouant l'attaquant : rien qui permette d'identifier le
   déploiement (pas de hostname, URL, IP, email, valeurs de settings) ; l'Install_ID change
   entre deux installations fraîches.
4. Couper le collecteur (endpoint down) : l'application fonctionne à l'identique, latences
   d'auth inchangées (mesure avant/après), aucun log d'erreur bruyant.
5. Repasser `TELEMETRY_ENABLED=False` : plus aucune émission (recapture 15 min).
6. **Revue de la Transparency_Doc** par un œil DPO/RGPD : le texte permet-il à un client
   régulé d'approuver l'activation ? Consigner le verdict.
7. Vérifier le North_Star_Dashboard : les 6 familles de métriques du readme.md remontent ;
   dérouler une première instance du rituel mensuel.

✅ Attendu : silence réseau par défaut prouvé par capture, payload conforme à la doc au champ
près, kill switch total, verdict DPO favorable.

---

## MT-7 — Demo_Instance et chronométrages des claims de vitesse

**Couvre :** Requirements 6.1, 6.2, 6.3, 6.4 · **Tâches :** 6.3, 6.4
**Prérequis :** Demo_Instance en ligne, quickstarts Django et FastAPI publiés.

### Procédure

1. **Parcours visiteur** : depuis le lien du site, dérouler le scénario scripté AIRS sans
   aucune connaissance préalable : déclencher l'action d'agent, constater le `202` HITL,
   l'approuver dans le dashboard, voir l'action aboutir — chronométrer (cible : < 3 min,
   c'est le « aha moment » D8).
2. Vérifier l'hygiène de l'instance : reset périodique effectif (revenir après le cycle),
   rate-limiting déclenché par un burst volontaire, aucun email/SMS réel émis, seed
   déterministe (deux visites donnent le même état initial).
3. **Chronométrages** : dérouler le quickstart Django puis le quickstart FastAPI sur machine
   vierge, chronomètre en main (protocole des MT z_aud_1/z_aud_3) ; consigner les temps dans
   `marketing/claims.yml` — le site et le README affichent CES valeurs, pas un slogan.
4. **Templates** : exécuter chaque template de départ référencé par le site tel que
   documenté ; tout écart ⇒ correction du template ou de la doc.
5. Laisser l'instance sous monitoring 72 h : disponibilité et absence d'abus consignées.

✅ Attendu : « aha moment » < 3 min pour un visiteur neuf, instance saine sous abus, temps
annoncés = temps mesurés, templates exécutables.

---

## MT-8 — Revue du pipeline commercial (partners, études de cas, pricing)

**Couvre :** Requirements 7.1, 7.2, 7.3, 7.4 · **Tâches :** 9.1, 9.3

### Procédure

1. **Charte design partners** : relecture croisée mainteneur + un partner candidat — l'échange
   (offre managée gratuite vs feedback + étude de cas) est-il compris à l'identique des deux
   côtés ? Ambiguïtés corrigées avant signature.
2. Vérifier le CRM : chaque partner a un statut, un historique de feedback mensuel et une
   intention de conversion renseignés ; le seuil « ≥ 5 actifs » est objectivable.
3. **Études de cas** : validation écrite du partner archivée ; chaque chiffre passe par le
   Claims_Registry (lint vert sur les pages) ; relecture « survivrait-elle à une vérification
   par un journaliste tech ? ».
4. **Pricing** : vérifier la dérivation depuis `editions.md` (z_aud_4) et les données
   partners (willingness-to-pay documentée) ; cohérence Open_Core_Boundary (aucune capacité
   OSS reclassée payante) ; la page pricing passe le Claims_Lint.
5. Vérifier la règle D7 : la date de publication du pricing est postérieure à la date où le
   5ᵉ partner est devenu actif (ou dérogation mainteneur motivée et consignée).
6. Approbation finale du mainteneur (comme MT-8 de z_aud_4 : c'est un engagement public).

✅ Attendu : charte sans ambiguïté, CRM vivant, études de cas blindées, pricing dérivé des
données et conforme à la frontière open-core, approbation datée.

---

## Registre d'exécution

> À compléter à chaque exécution. Une ligne par run (garder l'historique en cas de re-run).

| ID | Intitulé | Date | Exécutant | Environnement | Résultat | Notes / lien preuve |
|----|----------|------|-----------|---------------|----------|---------------------|
| MT-1 | Positionnement (5 s + revue hostile) | — | — | — | ⬜ À exécuter | testeurs : — |
| MT-2 | Audit du site produit | — | — | — | ⬜ À exécuter | Lighthouse : — |
| MT-3 | README repositionné | — | — | — | ⬜ À exécuter | |
| MT-4 | Dry-run launch + bilan J+7 | — | — | — | ⬜ À exécuter | debrief : — |
| MT-5 | Parcours contributeur externe | — | — | — | ⬜ À exécuter | PR : — |
| MT-6 | Télémétrie + transparence (capture réseau) | — | — | — | ⬜ À exécuter | verdict DPO : — |
| MT-7 | Demo_Instance + chronométrages | — | — | — | ⬜ À exécuter | temps mesurés : — |
| MT-8 | Pipeline commercial | — | — | — | ⬜ À exécuter | approbation : — |

**Légende résultat :** ✅ PASS · ❌ FAIL (ouvrir une issue, référencer ici) · ⚠️ PASS avec réserve
(documenter la réserve) · ⬜ À exécuter

## Critère de sortie de la phase

La phase est validée lorsque : toutes les lignes du registre sont ✅ (ou ⚠️ avec réserve
acceptée par le mainteneur), les propriétés automatisées 1–8 sont vertes en CI (télémétrie,
Claims_Lint, invisibilité), le debrief J+7 du launch est classé avec ses décisions, ≥ 5 design
partners sont actifs (ou dérogation motivée), le 2ᵉ mainteneur est nommé ou en Maintainer_Path
documenté, les rituels récurrents (revue semestrielle des comparatifs, revue mensuelle du
North_Star_Dashboard) ont tourné au moins une fois, la suite existante passe sans
modification, et le checkpoint final de `tasks.md` est coché. C'est la dernière phase de la
feuille de route : sa sortie déclenche la revue globale des 5 phases contre le scénario
« game-changer de niche » de l'audit (§6.4).
