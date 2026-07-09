# Tests Manuels — Phase 1 « Crédibilité » (z_aud_1)

> Ce document consigne les procédures de vérification **non automatisables** de la phase, et sert
> de **registre d'exécution** : chaque procédure doit être déroulée et son résultat consigné dans
> le tableau final avant de cocher la tâche correspondante dans `tasks.md`.

**Convention :** chaque section porte un identifiant `MT-x` référencé depuis `tasks.md`.
Un test manuel est **PASS** uniquement si toutes ses étapes de vérification sont satisfaites.

---

## MT-1 — Matrice d'installation en environnement vierge

**Couvre :** Requirements 2.1, 2.2, 2.3, 2.4, 2.6 · **Tâches :** 4.1, 4.3
**Prérequis :** Python 3.10+ propre (pas de venv réutilisé), accès au build local (`pip install .`).

### Procédure

1. **Core seul (`pip install tenxyte`)**
   ```bash
   python -m venv /tmp/vx-core && source /tmp/vx-core/bin/activate   # Windows: .\vx-core\Scripts\activate
   pip install <chemin-du-repo-ou-wheel-1.0>
   python -c "import tenxyte; print(tenxyte.__version__)"
   python -c "import django"   # DOIT échouer (ModuleNotFoundError)
   python -c "from tenxyte.core.jwt_service import JWTService; print('core OK')"
   python -c "import tenxyte; tenxyte.setup({})"   # DOIT lever TenxyteMissingDependencyError
   ```
   ✅ Attendu : import OK, version 1.0.0, Django ABSENT, Core utilisable, message d'erreur
   contenant exactement `pip install tenxyte[django]`.

2. **Stack Django (`pip install tenxyte[django]`)**
   ```bash
   python -m venv /tmp/vx-dj && source /tmp/vx-dj/bin/activate
   pip install "<chemin>[django]"
   pip freeze | grep -iE "django|djangorestframework|cors|spectacular|google-auth"
   ```
   Puis dans un projet Django minimal : `tenxyte.setup(globals())` dans settings,
   `python manage.py tenxyte_quickstart`, `python manage.py runserver`, et un cycle
   register → login → `GET /me/` via curl.
   ✅ Attendu : les 6 packages Django présents, quickstart OK, cycle API complet OK — comportement
   identique à une installation 0.9.6.4.

3. **Alias déprécié (`pip install tenxyte[core]`)**
   ```bash
   pip install "<chemin>[core]"
   ```
   ✅ Attendu : installation réussie, empreinte identique au cas 1 (extra no-op).

4. **Combinaison (`tenxyte[django,webauthn]`)**
   ✅ Attendu : stack Django + package `webauthn` présents.

