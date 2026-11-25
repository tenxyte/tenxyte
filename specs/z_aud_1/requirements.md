# Requirements Document

## Introduction

Cette spécification couvre la **Phase 1 « Crédibilité »** de la feuille de route issue de
`AUDIT.md` : l'ensemble des livrables nécessaires au passage de Tenxyte en version **1.0.0**
adoptable en entreprise. Elle regroupe sept chantiers :

1. Un **contrat de stabilité d'API** formel (surface publique définie, politique SemVer,
   politique de dépréciation).
2. L'**inversion des extras de packaging** : `pip install tenxyte` installe le Core seul ;
   la stack Django devient l'extra `tenxyte[django]`. C'est le breaking change assumé de la 1.0.
3. Une **politique de divulgation de vulnérabilités** (`SECURITY.md`, canal privé, SLA, CVE).
4. La **signature et l'attestation des releases** (PyPI Trusted Publishing, attestations PEP 740).
5. **Apple Sign-In** comme cinquième provider social, levant le blocage des applications iOS.
6. La **préparation documentaire de l'audit de sécurité externe** (modèle de menaces, périmètre,
   checklist d'auto-évaluation).
7. L'**ingénierie de release 1.0** (version, classifieurs, CHANGELOG, guide de migration).

Le seul changement de comportement autorisé pour un utilisateur existant est le packaging
(Requirement 2), explicitement documenté et précédé d'un avertissement en 0.9.x. Tout le reste
est additif.

## Glossary

- **Public_API_Surface** : l'ensemble contractuel des éléments couverts par la garantie de
  stabilité : endpoints HTTP documentés dans `endpoints.md`, réglages `TENXYTE_*` documentés dans
  `settings.md`, modèles abstraits publics (`AbstractUser`, `AbstractRole`, `AbstractPermission`,
  `AbstractApplication`), décorateurs publics, symboles exportés par `tenxyte/__init__.py`, et le
  format de réponse d'erreur `{"error", "code", "details"}`.
- **Stability_Contract** : les documents `docs/en/stability.md` et `docs/fr/stability.md`
  définissant la Public_API_Surface, la politique SemVer et la politique de dépréciation.
- **Deprecation_Policy** : la règle imposant qu'aucun élément de la Public_API_Surface ne soit
  retiré sans avoir émis un `DeprecationWarning` pendant au moins une version MINOR complète.
- **Core_Install** : l'installation obtenue par `pip install tenxyte` après la 1.0 — dépendances
  du Core uniquement (PyJWT, bcrypt, pyotp, qrcode, cryptography, Pillow, requests, pydantic,
  email-validator), sans Django ni DRF.
- **Django_Extra** : l'extra `tenxyte[django]` installant la stack Django complète (django,
  djangorestframework, django-cors-headers, drf-spectacular, google-auth, google-auth-oauthlib).
- **Import_Guard** : le mécanisme de chargement paresseux garantissant que `import tenxyte`
  réussit sans Django installé, et que l'accès à un symbole Django-only sans Django lève une
  erreur explicite indiquant `pip install tenxyte[django]`.
- **Security_Policy** : le fichier `SECURITY.md` à la racine du dépôt (versions supportées, canal
  de signalement, SLA, embargo, crédit).
- **Private_Reporting_Channel** : GitHub Private Vulnerability Reporting (Security Advisories) du
  dépôt `tenxyte/tenxyte`.
- **Trusted_Publishing** : le mécanisme OIDC de PyPI permettant à un workflow GitHub Actions
  identifié de publier sans token long-lived.
- **Release_Attestations** : les attestations de provenance PEP 740 (Sigstore) générées et
  publiées avec chaque artefact PyPI.
- **Apple_Provider** : le nouveau provider `AppleOAuthProvider` implémentant `AbstractOAuthProvider`
  pour Sign in with Apple.
- **Apple_Client_Secret** : le JWT signé ES256 (clé privée `.p8`) généré à la volée, servant de
  `client_secret` auprès d'Apple (claims `iss`=Team ID, `sub`=Services ID,
  `aud`=`https://appleid.apple.com`, durée ≤ 6 mois).
- **Apple_ID_Token** : le JWT RS256 émis par Apple contenant l'identité utilisateur, à valider
  contre le JWKS `https://appleid.apple.com/auth/keys` (signature, `iss`, `aud`, `exp`).
- **Private_Relay_Email** : une adresse `@privaterelay.appleid.com` fournie par Apple lorsque
  l'utilisateur masque son email réel.
- **First_Auth_User_Payload** : le champ `user` (JSON) transmis par Apple **uniquement lors de la
  première autorisation**, contenant le nom de l'utilisateur (jamais présent dans l'Apple_ID_Token).
