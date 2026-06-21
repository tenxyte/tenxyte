# 📋 Plan d'action — WebAuthn + OAuth

> Basé sur `plan/audit-webauthn-oauth.md` du 2026-06-12.
> **Cible** : WebAuthn 8/10, OAuth 8/10. **Release gating** : 0 finding 🔴 restant pour autoriser la prod.

## Convention de sévérité

- 🔴 **CRITIQUE** : bloque toute mise en prod (exploit à distance, account takeover, CSRF)
- 🟠 **HAUTE** : doit être résolu avant v0.9.6 (defense-in-depth, vecteur connu)
- 🟡 **MOYENNE** : dette / qualité, à régler avant v0.10.0
- 🟢 **BASSE** : nice to have, scope feature

## Convention de statut

- `[ ]` à faire
- `[~]` en cours
- `[x]` terminé
- `[!]` bloqué

## Convention de référence

Chaque item référence son ID d'audit (W-1 à W-13 pour WebAuthn, O-1 à O-14 pour OAuth, D-1 à D-5 pour Doc).

---

# 🔴 Phase 1 — Hotfix sécurité (à pousser dans la semaine)

> **Durée estimée** : 3-5 jours ouvrés.
> **Gating** : aucun utilisateur ne doit pouvoir s'authentifier via OAuth ou WebAuthn en prod sans ces fixes.
> **Release** : hotfix `0.9.5.1` (correctif de sécurité, pas de nouvelle feature).

## 1.1 — WebAuthn : atomic consume du challenge (W-2)

- [ ] **1.1.1** — Modifier `src/tenxyte/adapters/django/webauthn_storage.py:431-440` (méthode `consume`).
  - Remplacer le pattern `get()` + `save()` par un `update()` atomique :
    ```python
    def consume(self, challenge_id: str) -> bool:
        updated = WebAuthnChallengeModel.objects.filter(
            id=challenge_id, is_used=False, expires_at__gt=timezone.now()
        ).update(is_used=True)
        return updated == 1
    ```
  - Importer `from django.utils import timezone` (déjà présent dans le modèle).
- [ ] **1.1.2** — Modifier `src/tenxyte/core/webauthn_service.py:267-292` (complete_registration) pour :
  - Vérifier que `consume(challenge_id)` retourne `True` **après** `verify_registration_response`.
  - Si `False` → lever `RegistrationResult(success=False, error="Challenge already used or expired")`.
- [ ] **1.1.3** — Idem dans `complete_authentication` (lignes 387-422).
- [ ] **1.1.4** — Écrire un test de race condition dans `tests/integration/django/unit/test_webauthn.py` :
  - Lancer 2 threads simultanés avec le même `challenge_id`.
  - Vérifier qu'**un seul** retourne `success=True`, l'autre `success=False` avec `"already used"`.
  - Utiliser `threading.Barrier(2)` pour synchroniser le départ.
- [ ] **1.1.5** — Écrire un test unitaire dans `tests/core/test_webauthn_service.py` :
  - Mocker le storage pour que `consume()` retourne `False` après une verify réussie.
  - Vérifier que le service retourne une erreur.

## 1.2 — WebAuthn : rate-limit sur les endpoints d'auth (W-8)

- [ ] **1.2.1** — Ajouter dans `src/tenxyte/views/webauthn_views.py` :
  - Import : `from ..throttles import LoginThrottle, LoginHourlyThrottle`.
  - `WebAuthnRegisterBeginView` : pas de throttle (utilisateur authentifié, JWT déjà requis).
  - `WebAuthnRegisterCompleteView` : pas de throttle (idem, JWT requis).
  - `WebAuthnAuthenticateBeginView` (ligne 273) : ajouter `throttle_classes = [LoginThrottle, LoginHourlyThrottle]`.
  - `WebAuthnAuthenticateCompleteView` (ligne 346) : ajouter `throttle_classes = [LoginThrottle, LoginHourlyThrottle]`.
- [ ] **1.2.2** — Écrire un test dans `tests/integration/django/unit/test_webauthn.py` :
  - Spam 20 requêtes `authenticate/begin` en 1 minute depuis la même IP.
  - Vérifier que les 11+ retournent 429 Too Many Requests.
- [ ] **1.2.3** — Documenter dans `docs/en/endpoints.md:4546+` que les endpoints d'auth sont rate-limités.

## 1.3 — OAuth : implémenter le `state` parameter (O-1)

