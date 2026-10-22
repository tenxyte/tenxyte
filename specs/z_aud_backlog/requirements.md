# Requirements Document — z_aud_backlog

## Introduction

Spec de complétion fermant les 4 écarts résiduels de la couverture d'`AUDIT.md` : extension
des providers sociaux (F8), des backends SMS (F10), du programme de divulgation (bug bounty
léger, §8 P0) et de la DX résiduelle (§4.3). Tout est additif : aucun modèle, aucune
migration, aucune dépendance par défaut.

## Glossaire

| Terme | Définition |
|---|---|
| **Provider_Contract** | Contrat d'`AbstractOAuthProvider` : `provider_name`, `exchange_code(code, redirect_uri, code_verifier)`, `get_user_info(access_token)` → dict normalisé documenté |
| **Normalized_Dict** | `{provider_user_id, email, email_verified, first_name, last_name, avatar_url}` |
| **New_Providers** | GitLab, LinkedIn, Slack, Discord, X (Twitter), Bitbucket |
| **OIDC_Providers** | Sous-ensemble OIDC-compliant des New_Providers : GitLab, LinkedIn, Slack |
| **SMS_Backend_Template** | Gabarit `TwilioBackend` : `BaseSMSBackend`, import paresseux, extra dédié, settings dédiés, numéro masqué en logs, échec loggé sans exception dans le flux OTP |
| **New_SMS_Backends** | `VonageBackend`, `SNSBackend` (AWS), `MessageBirdBackend` |
| **VDP** | Vulnerability Disclosure Program : périmètre in/out, safe harbor, reconnaissance — extension de SECURITY.md (z_aud_1) |
| **Hall_of_Fame** | Page publique de reconnaissance des rapporteurs (`docs/security/hall-of-fame.md`) |
| **UTF8_Self_Reconfigure** | Les scripts de validation forcent eux-mêmes stdout/stderr en UTF-8, sans variable d'environnement requise |

## Requirements

### Requirement 1 — Six providers sociaux supplémentaires

**User Story:** En tant qu'intégrateur, je veux proposer les logins sociaux attendus par mon
public (dev, B2B, communautés), afin de ne pas perdre d'utilisateurs à l'inscription.

#### Acceptance Criteria

1. WHEN each of the New_Providers is configured, THEN it SHALL implement the
   Provider_Contract and return a correct Normalized_Dict, registered under its
   `provider_name` in the existing provider registry.
2. WHEN an OIDC_Provider validates an identity, THEN it SHALL reuse the existing OIDC
   validation helpers (state/nonce/JWKS from the Apple flow, or GenericOIDCProvider when
   z_aud_4 is available) rather than reimplementing validation.
3. WHEN the X (Twitter) provider is used, THEN PKCE (S256) SHALL be mandatory per the
   platform's OAuth2 requirements.
4. WHEN a provider returns no verified email (Discord unverified, X without email scope),
   THEN the existing account-linking rules SHALL apply unchanged: no linking on unverified
   email, no duplicate accounts, anti-enumeration response shapes preserved.
5. WHEN the existing social endpoints (`/social/<provider>/`, callback) serve the
   New_Providers, THEN no endpoint signature or existing response shape SHALL change, and
   the five existing providers SHALL be unmodified.
6. WHEN provider settings are absent, THEN the provider SHALL be inactive with the existing
   explicit configuration error pattern; each provider SHALL have `TENXYTE_<PROVIDER>_*`
   settings documented EN/FR.

### Requirement 2 — Trois backends SMS supplémentaires

**User Story:** En tant qu'intégrateur, je veux choisir mon fournisseur SMS (Vonage, AWS SNS,
MessageBird), afin de ne pas être contraint à Twilio.

#### Acceptance Criteria

1. WHEN each of the New_SMS_Backends is implemented, THEN it SHALL follow the
   SMS_Backend_Template exactly: lazy import, dedicated settings, masked phone number in
   logs, failures logged without raising into the OTP flow.
2. WHEN `pip install tenxyte` (or `[django]`) is performed, THEN no new dependency SHALL be
   pulled; `SNSBackend` SHALL require the `[sns]` extra (boto3); Vonage and MessageBird
   SHALL use plain HTTP via the existing `requests` dependency with explicit timeouts.
3. WHEN a backend's credentials are missing, THEN it SHALL log the explicit
   settings-naming error at init (Twilio pattern) and never crash the caller.
4. WHEN the SMS backend selection setting points to a new backend, THEN OTP login,
   phone verification and 2FA SMS flows SHALL work unchanged (backend-agnostic).
5. WHEN any SMS backend logs, THEN no message body and no full phone number SHALL appear.

### Requirement 3 — Bug bounty léger (VDP)

**User Story:** En tant que chercheur en sécurité, je veux un cadre clair et sûr pour tester
et signaler, afin de contribuer sans risque juridique ; en tant que mainteneur, je veux
canaliser ces signalements sans infrastructure payante.

#### Acceptance Criteria

1. WHEN SECURITY.md is extended, THEN it SHALL define the VDP: in-scope (the package,
   z_aud_2 connectors), out-of-scope (demo instances, volumetric DoS, social engineering),
   safe harbor statement, and response commitments reusing the z_aud_1 SLA.
2. WHEN a valid report is resolved, THEN the reporter SHALL be credited in the Hall_of_Fame
   (opt-out possible) with discretionary non-monetary recognition; no monetary bounty
   platform SHALL be introduced in this phase.
3. WHEN a report arrives, THEN the documented maintainer triage process (severity grid,
   advisory/CVE path from z_aud_1) SHALL apply.
4. WHEN the VDP is published, THEN a blind-test submission SHALL have validated the full
   path end-to-end (MT-3) before public announcement.

### Requirement 4 — DX résiduelle

**User Story:** En tant que contributeur sous Windows, je veux que les scripts du projet
fonctionnent sans incantation d'environnement, afin que l'onboarding (z_aud_5 MT-5) ne
bute pas sur l'outillage.

#### Acceptance Criteria

1. WHEN validation scripts run on a Windows cp1252 console, THEN they SHALL succeed without
   any environment variable, via UTF8_Self_Reconfigure applied at script start.
2. WHEN documentation examples are audited, THEN no published example SHALL contain
   redaction artifacts (e.g. "secrets redacted"); secrets SHALL appear as explicit
   placeholders (`<YOUR_API_KEY>`), and `validate_endpoints.py` SHALL pass on both languages.
3. WHEN CONTRIBUTING.md mentions script usage, THEN the `PYTHONIOENCODING` workaround SHALL
   be removed as obsolete.

### Requirement 5 — Non-régression

**User Story:** En tant que mainteneur, je veux que cette spec de complétion soit purement
additive, afin de pouvoir l'exécuter en parallèle des phases sans risque.

#### Acceptance Criteria

1. WHEN the full existing test suite runs, THEN it SHALL pass without modification; no
   migration SHALL be added; no existing provider, backend, endpoint or response shape
   SHALL change.
2. WHEN the OpenAPI schema is compared, THEN existing endpoints SHALL be unchanged (new
   providers appear only as new values of the existing `<provider>` path parameter).
3. WHEN gitleaks runs, THEN new provider/SMS test fixtures SHALL pass via allowlist entries,
   never via real-looking secrets.