- **Threat_Model_Document** : `docs/security-audit/threat-model.md` — actifs, acteurs, surfaces
  d'attaque, hypothèses de déploiement.
- **Audit_Scope_Document** : `docs/security-audit/audit-scope.md` — périmètre proposé au
  prestataire d'audit externe.
- **Pre_Audit_Checklist** : `docs/security-audit/pre-audit-checklist.md` — auto-évaluation OWASP
  ASVS L2 ciblée.
- **Core** : la couche applicative framework-agnostic existante (`tenxyte.core` / `tenxyte.ports`).
- **Django_Adapter** : la couche d'implémentation existante (`tenxyte.adapters.django`,
  `tenxyte.views`, `tenxyte.serializers`, `tenxyte.services`, `tenxyte.models`).
- **Existing_Public_Contract** : l'ensemble des endpoints, formats de requête/réponse, codes HTTP,
  réglages, migrations et comportements déjà documentés ou couverts par des tests avant cette phase.

## Requirements

### Requirement 1: Contrat de stabilité d'API publique

**User Story:** En tant qu'intégrateur de la librairie, je veux un contrat de stabilité formel et
une politique de dépréciation, afin de pouvoir adopter Tenxyte en production sans craindre des
ruptures silencieuses.

#### Acceptance Criteria

1. THE System SHALL publish a Stability_Contract in both English and French (`docs/en/stability.md`,
   `docs/fr/stability.md`) that enumerates the Public_API_Surface explicitly.
2. THE Stability_Contract SHALL state the SemVer policy: breaking changes to the Public_API_Surface
   only in MAJOR versions; additive changes in MINOR versions; fixes in PATCH versions.
3. THE Stability_Contract SHALL state the Deprecation_Policy: any removal from the
   Public_API_Surface requires a `DeprecationWarning` emitted for at least one full MINOR version
   before removal.
4. THE System SHALL provide an automated test that snapshots the public symbols exported by
   `tenxyte/__init__.py` and fails when a previously exported public symbol disappears.
5. THE Stability_Contract SHALL explicitly list what is NOT covered (private modules prefixed with
   `_`, internal test helpers, undocumented behaviors, the `tenxyte.core` internal layout).

### Requirement 2: Inversion des extras de packaging

**User Story:** En tant que développeur FastAPI ou intégrateur custom, je veux que
`pip install tenxyte` n'installe pas Django, afin d'obtenir une empreinte de dépendances minimale
cohérente avec le positionnement framework-agnostic.

#### Acceptance Criteria

1. WHEN version 1.0.0 is installed via `pip install tenxyte`, THE System SHALL install only the
   Core dependencies (Core_Install) and SHALL NOT install django, djangorestframework,
   django-cors-headers, drf-spectacular, google-auth, or google-auth-oauthlib.
2. WHEN version 1.0.0 is installed via `pip install tenxyte[django]`, THE System SHALL install the
   full Django stack (Django_Extra) with the same packages as today's default install.
3. WHEN `import tenxyte` is executed in an environment without Django, THE Import_Guard SHALL
   allow the import to succeed and SHALL allow access to Core symbols (JWT, TOTP, schemas).
4. WHEN a Django-only symbol (e.g. `tenxyte.setup`, Django models, Django views) is accessed in an
   environment without Django, THE Import_Guard SHALL raise an explicit error whose message
   instructs the user to run `pip install tenxyte[django]`.
5. WHEN version 1.0.0 is installed via `pip install tenxyte[django]` in an existing 0.9.x Django
   project, THE System SHALL behave identically to the previous default install (same endpoints,
   same settings, same migrations), with no code change required beyond the install command.
6. THE System SHALL keep the `[core]` extra as a no-op compatibility alias in 1.0, documented as
   deprecated, and SHALL keep `[fastapi]`, `[postgres]`, `[mysql]`, `[mongodb]`, `[twilio]`,
   `[sendgrid]`, `[webauthn]`, and `[all]` extras functional.
7. THE System SHALL ship a final 0.9.x release that emits a visible `DeprecationWarning` at import
   time announcing the 1.0 packaging change, and SHALL document the change in the README and the
   migration guide before 1.0 is published.
8. THE System SHALL update the migration guide (`docs/en/MIGRATION_GUIDE.md`,
   `docs/fr/MIGRATION_GUIDE.md`) with a dedicated « 0.9 → 1.0 » section covering the install
   command change and the Import_Guard behavior.

### Requirement 3: Politique de divulgation de vulnérabilités

**User Story:** En tant que chercheur en sécurité ou utilisateur en production, je veux un canal de
signalement privé et des engagements de réponse documentés, afin de signaler une vulnérabilité de
manière responsable et de savoir quelles versions sont protégées.

#### Acceptance Criteria

