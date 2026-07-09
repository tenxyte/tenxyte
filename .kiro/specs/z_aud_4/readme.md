# z_aud_4 — Phase 4 « Enterprise » (T+8 → T+16 mois)

> Source : `AUDIT.md` §9 (feuille de route, Phase 4) et §8 (écarts 🟡 P2 « Mode OIDC Provider »,
> 🟡 P2 « SCIM + SAML entrant », 🟢 P3 « Offre commerciale »).
> Prérequis : z_aud_1 (crédibilité, release 1.0), z_aud_2 (AIRS ouvert), z_aud_3 (multi-framework).

## Le problème que cette phase résout

Tenxyte sait authentifier **ses** utilisateurs, mais reste invisible du mid-market et de
l'enterprise pour trois raisons mesurées dans l'audit (F4) :

1. **Pas de rôle fournisseur d'identité.** Une entreprise qui adopte Tenxyte ne peut pas s'en
   servir comme SSO pour ses autres applications (Grafana, outils internes, SaaS tiers).
   Authentik, Zitadel et Keycloak gagnent ces déploiements par défaut.
2. **Pas de fédération entrante enterprise.** Un client B2B dont les employés vivent dans
   Okta ou Microsoft Entra ne peut ni se connecter via son IdP corporate (SAML), ni
   provisionner/déprovisionner ses comptes automatiquement (SCIM). C'est un critère
   éliminatoire dans la quasi-totalité des appels d'offres B2B.
3. **Pas de modèle économique.** Le projet n'a aucune source de revenus pour financer audits,
   maintenance et support — l'audit identifie le **dashboard HITL** (approbations humaines des
   actions d'agents IA) comme l'UI naturellement monétisable, unique au marché.

## Ce que la phase livre

| # | Livrable | Nature |
|---|----------|--------|
| 1 | **Mode OIDC Provider** : Tenxyte devient un OP — discovery, JWKS, authorization code + PKCE, token, userinfo, consentement, gestion de clients | Code (Core + adapters) |
| 2 | **SSO entreprise entrant** : connexions SAML 2.0 (SP) et OIDC générique **par organisation**, routage par domaine email, provisionnement JIT contrôlé | Code (extra `[saml]`) |
| 3 | **Serveur SCIM 2.0** : /Users et /Groups entrants (Okta, Entra), tokens par connexion, synchronisation avec les organisations | Code |
| 4 | **Dashboard HITL** : produit web self-hostable consommant uniquement les API AIRS publiques — socle de l'offre managée | Produit (package séparé) |
| 5 | **Offre commerciale** : frontière open-core documentée, éditions, blueprint cloud managé multi-tenant, politique de support | Docs + garde-fous techniques |

## Décisions structurantes

- **D1 — RS256 obligatoire en mode OP.** Le mode OIDC Provider refuse de démarrer en HS256
  (clé symétrique impubliable en JWKS). L'infrastructure RS256 + rotation
  (`JWT_PREVIOUS_PUBLIC_KEY`) existe déjà ; on ajoute le `kid` et la publication JWKS.
- **D2 — Cœur protocolaire dans le Core.** La logique OIDC Provider (grants, PKCE, id_token,
  consentement) vit dans `tenxyte/core/oidc_provider_service.py`, framework-agnostic — les
  adapters Django et FastAPI (z_aud_3) n'exposent que les endpoints.
- **D3 — `OIDCClient` est un nouveau modèle, `Application` reste intact.** Un client OIDC
  référence une `Application` (FK) mais porte ses propres redirect URIs (exact-match), type
  (confidentiel/public) et secret hashé. Zéro modification du modèle existant.
- **D4 — SSO entrant par organisation, SAML en extra optionnel.** `SSOConnection` (protocole
  `saml`|`oidc`, domaines email, config, règles JIT) attachée à une `Organization`. La
  dépendance native xmlsec est isolée dans l'extra `tenxyte[saml]` — l'install par défaut
  reste légère (cohérent avec le packaging z_aud_1).