- [ ] **1.3.1** — Créer un nouveau modèle `src/tenxyte/models/oauth_state.py` :
  ```python
  class OAuthState(models.Model):
      id = models.CharField(primary_key=True, max_length=64)  # token_urlsafe(32)
      user = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
      provider = models.CharField(max_length=32)
      redirect_uri = models.CharField(max_length=500)
      code_verifier = models.CharField(max_length=128, blank=True)  # pour PKCE
      created_at = models.DateTimeField(auto_now_add=True)
      expires_at = models.DateTimeField()
      consumed = models.BooleanField(default=False)
  ```
  - TTL par défaut 600s (10 min).
  - Index composite `(provider, expires_at)`.
- [ ] **1.3.2** — Migration `00XX_oauth_state.py` (Django).
- [ ] **1.3.3** — Ajouter une méthode de classe `OAuthState.generate(user, provider, redirect_uri, code_verifier=None)` :
  - Génère un token `secrets.token_urlsafe(32)`.
  - Crée l'instance avec `expires_at = now() + 600s`.
  - Retourne le token.
- [ ] **1.3.4** — Ajouter une méthode `consume(token) -> Optional[OAuthState]` :
  - Cherche par id + `consumed=False` + `expires_at > now()`.
  - UPDATE atomique `consumed=True` (cf. pattern W-2).
  - Retourne l'instance si succès, `None` sinon.
  - **One-shot** : la 2e utilisation retourne `None`.
- [ ] **1.3.5** — Créer un service `src/tenxyte/services/oauth_state_service.py` :
  - `initiate_state(user, provider, redirect_uri, code_verifier=None) -> str` (retourne le token).
  - `validate_and_consume_state(token, provider) -> Optional[OAuthState]`.
- [ ] **1.3.6** — Modifier `src/tenxyte/views/social_auth_views.py:135-225` (`SocialAuthView.post`) :
  - Si on reçoit un `code` (flow authorization code), vérifier qu'un `state` est aussi présent.
  - Lire ou générer un `code_verifier` (PKCE) côté serveur.
  - Appeler `oauth_state_service.initiate_state(...)` → stocker le state.
  - Si state manquant → 400 `MISSING_STATE`.
  - Le state doit être renvoyé par le front dans le callback.
- [ ] **1.3.7** — Modifier `src/tenxyte/views/social_auth_views.py:335-396` (`SocialAuthCallbackView.get`) :
  - Lire `state` depuis `request.GET.get("state")`.
  - Si manquant → 400 `MISSING_STATE`.
  - Appeler `oauth_state_service.validate_and_consume_state(state, provider_name)`.
  - Si invalide/expiré/déjà consommé → 400 `INVALID_STATE`.
  - Récupérer `code_verifier` du state, le passer à `exchange_code()`.
- [ ] **1.3.8** — Modifier `src/tenxyte/services/social_auth_service.py:69, 144, 214, 263, 320` :
  - Rendre `code_verifier` **obligatoire** (pas `Optional`) dans le flow authorization code.
  - Garder `code_verifier=None` autorisé uniquement pour `id_token` flow Google.
- [ ] **1.3.9** — Écrire des tests dans `tests/integration/django/unit/test_oauth_state.py` :
  - `test_initiate_creates_state`
  - `test_validate_consumes_state_one_shot` (2e utilisation → None)
  - `test_validate_expired_state_returns_none`
  - `test_validate_wrong_provider_returns_none`
  - `test_view_missing_state_returns_400`
  - `test_view_invalid_state_returns_400`
  - `test_view_expired_state_returns_400`
  - `test_callback_with_state_creates_user` (end-to-end)
- [ ] **1.3.10** — Documentation :
  - Mettre à jour `docs/en/endpoints.md:266-272` : expliquer que `state` est **required** (pas "recommended").
  - Ajouter un exemple curl montrant le flow complet.
  - Doc FR miroir.

## 1.4 — OAuth : `nonce` sur Google `id_token` (O-2 + O-4)

- [ ] **1.4.1** — Réutiliser le modèle `OAuthState` (créé en 1.3.1) pour stocker le `nonce` :
  - Ajouter un champ `nonce = models.CharField(max_length=128, blank=True, default="")`.
  - Migration.
- [ ] **1.4.2** — Modifier `oauth_state_service.initiate_state()` pour accepter un `nonce` optionnel.
- [ ] **1.4.3** — Modifier `SocialAuthView.post` : si `provider="google"` et on est sur un flow `id_token`, générer un `nonce` (32 bytes URL-safe) et le passer en `state` (ou le combiner).
- [ ] **1.4.4** — Modifier `src/tenxyte/services/social_auth_service.py:113-136` (`verify_id_token`) :
  - Récupérer le `nonce` attendu depuis `OAuthState` (par `id_token` lookup, ou via state_id dans le body).
  - Après `google_id_token.verify_oauth2_token(...)`, vérifier `idinfo.get("nonce") == expected_nonce`.
  - Si mismatch → return None.