1. THE System SHALL publish a Security_Policy (`SECURITY.md`) at the repository root.
2. THE Security_Policy SHALL define the supported-versions table: 1.0.x fully supported; 0.9.x
   receiving critical fixes only for 6 months after the 1.0 release; older versions unsupported.
3. THE Security_Policy SHALL designate the Private_Reporting_Channel as the only accepted reporting
   channel and SHALL explicitly instruct reporters NOT to open public issues for vulnerabilities.
4. THE Security_Policy SHALL commit to a response SLA: acknowledgment within 72 hours, triage
   within 7 days, and fix targets by severity (critical 14 days, high 30 days, medium/low 90 days).
5. THE Security_Policy SHALL define a coordinated-disclosure embargo of at most 90 days and a
   reporter-credit policy.
6. THE Security_Policy SHALL define the scope: vulnerabilities in Tenxyte code are in scope;
   vulnerabilities exclusively in third-party dependencies are out of scope (to be reported
   upstream) but coordinated pinning fixes are in scope.
7. THE System SHALL document the internal advisory-to-CVE process (GitHub draft advisory → private
   fix → patch release → advisory publication → CVE request via GitHub) in the Security_Policy or a
   linked maintainer document.
8. THE Private_Reporting_Channel SHALL be enabled on the GitHub repository (manual action, verified
   per `manual_tests.md`).

### Requirement 4: Signature et attestation des releases

**User Story:** En tant qu'équipe sécurité d'un adopteur, je veux pouvoir vérifier
cryptographiquement la provenance des artefacts PyPI, afin de me protéger contre une compromission
de la chaîne d'approvisionnement.

#### Acceptance Criteria

1. THE release workflow (`.github/workflows/publish.yml`) SHALL publish to PyPI via
   Trusted_Publishing (OIDC), and SHALL NOT use a long-lived PyPI API token.
2. THE release workflow SHALL generate and upload Release_Attestations (PEP 740) for every
   published artifact.
3. THE release workflow job that publishes SHALL declare `permissions: id-token: write` and SHALL
   run in a protected GitHub environment requiring manual approval.
4. THE System SHALL document the release procedure (tag signing, workflow trigger, attestation
   verification command for consumers) in the contributor/maintainer documentation.
5. WHEN a published artifact is verified with the documented verification command, THE verification
   SHALL succeed and SHALL link the artifact to the `tenxyte/tenxyte` repository and the release
   workflow (manual verification per `manual_tests.md`).

### Requirement 5: Apple Sign-In

**User Story:** En tant qu'éditeur d'application iOS, je veux authentifier mes utilisateurs via
Sign in with Apple, afin de satisfaire l'exigence de l'App Store imposant Apple Sign-In dès qu'un
login social tiers est proposé.

#### Acceptance Criteria

1. THE System SHALL provide an Apple_Provider implementing the existing `AbstractOAuthProvider`
   interface with `provider_name` equal to `"apple"`.
2. THE Apple_Provider SHALL generate the Apple_Client_Secret on the fly by signing an ES256 JWT
   with the configured private key, and SHALL NOT persist any generated client secret.
3. THE Apple_Provider SHALL exchange an authorization code against
   `https://appleid.apple.com/auth/token` using the generated Apple_Client_Secret.
4. THE Apple_Provider SHALL validate every Apple_ID_Token against Apple's JWKS
   (`https://appleid.apple.com/auth/keys`): signature, `iss` equal to `https://appleid.apple.com`,
   `aud` equal to the configured client ID, and expiry.
5. IF Apple_ID_Token validation fails for any reason, THEN THE Apple_Provider SHALL reject the
   authentication without creating or matching any user, and THE System SHALL respond with the
   existing `PROVIDER_AUTH_FAILED` error shape.
6. THE Apple_Provider SHALL return the same normalized user-info dictionary shape as the existing
   providers (`provider_user_id`, `email`, `email_verified`, `first_name`, `last_name`,
   `avatar_url`), sourcing identity from the validated Apple_ID_Token, normalizing Apple's
   string-typed `email_verified` values, and treating a Private_Relay_Email as a valid email.
7. WHEN a First_Auth_User_Payload is provided in the request, THE System SHALL use it to populate
   `first_name` and `last_name`; WHEN it is absent (subsequent logins), THE System SHALL proceed
   with empty name fields without failing.
8. THE System SHALL add the settings `APPLE_CLIENT_ID`, `APPLE_TEAM_ID`, `APPLE_KEY_ID`, and
   `APPLE_PRIVATE_KEY` following the existing provider-settings conventions in `conf/social.py`.
9. THE System SHALL include `"apple"` in the default `SOCIAL_PROVIDERS` list and in the
   `supported_providers` field of the `INVALID_PROVIDER` error response.
10. THE System SHALL route `POST /social/apple/` and `GET /social/apple/callback/` through the
    existing social views without modifying the behavior of the google, github, microsoft, or
    facebook providers.
