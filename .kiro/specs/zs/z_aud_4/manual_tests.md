# Tests Manuels — Phase 4 « Enterprise » (z_aud_4)

> Ce document consigne les procédures de vérification **non automatisables** de la phase —
> essentiellement l'**interopérabilité avec des implémentations réelles** (conformance suite
> OpenID, Okta, Microsoft Entra, Grafana) que les property tests ne peuvent pas remplacer —
> et sert de **registre d'exécution** : chaque procédure doit être déroulée et son résultat
> consigné dans le tableau final avant de cocher la tâche correspondante dans `tasks.md`.

**Convention :** chaque section porte un identifiant `MT-x` référencé depuis `tasks.md`.
Un test manuel est **PASS** uniquement si toutes ses étapes de vérification sont satisfaites.

---

## MT-1 — Tenxyte comme OP pour un RP réel (Grafana)

**Couvre :** Requirements 1.3–1.8, 2.1–2.3 · **Tâches :** 2.1, 3.1–3.3
**Prérequis :** backend Tenxyte avec `OIDC_PROVIDER_ENABLED=True`, clés RS256 configurées,
Grafana (docker) ou tout RP OIDC standard ; un utilisateur de test.

### Procédure

1. Créer un OIDC_Client confidentiel via l'API admin ; noter `client_id` et le secret
   (vérifier qu'il n'est affiché **qu'une seule fois** — le re-GET ne doit pas le montrer).
2. Configurer Grafana en `generic_oauth` : issuer = URL Tenxyte, endpoints depuis
   `/.well-known/openid-configuration` (vérifier que Grafana les découvre seul).
3. Cliquer « Sign in with Tenxyte » : redirection vers Tenxyte, login, **écran de
   consentement** (client avec `require_consent=True`) listant les scopes, puis retour
   Grafana connecté avec nom/email corrects.
4. Se reconnecter : le consentement ne doit **pas** être redemandé (Consent persisté).
5. Contre-épreuves :
   - Modifier la redirect_uri de Grafana d'un caractère → l'authorize doit refuser SANS
     rediriger (page d'erreur, pas de redirection vers l'URI non validée).
   - Désactiver le client via l'API admin → nouvelle tentative refusée.
   - Rejouer manuellement (curl) le dernier `code` capturé → `invalid_grant` au format OAuth2.
6. Décoder l'id_token reçu (jwt.io hors ligne ou script local) : `iss`, `aud`=client_id,
   `nonce` correspondant, signature vérifiable avec `/oauth/jwks/`.

✅ Attendu : login SSO complet sans configuration manuelle d'endpoints, les 3 contre-épreuves
rejetées proprement, id_token vérifiable par le JWKS publié.

---

## MT-2 — Suite de conformité OpenID Foundation (profil Basic OP)

**Couvre :** Requirement 1 (exhaustivité protocolaire) · **Tâches :** 2.1, 3.2
**Prérequis :** instance Tenxyte accessible par la suite (https public ou tunnel),
compte sur https://www.certification.openid.net/.

### Procédure

1. Créer un plan de test « Basic OP » sur la plateforme de certification ; enregistrer les
   deux clients de test demandés (confidentiel + public/PKCE) via l'API admin.
2. Dérouler la totalité du plan. Pour chaque test : consigner PASS/FAIL/WARNING.
3. Pour chaque FAIL : ouvrir une issue avec l'identifiant du test de la suite, la trace, et
   la classer (bug à corriger avant sortie de phase / limitation assumée à documenter).
4. Re-dérouler après corrections jusqu'à stabilisation.

✅ Attendu : zéro FAIL non tracé. La communication publique n'emploie « certifiable » que si
le plan passe intégralement ; sinon, la page de doc liste explicitement les écarts.
**Aucun résultat de cette suite ne se devine : ce test est le juge de paix du rôle OP.**

---

## MT-3 — SSO SAML entrant de bout en bout avec Okta

**Couvre :** Requirements 3.2–3.4, 4.1–4.4 · **Tâches :** 5.1, 5.2, 6.2, 6.3
**Prérequis :** tenant Okta Developer (gratuit), Tenxyte avec `ENTERPRISE_SSO_ENABLED=True` +
extra `[saml]` installé, une Organization de test avec domaine dédié (ex. `acme-test.example`).

### Procédure

1. Créer l'app SAML dans Okta ; récupérer les metadata SP de Tenxyte
   (`/sso/<connection>/metadata/`) et vérifier qu'Okta les importe sans édition manuelle.
2. Créer la SSOConnection (protocol=saml, domaine, certificat IdP Okta, `jit_enabled=True`,
   default_role).
3. `POST /login/sso/` avec `user@acme-test.example` → URL de redirection Okta ; dérouler le
   login Okta → retour ACS → session Tenxyte ouverte.
4. Vérifier le JIT : l'utilisateur inconnu a été créé (mot de passe inutilisable), membre de
   l'organisation avec le default_role ; événement d'audit présent.
5. Contre-épreuves :
   - `POST /login/sso/` avec un domaine sans connexion → **même forme de réponse**
     (anti-énumération, comparer les JSON côte à côte).
   - Passer `jit_enabled=False`, tenter un login avec un nouvel utilisateur Okta → rejet
     générique, vérifier en base qu'AUCUN utilisateur n'a été créé.
   - Rejouer la dernière SAMLResponse capturée (replay) → rejet.
   - Soumettre la SAMLResponse avec un caractère altéré dans la signature → rejet + entrée
     d'audit détaillée, réponse utilisateur générique.

✅ Attendu : cycle complet fonctionnel, JIT gouverné, les 4 contre-épreuves rejetées sans
effet partiel.

---

## MT-4 — SSO entrant avec Microsoft Entra (SAML puis OIDC générique)

**Couvre :** Requirements 3.4, 3.5, 4.4 · **Tâches :** 6.1, 6.2
**Prérequis :** tenant Entra ID (essai gratuit), deux SSOConnections de test (une saml, une
oidc) sur deux domaines distincts.

### Procédure

1. **Volet SAML** : rejouer le scénario MT-3 étapes 1–4 avec Entra (Enterprise Application
   SAML). Point d'attention connu : format du NameID et claims mapping — documenter la
   configuration exacte qui fonctionne dans `enterprise_sso.md` (le guide doit permettre à
   un client de réussir du premier coup).
2. **Volet OIDC générique** : créer une App Registration Entra ; configurer la connexion
   `protocol=oidc` avec le seul issuer (`https://login.microsoftonline.com/<tenant>/v2.0`) —
   vérifier que la **discovery** remplit les endpoints seule. Dérouler le login complet.
3. Vérifier la liaison de compte (Req 4.4) : créer d'abord un utilisateur Tenxyte local avec
   l'email Entra vérifié, puis se connecter via Entra → l'identité doit se **lier** au compte
   existant (vérifier en base : un seul utilisateur, pas de doublon).
4. Vérifier `state`/`nonce` : intercepter la redirection (proxy/dev tools), altérer `state`
   au retour → rejet.

✅ Attendu : les deux protocoles fonctionnels contre Entra, liaison sans doublon, altération
de state rejetée, guides de configuration validés « premier coup ».

---

## MT-5 — Provisionnement SCIM depuis Okta

**Couvre :** Requirement 5 (intégral) · **Tâches :** 8.1–8.3
**Prérequis :** tenant Okta avec provisioning SCIM, connexion MT-3 avec `scim_enabled=True`,
SCIM_Token généré.

### Procédure

1. Configurer le provisioning SCIM dans Okta (Base URL `/scim/v2/`, bearer = SCIM_Token) ;
   lancer le « Test Connector Configuration » d'Okta → doit passer (ServiceProviderConfig).
2. Assigner 3 utilisateurs à l'app dans Okta → vérifier leur création côté Tenxyte
   (externalId persisté, membres de l'organisation).
3. Modifier le prénom d'un utilisateur dans Okta → la mise à jour se propage (PUT/PATCH).
4. Désassigner un utilisateur → vérifier `is_active=False` côté Tenxyte, sessions/refresh
   révoqués (tenter un refresh avec son ancien token → rejet), et **présence toujours en
   base** (pas de suppression physique).
5. Push Groups : pousser un groupe Okta → vérifier le mapping rôle/membership ; re-pousser le
   même groupe (rejeu) → aucun doublon (idempotence).
6. Contre-épreuves :
   - Appel SCIM avec un token invalide ou celui d'une AUTRE connexion → 401.
   - Vérifier que le JIT est bien inhibé : `jit_enabled=True` + `scim_enabled=True`, login
     SAML d'un utilisateur non provisionné → rejet sans création (précédence SCIM).
7. Vérifier l'audit log : chaque mutation SCIM y figure (connexion, opération, cible, issue).

✅ Attendu : cycle de vie complet piloté par Okta, désactivation non destructive, précédence
SCIM>JIT effective, audit exhaustif.

---

## MT-6 — Dashboard HITL : cycle réel approve/deny

**Couvre :** Requirement 6 (intégral) · **Tâches :** 11.1, 11.2
**Prérequis :** image Docker du dashboard, backend Tenxyte AIRS activé, un AgentToken de test
générant des actions HITL (script de seed ou agent LangChain z_aud_2).

### Procédure

1. Démarrer le dashboard avec pour SEULE configuration l'URL backend + credentials → il doit
   être fonctionnel sans modification de code (Req 6.5).
2. Se connecter avec un compte SANS la permission pending-actions → l'accès aux actions doit
   être refusé (pas de bypass, Req 6.4). Se reconnecter avec un compte autorisé.
3. Déclencher 3 actions sensibles via l'agent de test → elles apparaissent dans la liste en
   quasi temps réel avec agent, endpoint, trace ID (`X-Prompt-Trace-ID`), expiration.
4. **Approuver** la première (avec justification) → l'agent voit sa requête aboutir au rejeu ;
   l'état terminal `confirmed` s'affiche.
5. **Refuser** la deuxième → rejeu de l'agent rejeté ; état `denied`.
6. Laisser **expirer** la troisième → état `expired` affiché tel que rapporté par le backend
   (aucune mutation locale : couper le réseau du dashboard 30 s, le rouvrir, l'état doit se
   resynchroniser depuis le backend).
7. Vérifier l'historique/audit du dashboard et la présence de la justification.
8. Vérifier la HTTP_Only_Rule : le check automatisé z_aud_2 passe sur le code du dashboard
   (lancer le job, consigner le lien).

✅ Attendu : les trois états terminaux fidèles au backend, RBAC respecté, déploiement
« URL + credentials » suffisant.

---

## MT-7 — Revue documentaire des trois rôles

**Couvre :** guides oidc_provider / enterprise_sso / scim, endpoints.md, settings.md
**Tâches :** 12.1, 12.2

### Procédure

1. **Guide OP** : une personne n'ayant pas participé au chantier configure un RP (au choix)
   en suivant uniquement `oidc_provider.md` → succès sans aide extérieure.
2. **Guide SSO** : relire les pas-à-pas Okta et Entra en les confrontant aux captures/notes
   de MT-3 et MT-4 (chaque écart UI des consoles IdP corrigé dans la doc).
3. **Guide SCIM** : vérifier que le sous-ensemble de filtres supporté et la précédence
   SCIM>JIT sont énoncés sans ambiguïté.
4. Synchronisation EN/FR section par section ; `validate_endpoints.py` vert sur les deux
   langues (Windows : `set PYTHONIOENCODING=utf-8`).
5. Collection Postman : dérouler les nouveaux dossiers (OP, SSO, SCIM) contre une instance
   de test.

✅ Attendu : docs auto-suffisantes validées par des tiers, parité EN/FR, validation CI verte.

---

## MT-8 — Revue de l'offre commerciale (éditions, blueprint, support)

**Couvre :** Requirement 7 (intégral) · **Tâches :** 10.1, 10.2

### Procédure

1. Relire `editions.md` avec la question-filtre : « un utilisateur OSS peut-il se sentir
   floué par cette frontière ? » — chaque capacité doit être explicitement classée OSS ou
   commercial, sans zone grise.
2. Vérifier le garde-fou anti-crippleware : le check CI (motifs license_key/entitlement dans
   `src/`) passe ; revue manuelle par sondage de 5 modules ajoutés en phase 4.
3. Relire le blueprint cloud managé avec un œil d'ops : isolation multi-tenant, gestion de
   clés (rotation RS256 !), backup/restore, upgrade — chaque section doit être actionnable.
4. Vérifier la politique de support : canaux, délais par tier, chemin de signalement sécurité
   cohérent avec `SECURITY.md` (z_aud_1).
5. Approbation finale du mainteneur consignée (date + décision) — c'est un engagement public,
   pas un document technique.

✅ Attendu : frontière open-core nette et défendable publiquement, zéro license-check dans
l'OSS, blueprint actionnable, approbation mainteneur enregistrée.

---

## Registre d'exécution

> À compléter à chaque exécution. Une ligne par run (garder l'historique en cas de re-run).

| ID | Intitulé | Date | Exécutant | Environnement | Résultat | Notes / lien preuve |
|----|----------|------|-----------|---------------|----------|---------------------|
| MT-1 | OP avec RP réel (Grafana) | — | — | — | ⬜ À exécuter | |
| MT-2 | Conformance OpenID Foundation (Basic OP) | — | — | — | ⬜ À exécuter | lien plan : — |
| MT-3 | SAML E2E Okta + contre-épreuves | — | — | — | ⬜ À exécuter | |
| MT-4 | Entra SAML + OIDC générique + liaison | — | — | — | ⬜ À exécuter | |
| MT-5 | SCIM Okta (cycle de vie + groupes) | — | — | — | ⬜ À exécuter | |
| MT-6 | Dashboard HITL (3 états terminaux) | — | — | — | ⬜ À exécuter | versions : — |
| MT-7 | Revue documentaire trois rôles | — | — | — | ⬜ À exécuter | |
| MT-8 | Revue offre commerciale | — | — | — | ⬜ À exécuter | approbation : — |

**Légende résultat :** ✅ PASS · ❌ FAIL (ouvrir une issue, référencer ici) · ⚠️ PASS avec réserve
(documenter la réserve) · ⬜ À exécuter

## Critère de sortie de la phase

La phase est validée lorsque : toutes les lignes du registre sont ✅ (ou ⚠️ avec réserve
acceptée par le mainteneur — pour MT-2, les écarts de conformance restants sont tracés en
issues ET documentés publiquement), toutes les gates CI sont vertes (snapshot OpenAPI
byte-identique flags éteints, jobs avec/sans `[saml]`, check anti-crippleware, HTTP_Only_Rule
du dashboard), les 14 propriétés sont couvertes, la suite existante passe sans modification,
et le checkpoint final de `tasks.md` est coché. Toute communication « enterprise-ready » ou
« certifiable OIDC » n'intervient qu'après.
