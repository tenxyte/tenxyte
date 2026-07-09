#### Plan : Phase 1 « Crédibilité » — passage en 1.0 (z_aud_1)

  Objectif : lever les bloqueurs de confiance identifiés dans AUDIT.md (F1, F2,
  F8, F11) pour rendre Tenxyte adoptable en entreprise. Quatre chantiers :
  contrat de stabilité + 1.0, inversion du packaging, posture de divulgation
  sécurité + signature des releases, et Apple Sign-In.

---------------------------------------------------------------------------

  1. Contrat de stabilité d'API (API freeze)

    * Définir la surface publique : endpoints documentés (endpoints.md),
      settings TENXYTE_*, modèles abstraits (AbstractUser/Role/Permission/
      Application), décorateurs (require_jwt, require_permission, ...),
      exports de tenxyte/__init__.py, serializers exportés, format des
      réponses d'erreur ({error, code, details}).
    * Politique SemVer : breaking uniquement en MAJOR ; toute dépréciation
      annoncée >= 1 version MINOR avant retrait, avec DeprecationWarning.
    * Documents : docs/en/stability.md + docs/fr/stability.md.
    * Test automatisé : snapshot des exports publics de tenxyte/__init__.py
      (échoue si un symbole public disparaît).

  2. Inversion des extras de packaging (breaking 1.0)

    État actuel (pyproject.toml v0.9.6.4) :
      dependencies = Django + DRF + cors + spectacular + google-auth + core...
      [core] = extra minimal, [django] = extra redondant, [fastapi], etc.

    État cible 1.0 :
      dependencies = core seul (PyJWT, bcrypt, pyotp, qrcode, cryptography,
                     Pillow, requests, pydantic, email-validator)
      [django]  = django, djangorestframework, django-cors-headers,
                  drf-spectacular, google-auth, google-auth-oauthlib
      [fastapi] = inchangé
      [all]     = django + fastapi + tous les extras features
      [core]    = conservé comme alias no-op de compatibilité (déprécié)

    * Garde d'import : `import tenxyte` NE DOIT PAS lever ImportError si
      Django est absent. Aujourd'hui tenxyte/__init__.py importe du Django ?
      → à vérifier ; introduire un lazy-load : les symboles Django-only
      (setup, modèles) ne sont importés qu'à l'accès, avec un message
      d'erreur clair « pip install tenxyte[django] » si le module manque.
    * Ultime release 0.9.x : DeprecationWarning à l'import annonçant le
      changement de packaging en 1.0 (+ note README).
    * Guide de migration : docs/*/MIGRATION_GUIDE.md section 0.9 → 1.0.

  3. SECURITY.md + processus CVE

    * SECURITY.md à la racine :
      - versions supportées (1.0.x ✅, 0.9.x correctifs critiques 6 mois, < 0.9 ❌)
      - canal : GitHub Private Vulnerability Reporting (Security Advisories)
      - SLA : accusé de réception 72 h, triage 7 j, correctif selon sévérité
        (critique 14 j, haute 30 j, moyenne/basse 90 j)
      - embargo coordonné 90 jours max, crédit du rapporteur
      - périmètre in/out (les dépendances tierces sont hors périmètre direct)
    * Processus interne documenté : advisory GitHub → correctif en privé →
      release patch → publication advisory + demande CVE via GitHub.
    * Activer Private Vulnerability Reporting sur le repo (action manuelle,
      voir manual_tests.md).

  4. Signature et attestation des releases

    * publish.yml : migrer vers PyPI Trusted Publishing (OIDC GitHub) —
      suppression du token PyPI long-lived des secrets.
    * Attestations PEP 740 : pypa/gh-action-pypi-publish >= v1.11 avec
      attestations: true (Sigstore sous le capot).
    * permissions: id-token: write sur le job de publish.
    * Tags git signés pour les releases (documentation du processus ;
      l'application est une action mainteneur).
    * environment: pypi protégé (approbation manuelle) sur le job.

  5. Apple Sign-In (provider `apple`)

    Spécificités Apple vs OAuth2 classique :
    * client_secret = JWT signé ES256 avec la clé privée .p8 du compte
      développeur (claims: iss=TEAM_ID, sub=CLIENT_ID/Services ID,
      aud=https://appleid.apple.com, exp<=6 mois). Généré à la volée.
    * Token endpoint: https://appleid.apple.com/auth/token
    * Pas de userinfo endpoint : les infos utilisateur viennent de
      l'id_token (JWT signé RS256 par Apple, à valider contre le JWKS
      https://appleid.apple.com/auth/keys : iss, aud, exp).
    * L'email peut être un private relay (@privaterelay.appleid.com) ;
      email_verified est fourni dans l'id_token (parfois string "true").
    * Le nom (first/last) n'est fourni QUE lors de la première autorisation,
      dans le corps du POST (champ `user` JSON) — jamais dans l'id_token.
      → le serializer/la vue doivent accepter un champ optionnel `user`.
    * response_mode=form_post obligatoire quand scope contient name/email
      (impact frontend, documenté ; le backend reste JSON-first).

    Implémentation :
    * AppleOAuthProvider(AbstractOAuthProvider) dans social_auth_service.py :
      - provider_name = "apple"
      - _generate_client_secret() (ES256 via cryptography, déjà dépendance)
      - exchange_code(code, redirect_uri) → POST auth/token
      - verify_id_token(id_token) → validation JWKS (PyJWT PyJWKClient)
      - get_user_info : Apple ne l'offre pas → décodage id_token validé
    * Settings (conf/social.py) : APPLE_CLIENT_ID, APPLE_TEAM_ID,
      APPLE_KEY_ID, APPLE_PRIVATE_KEY (contenu PEM du .p8)
    * SOCIAL_PROVIDERS défaut : + "apple"
    * SocialAuthService.authenticate : inchangé (dict normalisé identique)
    * Vue sociale : le path <provider> accepte "apple" ; réponses d'erreur
      INVALID_PROVIDER mises à jour (supported_providers)
    * Doc endpoints.md (EN/FR) : provider apple + notes form_post/relay.

  6. Préparation de l'audit de sécurité externe

    * docs/security-audit/threat-model.md : actifs, acteurs, surfaces
      d'attaque (STRIDE léger par domaine : JWT, OTP, WebAuthn, AIRS,
      reset password, orgs), hypothèses de déploiement.
    * docs/security-audit/audit-scope.md : périmètre proposé au prestataire
      (core/jwt_service, core/totp_service, core/webauthn_service,
      services/otp_service, services/agent_service, decorators, flows
      login/reset/2FA), hors-périmètre, environnement de test fourni.
    * docs/security-audit/pre-audit-checklist.md : auto-évaluation OWASP
      ASVS L2 ciblée (sections 2, 3, 6) avec statut par point.

  7. Release 1.0

    * pyproject.toml : version = "1.0.0",
      classifier "Development Status :: 5 - Production/Stable".
    * CHANGELOG 1.0.0 (breaking: packaging ; added: apple, SECURITY.md,
      attestations ; docs: stability).
    * MIGRATION_GUIDE section 0.9 → 1.0.
    * README : mise à jour install (tenxyte[django]) + badges.

---------------------------------------------------------------------------

  Contraintes transverses

  * Non-régression absolue : aucun endpoint, setting, modèle ou format de
    réponse existant ne change (hors packaging, qui est le breaking assumé
    et documenté de la 1.0).
  * Architecture hexagonale respectée : AppleOAuthProvider vit dans
    Django_Adapter (services legacy) comme les 4 providers existants ;
    aucun code Django dans tenxyte.core.
  * Les éléments purement process (activation GitHub PVR, config PyPI
    Trusted Publisher, commande de l'audit) sont tracés dans
    manual_tests.md avec procédure de vérification.
