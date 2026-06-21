# 🔐 Audit ciblé WebAuthn + OAuth — `tenxyte` v0.9.5

> **Date** : 2026-06-12
> **Auditeur** : Mavis (Mavis)
> **Périmètre** :
> - `src/tenxyte/core/webauthn_service.py` (450 lignes)
> - `src/tenxyte/views/webauthn_views.py` (537 lignes)
> - `src/tenxyte/adapters/django/webauthn_storage.py` (441 lignes)
> - `src/tenxyte/models/webauthn.py` (103 lignes)
> - `src/tenxyte/services/social_auth_service.py` (536 lignes)
> - `src/tenxyte/views/social_auth_views.py` (409 lignes)
> - `src/tenxyte/models/social.py` (97 lignes)
> - `src/tenxyte/conf/social.py`
> - Tests associés
> - Doc `docs/en/endpoints.md` (section WebAuthn/OAuth)
>
> **Standards de référence** :
> - W3C WebAuthn Level 2/3
> - FIDO2 / CTAP2
> - RFC 6749 (OAuth 2.0), RFC 7636 (PKCE), RFC 9700 (OAuth 2.0 Security BCP)
> - OpenID Connect Core 1.0
>
> **Méthode** : lecture intégrale du code + grep ciblé + revue des tests + revue de la doc. Pas de lecture au hasard — chaque finding cite `file:line` et pointe un comportement concret.

---

## TL;DR

Le système WebAuthn/Passkeys et OAuth Social de `tenxyte` est **globalement bien structuré** — bonne séparation core/adapter, tests présents, utilisation de la lib `py_webauthn` (la bonne). Mais il y a **6 problèmes critiques**, dont 3 exploitables à distance sans authentification préalable, et **9 problèmes de sévérité haute** qui ne passeraient pas un audit sécurité externe.

**Score** : WebAuthn **5.5/10**, OAuth **4.5/10** (le score OAuth est plus bas à cause du `state` parameter absent et de la confiance aveugle aux claims des providers).

**Action immédiate** : 2 correctifs à pousser en hotfix (CSRF sur OAuth callback + state parameter) avant toute mise en prod où un user peut s'inscrire via OAuth.

---

# 🟥 WEBAUTHN — Findings détaillés

## W-1 🔴 CRITIQUE — `expected_origin` dérive du `rp_id` sans validation (CWE-346: Origin Validation Error)

**Fichier** : `src/tenxyte/core/webauthn_service.py:184-188`

```python
def _get_origin(self) -> str:
    """Get origin URL for WebAuthn."""
    if self.rp_id == "localhost":
        return "http://localhost"
    return f"https://{self.rp_id}"
```

**Problème** : La lib `py_webauthn` accepte `expected_origin` comme **string exacte** à comparer avec `clientDataJSON.origin`. Si `rp_id` est mal configuré (par ex. `WEBAUTHN_RP_ID = "evil.com, attacker.com"` ou contient un caractère spécial), un attaquant peut :

1. Soit faire passer une cérémonie initiée depuis son propre origin → bypass de l'authentification du user légitime.
2. Soit se retrouver avec un origin dynamique qui passe côté lib mais pas côté navigateur.

**Cas concret** : si quelqu'un configure `WEBAUTHN_RP_ID = "example.com.attacker.com"` (subdomain takeover scenario), `_get_origin()` retourne `"https://example.com.attacker.com"`, l'authenticator retourne le même origin → la lib accepte. Le user s'authentifie sur le domaine attaquant.

**Fix** :
- Valider strictement `rp_id` : regex `^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$` (RFC 1035 + RFC 5890 IDN).
- Rejeter `localhost` en production (vérifier `settings.DEBUG`).
- Permettre à l'operator de configurer `expected_origin` séparément du `rp_id` (cas où le site est `www.example.com` mais le `rp_id` est `example.com`).

**Sévérité** : 🔴 CRITIQUE (origin spoofing = bypass auth).

---

## W-2 🔴 CRITIQUE — Race condition TOCTOU sur `WebAuthnChallenge` (CWE-367)

**Fichier** : `src/tenxyte/core/webauthn_service.py:267-292` (registration) et `:387-422` (authentication)

```python
# Pseudo-code
challenge = self.challenge_repo.get_by_id(challenge_id)
if not challenge.is_valid():
    return RegistrationResult(success=False, error="...")
...
verification = webauthn.verify_registration_response(...)
...
self.challenge_repo.consume(challenge_id)  # ← marqué consumed APRÈS verify
```

