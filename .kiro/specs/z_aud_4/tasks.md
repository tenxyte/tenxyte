# Implementation Plan: Phase 4 « Enterprise » (z_aud_4)

## Overview

L'implémentation suit le jalonnement du design : **socle commun** (snapshot OpenAPI pris AVANT
tout code, flags, kid/JWKS), puis **Rôle 1 — OpenID Provider** (Core → modèles → endpoints →
consentement), puis **Rôle 2 — SSO entrant** (SSOConnection → routage → OIDC générique → SAML
en extra), puis **Rôle 3 — SCIM**, puis **produit et offre** (frontière open-core publiée avant
le code du dashboard — D8), enfin docs et non-régression. Chaque rôle est fusionnable
indépendamment derrière son flag ; les vérifications d'interop réelle portent le marqueur
`[MT-x]` renvoyant à `manual_tests.md`.

## Tasks

- [ ] 1. Socle commun de la phase
  - [ ] 1.1 Capturer le snapshot OpenAPI pré-phase
    - Export du schéma existant en artefact versionné (`tests/snapshots/openapi_pre_z_aud_4.json`)
      + job CI comparant byte à byte le schéma flags éteints — installé AVANT tout autre code
    - **Property 13 (socle)** · _Requirements: 9.3_

  - [ ] 1.2 Ajouter les Feature_Flags_P4 et le check de boot
    - `conf/` : `OIDC_PROVIDER_ENABLED`, `ENTERPRISE_SSO_ENABLED`, `SCIM_ENABLED` (défaut
      False, attention au préfixe auto de `_get()`) ; check de démarrage OP+HS* ⇒ erreur
      explicite ; check `saml` sans extra ⇒ `TenxyteMissingDependencyError`
    - _Requirements: 1.1, 1.2, 3.1, 3.6, 5.1_

  - [ ] 1.3 Write property test for symmetric-boot refusal and gating
    - **Property 2: Refus de boot OP en symétrique**
    - **Property 1 (volet flags): 404 FEATURE_DISABLED sur toute surface, tout flag éteint**
    - **Validates: Requirements 1.1, 1.2, 3.1, 5.1**

  - [ ] 1.4 Ajouter kid déterministe et sérialisation JWKS au JWTService
    - Fonctions pures dans `core/jwt_service.py` : kid = SHA-256 tronqué de la clé publique
      DER ; export JWK(S) de la clé active + `JWT_PREVIOUS_PUBLIC_KEY` si configurée — aucune
      signature existante modifiée
    - _Requirements: 1.4_

