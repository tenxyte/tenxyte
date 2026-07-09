# Spec z_aud_1 — Phase 1 « Crédibilité » (v1.0 Readiness)

> **Source :** `AUDIT.md` (racine du projet), §9 « Feuille de route recommandée », Phase 1 (T+0 → T+4 mois)
> **Statut :** 📋 Spécifié — prêt pour implémentation
> **Version cible :** 1.0.0 (depuis 0.9.6.4)

---

## Contexte

L'audit stratégique (`AUDIT.md`) a identifié la **crédibilité** comme le premier chantier bloquant
pour que Tenxyte passe du statut de package prometteur à celui de produit adoptable en entreprise.
Les faiblesses adressées par cette phase sont :

| Faiblesse (AUDIT.md) | Adressée par |
|---|---|
| F1 — Pré-1.0, classifieur « Beta » | Requirement 1 (contrat de stabilité) + Requirement 7 (release 1.0) |
| F2 — Aucun audit de sécurité externe publié | Requirement 3 (SECURITY.md/CVE) + Requirement 6 (préparation d'audit) |
| F8 — Pas d'Apple Sign-In (bloquant iOS) | Requirement 5 (AppleOAuthProvider) |
| F11 — Dépendances par défaut lourdes | Requirement 2 (inversion des extras de packaging) |
| — Releases non signées | Requirement 4 (Trusted Publishing + attestations) |

## Périmètre de la phase

1. **Contrat de stabilité d'API** — définition formelle de la surface publique, politique SemVer,
   politique de dépréciation (`docs/en/stability.md`, `docs/fr/stability.md`).
2. **Inversion des extras de packaging** — `pip install tenxyte` = Core seul ;
   `pip install tenxyte[django]` = stack Django. Garde d'import pour que `import tenxyte`
   fonctionne sans Django installé. Guide de migration 0.9 → 1.0.
3. **Politique de divulgation de vulnérabilités** — `SECURITY.md` à la racine, canal de
   signalement privé (GitHub Security Advisories), SLA de réponse, processus CVE.
4. **Signature et attestation des releases** — PyPI Trusted Publishing (OIDC), attestations
   PEP 740 / Sigstore, tags git signés.
5. **Apple Sign-In** — nouveau provider `apple` dans le système social multi-provider existant
   (client secret JWT ES256, validation `id_token` via JWKS Apple, gestion du private relay email).
6. **Préparation de l'audit de sécurité externe** — modèle de menaces, document de périmètre
   d'audit, checklist d'auto-évaluation (livrables documentaires pour le prestataire).
7. **Ingénierie de release 1.0** — bump de version, classifieur « Production/Stable », CHANGELOG,
   guide de migration, non-régression complète.

## Hors périmètre (phases ultérieures)

- Adapter FastAPI complet et Core async → Phase 3 (spec future).
- Spec AIRS ouverte + connecteurs LangChain/MCP → Phase 2 (spec future).
- Mode OIDC Provider, SAML, SCIM → Phase 4 (spec future).
- Providers sociaux additionnels au-delà d'Apple (Vonage SMS, etc.) → backlog.
- La **réalisation** de l'audit de sécurité externe lui-même (prestation tierce) — cette spec ne
  couvre que sa **préparation** (livrables documentaires et durcissement pré-audit).

## Fichiers de cette spec

| Fichier | Rôle |
|---|---|
| `readme.md` | Ce document — vue d'ensemble, contexte, statut, journal de décisions |
| `base.md` | Plan initial issu de l'audit (notes brutes de cadrage) |
| `requirements.md` | Exigences formelles EARS avec glossaire et critères d'acceptation |
| `design.md` | Conception détaillée : architecture, composants, propriétés de correction, stratégie de test |
| `tasks.md` | Plan d'implémentation traçable (tâches ↔ requirements, graphe de dépendances) |
| `manual_tests.md` | Procédures de tests manuels (non automatisables : Apple E2E, PyPI, GitHub Advisories…) |
| `.config.kiro` | Métadonnées de la spec |

## Décisions structurantes (journal)

| # | Décision | Justification |
|---|---|---|
| D1 | L'inversion des extras est livrée **directement en 1.0** (breaking change), précédée d'un `DeprecationWarning` dans une ultime release 0.9.x | SemVer autorise le breaking en 1.0 ; c'est le seul moment où ce changement est possible sans coût politique |
| D2 | Apple Sign-In réutilise `AbstractOAuthProvider` existant sans modifier les 4 providers en place | Non-régression stricte ; le pattern est prévu pour ça |
| D3 | Le client secret Apple (JWT ES256) est généré à la volée et jamais persisté ; seule la clé privée `.p8` est configurée | Conformité au modèle Apple ; la clé privée reste dans les settings de l'intégrateur |
| D4 | Le canal de signalement de vulnérabilités est GitHub Private Vulnerability Reporting (pas d'email dédié en Phase 1) | Zéro infrastructure supplémentaire, workflow d'advisory + CVE intégré |
| D5 | Signature via PyPI Trusted Publishing + attestations PEP 740 (pas de GPG) | Standard moderne de l'écosystème Python, vérifiable par `pip` et Sigstore, pas de gestion de clés |
| D6 | La surface d'API publique est définie par une liste explicite dans `docs/*/stability.md`, pas par convention d'underscore | Auditables et testable (test snapshot des exports publics) |

## Definition of Done de la phase

- [ ] Tous les tests existants passent sans modification (non-régression, Requirement 8).
- [ ] `pip install tenxyte` dans un venv vierge sans Django : `import tenxyte` fonctionne, version core utilisable.
- [ ] `pip install tenxyte[django]` : comportement identique à l'actuel `pip install tenxyte`.
- [ ] `SECURITY.md` publié et rendu par GitHub (onglet Security).
- [ ] `publish.yml` utilise Trusted Publishing + génère des attestations.
- [ ] Login Apple E2E validé manuellement (voir `manual_tests.md` §3).
- [ ] `docs/en/stability.md` + `docs/fr/stability.md` publiés.
- [ ] Modèle de menaces + périmètre d'audit livrés dans `docs/security-audit/`.
- [ ] `pyproject.toml` : version `1.0.0`, classifieur `Development Status :: 5 - Production/Stable`.
- [ ] CHANGELOG 1.0.0 + guide de migration 0.9 → 1.0 publiés.

## Suivi

Consulter `tasks.md` pour l'avancement tâche par tâche (cases à cocher mises à jour au fil de
l'implémentation), et `manual_tests.md` pour le registre d'exécution des tests manuels.