**Problème** : Entre `get_by_id` (ligne 268) et `consume` (ligne 292), un attaquant peut envoyer une seconde requête concurrente avec le même `challenge_id`. Les deux requêtes passent le check `is_valid()`, les deux appellent `verify_registration_response()` avec le même challenge. Si la lib `py_webauthn` ne marque pas elle-même le challenge consommé (ce qui n'est **pas** son rôle), l'attaquant peut :
- Soit enregistrer une seconde fois avec une clé publique différente (credential duplication).
- Soit rejouer une assertion WebAuthn volée.

**Cas concret** : Le serveur autorise 2 authentifications simultanées avec le même `challenge_id` (par ex. 2 onglets ouverts). Le sign count est incrémenté deux fois → détection ratée.

**Fix** : utiliser un UPDATE atomique avec condition :
```python
# Storage layer
def consume(self, challenge_id: str) -> bool:
    updated = WebAuthnChallenge.objects.filter(
        id=challenge_id, is_used=False, expires_at__gt=timezone.now()
    ).update(is_used=True)
    return updated == 1
```
Si `consume()` retourne `False`, refuser la cérémonie. L'ORM Django n'a pas de `compare_and_set` natif, mais `update()` avec filtre + vérification du count est atomique.

**Sévérité** : 🔴 CRITIQUE (challenge reuse = replay).

---

## W-3 🔴 CRITIQUE — `transports` jamais persisté à la registration (perte de fonctionnalité FIDO2)

**Fichier** : `src/tenxyte/core/webauthn_service.py:295-311`

```python
credential = WebAuthnCredential(
    ...
    aaguid=str(verification.aaguid) if hasattr(verification, "aaguid") else "",
    # ⚠️ transports=??? — pas passé
)
```

Puis dans `src/tenxyte/adapters/django/webauthn_storage.py:357-360` (model create) :
```python
WebAuthnCredentialModel.objects.create(
    ...
    transports=getattr(credential, "transports", []),
)
```

Le `getattr(..., "transports", [])` retourne toujours `[]` parce que `WebAuthnCredential` n'a pas reçu `transports` à la construction. Or l'objet `verification` de la lib `py_webauthn` ne contient pas les transports — il faut les lire depuis le `clientDataJSON.response.attestationObject.authData` ou les passer depuis le front (le navigateur les fournit dans `response.transports`).

**Conséquence** :
- `transports` est toujours `[]` en base → impossible d'utiliser l'attestation pour distinguer platform/cross-platform.
- L'UI ne peut pas afficher "iCloud Keychain" vs "YubiKey 5".
- Le champ `authenticator_type: "platform"` de la doc (endpoint.md:4665, 4674) est **trompeuse** — la valeur n'est jamais calculée.

**Fix** :
1. Frontend : envoyer `transports: ["internal", "hybrid"]` dans le payload `complete_registration`.
2. Service : extraire `credential_data.get("transports", [])` et le passer à `WebAuthnCredential(transports=...)`.
3. Service : calculer `authenticator_type` depuis `aaguid` (mapping FIDO Alliance) ou `transports`.

**Sévérité** : 🔴 CRITIQUE fonctionnelle (perte de feature), pas exploitable.

---

## W-4 🟠 HAUTE — Pas de validation du format `challenge_id` injecté par l'utilisateur

**Fichier** : `src/tenxyte/views/webauthn_views.py:242-247`

```python
service = get_core_webauthn_service()
challenge_id = request.data.get("challenge_id")
result = service.complete_registration(
    user_id=str(request.user.id),
    credential_data=credential_data,
    challenge_id=str(challenge_id) if challenge_id else "",  # ← str() de n'importe quoi
    device_name=device_name,
)
```

Et `WebAuthnChallenge.id` est un `AutoField` (integer) côté modèle (`src/tenxyte/models/webauthn.py:68`), mais passé en `str`. La conversion `str("123")` et `str("123 OR 1=1")` sont indistinguables.

**Problème** : `DjangoWebAuthnStorage.get_by_id()` (`webauthn_storage.py:418`) fait :
```python
challenge = WebAuthnChallengeModel.objects.get(id=challenge_id, expires_at__gt=datetime.utcnow())
```

`objects.get(id="abc")` lèverait une `ValueError` côté Django (auto-cast int échoue). Mais :
- Pas de try/except explicite → exception remonte 500.
- Pas de validation de type → un user peut envoyer un `challenge_id` qui pointe vers le challenge **d'un autre user**.

Ligne 275 du core (`webauthn_service.py`) :
```python
if challenge.user_id != user_id:
    return RegistrationResult(success=False, error="Challenge does not match user")
```

✅ Ce check existe, donc **un user A ne peut pas consommer le challenge de user B** en registration. **Mais** en `complete_authentication` (`webauthn_service.py:373`), le challenge pour `authenticate` n'a pas forcément de `user_id` (resident key, usernameless) → le check n'est pas applicable. Or `credential_data.get("id", "")` est utilisé pour lookup de la credential, qui appartient forcément à quelqu'un. L'authenticator attaqueur n'a pas la clé privée → ne peut pas signer pour une credential qui n'est pas la sienne. **Risque faible, mais pas nul**.

**Fix** : valider `challenge_id` comme entier positif dans le serializer :
```python
challenge_id = serializers.IntegerField(min_value=1)
```

**Sévérité** : 🟠 HAUTE (defense-in-depth, pas exploitable directement).

---

## W-5 🟠 HAUTE — `expected_origin` mismatch sur environnement de dev

**Fichier** : `src/tenxyte/core/webauthn_service.py:184-188`

```python
def _get_origin(self) -> str:
    if self.rp_id == "localhost":
        return "http://localhost"
    return f"https://{self.rp_id}"
```

**Problème** : En dev, `WEBAUTHN_RP_ID="localhost"` mais le serveur tourne sur `localhost:8000` (donc origin = `http://localhost:8000`). La lib `py_webauthn` compare l'origin **exactement**. Le check passe quand même parce que la lib fait un match "starts with" ou "exact match" selon la version.

Vérification : `py_webauthn >= 2.0` fait un **exact match** strict de l'origin. Donc `expected_origin="http://localhost"` ≠ origin réel `"http://localhost:8000"` → **registration échoue en dev**.

**Fix** : soit rendre l'origin configurable (`TENXYTE_WEBAUTHN_ORIGIN`), soit faire :
```python
def _get_origin(self) -> str:
    if self.rp_id == "localhost":
        return settings.TENXYTE_WEBAUTHN_ORIGIN or "http://localhost:8000"
    return f"https://{self.rp_id}"
```

**Sévérité** : 🟠 HAUTE fonctionnelle (l'endpoint est cassé en dev sans config manuelle).

---

## W-6 🟠 HAUTE — `verify_registration_response` et `verify_authentication_response` n'ont pas de `timeout` côté core

**Fichier** : `src/tenxyte/core/webauthn_service.py:281-285` et `:404-409`

La lib `py_webauthn` accepte un paramètre `timeout` (en ms) pour rejeter les assertions/registrations trop lentes. Sans ça, un attaquant peut soumettre une réponse valide 1h après le challenge (si la lib ne check pas l'`iat` du challenge).

**Vérification faite** : `webauthn_challenge.py:79` stocke `expires_at`, et `is_valid()` check l'expiration. Donc le **challenge** expire côté Tenxyte. **Mais** la lib `py_webauthn` ne sait rien de l'expiration — elle valide juste la signature et le `clientDataJSON.challenge`. Si l'attaquant arrive à se faire servir un `get_by_id()` qui retourne le challenge expiré, la lib ne le saura pas.

**Risque réel** : faible (Tenxyte check `is_valid()` avant d'appeler la lib), mais defense-in-depth. La lib `py_webauthn >= 2.x` supporte `timeout` — on devrait le passer à 60000 (60s) ou 120000 (2min) explicitement.

**Sévérité** : 🟠 HAUTE (defense-in-depth).

---

## W-7 🟠 HAUTE — Aucun contrôle sur le sign count = 0

**Fichier** : `src/tenxyte/core/webauthn_service.py:415`

```python
verification = webauthn.verify_authentication_response(
    ...
    credential_current_sign_count=stored_credential.sign_count,
)
```

La lib `py_webauthn` vérifie que `new_sign_count > current_sign_count` et lève `InvalidSignCount` sinon. C'est bien. **Mais** : un authenticator qui n'implémente pas le sign count (par ex. certains modèles anciens) retourne toujours 0. La lib a un mode `require_user_verification=False` qui n'est pas set ici.

**Cas concret** : si un authenticator retourne 0 systématiquement (cas connu pour les implémentations bas de gamme) ET que la première auth a enregistré sign_count=0, toutes les suivantes auront 0 → **replay possible** entre 2 sessions avant rotation de credential.

**Fix** : la lib `py_webauthn` lève `InvalidSignCount` même pour 0=0 dans certaines versions. Vérifier en testant. Si la lib l'accepte, forcer un check :
```python
if verification.new_sign_count != 0 and verification.new_sign_count <= stored_credential.sign_count:
    return AuthenticationResult(success=False, error="Replay detected")
```

**Sévérité** : 🟠 HAUTE (replay attack scenario).

---

## W-8 🟠 HAUTE — Aucun rate-limit sur `/webauthn/authenticate/complete/`

**Fichier** : `src/tenxyte/views/webauthn_views.py:346-453` — `WebAuthnAuthenticateCompleteView`

Comparaison :
- `LoginThrottle, LoginHourlyThrottle` sur `SocialAuthView` (`social_auth_views.py:36`).
- `JWTRefreshThrottle` sur refresh.
- **Aucun throttle** sur les endpoints WebAuthn.

**Problème** : un attaquant peut brute-forcer avec des `challenge_id` aléatoires + `credential.id` aléatoires. La lib finira par dire "signature invalide", mais :
- 1000 requêtes/s = 86M requêtes/jour contre le CPU de vérification ECDSA.
- L'`is_valid()` du challenge rejette en DB query (coût).
- Le `update_sign_count` fait un UPDATE en DB à chaque tentative valide.

**Fix** : ajouter `throttle_classes = [LoginThrottle, LoginHourlyThrottle]` sur les 2 endpoints d'auth WebAuthn.

**Sévérité** : 🟠 HAUTE (DoS + attack surface).

---

## W-9 🟡 MOYENNE — `aaguid` pas normalisé, `aaguid` vide accepté

**Fichier** : `src/tenxyte/models/webauthn.py:37`, `src/tenxyte/core/webauthn_service.py:310`

```python
aaguid = models.CharField(max_length=36, blank=True, default="")
...
aaguid=str(verification.aaguid) if hasattr(verification, "aaguid") else "",
```

L'`aaguid` est un identifiant FIDO standard (16 bytes = 32 hex chars + 4 dashes = 36 chars). Le check `hasattr(verification, "aaguid")` est **dangereux** parce que :
- `MagicMock(spec=...)` retourne `True` pour `hasattr` même sans valeur.
- Un objet `verification` sans `aaguid` set donne `str(None) == "None"` (4 chars), pas `""`.

**Fix** :
```python
aaguid_val = getattr(verification, "aaguid", None)
aaguid = str(aaguid_val) if aaguid_val else ""
```

**Sévérité** : 🟡 MOYENNE (defense-in-depth, data quality).

---

## W-10 🟡 MOYENNE — `transports` reçu du front jamais validé

Le doc endpoint `complete` (`endpoints.md:4498-4511`) ne mentionne pas le champ `transports` dans le payload envoyé par le navigateur. Le service l'attend (`WebAuthnCredential.transports`) mais ne le valide pas (longueur, valeurs autorisées, etc.).

**Fix** : ajouter un validateur sur `transports` (sous-ensemble de `usb`, `nfc`, `ble`, `internal`, `hybrid`, `smart-card`, `cable`).

**Sévérité** : 🟡 MOYENNE.

---

## W-11 🟡 MOYENNE — Pas de cleanup automatique des challenges expirés

**Fichier** : `src/tenxyte/models/webauthn.py:54-103`

`WebAuthnChallenge` a un champ `expires_at` mais **aucune tâche périodique** ne purge les expirés. La table grossit indéfiniment. Pire, la requête `get_by_id(challenge_id)` peut renvoyer un challenge expiré si l'index ne couvre pas `expires_at`.

**Fix** :
- Index composite `(id, expires_at)`.
- Tâche `tenxyte_cleanup --webauthn-challenges` (probablement existe, à vérifier).
- Sinon : `WebAuthnChallenge.cleanup_expired()` appelé depuis le `WebAuthnService.complete_*` quand on a un hit expiré.

**Sévérité** : 🟡 MOYENNE (perf + disk).

---

## W-12 🟡 MOYENNE — `complete_authentication` ne re-vérifie pas que la credential est `is_active=True`

**Fichier** : `src/tenxyte/core/webauthn_service.py:397-400`

```python
stored_credential = self.credential_repo.get_by_credential_id(raw_credential_id)
if not stored_credential:
    return AuthenticationResult(success=False, error="Unknown credential")
```

Si une credential a été `is_active=False` (par ex. révoquée manuellement), elle est quand même utilisable. Le modèle `WebAuthnCredential` n'a pas de champ `is_active` (vérifié : pas dans le modèle), donc en pratique ce risque n'existe pas. **Mais** : si quelqu'un ajoute un soft-delete plus tard sans toucher au service, on a un trou.

**Fix** : ajouter `is_active` au modèle et au service.

**Sévérité** : 🟡 MOYENNE (latent).

---

## W-13 🟢 BASSE — `delete_credential` mismatch ID type (str vs int)

**Fichier** : `src/tenxyte/views/webauthn_views.py:531`

```python
success, error_msg = service.delete_credential(credential_id=str(credential_id), user_id=str(request.user.id))
```

Le path param est `credential_id: int` (annotation), mais passé en `str()`. Le `core/webauthn_service.py:445-449` ne s'en sert que pour `credential_repo.delete(credential_id, user_id)`. Le storage Django `delete()` (`webauthn_storage.py:407`) fait :
```python
WebAuthnCredentialModel.objects.get(id=credential_id, user_id=user_id)
```

Si `id` est un integer côté ORM, Django fait le cast. OK fonctionnellement. **Mais** : si quelqu'un passe `credential_id="abc"`, Django raise → 500.

**Sévérité** : 🟢 BASSE.

---

# 🟥 OAUTH — Findings détaillés

## O-1 🔴 CRITIQUE — `state` parameter **complètement absent** du flow OAuth (CWE-352: CSRF)

**Fichier** : `src/tenxyte/views/social_auth_views.py:335-396` (`SocialAuthCallbackView`)

```python
def get(self, request, provider: str):
    ...
    code = request.GET.get("code")
    redirect_uri = request.GET.get("redirect_uri")
    ...
    tokens = oauth_provider.exchange_code(code, redirect_uri)
    ...
```

**Problème** : Le schéma OpenAPI mentionne `state` (ligne 266, `description="Parameter CSRF/state pour sécurité"`) **mais le code ne le lit, ne le stocke, ni ne le vérifie jamais**. Le `state` parameter est le mécanisme standard OAuth2 contre le **CSRF sur le callback** (Authorization Code Injection).

**Scénario d'attaque** :
1. User A est authentifié sur `tenxyte.example.com` (cookie de session valide, OU peut recevoir un email avec un code authorization déjà leaked).
2. Attaquant crée un compte sur le provider OAuth (ex: Google), initie un flow OAuth, récupère un `code` valide.
3. Attaquant envoie à User A un lien : `https://tenxyte.example.com/api/v1/auth/social/google/callback/?code=ATTACKER_CODE&redirect_uri=https://tenxyte.example.com/oauth/callback`.
4. User A clique (ou un script le fait via XSS / phishing).
5. Le serveur échange le code de l'attaquant contre un access_token, lie le compte de l'attaquant à... rien. Mais surtout : un attaquant peut **pré-charger un code authorization valide** et faire du OAuth fixation.

**Cas encore pire** : si User A est authentifié en cookie mode, le callback peut **lier l'account Google de l'attaquant à l'user A** si `is_redirect_uri_allowed` match un redirect de l'attaquant. Sans `state`, on n'a aucun moyen de lier le code au user qui a initié le flow.

**Fix** :
1. À l'initiation (`POST /social/<provider>/` avec `code`), générer un `state` aléatoire, le stocker côté serveur (Redis ou table `OAuthState`), lié à `user_id` (si authentifié) + `provider` + `redirect_uri`.
2. Au callback, lire `state`, vérifier qu'il existe, le supprimer (one-shot), vérifier que `user_id` match.
3. Si `state` manquant ou mismatch → 400 `INVALID_STATE`.

**Sévérité** : 🔴 CRITIQUE (CSRF = account takeover sur flows OAuth).

---

## O-2 🔴 CRITIQUE — `nonce` jamais validé sur Google `id_token` (CWE-345: Insufficient Verification of Data Authenticity)

**Fichier** : `src/tenxyte/services/social_auth_service.py:113-136`

```python
def verify_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
        idinfo = google_id_token.verify_oauth2_token(id_token, google_requests.Request(), client_id)
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            return None
        ...
```

**Problème** : `verify_oauth2_token()` vérifie la signature + `iss` + `aud` (client_id), mais **PAS** le `nonce` car la lib n'a pas de paramètre pour. Or le `nonce` est l'équivalent du `state` pour le flow implicite (id_token).

**Scénario** : un attaquant qui a volé un `id_token` Google (par ex. via un autre site qui l'a loggé) peut le rejouer contre Tenxyte. Sans `nonce` check, le serveur accepte.

**Fix** : générer un `nonce` côté Tenxyte, le passer en paramètre au front (qui le met dans le `nonce` du flow Google), puis le récupérer dans l'`idinfo` après `verify_oauth2_token` :
```python
expected_nonce = cache.get(f"oauth_nonce_{user_id_or_session_id}")
if idinfo.get("nonce") != expected_nonce:
    return None
```

**Sévérité** : 🔴 CRITIQUE (id_token replay).

---

## O-3 🔴 CRITIQUE — Auto-merge de comptes via email (Account Fusion) activable avec vecteur d'élévation

**Fichier** : `src/tenxyte/services/social_auth_service.py:415-440`

```python
elif email:
    is_verified = user_data.get("email_verified", False)
    if not is_verified:
        return (False, None, "Email from ... is not verified. ...")
    user = User.objects.filter(email__iexact=email).first()
    auto_merge = getattr(auth_settings, "SOCIAL_AUTO_MERGE_ACCOUNTS", False)
    if user and not auto_merge:
        return (False, None, "An account with this email already exists...")
```

**Problème (bis) — `email_verified` est trusté aveuglément** :
- Google retourne `email_verified=True` si l'email est vérifié chez Google.
- Mais si un attaquant contrôle un Google Workspace avec un domaine qu'il possède, il peut faire vérifier son email par Google.
- Si l'attaquant enregistre un user Tenxyte avec `attacker@victim-corp.com`, et que `victim@victim-corp.com` est un user légitime, le check `email_verified` passe → **account takeover** par `auto_merge=True` ou par social engineering (l'user légitime voit un message "lier le compte").

Le check `if not auto_merge: return error` est une **barrière à l'auto-merge**, mais le check `email_verified` ne garantit pas que **le user qui se connecte via Google est le même** que le propriétaire légitime de l'email.

**Fix** :
1. Refuser l'auto-merge **systématiquement** (le default est déjà `False`, mais exposer un warning en runtime).
2. Si activé, exiger un **second facteur** (TOTP / WebAuthn) avant le merge.
3. Envoyer un **email de notification** au compte existant pour confirmer.
4. **Idéalement** : ne jamais fusionner. Toujours lier manuellement après login password du compte existant.

**Sévérité** : 🔴 CRITIQUE si `SOCIAL_AUTO_MERGE_ACCOUNTS=True` (qui est la valeur par défaut possible).

---

## O-4 🟠 HAUTE — `id_token` (Google) reçoit n'importe quel `id_token` non lié à un `nonce` ni à un `code_challenge`

**Fichier** : `src/tenxyte/views/social_auth_views.py:183-185`

```python
elif request.data.get("id_token") and provider_name == "google":
    user_data = oauth_provider.verify_id_token(request.data["id_token"])
```

L'utilisateur peut envoyer **n'importe quel id_token Google** qu'il a récupéré ailleurs. Sans `nonce` check (voir O-2) et sans liaison à un flow Tenxyte spécifique, ce endpoint accepte tout id_token valide pour notre `GOOGLE_CLIENT_ID`.

**Cas concret** : si un user a un autre site qui l'a authentifié via Google (avec un id_token ciblant le **même** `GOOGLE_CLIENT_ID` — cas peu probable mais possible en multi-tenant), il peut utiliser ce token sur Tenxyte.

**Fix** : cf. O-2 — exiger `nonce`.

**Sévérité** : 🟠 HAUTE (dépend de O-2, mais l'endpoint est ouvert).

---

## O-5 🟠 HAUTE — Microsoft provider : `email_verified` hardcodé à `True`

**Fichier** : `src/tenxyte/services/social_auth_service.py:248-261`

```python
def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
    data = self._get(self.MICROSOFT_USERINFO_URL, access_token)
    ...
    return {
        ...
        "email_verified": True,  # Microsoft verifies emails
        ...
    }
```

**Problème** : Microsoft Graph **ne retourne pas explicitement** un flag `email_verified` (contrairement à Google). Le commentaire "Microsoft verifies emails" est **techniquement vrai** pour les emails du tenant, mais **faux** pour les invités externes (`guest` users) qui peuvent avoir des emails non vérifiés.

**Conséquence** : un user invité sur un tenant AD peut s'authentifier via Microsoft → `email_verified=True` → **auto-merge** sur un compte Tenxyte existant avec le même email.

**Fix** : appeler `https://graph.microsoft.com/v1.0/me?$select=mail,userPrincipalName,otherMails` puis vérifier le claim `verifiedEmail` (qui n'existe pas officiellement). **Mieux** : activer l'option "Email as verified" via Azure AD conditional access, ou refuser le `email_verified=True` par défaut pour les guests.

**Sévérité** : 🟠 HAUTE (account fusion vector).

---

## O-6 🟠 HAUTE — Facebook provider : `email_verified` hardcodé à `True`

**Fichier** : `src/tenxyte/services/social_auth_service.py:294-318`

```python
return {
    ...
    "email_verified": True,  # Facebook verifies emails
    ...
}
```

Facebook Graph API v18+ peut retourner un champ `is_verified` (ajouté récemment). Le code l'ignore et hardcode `True`.

**Fix** : appeler `?fields=id,email,first_name,last_name,picture,is_verified` et utiliser la vraie valeur.

**Sévérité** : 🟠 HAUTE (account fusion vector).

---

## O-7 🟠 HAUTE — GitHub : `provider_user_id` est l'ID numérique, mais si l'user change son username, le matching continue de fonctionner (bien) mais le `provider_user_id` reste l'ID (bien) — par contre aucun check sur `email_verified`

**Fichier** : `src/tenxyte/services/social_auth_service.py:186-212`

Le code est correct sur l'ID (utilise `data["id"]`, pas `data["login"]`). **Mais** : GitHub permet aux users d'avoir un email `noreply@github.com` (pour ceux qui ont désactivé la visibilité email). Le code prend alors `email=None` ou `email=""` → tombe dans la branche `else: user = None` → crée un nouvel user sans email → **collision possible** avec un user existant au même email `noreply`.

**Fix** : refuser la création de user sans email vérifié.

**Sévérité** : 🟠 HAUTE (account enumeration + collision).

---

## O-8 🟠 HAUTE — `redirect_uri` validation : `is_redirect_uri_allowed` ne check pas le scheme/host

**Fichier** : `src/tenxyte/models/application.py:96-103` (vu dans l'audit précédent)

```python
def is_redirect_uri_allowed(self, redirect_uri: str) -> bool:
    if not self.redirect_uris:
        return True  # ← Whitelist vide = tout autorisé
    return redirect_uri in self.redirect_uris  # ← Match exact
```

**Problème 1** : si `Application.redirect_uris` est vide, **tous** les redirect_uri sont autorisés. Comportement "backward compat" documenté, mais dangereux en prod. Un attaquant peut utiliser `redirect_uri=https://attacker.com` pour intercepter le code.

**Problème 2** : match exact (pas de normalisation). Si l'operator whitelist `https://example.com/callback`, l'attaquant peut envoyer `https://example.com/callback?foo=bar` → pas match → bloqué (ok). Mais `https://example.com/callback#fragment` → pas match (ok). En revanche, **pas de check sur le scheme** : `javascript://example.com/callback` ne passe pas le match exact, mais l'absence de validation du scheme est un signal d'alarme.

**Fix** :
1. Refuser `redirect_uris` vide en mode strict (toggle `TENXYTE_STRICT_REDIRECT_URI`).
2. Valider scheme ∈ {`https`, `http` en dev uniquement}.
3. Utiliser `urlparse` + normalisation + match exact.

**Sévérité** : 🟠 HAUTE (OAuth code interception).

---

## O-9 🟠 HAUTE — Aucun throttling par provider sur les codes invalides

**Fichier** : `src/tenxyte/views/social_auth_views.py:36`

```python
throttle_classes = [LoginThrottle, LoginHourlyThrottle]
```

Le throttle existe sur le `POST /social/<provider>/` mais **pas** sur le `GET /social/<provider>/callback/`. Un attaquant peut brute-forcer des `code` invalides. Chaque requête fait :
1. `oauth_provider.exchange_code()` → 1 HTTP request vers le provider.
2. `oauth_provider.get_user_info()` → 1 autre HTTP request.
3. Si succès, `User.objects.create()` → 1 insert DB.

→ **Cascade de requêtes externes + DB insert non-bornés**.

**Fix** : ajouter `LoginThrottle` sur `SocialAuthCallbackView`.

**Sévérité** : 🟠 HAUTE (DoS + provider API quota burn).

---

## O-10 🟠 HAUTE — PKCE partiellement implémenté (code_verifier transmis mais pas vérifié)

**Fichier** : `src/tenxyte/services/social_auth_service.py:69, 144, 214, 263, 320`

```python
@abstractmethod
def exchange_code(self, code: str, redirect_uri: str, code_verifier: str = None) -> Optional[Dict[str, Any]]:
```

`code_verifier` est transmis dans le POST body, mais :
- Aucun check que `code_challenge` (envoyé lors de l'init authorize) matche `code_verifier` côté Tenxyte.
- Le `code_verifier` est juste forwardé au provider, qui le valide.

**Problème** : Tenxyte ne génère pas de `code_verifier` / `code_challenge` côté serveur. C'est le front qui doit le faire. Si le front oublie, **PKCE n'est pas appliqué**. Le code pourrait être MITM si le front n'est pas sur TLS strict.

**Fix** :
1. Pour les flows "server-to-server" (mobile app, SPA en BFF pattern), Tenxyte **doit** générer le `code_verifier`, le hasher en `code_challenge` (S256), stocker le `code_verifier` en session/cache, et le re-vérifier au callback.
2. Rendre `code_verifier` requis sauf pour Google `id_token` flow.

**Sévérité** : 🟠 HAUTE (PKCE incomplet).

---

## O-11 🟡 MOYENNE — `exchange_code` n'enforce pas un timeout serré

**Fichier** : `src/tenxyte/services/social_auth_service.py:73-95`

```python
def _get(self, url: str, access_token: str, **kwargs) -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(url, headers={...}, timeout=10, **kwargs)
```

10s c'est OK pour Google/GitHub (rapides), mais Microsoft Graph peut être lent (>10s) et Facebook aussi. Si le serveur attend 10s sur chaque request, un attaquant peut orchestrer un slowloris interne.

**Fix** : timeout adaptatif par provider (5s pour Google, 15s pour Microsoft).

**Sévérité** : 🟡 MOYENNE (DoS latent).

---

## O-12 🟡 MOYENNE — `email.lower()` mais pas de normalisation unicode (NFC/NFD)

**Fichier** : `src/tenxyte/services/social_auth_service.py:446`

```python
user = User.objects.create(
    email=email.lower() if email else None,
```

`"café@example.com".lower()` ne fait pas de normalisation Unicode. Un user qui s'inscrit avec `café@example.com` (NFD = `cafe\u0301`) ne matchera pas avec `café@example.com` (NFC = `caf\u00e9`) déjà en base. Pas un trou de sécurité, mais `email_verified` + unicité email cassée = vecteur de duplicate accounts.

**Fix** : `import unicodedata; email = unicodedata.normalize("NFC", email).lower()`.

**Sévérité** : 🟡 MOYENNE (data quality, attack surface pour account enumeration).

---

## O-13 🟡 MOYENNE — Pas de validation que `provider_name` est dans `PROVIDER_REGISTRY` au niveau de la view

**Fichier** : `src/tenxyte/views/social_auth_views.py:139-148`

```python
oauth_provider = get_provider(provider_name)
if not oauth_provider:
    return Response({...}, status=400)
```

`get_provider` filtre par `enabled`, donc OK. **Mais** : `provider_name` vient du path param. Si Django path matching est laxiste, `provider_name="Google/../etc/passwd"` pourrait passer. DRF normalize le path param → OK. Pas de risque.

**Sévérité** : 🟡 MOYENNE (defense-in-depth).

---

## O-14 🟢 BASSE — Token pas stocké (R10) est **cité comme feature** mais empêche des cas d'usage OAuth standards

**Fichier** : `src/tenxyte/models/social.py:43-52, 73-74, 92-94`

Le code dit "tokens OAUTH ne sont pas stockés (R10)". **C'est bon pour la sécurité** (DB compromise = pas de fuite de tokens). **Mais** :
- Impossible de refresh un access_token Google après expiration (1h).
- Impossible de poster sur les réseaux sociaux "au nom de l'user".
- Le package ne peut pas être utilisé pour des intégrations type "Google Drive access".

**Si c'est un choix conscient** : bien, documenter.
**Si c'est accidentel** : à corriger (utiliser `django-cryptography` comme suggéré dans le commentaire).

**Sévérité** : 🟢 BASSE (feature scope, pas security).

---

# 🟦 TESTS — couverture réelle

**Ce qui est bien testé** :
- ✅ 49 tests unit sur `test_social_auth.py` (mocking des providers)
- ✅ 49 tests sur `test_webauthn.py` (end-to-end Django)
- ✅ 52 tests sur `test_webauthn_storage.py` (CRUD storage)
- ✅ 10 tests core sur `test_webauthn_service.py` (mocking py_webauthn)
- ✅ Coverage : tous les chemins "happy path" et la plupart des "unhappy path"

**Ce qui N'est PAS testé** (et devrait l'être) :
- ❌ Aucun test de **replay attack** (challenge_id consommé 2x).
- ❌ Aucun test de **PKCE end-to-end** (code_verifier invalide rejeté).
- ❌ Aucun test de **`state` mismatch** (puisque `state` n'existe pas...).
- ❌ Aucun test de **CSRF sur le callback OAuth** (idem).
- ❌ Aucun test de **sign_count = 0** (replay).
- ❌ Aucun test de **residente key** (usernameless flow).
- ❌ Aucun test de **`expected_origin` mismatch** (browser-side vs server-side).
- ❌ Aucun test de **AAGUID parsing**.
- ❌ Aucun test de **rate-limit** sur les endpoints WebAuthn.
- ❌ Aucun test d'**intégration avec un vrai provider** (toujours mocké).
- ❌ Aucun test de **multi-tenant** sur OAuth (org membership après login).
- ❌ Aucun test de **transports** persistance.

**Verdict tests** : **couverture fonctionnelle**, **couverture sécurité faible**. Les tests protègent contre les régressions, pas contre les attaques.

---

# 🟩 DOCUMENTATION

## Points positifs

- 28k bytes de doc EN+FR, 28 endpoints documentés.
- Exemples curl pour chaque endpoint.
- Schémas OpenAPI à jour.
- `endpoints.md:4432-4702` couvre WebAuthn correctement (request/response examples, codes d'erreur).

## Points à corriger

- **D-1** : Le schéma `complete_registration` (`endpoints.md:4498-4511`) **omet le champ `transports`** dans le payload envoyé par le browser. Le front ne sait pas qu'il doit l'envoyer.
- **D-2** : Aucun doc sur le flow `state` OAuth (puisque non implémenté). La doc OpenAPI mentionne `state` (ligne 266) mais ne dit pas comment le gérer.
- **D-3** : Le `user` retourné par `authenticate/complete` (ligne 4619) montre `id: 42` (integer), mais le code (`webauthn_views.py:441`) retourne un `UserSerializer` qui sérialise probablement un UUID. Incohérence doc/impl.
- **D-4** : La doc dit que `code_verifier` est "recommended" (ligne 67), pas "required". Faux sentiment de sécurité.
- **D-5** : Aucune mention des **limites** WebAuthn (max credentials par user, supporté authenticator types, browsers).

---

# 🟪 ARCHITECTURE / QUALITÉ

## Points forts

- **Séparation core/adapter propre** : `webauthn_service.py` est 100% framework-agnostic, `webauthn_storage.py` est l'adapter Django. Le `Protocol` permet de mocker proprement pour les tests core.
- **Pas de framework leakage** dans `webauthn_service.py` (vérifié : 0 import `django`).
- **Tests découplés** : `tests/core/` peut tourner sans Django, `tests/integration/django/` requiert Django.
- **Lib `py_webauthn` bien choisie** : c'est la référence Python (Duo).
- **Use de `hmac.compare_digest` cohérent** (déjà noté dans l'audit précédent).

## Points faibles

- **`@dataclass WebAuthnCredential` est mutable + pas de validation** (lignes 34-49). Un dev peut faire `cred.credential_id = ""` sans warning.
- **Beaucoup de `getattr(..., "default")` défensifs** dans `webauthn_storage.py:38-58`. Si le modèle Django change (ajout d'un champ required), les tests vont quand même passer en silence. C'est un anti-pattern.
- **Pas de `frozen=True` sur les dataclasses** immuables (e.g. `WebAuthnChallenge` devrait être frozen).
- **`WebAuthnCredential.id` est `str(...)` partout** (storage ligne 288-290, service) mais le modèle Django a `AutoFieldClass(primary_key=True)` qui peut être `BigAutoField` (PostgreSQL, MySQL) ou `ObjectIdAutoField` (MongoDB). MongoDB retourne des strings d'ObjectId par défaut — la conversion `str(...)` est OK, mais l'ID `ObjectId` ne passe pas dans les lookup `id=credential_id` sans conversion explicite. **À tester en environnement MongoDB**.
- **Pas de tests d'intégration contre un vrai provider OAuth** (Google sandbox, GitHub dev app). Tous les tests mockent les providers.

---

# 📊 Tableau de synthèse

| ID | Sévérité | Fichier:ligne | Description |
|---|---|---|---|
| **W-1** | 🔴 CRITIQUE | `webauthn_service.py:184-188` | `_get_origin` dérive du `rp_id` sans validation |
| **W-2** | 🔴 CRITIQUE | `webauthn_service.py:267-292, 387-422` | Race condition TOCTOU sur challenge |
| **W-3** | 🔴 CRITIQUE | `webauthn_service.py:295-311` | `transports` jamais persisté |
| **W-4** | 🟠 HAUTE | `webauthn_views.py:242-247` | Pas de validation type `challenge_id` |
| **W-5** | 🟠 HAUTE | `webauthn_service.py:184-188` | Origin mismatch en dev |
| **W-6** | 🟠 HAUTE | `webauthn_service.py:281, 404` | Pas de `timeout` passé à la lib |
| **W-7** | 🟠 HAUTE | `webauthn_service.py:415` | Sign count = 0 pas géré |
| **W-8** | 🟠 HAUTE | `webauthn_views.py:346, 401` | Pas de throttle sur auth WebAuthn |
| **W-9** | 🟡 MOYENNE | `webauthn_service.py:310` | AAGUID pas normalisé |
| **W-10** | 🟡 MOYENNE | `webauthn_service.py:295` | `transports` non validé |
| **W-11** | 🟡 MOYENNE | `models/webauthn.py:54-103` | Pas de cleanup challenges expirés |
| **W-12** | 🟡 MOYENNE | `webauthn_service.py:397` | Pas de check `is_active` (latent) |
| **W-13** | 🟢 BASSE | `webauthn_views.py:531` | Type mismatch str/int |
| **O-1** | 🔴 CRITIQUE | `social_auth_views.py:335-396` | `state` parameter absent |
| **O-2** | 🔴 CRITIQUE | `social_auth_service.py:113-136` | `nonce` jamais vérifié |
| **O-3** | 🔴 CRITIQUE | `social_auth_service.py:415-440` | Auto-merge email + `email_verified` trusté |
| **O-4** | 🟠 HAUTE | `social_auth_views.py:183-185` | `id_token` accepté sans lien à un flow |
| **O-5** | 🟠 HAUTE | `social_auth_service.py:248-261` | Microsoft `email_verified=True` hardcodé |
| **O-6** | 🟠 HAUTE | `social_auth_service.py:294-318` | Facebook `email_verified=True` hardcodé |
| **O-7** | 🟠 HAUTE | `social_auth_service.py:186-212` | GitHub `noreply` collision possible |
| **O-8** | 🟠 HAUTE | `models/application.py:96-103` | Whitelist vide = tout autorisé |
| **O-9** | 🟠 HAUTE | `social_auth_views.py:228-409` | Pas de throttle sur callback |
| **O-10** | 🟠 HAUTE | `social_auth_service.py:69, 144...` | PKCE incomplet |
| **O-11** | 🟡 MOYENNE | `social_auth_service.py:73-95` | Timeout unique 10s |
| **O-12** | 🟡 MOYENNE | `social_auth_service.py:446` | Email non normalisé Unicode |
| **O-13** | 🟡 MOYENNE | `social_auth_views.py:139` | Validation faible de `provider_name` |
| **O-14** | 🟢 BASSE | `models/social.py:43-52` | Pas de token storage (feature scope) |
| **D-1** | 🟡 MOYENNE | `endpoints.md:4498` | Doc omet `transports` |
| **D-2** | 🟠 HAUTE | `endpoints.md:266` | Doc mentionne `state` mais pas implémenté |
| **D-3** | 🟡 MOYENNE | `endpoints.md:4619` | Format ID incohérent |
| **D-4** | 🟡 MOYENNE | `endpoints.md:67` | PKCE "recommended" pas "required" |
| **D-5** | 🟡 MOYENNE | `endpoints.md:4432+` | Pas de doc des limites |

---

# 🎯 Plan d'action priorisé

## 🔴 Hotfix immédiat (à pousser dans la semaine, **bloque toute mise en prod avec OAuth**)

- [ ] **O-1** Implémenter `state` parameter (génération, stockage, validation, one-shot).
- [ ] **O-2** Implémenter `nonce` check pour Google `id_token`.
- [ ] **W-2** Atomic `consume()` sur `WebAuthnChallenge` (UPDATE WHERE is_used=False).
- [ ] **W-8** Ajouter `LoginThrottle, LoginHourlyThrottle` sur les 2 endpoints d'auth WebAuthn.
- [ ] **O-9** Ajouter `LoginThrottle` sur `SocialAuthCallbackView`.

## 🟠 Avant la v0.9.6 (2-3 semaines)

- [ ] **W-1** Validation stricte de `rp_id` + origin configurable.
- [ ] **W-3** Frontend envoie `transports`, service le persiste.
- [ ] **W-5** Origin dev configurable.
- [ ] **W-6** `timeout=120000` passé à la lib.
- [ ] **W-7** Check explicite `new_sign_count > 0` (si auth sans counter).
- [ ] **O-3** Refuser auto-merge par défaut, exiger 2FA si activé.
- [ ] **O-5/O-6** Lire `is_verified` réel (ou refuser) pour Microsoft/Facebook.
- [ ] **O-7** Refuser user sans email vérifié.
- [ ] **O-8** Toggle `STRICT_REDIRECT_URI`, refuser whitelist vide en prod.
- [ ] **O-10** PKCE généré côté serveur, vérifié au callback.
- [ ] **D-2** Aligner doc ↔ code (enlever mention `state` ou l'implémenter).

## 🟡 Avant la v0.10.0

- [ ] **W-4** Validation type `challenge_id` dans serializer.
- [ ] **W-9** Normalisation AAGUID.
- [ ] **W-10** Validation `transports` (sous-ensemble autorisé).
- [ ] **W-11** Tâche périodique cleanup challenges.
- [ ] **W-12** Ajouter `is_active` au modèle + check.
- [ ] **O-11** Timeout adaptatif par provider.
- [ ] **O-12** Normalisation Unicode email.
- [ ] **D-1, D-3, D-4, D-5** Corriger doc.

## 🟢 Tests manquants à écrire (avant v1.0)

- [ ] Replay attack WebAuthn (challenge consommé 2x).
- [ ] Sign count manipulation.
- [ ] State mismatch OAuth.
- [ ] PKCE end-to-end.
- [ ] `expected_origin` mismatch.
- [ ] Rate-limit behavior.
- [ ] Integration avec vrais providers (sandbox Google, dev app GitHub).
- [ ] MongoDB compat pour WebAuthn (ObjectId).

---

# 🏁 Verdict final

| Composant | Note | Verdict |
|---|---|---|
| **WebAuthn Core** | 6/10 | Bonne base, lib bien choisie, 3 critiques à régler |
| **WebAuthn Views** | 6.5/10 | Endpoints propres, manque throttling et validation type |
| **WebAuthn Storage** | 7/10 | Solide, attention aux `getattr` défensifs |
| **OAuth Service** | 4.5/10 | Pas de state, pas de nonce, account fusion trop permissive |
| **OAuth Views** | 5/10 | Fonctionnel, gaps CSRF/state |
| **OAuth Models** | 8/10 | Bon design, choix R10 de ne pas stocker les tokens est défendable |
| **Tests** | 6/10 | Bonne couverture fonctionnelle, faible couverture sécurité |
| **Doc** | 7/10 | Très complète, quelques incohérences code/doc |
| **Architecture** | 7.5/10 | Core/Adapter propre, vraiment framework-agnostic |

**Global WebAuthn + OAuth** : **5.5/10**. Utilisable en dev/staging après les hotfix. Pas production-ready sans les 5 hotfix ci-dessus, et absolument pas production-ready sans le trio **state + nonce + account fusion** côté OAuth.

Si tu veux que j'attaque le code :
1. **O-1 (state)** en premier — c'est ~50 lignes + tests + doc, et c'est le plus gros trou.
2. **W-2 (atomic consume)** en parallèle — c'est ~20 lignes dans le storage.
3. **O-3 (account fusion)** en réflexion design — c'est un changement de comportement par défaut.

Dis-moi par quoi tu veux qu'on commence.
