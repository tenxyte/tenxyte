#### Plan : forcer le changement de mot de passe à la première connexion dans Tenxyte

  Objectif : couvrir le cas d'usage où un compte est créé par un tiers (un
  admin qui crée un compte employé, ou une organisation qui invite un membre)
  avec un mot de passe temporaire. À la première connexion, l'utilisateur doit
  être forcé de définir son propre mot de passe avant d'accéder à quoi que ce
  soit d'autre.

  Cas d'usage :
    * Un admin crée un compte pour un employé (ou une organisation invite un
      membre).
    * Le compte est créé avec un mot de passe temporaire (ou sans mot de passe).
    * À la première connexion, l'utilisateur est forcé de définir son propre
      mot de passe avant d'accéder à quoi que ce soit.

---------------------------------------------------------------------------

  Ce qui manque dans Tenxyte pour ce flux

  Il faudrait deux choses :

  1. Un flag must_change_password sur le modèle User

     must_change_password = models.BooleanField(default=False)

  2. Un middleware ou une vérification dans les vues protégées

     Quand un utilisateur avec must_change_password=True obtient ses tokens, la
     réponse signale l'obligation :

     {
       "access_token": "...",
       "must_change_password": true
     }

     Le client redirige vers l'écran de changement de mot de passe et bloque
     l'accès au reste. On restreint le token à un scope limité
     (scope: "password_change_only") pour que toutes les autres routes
     retournent 403 jusqu'à ce que le mot de passe soit changé.

     Une fois le mot de passe changé, must_change_password passe à False et les
     tokens normaux sont émis.

---------------------------------------------------------------------------

  Lien avec l'existant

  Ce cas couvre à la fois :

    * Compte créé par admin avec mot de passe temporaire →
      has_usable_password=True, must_change_password=True → passe par
      /password/change/.
    * Compte créé par invitation sans mot de passe → has_usable_password=False,
      must_change_password=True → passe par /password/set-initial/ (déjà
      implémenté par la feature passwordless-phone) ou un flow d'invitation par
      email/OTP.

---------------------------------------------------------------------------

  État actuel de la base (vérifié dans le code, feature passwordless-phone déjà
  livrée)

    * Le modèle User possède déjà le champ additif has_usable_password (défaut
      True) et la migration 0017_login_otp_type_and_passwordless_account. Un
      Passwordless_Account est un compte avec has_usable_password=False. Voir
      src/tenxyte/models/auth.py.
    * ChangePasswordView (src/tenxyte/views/password_views.py) :
      - refuse un Passwordless_Account (has_usable_password=False) avec
        PASSWORDLESS_ACCOUNT_USE_SET_INITIAL_PASSWORD (400) ;
      - sinon délègue la preuve à ReauthService.verify (mot de passe courant OU
        otp_code) et met à jour le mot de passe via le repository Core.
    * SetInitialPasswordView (src/tenxyte/views/password_views.py) : permet à un
      Passwordless_Account de poser son premier mot de passe après vérification
      d'un Login OTP, puis passe has_usable_password à True.
    * Le décorateur require_jwt (src/tenxyte/decorators.py) applique déjà un
      enforcement de scope : un token portant un claim "scope" non vide n'est
      accepté que sur les endpoints qui listent ce scope dans allowed_scopes
      (sinon 403 INSUFFICIENT_SCOPE). Le scope "2fa_setup_only" est déjà utilisé
      par le bootstrap 2FA admin. request.jwt_scope expose le scope courant.
    * Les endpoints de login (LoginEmailView, LoginPhoneView,
      LoginOTPVerifyView) et RefreshTokenView émettent les tokens via
      JWTService.generate_new_token_pair / generate_access_token, en passant des
      extra_claims. Le mécanisme d'extra_claims (dont "scope") est déjà en place.

  Conséquence : cette feature réutilise l'infrastructure existante (champ
  additif sur User + scope de token + endpoints /password/change/ et
  /password/set-initial/) plutôt que d'introduire une nouvelle couche. Le
  scope "password_change_only" est le pendant, pour le mot de passe, du scope
  "2fa_setup_only" déjà en production.

---------------------------------------------------------------------------

  Points d'implémentation pressentis (à détailler en conception)

    * Nouveau champ additif must_change_password (BooleanField, défaut False)
      sur AbstractUser, avec migration additive
      0018_user_must_change_password (AddField uniquement).
    * Nouveau scope de token "password_change_only" :
      - émis avec les tokens de login/refresh quand
        request.user.must_change_password est True ;
      - autorisé (allowed_scopes) uniquement sur /password/change/ et
        /password/set-initial/ (et endpoints strictement nécessaires au flow :
        /me/ en lecture éventuelle, /logout/), rejeté partout ailleurs avec
        403 INSUFFICIENT_SCOPE via require_jwt.
    * Les réponses de login incluent must_change_password: true/false (champ
      additif, jamais retiré).
    * ChangePasswordView et SetInitialPasswordView passent must_change_password
      à False après un changement réussi, puis émettent une nouvelle paire de
      tokens full-scope (upgrade), exactement comme le bootstrap 2FA le fait
      après confirmation.
    * Un endpoint/hook admin pour créer un compte avec mot de passe temporaire
      et must_change_password=True (peut réutiliser un chemin de création
      existant + setter du flag).
    * Réglage TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED (défaut
      False) pour activer le gating par scope, afin de préserver 100 % du
      comportement existant quand la feature n'est pas activée.

  Contrainte transverse : aucune régression. Tout est additif (nouveau champ,
  nouveau scope, nouveau réglage à défaut désactivé, nouveaux champs de réponse
  jamais retirés). Quand must_change_password reste False (cas de tous les
  comptes existants), le comportement doit être strictement identique à
  aujourd'hui.
