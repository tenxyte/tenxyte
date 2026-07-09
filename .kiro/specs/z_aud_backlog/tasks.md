# Implementation Plan: z_aud_backlog

## Overview

Quatre chantiers indépendants, exécutables dans n'importe quel ordre ou en parallèle. L'ordre
proposé maximise la valeur rapide : **DX d'abord** (débloque le confort de tout le reste),
puis **SMS** (petit, gabarit strict), puis **providers** (le plus gros volume), puis **VDP**.
Les propriétés « universelles » (contrat providers, hygiène logs SMS) sont écrites AVANT les
nouvelles classes pour protéger l'existant et guider les ajouts.

## Tasks

- [ ] 1. DX résiduelle
  - [ ] 1.1 Implémenter UTF8_Self_Reconfigure dans les scripts de validation
    - `sys.stdout/stderr.reconfigure(encoding="utf-8")` avec garde, en tête de
      `validate_endpoints.py` et des autres scripts émetteurs ; repli ASCII des symboles
      décoratifs ; retirer le contournement `PYTHONIOENCODING` de la doc et de CONTRIBUTING
    - **Property 8: Scripts UTF-8 autonomes** (stdout forcé cp1252) `[MT-4]`
    - **Validates: Requirements 4.1, 4.3**

  - [ ] 1.2 Purger les artefacts de redaction des exemples de doc
    - Audit de `docs/en+fr/` : remplacer toute mention de redaction par des placeholders
      `<YOUR_...>` ; re-passer `validate_endpoints.py` (désormais sans variable d'env)
    - _Requirements: 4.2_

- [ ] 2. Propriétés universelles (avant tout ajout)
  - [ ] 2.1 Write registry-wide property tests
    - **Property 1: Contrat de provider universel** (paramétrée sur le registre complet —
      verte sur les 5 providers existants avant tout ajout)
    - **Property 3: Hygiène des logs SMS universelle** (paramétrée sur les 3 backends
      existants)
    - **Property 6 (volet snapshot): formes de réponses sociales existantes figées**
    - **Validates: Requirements 1.1, 2.5, 5.1, 5.2**

- [ ] 3. Backends SMS
  - [ ] 3.1 Implémenter VonageBackend et MessageBirdBackend (HTTP pur)
    - `backends/sms.py` : gabarit Twilio strict, `requests` avec timeout ≤ 10 s, settings
      dédiés, masquage, échec ⇒ False loggé ; docs EN/FR
    - _Requirements: 2.1, 2.2, 2.3, 2.5_

  - [ ] 3.2 Implémenter SNSBackend (extra [sns])
    - boto3 en import paresseux (message nommant l'extra), extra `[sns]` dans
      `pyproject.toml` ; docs EN/FR
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 3.3 Write property tests for backend innocuousness and default install
    - **Property 4: Innocuité des backends** (credentials absents / API down / timeout)
    - **Property 7: Install par défaut inchangée** (snapshot arbre de dépendances)
    - Property 3 re-exécutée sur le registre étendu (6 backends)
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 5.1**

  - [ ] 3.4 Vérifier les flux OTP avec chaque backend `[MT-2]`
    - OTP login / vérification téléphone / 2FA SMS en mock HTTP par backend ; envoi réel en
      manuel
    - _Requirements: 2.4_

- [ ] 4. Checkpoint - Ensure all tests pass
  - DX + SMS verts, suite existante intacte ; ask the user if questions arise.

- [ ] 5. Providers sociaux
  - [ ] 5.1 Implémenter les OIDC_Providers : GitLab, LinkedIn, Slack
    - Réutilisation des helpers OIDC d'Apple (ou GenericOIDCProvider si z_aud_4 livré) ;
      settings `TENXYTE_<PROVIDER>_*` dans `conf/social.py` ; enregistrement au registre
    - _Requirements: 1.1, 1.2, 1.6_

  - [ ] 5.2 Implémenter Discord, Bitbucket et X
    - OAuth2 classique (Discord/Bitbucket, `email_verified` fidèle, emails via endpoint
      dédié si besoin — pattern GitHub) ; X avec PKCE S256 obligatoire et gestion « pas
      d'email »
    - _Requirements: 1.1, 1.3, 1.4, 1.6_

  - [ ] 5.3 Write property tests for the extended registry
    - Property 1 re-exécutée sur les 11 providers
    - **Property 2: Validation OIDC fail-closed partagée** (id_token mutés, identité de code)
    - **Property 5: PKCE obligatoire pour X**
    - **Property 6: Liaison sans email vérifié inchangée + snapshots intacts**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

  - [ ] 5.4 Documenter et valider E2E `[MT-1]`
    - Docs EN/FR par provider (création de l'app OAuth chez le provider, settings,
      particularités) ; sections endpoints.md ; gitleaks allowlist des fixtures ;
      `validate_endpoints.py` vert
    - _Requirements: 1.6, 5.3_

- [ ] 6. Bug bounty léger (VDP)
  - [ ] 6.1 Étendre SECURITY.md et créer le Hall_of_Fame
    - Périmètre in/out, safe harbor, engagements (SLA z_aud_1), reconnaissance non
      monétaire, critère de révision vers une plateforme ;
      `docs/security/hall-of-fame.md` ; processus de triage mainteneur (grille de
      sévérité, chemin advisory/CVE z_aud_1)
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ] 6.2 Valider le parcours par soumission à blanc `[MT-3]`
    - Test de bout en bout avant annonce publique
    - _Requirements: 3.4_

- [ ] 7. Checkpoint final - Ensure all tests pass
  - Les 8 propriétés vertes, suite existante inchangée, OpenAPI existant intact, registre
    manuel complet (MT-1 → MT-4) ; ask the user before closing the audit coverage.

## Notes

- Aucune migration, aucun modèle, aucune dépendance par défaut : la spec est parallélisable
  avec toute phase ≥ 2.
- Les propriétés universelles (2.1) sont volontairement écrites avant les ajouts : elles
  doivent être vertes sur l'existant, puis re-exécutées après chaque extension de registre.
- La tâche 5.1 fonctionne avec ou sans z_aud_4 (D2) — ne pas bloquer dessus.
- Property tests : Hypothesis ≥ 100 exemples, docstring **Feature: z_aud_backlog,
  Property N: <texte>** ; secrets de test en concaténation.
- À la clôture : mettre à jour l'analyse de couverture (AUDIT.md ↔ specs) — les 4 écarts
  résiduels passent à ✅.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["1.2", "3.1", "3.2"] },
    { "id": 2, "tasks": ["3.3", "5.1", "5.2"] },
    { "id": 3, "tasks": ["3.4", "5.3", "6.1"] },
    { "id": 4, "tasks": ["5.4", "6.2"] }
  ]
}
```