- **D5 — L'OIDC entrant générique réutilise `AbstractOAuthProvider`.** Le contrat existant
  (`exchange_code(code, redirect_uri, code_verifier)`, dict normalisé) devient un
  `GenericOIDCProvider` configuré par connexion — pas de deuxième pile OAuth cliente.
- **D6 — SCIM prime sur JIT.** Quand une connexion a SCIM actif, le JIT est désactivé pour ses
  domaines : la source de vérité des comptes est l'IdP. `externalId` porte le mapping.
- **D7 — Le dashboard HITL est HTTP-only et open-core.** Package séparé (`tenxyte-hitl-dashboard`)
  soumis à la même règle que les connecteurs z_aud_2 : interdiction d'importer `tenxyte`,
  consommation exclusive des API publiques AIRS. Le dashboard self-host est open source ; la
  version managée multi-tenant (+ SSO du dashboard lui-même, rétention étendue, SLA) est
  l'offre commerciale.
- **D8 — La certification se prouve.** Objectif : passer la suite de conformité de
  l'OpenID Foundation (profil Basic OP) — exécutée manuellement (MT-2), avec les blocages
  éventuels consignés comme issues avant toute communication « certifiable ».

## Fondations déjà en place (mesurées dans le code)

| Fondation | Localisation | Réutilisation |
|---|---|---|
| RS256 + rotation de clés | `conf/jwt.py` (`JWT_PRIVATE_KEY`, `JWT_PREVIOUS_PUBLIC_KEY`) | JWKS, signature id_token |
| `Application.redirect_uris` + validation | `models/application.py` (migration 0012) | Précédent de conception pour `OIDCClient` |
| `AbstractOAuthProvider` (PKCE inclus) | `services/social_auth_service.py` | OIDC entrant générique |
| Organisations (bases abstraites) | `models/organization.py` | Rattachement des `SSOConnection` |
| `AgentPendingAction` + endpoints HITL | `models/agent.py`, API `/ai/pending-actions` | Source de données du dashboard |
| Format d'erreur canonique, throttling, audit log | transverses | Toutes les nouvelles surfaces |

## Definition of Done de la phase

1. Un RP réel (Grafana ou équivalent) s'authentifie contre Tenxyte en OIDC (MT-1).
2. La suite de conformité OpenID Foundation (Basic OP) passe ou ses écarts sont tracés (MT-2).
3. SSO SAML de bout en bout avec Okta **et** Microsoft Entra (MT-3, MT-4).
4. Provisionnement SCIM depuis Okta : create/update/deactivate + groupes (MT-5).
5. Dashboard HITL : cycle réel approve/deny d'actions d'agents en attente (MT-6).
6. Les 14 propriétés de correction sont couvertes par des property tests (≥ 100 exemples).
7. Tous les flags (`OIDC_PROVIDER_ENABLED`, `ENTERPRISE_SSO_ENABLED`, `SCIM_ENABLED`)
   désactivés par défaut → **zéro changement de comportement** pour l'existant.
8. Migrations strictement additives ; suite existante verte sans modification.
9. Docs EN/FR (oidc_provider, enterprise_sso, scim, éditions/open-core) + `validate_endpoints.py` vert.
10. Le document d'offre commerciale (éditions, frontière open-core, blueprint cloud, support)
    est relu et approuvé par le mainteneur (MT-8).

## Fichiers de la spec

| Fichier | Rôle |
|---|---|
| `base.md` | État des lieux du code + plan brut des chantiers |
| `requirements.md` | 9 requirements EARS + glossaire |
| `design.md` | Architecture, décisions justifiées, 14 Correctness Properties, erreurs, stratégie de test |
| `tasks.md` | Plan d'implémentation en vagues + Task Dependency Graph |
| `manual_tests.md` | MT-1 → MT-8 + registre d'exécution + critère de sortie |