- [ ] 2. Rôle 1 — OpenID Provider : cœur protocolaire (Core)
  - [ ] 2.1 Implémenter `core/oidc_provider_service.py` et ses ports
    - Ports `AuthorizationCodeStorage` et `ConsentStorage` ; validation de requête
      d'autorisation (client actif, redirect_uri exact-match, scopes ⊆ allowed, PKCE S256
      obligatoire si client public) ; émission de code (opaque, hashé au stockage, TTL ≤ 120 s,
      liaisons complètes) ; échange token (usage unique, rejeu ⇒ révocation des tokens issus,
      vérification verifier) ; construction id_token (iss/sub/aud/exp/iat/nonce/at_hash) via
      JWTService ; logique consentement — zéro import Django, fonctions pures extraites
    - _Requirements: 1.5, 1.6, 1.7, 1.8, 2.2, 2.3, 9.4_

  - [ ] 2.2 Write property tests for the protocol core
    - **Property 4: Code à usage strictement unique** (séquences d'échanges générées)
    - **Property 5: PKCE obligatoire pour clients publics** (échec au plus tôt)
    - **Property 6: Exactitude des claims id_token** (configs générées)
    - **Property 7: redirect_uri exact-match** (mutations générées)
    - **Property 14 (volet pureté): aucun import Django dans le module**
    - **Validates: Requirements 1.5, 1.6, 1.7, 1.8, 2.2, 9.4**

- [ ] 3. Rôle 1 — OpenID Provider : modèles et endpoints Django
  - [ ] 3.1 Créer les modèles OP et la migration additive
    - `OIDCClient` (FK Application, client_id UUID, secret hashé retourné une fois,
      client_type, redirect_uris, allowed_scopes, require_consent, is_active),
      `OIDCAuthorizationCode` (code hashé, liaisons, used), `OIDCConsent` (user×client×scopes,
      révocable) — migration 0019+ strictement additive, `Application` intouchée
    - _Requirements: 2.1, 2.5, 9.2_

  - [ ] 3.2 Exposer discovery, JWKS, authorize, token, userinfo, revocation
    - Vues Django + urls sous gating ; discovery reflétant la config réelle ; authorize avec
      redirection login si non authentifié puis étape consentement (template + API) ; erreurs
      au Protocol_Error_Format (jamais de redirection vers une URI non validée) ; throttling
      familles dédiées ; audit log sur chaque événement de sécurité
    - _Requirements: 1.3, 1.5, 1.6, 2.3, 8.1, 8.2, 8.4_

  - [ ] 3.3 Implémenter le CRUD admin des clients OIDC
    - Endpoints admin (RBAC existant) : création (secret affiché une fois), rotation de
      secret, désactivation (⇒ rejet authorize/token + révocation), liste/détail ;
      serializers dédiés
    - _Requirements: 2.1, 2.4_

  - [ ] 3.4 Write property tests for discovery, consent and client lifecycle
    - **Property 3: Cohérence discovery/JWKS/réalité** (incl. rotation de clé)
    - **Property 8: Consentement bloquant et fidèle + client désactivé rejeté**
    - **Validates: Requirements 1.3, 1.4, 2.3, 2.4**

- [ ] 4. Checkpoint - Ensure all tests pass
  - Rôle OP complet vert, snapshot OpenAPI flags éteints byte-identique, suite existante
    intacte ; ask the user if questions arise. Interop réelle : `[MT-1]` `[MT-2]`.

- [ ] 5. Rôle 2 — SSO entrant : connexions et routage
  - [ ] 5.1 Créer le modèle SSOConnection et son CRUD
    - FK Organization, protocol (saml|oidc), domains (unicité applicative instance-wide sur
      domaine actif), config JSON, jit_enabled, default_role, scim_enabled ; endpoints admin
      d'organisation ; migration additive
    - _Requirements: 3.2, 9.2_

  - [ ] 5.2 Implémenter le Domain_Routing
    - `POST /login/sso/` : email → domaine → connexion → URL de redirection IdP ; forme de
      réponse identique avec ou sans connexion (anti-énumération) ; throttling
    - _Requirements: 3.3, 8.2_

  - [ ] 5.3 Write property test for domain routing
    - **Property 9: Déterminisme et anti-énumération du Domain_Routing** (unicité de domaine
      imposée, formes de réponse comparées)
    - **Validates: Requirements 3.2, 3.3**

- [ ] 6. Rôle 2 — SSO entrant : protocoles
  - [ ] 6.1 Implémenter le GenericOIDCProvider
    - Dérivation d'`AbstractOAuthProvider` configurée par connexion (discovery de l'issuer à
      la config, state + nonce imposés) ; réutilisation du code de liaison utilisateur du
      flux social (email vérifié ⇒ liaison, jamais de doublon)
    - _Requirements: 3.5, 4.4_

  - [ ] 6.2 Implémenter le SP SAML dans l'extra `[saml]`
    - `pyproject.toml` : extra `[saml]` (lib xmlsec) jamais tiré par défaut ; metadata SP,
      émission AuthnRequest (corrélation InResponseTo en cache), endpoint ACS ; validation
      fail-closed dans l'ordre D5 : signature (certificat de la connexion), Audience,
      InResponseTo, NotBefore/NotOnOrAfter (skew ±60 s), unicité d'assertion ID (anti-replay) ;
      échec ⇒ rejet total sans effet partiel, message générique, détail en audit log
    - _Requirements: 3.4, 3.6, 8.1, 8.4, 9.5_

  - [ ] 6.3 Implémenter le JIT_Provisioning gouverné
    - jit_enabled=True ⇒ création (mot de passe inutilisable) + membership avec default_role +
      événement d'audit ; jit_enabled=False ⇒ rejet non-énumérant sans création ;
      scim_enabled ⇒ JIT inhibé (précédence D7)
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ] 6.4 Write property tests for SAML validation and JIT
    - **Property 10: Validation SAML fail-closed sans effet partiel** (assertions de fixture
      signées puis mutées : signature, audience, InResponseTo, horodatages, ID rejoué)
    - **Property 11: JIT gouverné et précédence SCIM**
    - **Validates: Requirements 3.4, 4.1, 4.2, 4.3, 4.4**