- [ ] **1.4.5** — Modifier `SocialAuthView.post` (ligne 183) :
  - Refuser `id_token` flow si le state/nonce n'a pas été généré par Tenxyte.
  - Retourner 400 `MISSING_NONCE` ou `INVALID_NONCE` sinon.
- [ ] **1.4.6** — Tests :
  - `test_google_id_token_without_nonce_rejected`
  - `test_google_id_token_with_wrong_nonce_rejected`
  - `test_google_id_token_with_correct_nonce_accepted`
- [ ] **1.4.7** — Documentation `endpoints.md` section Google id_token : expliquer le flow nonce.

## 1.5 — OAuth : throttle sur le callback (O-9)

- [ ] **1.5.1** — Dans `src/tenxyte/views/social_auth_views.py:228-409` (`SocialAuthCallbackView`) :
  - Ajouter `throttle_classes = [LoginThrottle, LoginHourlyThrottle]`.
- [ ] **1.5.2** — Test : spam de `GET /social/google/callback/?code=invalid` → 429 après 10 tentatives.
- [ ] **1.5.3** — Doc : mentionner le rate-limit.

---

# 🟠 Phase 2 — Avant v0.9.6 (2-3 semaines)

> **Durée estimée** : 2-3 semaines.
> **Gating** : 0 finding 🟠 restant côté OAuth, 0 finding 🔴/🟠 WebAuthn.
> **Release** : `0.9.6` (correctifs de sécurité + features de défense).

## 2.1 — WebAuthn : validation stricte de `rp_id` (W-1)

