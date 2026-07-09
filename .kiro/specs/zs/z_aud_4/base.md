# base.md — Phase 4 « Enterprise » : état des lieux et plan brut

## 1. Ce que dit l'audit

`AUDIT.md` §9, Phase 4 (T+8 → T+16 mois) :

> - Mode OIDC Provider, puis SAML/SCIM.
> - Offre commerciale : dashboard HITL managé (les approbations humaines sont une UI
>   naturellement monétisable), support, cloud optionnel.

Écarts correspondants (§8) : 🟡 P2 « Mode OIDC Provider (Tenxyte comme IdP) — ouvrir le
mid-market/SSO, concurrencer Authentik/Zitadel » ; 🟡 P2 « SCIM + SAML entrant — enterprise
readiness B2B » ; 🟢 P3 « Offre commerciale — soutenabilité économique ». Faiblesse F4 :
« Tenxyte authentifie ses utilisateurs mais ne peut pas servir de fournisseur d'identité pour
d'autres applications ».

## 2. État des lieux mesuré dans le code

### 2.1 Ce qui existe et se réutilise directement

- **Clés asymétriques et rotation** : `conf/jwt.py` expose `JWT_ALGORITHM` (défaut HS256),
  `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY` et `JWT_PREVIOUS_PUBLIC_KEY` (« ancienne clé publique
  pour validation pendant la rotation (RS256) »). Le mode OP s'appuie dessus ; il manque
  uniquement la notion de `kid` et la sérialisation JWKS.
- **`Application.redirect_uris`** : `models/application.py:48` (JSONField, migration 0012) avec
  méthode de validation exact-match (`redirect_uri in self.redirect_uris`, lignes 99-101).
  C'est le précédent de conception — mais `OIDCClient` sera un modèle distinct (voir D3).
- **Pile OAuth cliente avec PKCE** : `services/social_auth_service.py` définit
  `AbstractOAuthProvider` (contrat : `provider_name`, `get_user_info(access_token)`,
  `exchange_code(code, redirect_uri, code_verifier)`, dict normalisé documenté) + 4 providers
  concrets + Apple (z_aud_1). L'OIDC entrant générique par connexion en dérive.
- **Organisations** : `models/organization.py` — `Organization`, `OrganizationRole`,
  `OrganizationMembership`, `OrganizationInvitation`, toutes sur bases abstraites
  (extensibles). `SSOConnection` s'y rattache par FK.
- **AIRS/HITL** : `models/agent.py` — `AgentToken` et `AgentPendingAction`
  (table `agent_pending_actions`, FK `agent_token`, related_name `pending_actions`) ; endpoints
  `/ai/pending-actions/` list/confirm/deny existants. Le dashboard consomme cette API telle
  quelle (HTTP-only).
- **Transverses** : format d'erreur `{error, code, details}`, throttling par familles, audit
  log (avec `prompt_trace_id` depuis 0004), multi-tenancy (`tenant.py`, `tenant_context.py`),
  25 migrations (dernière : `0018_user_must_change_password`).

### 2.2 Ce qui n'existe pas (le chantier)

- Aucun endpoint `/.well-known/openid-configuration`, `/oauth/authorize`, `/oauth/token`,
  `/oauth/userinfo`, `/oauth/jwks` — Tenxyte n'est jamais côté serveur du protocole.
- Aucun modèle de client OIDC, de code d'autorisation, de consentement.
- Aucune notion de connexion SSO d'entreprise ni de routage par domaine email.
- Aucune dépendance ni code SAML (xmlsec absent, aucun parseur d'assertion).
- Aucun endpoint SCIM (`/scim/v2/...`), aucun parseur de filtre SCIM, pas d'`externalId`.
- Aucun produit dashboard (l'API HITL existe, l'UI n'existe pas).
- Aucun document d'éditions/open-core/support.

## 3. Plan brut des chantiers

1. **OP-Core** — `core/oidc_provider_service.py` : grants (authorization code + PKCE
   obligatoire pour clients publics), génération/validation des codes (usage unique, TTL
   court, liaison client+redirect_uri+code_challenge), id_token (iss/sub/aud/exp/iat/nonce/
   at_hash), consentement, JWKS (kid = empreinte de clé, publication de la clé précédente
   pendant rotation). Ports storage pour codes et consentements.
2. **OP-Modèles** — `OIDCClient` (FK Application, client_id public, secret hashé, type
   confidentiel/public, redirect_uris, scopes autorisés, `require_consent`),
   `OIDCAuthorizationCode`, `OIDCConsent`. Migration additive 0019+.
3. **OP-Endpoints Django** — discovery, jwks, authorize (session ou redirection login),
   token, userinfo, revocation ; écran de consentement (template + API) ; CRUD admin des
   clients. Gating `OIDC_PROVIDER_ENABLED` (défaut False) + refus de boot en HS256.
4. **SSO entrant** — modèle `SSOConnection` (org FK, protocole, domaines, config JSON,
   `jit_enabled`, rôle par défaut), endpoint de routage `POST /login/sso/` (email → domaine →
   connexion → URL de redirection), `GenericOIDCProvider` (D5), SP SAML dans l'extra `[saml]`
   (metadata SP, ACS, validation fail-closed : signature, audience, InResponseTo,
   NotOnOrAfter, replay). JIT contrôlé par connexion.
5. **SCIM 2.0** — routeur `/scim/v2/` : Users (GET/POST/PUT/PATCH/DELETE), Groups,
   ServiceProviderConfig, Schemas ; auth par bearer token par connexion (hashé SHA-256, comme
   les refresh tokens) ; sous-ensemble de filtres documenté (`eq`, `and`) ; mapping
   `externalId` ↔ User ; deactivate = `is_active=False` (jamais de suppression physique par
   SCIM) ; Groups ↔ OrganizationMembership/rôles.
6. **Dashboard HITL** — package `tenxyte-hitl-dashboard` (monorepo intégrations z_aud_2 ou
   repo dédié) : liste temps réel des pending actions, approve/deny avec justification,
   historique/audit, notifications ; config par URL + credentials AIRS ; HTTP-only vérifié
   par le même test que z_aud_2. Docker image self-host.
7. **Offre commerciale** — `docs/en+fr/editions.md` : frontière open-core (tout le protocole
   et le dashboard self-host = OSS ; managé multi-tenant, rétention, SLA = commercial),
   blueprint de déploiement cloud (`docs/deployment/managed-blueprint.md`), politique de
   support (canaux, délais par tier). Garde-fou technique : aucune fonctionnalité du repo
   OSS ne vérifie de licence (pas de « crippleware »).
8. **Transverse** — audit log sur toutes les nouvelles surfaces (émission de code, tokens OP,
   assertion SAML acceptée/refusée, opérations SCIM), throttling, docs EN/FR, Postman,
   conformité OpenID (MT-2), non-régression.

## 4. Contraintes héritées

- Migrations strictement additives ; modèles existants intouchés (FK uniquement).
- Flags par défaut False → un déploiement existant ne voit aucune différence.
- Format d'erreur canonique partout — SAUF sur les endpoints protocolaires où le standard
  prime (réponses d'erreur OAuth2 `{"error": "invalid_grant", ...}` RFC 6749 §5.2, erreurs
  SCIM RFC 7644 §3.12) : documenter l'exception.
- Cœur protocolaire sans import Django (prêt pour l'adapter FastAPI de z_aud_3).
- L'extra `[saml]` ne doit jamais être requis par l'import de base (Import_Guard z_aud_1).
