#### Plan : login passwordless natif par OTP (WhatsApp/SMS) dans Tenxyte

  Objectif : deux nouveaux endpoints qui permettent de se connecter (ou
  s'inscrire) uniquement avec le téléphone + un code OTP, sans jamais
  dépendre d'un mot de passe. Cela supprime le contournement fragile
  (register-or-login + mot de passe dérivé), le 429 sur /register/, et le
  conflit avec le changement de mot de passe.


---------------------------------------------------------------------------

  1. Nouveau type d'OTP : login

    * Dans OTPService, ajouter :
      * generate_login_otp(user) → invalide les anciens otp_type="login"
        puis OTPCode.generate(user, "login", validity_minutes=10).
      * verify_login_otp(user, code) → même logique que
        verify_password_reset_otp (pas de flag is_*_verified à modifier),
retourne
        (bool, message).
    * Vérifier que "login" est une valeur acceptée par le champ otp_type de
      OTPCode (si choices restrictif dans le modèle, l'ajouter à la liste).

  2. Endpoint POST /api/v1/auth/login/otp/request/ (nouveau
     LoginOTPRequestView)

    * permission_classes = [AllowAny], throttles dédiés (nouveaux
      LoginOTPThrottle ~5/min et LoginOTPDailyThrottle, calqués sur
      PasswordResetThrottle) — jamais les throttles de /register/.
    * Body : { phone_country_code, phone_number } (serializer type
      PasswordResetRequestSerializer, sans email pour rester phone-only, ou
en
      le supportant aussi).
    * Logique :
      1. validate_application_required(request) (cohérent avec les autres
         vues).
      2. Chercher l'utilisateur par téléphone
         (User.objects.filter(phone_country_code=..., phone_number=...,
         is_deleted=False)).
      3. Paramètre de config TENXYTE_OTP_LOGIN_AUTO_REGISTER (bool) :
      * Si True et utilisateur inexistant → créer un compte phone-only (via
        register_user_with_core sans password, ou avec un mot de passe
aléatoire
        inutilisable), is_phone_verified=False.
      * Si False et inexistant → anti-énumération : renvoyer 200 identique
        sans envoyer d'OTP (comme password/reset/request/).
      4. Si utilisateur trouvé/créé : otp, raw =
         otp_service.generate_login_otp(user) puis
otp_service.send_phone_otp(user,
          raw).
      5. Réponse 200 : { message, otp_id, expires_at, channel: "sms" }
         (jamais révéler l'existence si auto-register off).

  3. Endpoint POST /api/v1/auth/login/otp/verify/ (nouveau
     LoginOTPVerifyView)

    * permission_classes = [AllowAny], throttle OTPVerifyThrottle (déjà
      existant, réutilisé).
    * Body : { phone_country_code, phone_number, code }.
    * Logique :
      1. validate_application_required(request).
      2. Résoudre l'utilisateur par téléphone ; si absent → 401 { code:
         "OTP_INVALID" } (générique).
      3. success, err = otp_service.verify_login_otp(user, code) ; si échec
         → 401 { error: err, code: "OTP_INVALID" | "OTP_EXPIRED" }.
      4. Contrôles de sécurité (réutiliser la logique de
         authenticate_by_phone_with_core) : compte actif, non banni, non
         verrouillé. Sinon 401/423.
      5. Marquer is_phone_verified = True (le login OTP prouve la possession
         du numéro).
      6. Vérifier la 2FA : si user.mfa_type != NONE, exiger un totp_code
         dans le body → sinon 401 { code: "2FA_REQUIRED" }, puis valider via

         TOTPService. (Réutilise exactement le bloc 2FA de LoginPhoneView.)
      7. update_last_login, résoudre app_id = str(request.application.id)
         (le fix déjà appliqué), générer tokens =
         jwt_service.generate_new_token_pair(user_id, application_id=app_id,

         extra_claims={...}).
      8. Persister le RefreshToken en base (comme
         authenticate_by_phone_with_core).
      9. Réponse 200 identique à /login/phone/ : { access_token,
         refresh_token, token_type, expires_in, refresh_expires_in, user,
         requires_2fa, ... }.

  4. Routing (urls.py)

  Ajouter sous la section Login :

  path("login/otp/request/", LoginOTPRequestView.as_view(),
  name="login_otp_request"),
  path("login/otp/verify/",  LoginOTPVerifyView.as_view(),
  name="login_otp_verify"),

  Et exporter les vues depuis views/__init__.py.

  5. Réglages (conf/settings)

    * TENXYTE_OTP_LOGIN_ENABLED (bool, défaut False) pour activer la
      fonctionnalité.
    * TENXYTE_OTP_LOGIN_AUTO_REGISTER (bool, défaut True) : créer le compte
      à la volée ou non.
    * TENXYTE_OTP_LOGIN_VALIDITY_MINUTES (défaut 10).





PasswordResetConfirmSerializer attend "code" alors que la doc des endpoint stipule "otp_code", ça doit être otp_code et non code comme actuellement

get_phone rajoutte un + à l'indicatif qui en contient déjà un, le fix: on stock l'indicatif sans le + en base ex. 229 au lieu de +229, ce n'est qu'a l'affichage ou à la serialisation qu'on applique le formattage rajoutant le plus. ça doit etre corrigé partout où c'est relevant ...