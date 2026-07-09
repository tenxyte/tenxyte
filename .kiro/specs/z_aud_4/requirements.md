# Requirements Document — Phase 4 « Enterprise » (z_aud_4)

## Introduction

Cette phase transforme Tenxyte d'un consommateur d'identité en une **plateforme d'identité
enterprise** : fournisseur OIDC pour d'autres applications, point d'entrée fédéré pour les IdP
corporate (SAML/OIDC entrant), cible de provisionnement SCIM 2.0, et socle d'une offre
commerciale construite sur le dashboard HITL (différenciateur AIRS). Tout est additif,
feature-flagged (défaut : désactivé) et sans régression pour l'existant.

## Glossaire

| Terme | Définition |
|---|---|
| **OP (OpenID Provider)** | Rôle serveur OIDC : Tenxyte émet des id_tokens pour des applications tierces |
| **RP (Relying Party)** | Application tierce qui délègue son authentification à l'OP |
| **OIDC_Client** | Enregistrement d'un RP chez Tenxyte : `client_id`, secret hashé, type, redirect URIs, scopes |
| **Client_Confidentiel / Client_Public** | RP capable / incapable de garder un secret ; le public exige PKCE |
| **Authorization_Code** | Code opaque à usage unique, TTL court, lié au client + redirect_uri + code_challenge |
| **Consent** | Accord explicite de l'utilisateur pour libérer des claims à un client donné |
| **Discovery_Document** | `/.well-known/openid-configuration` (RFC 8414 / OIDC Discovery) |
| **JWKS** | Jeu de clés publiques de signature (`/oauth/jwks/`), chaque clé identifiée par un `kid` |
| **SSO_Connection** | Configuration de fédération entrante rattachée à une Organization : protocole (saml\|oidc), domaines email, config IdP, règles JIT |
| **Domain_Routing** | Résolution email → domaine → SSO_Connection → redirection vers l'IdP |
| **SAML_SP** | Rôle Service Provider SAML 2.0 de Tenxyte (metadata, ACS, validation d'assertions) |
| **Generic_OIDC_Provider** | Provider OIDC entrant configurable par connexion, dérivé d'`AbstractOAuthProvider` |
| **JIT_Provisioning** | Création automatique du compte à la première connexion fédérée, si la connexion l'autorise |
| **SCIM_Server** | Endpoints RFC 7643/7644 (`/scim/v2/Users`, `/Groups`, …) exposés par Tenxyte |
| **SCIM_Token** | Bearer token par SSO_Connection, stocké hashé, seul moyen d'authentifier les appels SCIM |
| **externalId** | Identifiant de l'utilisateur côté IdP, clé de synchronisation SCIM |
| **HITL_Dashboard** | Produit web listant les `AgentPendingAction` et permettant approve/deny — consomme uniquement l'API AIRS publique |
| **HTTP_Only_Rule** | Règle z_aud_2 : le dashboard ne peut pas importer `tenxyte`, uniquement parler HTTP |
| **Open_Core_Boundary** | Frontière documentée entre l'offre open source et l'offre commerciale |
| **Protocol_Error_Format** | Exception au format d'erreur canonique : RFC 6749 §5.2 (OAuth2) et RFC 7644 §3.12 (SCIM) sur leurs endpoints respectifs |
| **Feature_Flags_P4** | `TENXYTE_OIDC_PROVIDER_ENABLED`, `TENXYTE_ENTERPRISE_SSO_ENABLED`, `TENXYTE_SCIM_ENABLED` — tous défaut `False` |

## Requirements

### Requirement 1 — Mode OIDC Provider : cœur protocolaire

**User Story:** En tant qu'entreprise utilisant Tenxyte, je veux qu'il serve de fournisseur
d'identité OIDC à mes autres applications, afin de centraliser le SSO sans déployer Keycloak.

#### Acceptance Criteria

1. WHEN `OIDC_PROVIDER_ENABLED` is False (default), THEN all OP endpoints SHALL return 404
   `FEATURE_DISABLED` and no OP model row SHALL be required to exist.
2. WHEN the OP mode is enabled with `JWT_ALGORITHM` set to a symmetric algorithm (HS*), THEN
   the system SHALL refuse to start with an explicit configuration error naming the setting.
3. WHEN a client requests `GET /.well-known/openid-configuration`, THEN the system SHALL return
   a valid Discovery_Document whose `issuer`, endpoint URLs, `jwks_uri`, supported scopes,
   response types (`code`), and signing algorithms reflect the actual configuration.
4. WHEN `GET /oauth/jwks/` is requested, THEN the response SHALL contain the active public key
   with a stable `kid`, and SHALL also contain the previous public key while
   `JWT_PREVIOUS_PUBLIC_KEY` is configured.
5. WHEN an authenticated user completes `GET /oauth/authorize/` for a valid client, THEN the
   system SHALL issue a single-use Authorization_Code with a TTL ≤ 120 seconds, bound to the
   client, the exact redirect_uri, the scopes, the nonce, and the PKCE code_challenge when
   present.
6. WHEN `POST /oauth/token/` exchanges a valid code, THEN the response SHALL include an
   id_token signed with the active key whose claims (`iss`, `sub`, `aud`, `exp`, `iat`,
   `nonce`, `at_hash`) are correct per OIDC Core 3.1.3.6, plus an access token usable on
   `GET /oauth/userinfo/`.
7. WHEN a code is replayed, expired, bound to another client, or presented with a wrong PKCE
   `code_verifier`, THEN the token endpoint SHALL reject it with the standard OAuth2 error
   format (Protocol_Error_Format) and SHALL revoke tokens already issued from that code on
   replay (RFC 6749 §4.1.2 note).
8. WHEN a Client_Public requests authorization without PKCE (S256), THEN the request SHALL be
   rejected.

### Requirement 2 — Gestion des clients OIDC et consentement

**User Story:** En tant qu'administrateur, je veux enregistrer et gérer les applications
clientes (RP) et contrôler le consentement, afin de garder la maîtrise de ce qui accède à
l'identité de mes utilisateurs.

#### Acceptance Criteria

1. WHEN an admin creates an OIDC_Client via the admin API, THEN the system SHALL generate a
   `client_id` and, for confidential clients, a secret returned once and stored hashed.
2. WHEN an authorization request carries a `redirect_uri`, THEN it SHALL be validated by exact
   match against the client's registered list; no partial or wildcard matching SHALL occur.
3. WHEN a client has `require_consent=True` and the user has no stored Consent covering the
   requested scopes, THEN the authorize endpoint SHALL present the consent step before issuing
   any code, and the recorded Consent SHALL enumerate the granted scopes.
4. WHEN an admin deactivates an OIDC_Client, THEN authorize and token requests for that client
   SHALL be rejected and existing refresh capability for it SHALL be revoked.
5. WHERE the existing `Application` model is concerned, the system SHALL NOT modify its schema;
   OIDC_Client SHALL be a new additive model referencing Application.

### Requirement 3 — SSO entreprise entrant (SAML 2.0 et OIDC générique)

**User Story:** En tant qu'organisation cliente, je veux que mes employés se connectent via
notre IdP corporate (Okta, Microsoft Entra), afin de respecter notre politique SSO interne.

#### Acceptance Criteria

1. WHEN `ENTERPRISE_SSO_ENABLED` is False (default), THEN all SSO endpoints SHALL return 404
   `FEATURE_DISABLED`.
2. WHEN an org admin creates an SSO_Connection, THEN it SHALL specify protocol (`saml` or
   `oidc`), one or more email domains, the IdP configuration, and JIT rules; a domain SHALL
   belong to at most one active connection instance-wide.
3. WHEN a user posts an email to `POST /login/sso/`, THEN the system SHALL resolve the domain
   to its SSO_Connection and return the IdP redirect URL, and SHALL return the same
   anti-enumeration response shape whether or not a connection exists for that domain.
4. WHEN a SAML assertion is received on the ACS endpoint, THEN the system SHALL validate
   fail-closed: XML signature against the connection's IdP certificate, audience restriction,
   `InResponseTo` correlation, `NotBefore`/`NotOnOrAfter`, and one-time assertion ID (replay
   rejection). Any failure SHALL reject authentication without partial effects.
5. WHEN the protocol is `oidc`, THEN the connection SHALL use a Generic_OIDC_Provider derived
   from the existing `AbstractOAuthProvider` contract, with issuer discovery and `state`/
   `nonce` validation.
6. WHEN SAML support is not installed, THEN importing tenxyte and using non-SAML features
   SHALL work unchanged, and configuring a `saml` connection SHALL fail with
   `TenxyteMissingDependencyError` naming the `[saml]` extra.

### Requirement 4 — Provisionnement JIT contrôlé

**User Story:** En tant qu'admin d'organisation, je veux décider si les connexions fédérées
peuvent créer des comptes, afin de contrôler l'onboarding.

#### Acceptance Criteria

1. WHEN a federated login succeeds for an unknown email and the connection has
   `jit_enabled=True`, THEN the system SHALL create the user (unusable password), attach the
   org membership with the connection's default role, and log the provisioning event.
2. WHEN `jit_enabled=False` and the user is unknown, THEN authentication SHALL be rejected
   with a non-enumerating error and no user SHALL be created.
3. WHEN the connection has SCIM active, THEN JIT SHALL be treated as disabled for its domains
   regardless of `jit_enabled` (SCIM is the source of truth).
4. WHEN a federated login matches an existing user by verified email, THEN the system SHALL
   link the identity to that user without creating a duplicate.

### Requirement 5 — Serveur SCIM 2.0

**User Story:** En tant qu'IT enterprise, je veux provisionner et déprovisionner les comptes
depuis Okta/Entra via SCIM, afin d'automatiser le cycle de vie des accès.

#### Acceptance Criteria

1. WHEN `SCIM_ENABLED` is False (default), THEN all `/scim/v2/` endpoints SHALL return 404.
2. WHEN a SCIM request carries no valid SCIM_Token, THEN it SHALL be rejected 401; tokens
   SHALL be stored hashed (SHA-256) and scoped to one SSO_Connection.
3. WHEN `POST /scim/v2/Users` creates a user, THEN `externalId` SHALL be persisted as the sync
   key, and a subsequent create with the same `externalId` SHALL return 409 `uniqueness` per
   RFC 7644.
4. WHEN a SCIM PATCH sets `active=false`, THEN the user SHALL be deactivated
   (`is_active=False`, sessions/refresh revoked) and SHALL NOT be physically deleted.
5. WHEN `GET /scim/v2/Users?filter=...` uses the documented subset (`eq` on `userName`,
   `externalId`, `email`; `and` conjunction), THEN results SHALL be correct; unsupported
   filters SHALL return the SCIM error format with 400.
6. WHEN Group operations map to organization roles/memberships, THEN membership changes SHALL
   be reflected in `OrganizationMembership` and be idempotent on replay.
7. WHEN any SCIM operation completes, THEN an audit log entry SHALL record connection,
   operation, target, and outcome; errors SHALL use Protocol_Error_Format (RFC 7644).

### Requirement 6 — Dashboard HITL (produit)

**User Story:** En tant que responsable sécurité, je veux une interface où mes équipes
approuvent ou refusent les actions sensibles des agents IA, afin d'opérationnaliser le HITL
sans développer d'UI maison.

#### Acceptance Criteria

1. WHEN the dashboard is deployed self-host against any AIRS-conformant backend, THEN it SHALL
   list pending actions in near-real-time, allow approve/deny with an optional justification,
   and display the action's context (agent, endpoint, trace ID, expiry).
2. WHERE the dashboard codebase is concerned, it SHALL follow HTTP_Only_Rule: no import of
   tenxyte, exclusively public AIRS API calls (verified by the z_aud_2 style check).
3. WHEN an approval or denial is performed, THEN the dashboard SHALL rely on the backend
   response as the single source of truth and reflect terminal states (confirmed, denied,
   expired) without local mutation.
4. WHEN the dashboard user authenticates, THEN it SHALL use standard Tenxyte auth (JWT) with
   the RBAC permissions already required by the pending-actions API — no privileged bypass.
5. WHEN deployed via the provided Docker image with only a backend URL and credentials, THEN
   the dashboard SHALL be functional without code changes.

### Requirement 7 — Offre commerciale et frontière open-core

**User Story:** En tant que mainteneur, je veux une offre commerciale documentée et honnête,
afin de financer le projet sans trahir la communauté open source.

#### Acceptance Criteria

1. WHEN `docs/en/editions.md` (+ FR) is published, THEN it SHALL define the Open_Core_Boundary:
   the full protocol surface (OP, SSO, SCIM) and the self-host dashboard are open source; the
   managed multi-tenant dashboard, extended retention, and SLA support are commercial.
2. WHERE the OSS repository is concerned, no code path SHALL check a license key or degrade
   functionality based on payment status.
3. WHEN the managed-cloud blueprint is published, THEN it SHALL cover multi-tenant isolation,
   key management, backup/restore, and upgrade strategy at architecture level.
4. WHEN the support policy is published, THEN it SHALL define channels, response targets per
   tier, and the security-report path (consistent with z_aud_1 SECURITY.md).

### Requirement 8 — Sécurité, audit et durcissement des nouvelles surfaces

**User Story:** En tant qu'auditeur, je veux que les surfaces protocolaires ajoutées soient
durcies et traçables, afin que l'ouverture enterprise n'élargisse pas la surface d'attaque.

#### Acceptance Criteria

1. WHEN any OP, SSO, or SCIM security-relevant event occurs (code issued, token exchanged,
   consent granted/revoked, assertion accepted/rejected, SCIM mutation), THEN an audit log
   entry SHALL be written with actor, target, and outcome.
2. WHEN authorize, token, `/login/sso/`, ACS, and SCIM endpoints receive abusive traffic,
   THEN existing throttle families SHALL apply with dedicated scopes and `retry_after`.
3. WHEN secrets are at rest (client secrets, SCIM tokens, SAML IdP certs config), THEN
   secrets SHALL be hashed where verification-only suffices, and never logged; gitleaks rules
   SHALL be extended for the new fixtures.
4. WHEN error responses are produced on protocol endpoints, THEN Protocol_Error_Format SHALL
   apply and SHALL NOT leak internal identifiers; everywhere else the canonical
   `{error, code, details}` format SHALL apply.

### Requirement 9 — Non-régression et architecture additive

**User Story:** En tant que mainteneur, je veux que la phase Enterprise soit invisible pour les
déploiements existants tant qu'elle n'est pas activée, afin de tenir le contrat de stabilité 1.0.

#### Acceptance Criteria

1. WHEN the full existing test suite runs after this phase, THEN it SHALL pass without any
   modification to existing tests.
2. WHEN new migrations are inspected, THEN they SHALL be strictly additive (new tables, new
   nullable/defaulted columns only) and SHALL NOT alter existing tables' semantics.
3. WHEN all Feature_Flags_P4 are at their defaults, THEN the OpenAPI schema of existing
   endpoints SHALL be byte-identical to the pre-phase schema.
4. WHEN the protocol core is inspected, THEN `core/oidc_provider_service.py` SHALL contain no
   Django import, enabling the FastAPI adapter (z_aud_3) to expose the same endpoints.
5. WHEN `pip install tenxyte` (core) or `tenxyte[django]` is performed, THEN no SAML native
   dependency SHALL be pulled; only `tenxyte[saml]` SHALL require xmlsec.