- [ ] 7. Checkpoint - Ensure all tests pass
  - Rôle SSO complet vert (avec et sans extra `[saml]` installé — deux jobs CI) ; ask the user
    if questions arise. Interop réelle : `[MT-3]` `[MT-4]`.

- [ ] 8. Rôle 3 — Serveur SCIM 2.0
  - [ ] 8.1 Implémenter l'authentification et le socle SCIM
    - SCIM_Token par connexion (généré, affiché une fois, stocké SHA-256), 401 sans token
      valide ; endpoints ServiceProviderConfig et Schemas ; erreurs RFC 7644 ; throttling ;
      gating `SCIM_ENABLED`
    - _Requirements: 5.1, 5.2, 8.2, 8.4_

  - [ ] 8.2 Implémenter /Users (CRUD + filtres)
    - POST (externalId persisté, 409 uniqueness sur doublon), GET par id et par filtre
      (sous-ensemble : eq sur userName/externalId/email, conjonction and ; reste ⇒ 400
      scimType), PUT/PATCH (active=false ⇒ désactivation + révocation sessions/refresh,
      jamais de suppression physique), DELETE ⇒ désactivation
    - _Requirements: 5.3, 5.4, 5.5_

  - [ ] 8.3 Implémenter /Groups et le mapping organisationnel
    - Groups ↔ OrganizationMembership/rôles de l'organisation de la connexion ; opérations
      idempotentes au rejeu ; audit log de chaque mutation SCIM (connexion, opération, cible,
      issue)
    - _Requirements: 5.6, 5.7, 8.1_

  - [ ] 8.4 Write property test for SCIM integrity
    - **Property 12: Intégrité SCIM** (auth par connexion, unicité externalId, deactivate sans
      suppression, corpus de filtres générés, idempotence Groups)
    - **Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6**

- [ ] 9. Checkpoint - Ensure all tests pass
  - Les trois rôles verts sous flags, snapshot OpenAPI toujours byte-identique flags éteints ;
    ask the user if questions arise. Interop réelle : `[MT-5]`.