### Résultat attendu global
Aucune des quatre installations ne produit d'erreur pip ; les frontières de dépendances sont
exactement celles du design (§ « périmètre exact de l'inversion »).

---

## MT-2 — Ultime release 0.9.x d'avertissement

**Couvre :** Requirement 2.7 · **Tâche :** 4.5
**Prérequis :** release 0.9.x publiée sur PyPI (ou TestPyPI pour répétition).

### Procédure

1. `pip install tenxyte==0.9.<dernière>` dans un venv propre.
2. `python -W always -c "import tenxyte"`.
3. Vérifier la présence du `DeprecationWarning` annonçant l'inversion de packaging en 1.0 avec la
   nouvelle commande `pip install tenxyte[django]`.
4. Vérifier que la note correspondante figure dans le README publié sur PyPI et dans le CHANGELOG.

✅ Attendu : warning visible et explicite ; aucun autre changement de comportement dans cette
release (suite de tests 0.9.x verte).

---

## MT-3 — Sign in with Apple de bout en bout

**Couvre :** Requirements 5.1–5.7, 5.10–5.12 · **Tâches :** 1.2, 1.3, 1.10
**Prérequis :** compte Apple Developer actif ; App ID + **Services ID** (client_id) configurés ;
clé « Sign in with Apple » (.p8) téléchargée ; domaine + return URL vérifiés chez Apple ; un
frontend de test (ou la page HTML minimale ci-dessous) servi en **HTTPS** (exigence Apple —
utiliser ngrok/localtunnel en dev).

### Configuration

```python
# settings.py du projet de test
APPLE_CLIENT_ID = "com.example.app.signin"     # Services ID
APPLE_TEAM_ID = "ABCDE12345"
APPLE_KEY_ID = "XYZ9876543"
APPLE_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
<contenu du fichier .p8>
-----END PRIVATE KEY-----"""
```

Page de test minimale (bouton Apple JS) :
```html
<script src="https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js"></script>
<script>
AppleID.auth.init({
  clientId: "com.example.app.signin",
  scope: "name email",
  redirectURI: "https://<votre-tunnel>/apple-callback",
  responseMode: "form_post",   // OBLIGATOIRE avec scope name/email
  usePopup: true
});
</script>
<div id="appleid-signin" data-color="black" data-border="true" data-type="sign in"></div>
```

### Scénarios

| # | Scénario | Étapes | Attendu |
|---|---|---|---|
| 3.1 | **Première autorisation** (le compte Apple de test ne doit jamais avoir autorisé l'app — sinon révoquer dans Réglages → Apple ID → Connexion avec Apple) | Cliquer le bouton, choisir « Partager mon adresse », compléter Face ID/mdp ; transmettre `code` + `user` (JSON nom) au backend : `POST /api/v1/auth/social/apple/` avec `{code, redirect_uri, user}` | `200` avec `access_token`, `refresh_token`, `user.first_name`/`last_name` peuplés depuis le payload, `is_new_user: true` ; une `SocialConnection(provider="apple")` créée en base |
| 3.2 | **Reconnexion** (même compte) | Recliquer le bouton, renvoyer `code` seul (pas de `user` — Apple ne le renvoie plus) | `200`, même utilisateur résolu (`is_new_user: false`), noms conservés du premier login |
| 3.3 | **Email masqué (private relay)** | Répéter 3.1 avec un second compte de test en choisissant « Masquer mon adresse » | `200` ; `user.email` en `@privaterelay.appleid.com` ; compte créé normalement |
| 3.4 | **Code invalide** | `POST /social/apple/` avec `code: "garbage"` | `401 CODE_EXCHANGE_FAILED`, aucun utilisateur créé |
| 3.5 | **id_token forgé** | Rejouer 3.1 en substituant un id_token signé localement (mauvaise clé) dans le flow id_token direct | `401 PROVIDER_AUTH_FAILED`, aucun utilisateur créé |
| 3.6 | **Provider non configuré** | Vider `APPLE_PRIVATE_KEY`, tenter 3.1 | `401 PROVIDER_AUTH_FAILED` propre (pas de 500), log explicite |
| 3.7 | **Non-régression Google** | Dérouler un login Google complet sur le même déploiement | Comportement identique à la 0.9.x |

### Points de vigilance
- Le champ `user` n'apparaît **qu'une seule fois par vie d'autorisation** : pour re-tester 3.1,
  révoquer l'autorisation dans les réglages du compte Apple.
- Vérifier dans les logs qu'**aucun client secret généré n'est loggé** (grep `eyJ` dans les logs
  applicatifs pendant la session de test).

---

## MT-4 — Activation de GitHub Private Vulnerability Reporting

**Couvre :** Requirement 3.8 · **Tâche :** 6.2
**Prérequis :** droits admin sur `tenxyte/tenxyte`.

### Procédure

1. GitHub → repo → **Settings → Code security and analysis** → activer
   **Private vulnerability reporting**.
2. Vérifier que l'onglet **Security** du repo affiche `SECURITY.md` (« Security policy ») et le
   bouton **« Report a vulnerability »**.
3. Depuis un **compte GitHub secondaire** (non-mainteneur), soumettre un rapport de test
   (`[TEST] Vérification du canal — merci d'ignorer`) via le bouton.
4. Côté mainteneur : vérifier la réception de la notification, l'apparition du draft advisory,
   puis fermer le rapport de test avec le motif approprié.
5. Chronométrer : l'accusé de réception (étape 4) doit être réalisable dans le SLA de 72 h
   annoncé par `SECURITY.md`.

✅ Attendu : canal fonctionnel de bout en bout, policy visible, rapport de test fermé proprement.

---

## MT-5 — Trusted Publishing PyPI et environnement protégé

**Couvre :** Requirements 4.1, 4.3 · **Tâche :** 7.2
**Prérequis :** droits owner sur le projet PyPI `tenxyte` et admin sur le repo GitHub.
**Recommandation :** répéter d'abord la procédure complète sur **TestPyPI**.

### Procédure

1. **PyPI** → projet `tenxyte` → **Publishing** → ajouter un Trusted Publisher :
   - Owner : `tenxyte` · Repository : `tenxyte` · Workflow : `publish.yml` · Environment : `pypi`.
2. **GitHub** → Settings → **Environments** → créer `pypi` avec **Required reviewers**
   (au moins un mainteneur) et restriction aux tags `v*`.
3. Supprimer le secret `PYPI_API_TOKEN` (ou équivalent) des secrets du repo, et vérifier par
   lecture de `publish.yml` qu'aucun `password:`/token n'y subsiste.
4. Déclencher une release (TestPyPI d'abord) et vérifier :
   - le job attend l'approbation manuelle de l'environnement `pypi` ;
   - la publication réussit **sans** token (OIDC seul) ;
   - les logs du job montrent la génération d'attestations.

✅ Attendu : publication OIDC pure, approbation manuelle exigée, aucun secret long-lived résiduel.

---

## MT-6 — Vérification des attestations d'un artefact publié

**Couvre :** Requirements 4.2, 4.5 · **Tâche :** 7.3
**Prérequis :** une release publiée via MT-5 ; `pip >= 24.x`, `pypi-attestations` installé.

### Procédure

1. Sur la page PyPI du fichier (`https://pypi.org/project/tenxyte/#files`), vérifier la présence
   du badge/détail de provenance (« Verified details » / attestations) sur le wheel et le sdist.
2. Vérification en ligne de commande :
   ```bash
   pip download tenxyte==1.0.0 --no-deps -d /tmp/att
   python -m pip install pypi-attestations
   python -m pypi_attestations verify pypi --repository https://github.com/tenxyte/tenxyte /tmp/att/tenxyte-1.0.0-*.whl
   ```
3. Vérifier que la provenance référencée pointe vers `tenxyte/tenxyte` et le workflow
   `publish.yml` (identité Sigstore du run GitHub Actions).
4. Contrôle négatif : la même commande avec `--repository https://github.com/autre/depot`
   DOIT échouer.

✅ Attendu : vérification positive liée au bon repo/workflow ; contrôle négatif en échec.

---

## MT-7 — Revue de publication des documents

**Couvre :** Requirements 1.1, 3.1, 6.4, 7.2, 7.3 · **Tâches :** 6.1, 8.1–8.4, 9.2

### Procédure

1. **SECURITY.md** : rendu correct sur GitHub (onglet Security + racine) ; le tableau de versions,
   le SLA, l'embargo et le lien `docs/security-audit/` sont présents et cohérents avec la 1.0.
2. **stability.md (EN/FR)** : chaque symbole listé dans la Public_API_Surface existe réellement
   (vérification croisée avec `tenxyte.__all__` — doit matcher le test snapshot) ; les deux
   langues sont synchronisées section par section.
3. **docs/security-audit/** : les trois documents existent, le threat model couvre bien les six
   domaines (JWT, OTP, WebAuthn, AIRS, reset, orgs), la checklist ASVS a un statut par point.
4. **README (EN/FR)** : le quickstart affiche `pip install tenxyte[django]` ; plus aucune
   occurrence de l'ancienne commande par défaut pour les utilisateurs Django.
5. **CHANGELOG** : l'entrée 1.0.0 liste le breaking packaging en tête, puis les ajouts.
6. Lancer `python scripts/validate_endpoints.py --file docs/en/endpoints.md` (et FR) : 0 erreur
   après l'ajout du provider Apple.

✅ Attendu : tous les points vérifiés, zéro divergence EN/FR, validation docs verte.

---

## Registre d'exécution

> À compléter à chaque exécution. Une ligne par run (garder l'historique en cas de re-run).

| ID | Intitulé | Date | Exécutant | Environnement | Résultat | Notes / lien preuve |
|----|----------|------|-----------|---------------|----------|---------------------|
| MT-1 | Matrice d'installation | — | — | — | ⬜ À exécuter | |
| MT-2 | Release 0.9.x d'avertissement | — | — | — | ⬜ À exécuter | |
| MT-3 | Apple Sign-In E2E (scénarios 3.1–3.7) | — | — | — | ⬜ À exécuter | |
| MT-4 | GitHub PVR | — | — | — | ⬜ À exécuter | |
| MT-5 | Trusted Publishing | — | — | — | ⬜ À exécuter | TestPyPI d'abord |
| MT-6 | Attestations | — | — | — | ⬜ À exécuter | |
| MT-7 | Revue documentaire | — | — | — | ⬜ À exécuter | |

**Légende résultat :** ✅ PASS · ❌ FAIL (ouvrir une issue, référencer ici) · ⚠️ PASS avec réserve
(documenter la réserve) · ⬜ À exécuter

## Critère de sortie de la phase

La phase est validée lorsque : toutes les lignes du registre sont ✅ (ou ⚠️ avec réserve acceptée
par le mainteneur), la suite automatisée est verte (tâche 10.1), et le checkpoint final de
`tasks.md` est coché. Le tag `v1.0.0` n'est posé qu'après.
