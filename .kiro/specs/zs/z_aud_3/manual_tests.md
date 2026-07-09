# Tests Manuels — Phase 3 « Multi-framework réel » (z_aud_3)

> Ce document consigne les procédures de vérification **non automatisables** de la phase, et sert
> de **registre d'exécution** : chaque procédure doit être déroulée et son résultat consigné dans
> le tableau final avant de cocher la tâche correspondante dans `tasks.md`.

**Convention :** chaque section porte un identifiant `MT-x` référencé depuis `tasks.md`.
Un test manuel est **PASS** uniquement si toutes ses étapes de vérification sont satisfaites.

---

## MT-1 — Quickstart FastAPI chronométré (« 5 minutes au premier appel »)

**Couvre :** Requirements 3.1, 3.2, 3.3, 7.1 · **Tâches :** 2.1, 2.2, 16.1
**Prérequis :** machine vierge du projet (ou venv neuf), Python 3.10+, chronomètre.
**Règle d'or :** suivre `docs/en/fastapi_quickstart.md` **mot à mot, sans aucune connaissance
externe** — le test valide la doc autant que le code.

### Procédure

1. Démarrer le chronomètre. Dérouler le quickstart tel qu'écrit :
   ```bash
   python -m venv /tmp/vx-fapi && source /tmp/vx-fapi/bin/activate
   pip install "tenxyte[fastapi]"          # SANS Django — vérifier: pip freeze | grep -i django → vide
   # créer main.py selon la doc (create_tenxyte_app)
   uvicorn main:app --reload
   ```