11. THE System SHALL apply the existing unverified-email fusion refusal (F-03) to Apple
    authentications: an Apple account whose email is not verified SHALL NOT be merged into an
    existing email account.
12. THE System SHALL document the Apple provider in `docs/en/endpoints.md`, `docs/fr/endpoints.md`,
    `docs/en/settings.md`, and `docs/fr/settings.md`, including the `form_post` response-mode note
    and the Private_Relay_Email behavior.

### Requirement 6: Préparation de l'audit de sécurité externe

**User Story:** En tant que mainteneur, je veux fournir au prestataire d'audit un dossier complet
(modèle de menaces, périmètre, auto-évaluation), afin de maximiser la valeur de l'audit et de
réduire son coût.

#### Acceptance Criteria

1. THE System SHALL publish a Threat_Model_Document covering: protected assets, threat actors,
   attack surfaces per domain (JWT lifecycle, OTP flows, WebAuthn, AIRS agent tokens, password
   reset, organizations isolation), and deployment assumptions.
2. THE System SHALL publish an Audit_Scope_Document proposing the audit perimeter (at minimum:
   `core/jwt_service`, `core/totp_service`, `core/webauthn_service`, `services/otp_service`,
   `services/agent_service`, `decorators`, and the login / reset / 2FA flows), the exclusions, and
   the test environment provided to the auditor.
3. THE System SHALL publish a Pre_Audit_Checklist self-assessing the codebase against a targeted
   OWASP ASVS Level 2 subset (sections V2 Authentication, V3 Session Management, V6 Cryptography),
   with a pass / fail / not-applicable status and a code reference for each item.
4. THE three documents SHALL live under `docs/security-audit/` and be linked from the
   Security_Policy.

### Requirement 7: Ingénierie de release 1.0

**User Story:** En tant qu'utilisateur évaluant Tenxyte, je veux une release 1.0 marquée
« Production/Stable » avec un CHANGELOG et un guide de migration, afin de disposer du signal de
maturité attendu pour une adoption sérieuse.

#### Acceptance Criteria

1. THE System SHALL set the package version to `1.0.0` and replace the classifier
   `Development Status :: 4 - Beta` with `Development Status :: 5 - Production/Stable`.
2. THE CHANGELOG SHALL contain a `1.0.0` entry listing: the packaging inversion as a breaking
   change, Apple Sign-In, the Security_Policy, Release_Attestations, and the Stability_Contract.
3. THE README (EN and FR) SHALL be updated to reflect the new install commands
   (`pip install tenxyte[django]` for Django users) prominently in the quickstart.
4. THE migration guide SHALL contain the complete « 0.9 → 1.0 » section (Requirement 2.8).

### Requirement 8: Compatibilité ascendante et respect de l'architecture hexagonale

**User Story:** En tant que mainteneur, je veux que cette phase n'altère aucun comportement runtime
existant en dehors du packaging, afin que la 1.0 soit une consolidation et non une réécriture.

#### Acceptance Criteria

1. THE System SHALL implement every capability of Requirements 1, 3, 4, 5, 6, and 7 as additive
   changes: no existing endpoint, serializer field, response shape, setting default, model field,
   or migration is modified or removed.
2. THE only permitted behavior change for existing users SHALL be the packaging inversion
   (Requirement 2), and only at install time — runtime behavior with the Django stack installed
   SHALL be byte-identical.
3. THE Apple_Provider SHALL be implemented in the Django_Adapter layer (same module as the existing
   providers), and NO Django-specific or provider-specific logic SHALL be introduced into
   `tenxyte.core` or `tenxyte.ports`.
4. THE System SHALL ensure that all automated tests passing before this phase continue to pass
   after it, and SHALL add new automated tests covering Requirements 1 through 7 where automation
   is possible; non-automatable verifications SHALL be recorded in `manual_tests.md`.

## Notes de conception ouvertes

- La stratégie exacte de l'Import_Guard (module `__getattr__` PEP 562 vs try/except à l'import)
  est arrêtée en conception — contrainte : `import tenxyte` sans Django doit réussir ET
  `pip install tenxyte[django]` doit rester à comportement strictement identique à aujourd'hui.
- Apple ne fournissant pas de endpoint userinfo, la sémantique de `get_user_info(access_token)`
  pour l'Apple_Provider est adaptée en conception (l'identité vient de l'id_token) tout en
  respectant la signature de `AbstractOAuthProvider`.
- Le renouvellement du JWKS Apple (cache/TTL) et le comportement en cas d'indisponibilité du JWKS
  sont précisés en conception (fail-closed obligatoire).
- L'ultime release 0.9.x (Requirement 2.7) est un livrable de cette phase mais peut être publiée
  avant le gros de l'implémentation 1.0.