- [ ] **2.1.1** — Créer `src/tenxyte/core/validators.py::validate_rp_id` :
  - Regex : `^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$`.
  - Rejeter `localhost` sauf si `settings.DEBUG = True` (configurable).
  - Rejeter les IDN (pas de `xn--` pour l'instant).
- [ ] **2.1.2** — Modifier `WebAuthnService.__init__` (ligne 161) :
  - Appeler `validate_rp_id(self.rp_id)` à l'init.
  - Lever `ValueError` si invalide.
- [ ] **2.1.3** — Modifier `_get_origin()` (ligne 184) :
  - Rendre configurable via `settings.TENXYTE_WEBAUTHN_ORIGIN` (au lieu de dériver du rp_id).
  - Documenter le besoin.
- [ ] **2.1.4** — Tests :
  - `test_rp_id_validation_rejects_invalid` (caractères spéciaux, double dots, etc.)
  - `test_rp_id_localhost_rejected_in_production`
  - `test_get_origin_uses_settings_override`

## 2.2 — WebAuthn : `transports` persistés (W-3)

- [ ] **2.2.1** — Modifier `src/tenxyte/views/webauthn_views.py:230-248` :
  - Lire `request.data.get("transports", [])`.
  - Valider : sous-ensemble de `{usb, nfc, ble, internal, hybrid, smart-card, cable, test}`.
  - Passer au service.
- [ ] **2.2.2** — Modifier `src/tenxyte/core/webauthn_service.py:295-311` :
  - Accepter `transports: List[str] = field(default_factory=list)` dans le constructeur de `WebAuthnCredential`.
  - Stocker dans l'instance.
- [ ] **2.2.3** — Tests :
  - `test_complete_registration_persists_transports`
  - `test_complete_registration_rejects_invalid_transports`
- [ ] **2.2.4** — Documentation `endpoints.md:4498` :
  - Ajouter le champ `transports` dans l'exemple de payload.
  - Lister les valeurs autorisées.

## 2.3 — WebAuthn : origin configurable (W-5)

- [ ] **2.3.1** — Ajouter `WEBAUTHN_ORIGIN` dans `src/tenxyte/conf/social.py:65-70` (à côté de `WEBAUTHN_RP_ID`).
  - Default : `https://{rp_id}`.
  - Dev override possible : `http://localhost:8000`.
- [ ] **2.3.2** — Modifier `WebAuthnService._get_origin()` pour utiliser `settings.WEBAUTHN_ORIGIN`.
- [ ] **2.3.3** — Tests `test_get_origin_uses_settings_override` (couvre W-5 + W-1).
- [ ] **2.3.4** — Doc : ajouter une section "WebAuthn Configuration" dans `docs/en/security.md` ou `docs/en/settings.md`.

## 2.4 — WebAuthn : `timeout` passé à la lib (W-6)

- [ ] **2.4.1** — Modifier `WebAuthnService.begin_registration` (ligne 226) :
  - Passer `timeout=120000` (120s) à `webauthn.generate_registration_options()`.
- [ ] **2.4.2** — Idem `begin_authentication` (ligne 354).
- [ ] **2.4.3** — Idem `complete_registration` et `complete_authentication` (paramètre `timeout` supporté par la lib).
- [ ] **2.4.4** — Rendre le timeout configurable via `WEBAUTHN_TIMEOUT_MS`.
- [ ] **2.4.5** — Tests : mocker la lib pour vérifier que `timeout=` est passé avec la bonne valeur.

## 2.5 — WebAuthn : sign_count = 0 géré (W-7)

- [ ] **2.5.1** — Vérifier la version exacte de `py_webauthn` utilisée (probablement 2.x).
  - Lire `requirements-core.txt:30` (vu dans l'audit : `webauthn>=2.7.0`).
  - Consulter la doc pour la gestion de sign_count=0.
- [ ] **2.5.2** — Si la lib l'accepte : ajouter un check explicite dans `complete_authentication` (ligne 415) :
  ```python
  if (verification.new_sign_count != 0
      and verification.new_sign_count <= stored_credential.sign_count):
      return AuthenticationResult(success=False, error="Sign count replay detected")
  ```
- [ ] **2.5.3** — Si la lib lève déjà `InvalidSignCount` : ne rien faire, juste un test de régression.
- [ ] **2.5.4** — Tests :
  - `test_authentication_with_decreasing_sign_count_rejected`
  - `test_authentication_with_zero_sign_count_accepted_on_first_use`
  - `test_authentication_with_zero_sign_count_rejected_on_replay`

## 2.6 — OAuth : account fusion sécurisé (O-3)

- [ ] **2.6.1** — Décision design (à valider avec le mainteneur) :
  - Option A : **désactiver l'auto-merge par défaut** (default `False`, exiger opt-in explicite).
  - Option B : **2FA requis** pour activer l'auto-merge.
  - Option C : **email de confirmation** envoyé au compte existant.
  - Recommandation : **A + C** (le plus simple, le plus safe).
- [ ] **2.6.2** — Implémenter Option A :
  - Modifier `src/tenxyte/services/social_auth_service.py:431-438` :
    - Si `auto_merge=True` ET `user` existe par email → 2FA requis côté user existant.
  - Si Option C : envoyer un email de confirmation avec un lien à cliquer dans 24h.
- [ ] **2.6.3** — Tests :
  - `test_auto_merge_disabled_by_default`
  - `test_auto_merge_with_2fa_required`
  - `test_auto_merge_sends_confirmation_email`
- [ ] **2.6.4** — Doc : expliquer clairement le comportement dans `endpoints.md` section OAuth.

## 2.7 — OAuth : Microsoft `email_verified` réel (O-5)

- [ ] **2.7.1** — Étudier la Microsoft Graph API pour récupérer un champ "is_verified".
  - Pas de flag natif. Options :
    1. Appeler `https://graph.microsoft.com/v1.0/me?$select=mail,otherMails,proxyAddresses` et vérifier que `mail` n'est pas vide.
    2. Considérer vérifié si le user est dans le même tenant que l'app Azure AD.
    3. **Mieux** : rejeter `email_verified` pour les guests (`userType=guest`).
- [ ] **2.7.2** — Implémenter l'option 3 :
  - Ajouter `user_type` à la réponse.
  - `email_verified = (user_type == "member")`.
- [ ] **2.7.3** — Tests avec un mock Microsoft Graph retournant `userType=guest`.

## 2.8 — OAuth : Facebook `is_verified` réel (O-6)

- [ ] **2.8.1** — Modifier `src/tenxyte/services/social_auth_service.py:294-303` :
  - Ajouter `is_verified` aux fields : `?fields=id,email,first_name,last_name,picture,is_verified`.
  - Lire `data.get("is_verified", False)` au lieu de hardcoder `True`.
- [ ] **2.8.2** — Tests mockés pour les 2 cas (vérifié / non vérifié).

## 2.9 — OAuth : GitHub `noreply` collision (O-7)

- [ ] **2.9.1** — Modifier `src/tenxyte/services/social_auth_service.py:186-212` :
  - Si `email` est `None` ou `""` ou se termine par `@users.noreply.github.com` → `email_verified=False`.
  - Refuser la création d'user sans email vérifié.
- [ ] **2.9.2** — Tests :
  - `test_github_noreply_email_rejected`
  - `test_github_no_email_rejected`

## 2.10 — OAuth : redirect_uri strict (O-8)

- [ ] **2.10.1** — Ajouter `TENXYTE_STRICT_REDIRECT_URI` dans `src/tenxyte/conf/social.py` (default `True` en prod, `False` en dev).
- [ ] **2.10.2** — Modifier `src/tenxyte/models/application.py:96-103` (`is_redirect_uri_allowed`) :
  - Si `strict=True` et `redirect_uris` est vide → lever une `ImproperlyConfigured`.
  - Si `redirect_uris` non vide → match exact (déjà le cas).
- [ ] **2.10.3** — Ajouter validation scheme dans `is_redirect_uri_allowed` :
  - `https://` requis en prod.
  - `http://` autorisé uniquement pour `localhost` ou `127.0.0.1`.
- [ ] **2.10.4** — Tests :
  - `test_redirect_uri_strict_rejects_empty_whitelist_in_prod`
  - `test_redirect_uri_rejects_http_in_prod`
  - `test_redirect_uri_accepts_localhost_http_in_dev`
- [ ] **2.10.5** — Doc `application.md` : expliquer `STRICT_REDIRECT_URI`.

## 2.11 — OAuth : PKCE généré serveur (O-10)

- [ ] **2.11.1** — Le state (cf. 1.3) stocke déjà `code_verifier` côté serveur. Maintenant :
  - Quand `initiate_state()` est appelé sans `code_verifier`, en générer un :
    ```python
    code_verifier = base64url(secrets.token_bytes(32))
    code_challenge = base64url(hashlib.sha256(code_verifier.encode()).digest())
    ```
  - Stocker `code_verifier` dans `OAuthState`.
  - Renvoyer `code_challenge` au front (pour qu'il le passe au provider).
- [ ] **2.11.2** — Modifier `exchange_code()` pour passer le `code_verifier` au provider.
- [ ] **2.11.3** — Tests : flow complet PKCE end-to-end avec un provider mocké.

## 2.12 — Doc : aligner `state` (D-2)

- [ ] **2.12.1** — `docs/en/endpoints.md:266-272` : passer `state` de "recommended" à "**required**".
- [ ] **2.12.2** — `docs/fr/endpoints.md` : idem.
- [ ] **2.12.3** — Ajouter un diagramme de séquence montrant le flow state init/validate/consume.

---

# 🟡 Phase 3 — Avant v0.10.0 (qualité + tests de sécurité)

> **Durée estimée** : 4-6 semaines.
> **Gating** : tests d'intégration avec vrais providers (sandbox).
> **Release** : `0.10.0`.

## 3.1 — WebAuthn : validation type `challenge_id` (W-4)

- [ ] **3.1.1** — Modifier `src/tenxyte/views/webauthn_views.py:91-167, 170-269, 273-343, 346-453` :
  - Utiliser un `Serializer` au lieu de `request.data.get(...)` direct.
  - Définir `WebAuthnChallengeIdField(serializers.IntegerField)` avec `min_value=1, max_value=2^63`.
- [ ] **3.1.2** — Tests : payload avec `challenge_id="abc"` ou `=-1` ou `=None` → 400.

## 3.2 — WebAuthn : normalisation AAGUID (W-9)

- [ ] **3.2.1** — Modifier `src/tenxyte/core/webauthn_service.py:310` :
  - Utiliser `getattr(verification, "aaguid", None)` au lieu de `hasattr`.
  - Si `None` ou `UUID(...)` invalide → `""`.
- [ ] **3.2.2** — Tests : `verification.aaguid = None` → aaguid vide en base.

## 3.3 — WebAuthn : validation `transports` côté service (W-10)

- [ ] **3.3.1** — Ajouter un validateur dans `WebAuthnCredential` :
  ```python
  ALLOWED_TRANSPORTS = {"usb", "nfc", "ble", "internal", "hybrid", "smart-card", "cable", "test"}
  ```
  - `__post_init__` valide que tous les transports sont dans la whitelist.
- [ ] **3.3.2** — Tests : transport invalide → `ValueError` au create.

## 3.4 — WebAuthn : cleanup challenges expirés (W-11)

- [ ] **3.4.1** — Vérifier l'existence de la commande `tenxyte_cleanup` (mentionnée dans le changelog 0.9.1.7).
  - Lire `src/tenxyte/management/commands/tenxyte_seed.py` (vu dans l'audit précédent).
- [ ] **3.4.2** — Si elle existe : ajouter le nettoyage WebAuthnChallenge.
  ```python
  WebAuthnChallengeModel.objects.filter(expires_at__lt=timezone.now()).delete()
  ```
- [ ] **3.4.3** — Si elle n'existe pas : créer `tenxyte_cleanup --webauthn`.
- [ ] **3.4.4** — Ajouter un index composite `(expires_at, is_used)` pour la perf.
- [ ] **3.4.5** — Tests : créer 100 challenges, en expirer 50, vérifier que cleanup en supprime 50.

## 3.5 — WebAuthn : `is_active` sur credential (W-12)

- [ ] **3.5.1** — Migration : ajouter `is_active = models.BooleanField(default=True)` à `WebAuthnCredential`.
- [ ] **3.5.2** — Modifier `WebAuthnService.complete_authentication` (ligne 397) :
  - Si `stored_credential.is_active == False` → return error.
- [ ] **3.5.3** — Modifier `delete_credential` pour faire un **soft-delete** (set `is_active=False`) au lieu d'un hard delete.
- [ ] **3.5.4** — Tests : credential inactive → auth rejected.
- [ ] **3.5.5** — Décision : faut-il une tâche périodique de hard-delete des credentials inactives > 90 jours ? (GDPR).

## 3.6 — WebAuthn : type mismatch str/int (W-13)

- [ ] **3.6.1** — Modifier `src/tenxyte/views/webauthn_views.py:531` :
  - Garder `credential_id` en `int` côté URL (DRF le convertit), passer en `str` au service pour cohérence.
- [ ] **3.6.2** — Tests : `credential_id="abc"` dans l'URL → 400 ou 404 (pas 500).

## 3.7 — OAuth : timeout adaptatif par provider (O-11)

- [ ] **3.7.1** — Ajouter `SOCIAL_<PROVIDER>_TIMEOUT` settings (default 10s).
- [ ] **3.7.2** — Modifier `AbstractOAuthProvider._get` et `_post` pour utiliser le timeout du provider courant.
- [ ] **3.7.3** — Tests : mocker `requests.get` avec un `side_effect=requests.Timeout` → graceful error.

## 3.8 — OAuth : normalisation email Unicode (O-12)

- [ ] **3.8.1** — Helper `normalize_email(email: str) -> str` dans `src/tenxyte/core/validators.py` :
  ```python
  import unicodedata
  return unicodedata.normalize("NFC", email).lower().strip()
  ```
- [ ] **3.8.2** — Appliquer dans `SocialAuthService.authenticate` (ligne 446), `register`, `login`.
- [ ] **3.8.3** — Tests : `"CAFÉ@example.com"` (NFD) et `"café@example.com"` (NFC) → même user.

## 3.9 — OAuth : validation `provider_name` (O-13)

- [ ] **3.9.1** — Ajouter un `ChoiceField` dans le serializer du path param.
- [ ] **3.9.2** — Tests : `provider="google/../etc/passwd"` → 404 (Django URL resolver le bloque déjà, mais defense-in-depth).

## 3.10 — Tests d'intégration OAuth avec vrais providers

- [ ] **3.10.1** — Google : créer une OAuth app de dev, configurer `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET` de test dans CI.
  - Utiliser un compte Google sandbox.
  - Tests : flow complet code + id_token + state.
- [ ] **3.10.2** — GitHub : créer une GitHub App pour les tests.
  - Tests : flow code, sans email visible, avec 2 emails.
- [ ] **3.10.3** — Microsoft : Azure AD tenant de dev.
  - Tests : flow code, member vs guest.
- [ ] **3.10.4** — Facebook : app dev, test users.
  - Tests : flow code, is_verified true/false.
- [ ] **3.10.5** — Utiliser `responses` ou `vcrpy` pour mocker les réponses HTTP.

## 3.11 — Tests d'intégration WebAuthn réels

- [ ] **3.11.1** — Setup d'un virtual authenticator (Chromium DevTools Protocol ou `py_webauthn` test helpers).
- [ ] **3.11.2** — Tests end-to-end : register → auth → delete credential.
- [ ] **3.11.3** — Tests : origin mismatch, sign_count manipulation, challenge reuse, etc.

## 3.12 — Documentation (D-1, D-3, D-4, D-5)

- [ ] **3.12.1** — `endpoints.md:4498` : ajouter `transports` dans l'exemple.
- [ ] **3.12.2** — `endpoints.md:4619` : clarifier que `id` est `str` (UUID) et pas `int`.
- [ ] **3.12.3** — `endpoints.md:67` : `code_verifier` "**required**" (pas "recommended").
- [ ] **3.12.4** — Ajouter section "WebAuthn Limitations" :
  - Max credentials par user : `TENXYTE_WEBAUTHN_MAX_CREDENTIALS_PER_USER` (à définir, default 10).
  - Browsers supportés : Chrome 67+, Firefox 60+, Safari 14+, Edge 18+.
  - Mobile : iOS 14+ (Safari + in-app browsers), Android 7+ (Chrome).
  - Pas de support IE / anciens navigateurs (évident).
- [ ] **3.12.5** — Ajouter section "OAuth Limitations" :
  - Providers actifs par défaut : 4.
  - Token storage : pas de re-refresh automatique (par design R10).
  - PKCE : obligatoire depuis 0.9.6.

## 3.13 — Feature scope (O-14) : token storage optionnel

- [ ] **3.13.1** — Décision : activer ou non le token storage ?
  - Si oui : utiliser `django-cryptography` (`EncryptedTextField`).
  - Si non : ajouter dans la doc que c'est "by design" et proposer un middleware.
- [ ] **3.13.2** — Si oui :
  - Migration : modifier `access_token` et `refresh_token` en `EncryptedTextField`.
  - Service : `social_auth_service` peut recevoir un `store_tokens=True`.
  - Tests : vérifier que les tokens sont chiffrés en DB (pas en clair).
- [ ] **3.13.3** — Si non : juste documenter.

---

# 🟢 Phase 4 — Tests de sécurité manquants (avant v1.0)

> **Durée estimée** : 2-3 semaines.
> **Gating** : 0 test de sécurité manquant (cf. liste ci-dessous).

## 4.1 — Tests WebAuthn manquants

- [ ] **4.1.1** — Replay attack : `challenge_id` consommé 2x.
- [ ] **4.1.2** — Sign count = 0 : replay entre 2 sessions.
- [ ] **4.1.3** — `expected_origin` mismatch : browser envoie un origin différent de celui attendu.
- [ ] **4.1.4** — AAGUID : `None`, string vide, UUID invalide.
- [ ] **4.1.5** — Transports : liste vide, valeurs inconnues, taille démesurée.
- [ ] **4.1.6** — Rate-limit : vérifier 429 après N requêtes.
- [ ] **4.1.7** — Resident key (usernameless) : flow complet.
- [ ] **4.1.8** — Credential inactive : auth rejected.
- [ ] **4.1.9** — Multi-tenant : 2 orgs, 1 user, ne peut pas se logger sur la mauvaise org.

## 4.2 — Tests OAuth manquants

- [ ] **4.2.1** — State mismatch : state généré pour user A, présenté par user B.
- [ ] **4.2.2** — State reuse : state déjà consommé → 400.
- [ ] **4.2.3** — State expiré : TTL dépassé → 400.
- [ ] **4.2.4** — PKCE : `code_verifier` invalide → token exchange échoue.
- [ ] **4.2.5** — PKCE : `code_verifier` manquant → 400.
- [ ] **4.2.6** — Nonce (Google id_token) : manquant, mismatch, replay.
- [ ] **4.2.7** — `email_verified=False` : refusé (avec et sans auto-merge).
- [ ] **4.2.8** — `redirect_uri` non whitelisté : 400.
- [ ] **4.2.9** — `redirect_uri` vide en mode strict : ImproperlyConfigured.
- [ ] **4.2.10** — Auto-merge + 2FA (ou email de confirmation).
- [ ] **4.2.11** — Account enumeration : timing attack sur `/social/<provider>/callback/`.
- [ ] **4.2.12** — CSRF sur callback (avec `state` invalide).
- [ ] **4.2.13** — Provider response mocké : 5xx, timeout, JSON malformé.

## 4.3 — Tests de compatibilité cross-DB

- [ ] **4.3.1** — WebAuthn avec MongoDB : vérifier que `id` ObjectId passe dans les lookups.
- [ ] **4.3.2** — OAuthState avec SQLite, PostgreSQL, MySQL, MongoDB.
- [ ] **4.3.3** — Tests multi-tenants avec chaque DB.

## 4.4 — Tests de performance

- [ ] **4.4.1** — 1000 challenges actifs, lookup en <50ms (index ?).
- [ ] **4.4.2** — 10000 WebAuthn credentials, list en <100ms.
- [ ] **4.4.3** — Auto-merge avec 10000 users existants : pas de N+1 ?

## 4.5 — Tests de sécurité "from the outside"

- [ ] **4.5.1** — `bandit` (security linter) sur tout le code WebAuthn + OAuth.
- [ ] **4.5.2** — `safety` / `pip-audit` sur les dépendances.
- [ ] **4.5.3** — OWASP ZAP ou Burp scan sur les endpoints (manuels).
- [ ] **4.5.4** — Revue externe (pentest) avant v1.0.

---

# 🟢 Phase 5 — Nice to have (post-1.0)

> Pas de gating, opportuniste.

## 5.1 — UX

- [ ] **5.1.1** — WebAuthn : UI pour renommer une credential.
- [ ] **5.1.2** — WebAuthn : UI pour voir le dernier usage et la géolocalisation.
- [ ] **5.1.3** — OAuth : UI pour lier/délier un provider.

## 5.2 — Features

- [ ] **5.2.1** — Support Apple Sign-In.
- [ ] **5.2.2** — Support LinkedIn OAuth2.
- [ ] **5.2.3** — Support Discord OAuth2.
- [ ] **5.2.4** — WebAuthn : attestation verification (vérifier que l'authenticator est de confiance).
- [ ] **5.2.5** — WebAuthn : enterprise attestation.

## 5.3 — Observabilité

- [ ] **5.3.1** — Métriques Prometheus : `tenxyte_webauthn_register_total`, `tenxyte_webauthn_auth_total`, `tenxyte_oauth_login_total{provider=...}`, `tenxyte_oauth_failure_total{provider=...}`.
- [ ] **5.3.2** — Tracing OpenTelemetry sur les flows auth.
- [ ] **5.3.3** — Sentry tags : `provider`, `step` (begin/complete/exchange).

## 5.4 — AIRS

- [ ] **5.4.1** — WebAuthn pour les agents IA (machine credentials).
- [ ] **5.4.2** — OAuth pour les agents (delegate token).

---

# 📊 Tableau récapitulatif

| Phase | Items | Sévérité max | Release cible | Effort |
|---|---|---|---|---|
| **Phase 1** | 5 sections / ~25 tâches | 🔴 Critique | hotfix `0.9.5.1` | 3-5 jours |
| **Phase 2** | 12 sections / ~50 tâches | 🟠 Haute | `0.9.6` | 2-3 semaines |
| **Phase 3** | 13 sections / ~45 tâches | 🟡 Moyenne | `0.10.0` | 4-6 semaines |
| **Phase 4** | 5 sections / ~35 tâches | 🟢 Tests sécu | `1.0.0` | 2-3 semaines |
| **Phase 5** | 4 sections / ~15 tâches | 🟢 Basse | post-1.0 | opportuniste |

# 🎯 Definition of Done

**Hotfix `0.9.5.1` (Phase 1 complétée)**
- [ ] W-2 : consume atomique
- [ ] W-8 : throttle sur auth WebAuthn
- [ ] O-1 : state parameter
- [ ] O-2 : nonce Google id_token
- [ ] O-9 : throttle callback OAuth
- [ ] Test de race condition WebAuthn qui passe
- [ ] Test de state mismatch qui passe
- [ ] Aucune régression sur les 2390 tests existants

**`0.9.6` (Phase 2 complétée)**
- [ ] 0 finding 🔴 / 🟠 WebAuthn
- [ ] 0 finding 🔴 / 🟠 OAuth
- [ ] PKCE obligatoire sur tous les flows
- [ ] State parameter documenté comme **required**
- [ ] Doc alignée avec le code

**`0.10.0` (Phase 3 complétée)**
- [ ] Tests d'intégration avec vrais providers (sandbox)
- [ ] Tests de sécurité WebAuthn (replay, sign_count, etc.)
- [ ] Tests de sécurité OAuth (CSRF, state, PKCE)
- [ ] Compatibilité MongoDB vérifiée
- [ ] Doc complète avec limitations

**`1.0.0` (Phase 4 complétée)**
- [ ] 0 finding restant (toutes sévérités)
- [ ] Tests de sécurité automatisés en CI
- [ ] Pentest externe effectué
- [ ] Bandit + Safety + ZAP verts

# 📝 Notes

- **Phase 1 d'abord, sans exception** : le state parameter manquant (O-1) est le plus gros trou. Tant qu'il n'est pas là, Tenxyte ne devrait pas être exposé en prod avec OAuth activé.
- **PKCE + state + nonce** forment un trio indissociable côté OAuth. Si tu n'en fais qu'un seul, fais **state** en priorité.
- **WebAuthn est plus solide qu'OAuth** au global. Concentre-toi sur OAuth d'abord.
- **Le state parameter est documenté mais pas implémenté** — c'est typique d'un code qui a suivi un tutoriel OAuth sans vraiment internaliser la sécurité. Le fix est ~50 lignes.

---

*Plan généré le 2026-06-12 à partir de `plan/audit-webauthn-oauth.md` du 2026-06-12.*