2. Premier cycle API selon la doc (credentials d'application inclus) :
   ```bash
   curl -X POST .../register/  -H "X-Access-Key: ..." -d '{...}'
   curl -X POST .../login/email/ ...
   curl .../me/ -H "Authorization: Bearer <access_token>"
   ```
3. Arrêter le chronomètre au premier `GET /me/` réussi.
4. Vérifier : Swagger accessible (`/docs`), erreurs au format `{error, code, details}` (tester un
   login faux), aucun `NotImplementedError` rencontré.

✅ Attendu : cycle complet ≤ **5 minutes** sans sortir de la doc ; Django absent de
l'environnement ; toute étape ambiguë de la doc = FAIL de la doc (corriger puis re-tester).

---

## MT-2 — Parcours Postman croisés (parité vécue)

**Couvre :** Requirements 4.2, 4.3, 4.4 · **Tâches :** 5.1–12.2
**Prérequis :** la collection Postman du repo ; deux backends up en parallèle — Django
(`:8000`) et FastAPI (`:8001`) — chacun avec un seed identique (application + admin).

### Procédure

1. Configurer deux environnements Postman (`django`, `fastapi`) ne différant que par `base_url`.
2. Dérouler la collection complète sur `django`, puis sur `fastapi`. Pour chaque requête,
   comparer côte à côte : statut, clés de réponse, codes d'erreur.
3. Scénarios de flux transverses à rejouer explicitement sur **fastapi** :
   | # | Scénario | Attendu (identique à Django) |
   |---|---|---|
   | 2.1 | Register d'un email déjà pris | 201 anti-énumération, forme identique au succès |
   | 2.2 | Login admin sans 2FA | token `2fa_setup_only`, `requires_2fa_setup: true` |
   | 2.3 | Compte `must_change_password=true` | token `password_change_only`, 403 `INSUFFICIENT_SCOPE` sur `/2fa/status/`, upgrade full-scope après `/password/change/` |
   | 2.4 | Login OTP feature OFF | 404 `FEATURE_DISABLED` |
   | 2.5 | 5 logins échoués | 423 `ACCOUNT_LOCKED` + `retry_after` |
   | 2.6 | Throttle reset password | 429 avec `retry_after` |
   | 2.7 | Cycle AIRS (token → AgentBearer → HITL 202 → confirm → rejeu) | conforme au contrat |
4. Consigner toute divergence (endpoint, champ, code) — chaque divergence = issue de parité.

✅ Attendu : zéro divergence de contrat sur l'ensemble de la collection et des 7 scénarios.

---

## MT-3 — Tenue en charge async (non-blocage réel)

**Couvre :** Requirements 3.2, 5.4 · **Tâches :** 2.2, 3.3
**Prérequis :** backend FastAPI (Reference_Stack, asyncpg recommandé), outil de charge
(`hey`, `wrk` ou `locust`), un worker uvicorn UNIQUE (pour rendre tout blocage visible).

### Procédure

1. `uvicorn main:app --workers 1`.
2. Charge mixte 2 minutes : 50 connexions concurrentes sur `GET /me/` (JWT valide) + 10/s sur
   `POST /login/email/` + 5/s sur un endpoint AIRS AgentBearer.
3. Pendant la charge, sonde manuelle : `curl` sur `/docs` et sur la découverte AIRS toutes les
   ~5 s — les réponses doivent rester < 1 s (un event loop bloqué se manifeste ici).
4. Relever p95/p99 et erreurs ; vérifier l'absence de timeouts en cascade.
5. Contre-épreuve : introduire volontairement un `time.sleep(2)` dans un handler local, vérifier
   (a) que la sonde manuelle dégénère — preuve que le protocole de test détecte bien le blocage —
   et (b) que `scripts/check_async_purity.py` refuse ce code. Retirer la modification.

✅ Attendu : sonde stable sous charge, zéro erreur 5xx, contre-épreuve concluante dans les deux
directions.

---

## MT-4 — Reference_Stack sur PostgreSQL (asyncpg) et migrations Alembic

**Couvre :** Requirements 3.2 · **Tâche :** 2.2
**Prérequis :** PostgreSQL (docker), `pip install asyncpg`.

### Procédure

1. `TENXYTE_DATABASE_URL=postgresql+asyncpg://...` ; lancer les migrations Alembic depuis zéro
   (`alembic upgrade head`) — vérifier zéro erreur et le schéma attendu.
2. Rejouer le cycle MT-1 étapes 2–4 sur ce backend.
3. `alembic downgrade -1 && alembic upgrade head` — vérifier la réversibilité de la dernière
   migration.
4. Vérifier en base : mots de passe bcrypt (préfixe `$2b$`), tokens refresh hashés (aucune
   valeur brute), secret TOTP chiffré après un setup 2FA.

✅ Attendu : parité d'invariants de sécurité avec le stack Django, migrations propres A/R.

---

## MT-5 — `@tenxyte/ui-headless` dans une app React neuve

**Couvre :** Requirements 6.1, 6.2, 6.3 · **Tâche :** 15.1
**Prérequis :** backend démo (`examples/js-contract-backend/`) up ; Node 20+ ; packages headless
publiés (TestNpm/npm ou `npm pack` local).

### Procédure

1. `npm create vite@latest mt5-app -- --template react-ts && npm i @tenxyte/ui-headless @tenxyte/core`.
2. Monter `<SignIn.Root>` selon le README du package, pointé sur le backend démo. Vérifier :
   - Aucun style injecté (inspecteur : pas de feuille CSS du package, pas de style inline).
   - Le flux complet : erreur `LOGIN_FAILED` affichable, compte 2FA → état `twoFactorRequired`,
     compte `must_change_password` → état `passwordChangeRequired` enchaînant sur
     `<ForcedPasswordChange>`.
3. Monter `OTPInput`, `TwoFactorSetup` (scan QR réel avec une app TOTP), `PasskeyButton`
   (navigateur supportant WebAuthn — passkey de plateforme ou clé), `SignUp`, `OrgSwitcher`
   (backend démo avec 2 orgs seedées).
4. **Clavier uniquement** : dérouler SignIn + OTPInput sans souris (tab/flèches/entrée).
5. Lecteur d'écran (NVDA/VoiceOver) : labels et annonces d'erreurs perceptibles sur SignIn.
6. Lancer l'audit axe DevTools sur chaque écran : zéro violation critique/sérieuse.

✅ Attendu : les 7 composants fonctionnels, zéro CSS émis, navigation clavier complète, axe
propre. Consigner les versions exactes des packages testés.

---

## MT-6 — `@tenxyte/ui` : revue visuelle et thèmes

**Couvre :** Requirement 6.4 · **Tâche :** 15.2
**Prérequis :** MT-5 PASS ; `@tenxyte/ui` publié.

### Procédure

1. Dans l'app MT-5, remplacer les composants headless par leurs équivalents stylés (le README
   doit rendre la substitution triviale — c'est un critère).
2. Revue visuelle des 7 composants en thème clair ET sombre (bascule via l'API documentée) :
   états normal/hover/focus/disabled/erreur/chargement.
3. Personnalisation : surcharger 3 tokens (`--tenxyte-color-primary`, radius, font) et vérifier
   la propagation sans `!important` ni re-style profond.
4. Responsive : 360 px, 768 px, 1280 px — aucun débordement, zones tactiles ≥ 44 px.
5. Contraste : vérifier les paires texte/fond principales aux ratios WCAG AA (outil au choix).
6. Re-passer axe sur les versions stylées : zéro violation critique/sérieuse.

✅ Attendu : rendu professionnel dans les deux thèmes, theming par tokens effectif, AA respecté.
Captures d'écran archivées en preuve.

---

## MT-7 — Revue documentaire et table de parité

**Couvre :** Requirements 4.5, 7.1, 7.2, 7.3, 7.4 · **Tâches :** 16.1, 16.2

### Procédure

1. **Table de parité publiée** (EN/FR) : générée par la CI, datée ; chaque ligne 🚫 exclue porte
   une justification lisible et défendable (relecture critique : « cette exclusion
   survivrait-elle à une question publique ? »).
2. **Quickstart FastAPI** : re-déroulé par une personne différente de MT-1 (validation croisée).
3. **Guide async** : la recette `as_async()` + le gabarit `jwt_service` sont présents ; un
   développeur externe au chantier implémente un mini-repo async en suivant uniquement le guide
   (test de complétude).
4. **Doc UI** : installation, référence des 7 composants, guide de theming — vérifier que chaque
   exemple de code compile tel quel.
5. Synchronisation EN/FR section par section sur les quatre documents.
6. `scripts/validate_endpoints.py` vert sur les deux langues après tous les ajouts.

✅ Attendu : docs auto-suffisantes (validées par des tiers), parité EN/FR, validation CI verte.

---

## Registre d'exécution

> À compléter à chaque exécution. Une ligne par run (garder l'historique en cas de re-run).

| ID | Intitulé | Date | Exécutant | Environnement | Résultat | Notes / lien preuve |
|----|----------|------|-----------|---------------|----------|---------------------|
| MT-1 | Quickstart FastAPI chronométré | — | — | — | ⬜ À exécuter | temps mesuré : — |
| MT-2 | Parcours Postman croisés (2.1–2.7) | — | — | — | ⬜ À exécuter | |
| MT-3 | Tenue en charge async + contre-épreuve | — | — | — | ⬜ À exécuter | p95/p99 : — |
| MT-4 | PostgreSQL/asyncpg + Alembic A/R | — | — | — | ⬜ À exécuter | |
| MT-5 | ui-headless app React neuve (7 composants) | — | — | — | ⬜ À exécuter | versions : — |
| MT-6 | ui stylé — thèmes, tokens, AA | — | — | — | ⬜ À exécuter | captures : — |
| MT-7 | Revue documentaire + table de parité | — | — | — | ⬜ À exécuter | |

**Légende résultat :** ✅ PASS · ❌ FAIL (ouvrir une issue, référencer ici) · ⚠️ PASS avec réserve
(documenter la réserve) · ⬜ À exécuter

## Critère de sortie de la phase

La phase est validée lorsque : toutes les lignes du registre sont ✅ (ou ⚠️ avec réserve acceptée
par le mainteneur), toutes les gates CI sont vertes (matrice complète, Contract_Suite × 2,
Coverage_Gate ≥ 90 % sur l'adapter FastAPI, Async_Purity_Check, conformité AIRS contre FastAPI,
drift OpenAPI), la suite Django existante passe sans modification, et le checkpoint final de
`tasks.md` est coché. L'annonce « multi-framework GA » n'intervient qu'après.