- [ ] 10. Offre commerciale (documents AVANT le code du dashboard — D8)
  - [ ] 10.1 Publier la frontière open-core et la politique de support `[MT-8]`
    - `docs/en/editions.md` + FR : OSS = protocole complet (OP/SSO/SCIM) + dashboard
      self-host ; commercial = dashboard managé multi-tenant, rétention étendue, SLA ;
      politique de support (canaux, délais par tier, lien SECURITY.md z_aud_1)
    - _Requirements: 7.1, 7.4_

  - [ ] 10.2 Publier le blueprint cloud managé et le garde-fou anti-crippleware
    - `docs/deployment/managed-blueprint.md` (isolation multi-tenant, gestion de clés,
      backup/restore, stratégie d'upgrade — niveau architecture) ; check CI grep motifs
      `license_key`/`entitlement` dans `src/` ⇒ échec
    - **Property 14 (volet license-check)** · _Requirements: 7.2, 7.3_

- [ ] 11. Dashboard HITL (produit — hors package Python, tracé ici)
  - [ ] 11.1 Livrer le socle du dashboard `[MT-6]`
    - `tenxyte-hitl-dashboard` : auth Tenxyte standard (JWT + RBAC pending-actions, aucun
      bypass), liste quasi temps réel des pending actions (agent, endpoint, trace ID,
      expiration), approve/deny avec justification, états terminaux tirés du backend,
      historique/audit ; HTTP_Only_Rule vérifiée par le check z_aud_2
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ] 11.2 Livrer l'image Docker self-host + E2E
    - Image configurable par URL backend + credentials uniquement ; E2E contre le backend
      démo z_aud_3 (seed d'actions en attente)
    - _Requirements: 6.5_

- [ ] 12. Documentation et intégration finale
  - [ ] 12.1 Documenter les trois rôles EN/FR
    - `oidc_provider.md`, `enterprise_sso.md` (guides Okta et Entra pas-à-pas), `scim.md`
      (sous-ensemble de filtres, précédence SCIM>JIT) ; sections endpoints.md + settings.md ;
      collection Postman augmentée ; `validate_endpoints.py` vert (`set PYTHONIOENCODING=utf-8`)
    - _Requirements: 7.1 (renvois), 1.3, 3.2, 5.5_

  - [ ] 12.2 Étendre l'hygiène secrets
    - `.gitleaks.toml` : allowlist des fixtures SAML/JWKS de test ; vérification qu'aucun
      secret client ni token SCIM n'apparaît dans les logs (assertions dans les tests
      d'intégration)
    - _Requirements: 8.3_

  - [ ] 12.3 Write final non-regression property test
    - **Property 13 (finale): Invisibilité totale flags éteints** — suite existante verte sans
      modification, migrations additives vérifiées, OpenAPI byte-identique
    - **Property 1 (finale): gating exhaustif sur la surface complète de la phase**
    - **Validates: Requirements 9.1, 9.2, 9.3**

  - [ ] 12.4 Dérouler la campagne de tests manuels
    - Exécuter `manual_tests.md` MT-1 à MT-8 et compléter le registre
    - _Requirements: interop et revues (toutes)_

- [ ] 13. Checkpoint final - Ensure all tests pass
  - Trois rôles + produit + offre verts, registre manuel complet, écarts de conformance OpenID
    tracés en issues ; ask the user before any « enterprise-ready » announcement.

## Notes

- Les tâches `[MT-x]` ont une contrepartie obligatoire dans `manual_tests.md`.
- Le snapshot OpenAPI (1.1) est la PREMIÈRE tâche : sans référence pré-phase, la Property 13
  n'est pas prouvable.
- Deux jobs CI pour le rôle SSO : avec et sans extra `[saml]` (Requirement 9.5).
- Les tâches 11.x s'exécutent hors de ce repo ; elles sont cochées ici sur preuve (lien PR +
  résultat MT-6 au registre).
- Property tests : Hypothesis ≥ 100 exemples, docstring **Feature: z_aud_4, Property N: <texte>**.
  Mots de passe de test en concaténation (`"Enter" + "prise" + "Pass123!"`).

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.4"] },
    { "id": 2, "tasks": ["1.3", "2.1"] },
    { "id": 3, "tasks": ["2.2", "3.1"] },
    { "id": 4, "tasks": ["3.2", "3.3"] },
    { "id": 5, "tasks": ["3.4", "5.1"] },
    { "id": 6, "tasks": ["5.2", "6.1", "6.2"] },
    { "id": 7, "tasks": ["5.3", "6.3"] },
    { "id": 8, "tasks": ["6.4", "8.1"] },
    { "id": 9, "tasks": ["8.2", "8.3", "10.1"] },
    { "id": 10, "tasks": ["8.4", "10.2", "11.1"] },
    { "id": 11, "tasks": ["11.2", "12.1", "12.2"] },
    { "id": 12, "tasks": ["12.3", "12.4"] }
  ]
}
```
