# base.md — z_aud_backlog : état des lieux et plan brut

## 1. Origine

L'analyse de couverture `AUDIT.md` vs `z_aud_1`…`z_aud_5` a identifié 4 items actionnables de
l'audit non livrés par aucune spec :

1. **F8 / §8 P1** : « Apple Sign-In + **4–6 providers sociaux supplémentaires** — effort
   faible — lever le blocage iOS ». Apple est livré (z_aud_1) ; le reste est en backlog.
   Contexte concurrentiel : « allauth en a 50+, Auth0 30+ » ; l'audit précise que
   « Google/GitHub/Microsoft/Facebook = 90 % des usages » — on complète par valeur ICP, pas
   par volume.
2. **F10** : « SMS backends limités (Twilio, NGH, Console). Vonage, AWS SNS, MessageBird
   absents. »
3. **§8 P0** (parenthèse) : « politique de divulgation (SECURITY.md, **bug bounty léger**) ».
   z_aud_1 livre SECURITY.md + GitHub Private Vulnerability Reporting ; le volet bounty
   n'existe pas.
4. **§4.3** : « fragilités DX résiduelles (erreurs d'encodage console Windows dans les
   scripts de validation, `Note: 2 secrets redacted` dans certains exemples de doc) ».

## 2. État des lieux mesuré dans le code

- **Providers sociaux** : `services/social_auth_service.py` — `AbstractOAuthProvider`
  (contrat : `provider_name`, `get_user_info(access_token)`,
  `exchange_code(code, redirect_uri, code_verifier)`, dict normalisé : provider_user_id,
  email, email_verified, first_name, last_name, avatar_url) + Google, GitHub, Microsoft,
  Facebook, Apple (z_aud_1). Le flux (state, PKCE, liaison utilisateur, `SocialConnection`)
  est mutualisé dans `SocialAuthService` — un nouveau provider = une classe + settings +
  enregistrement.
- **Backends SMS** : `backends/sms.py` — `BaseSMSBackend`, `TwilioBackend` (import paresseux
  `twilio.rest`, settings `TWILIO_*`, message d'erreur pointant `pip install
  tenxyte[twilio]`, numéro masqué dans les logs), NGH et Console. Le port et le pattern
  d'extra existent ; il manque 3 implémentations.
- **Sécurité** : `SECURITY.md` (z_aud_1) définit le canal privé et le SLA ; aucun périmètre
  de test autorisé, pas de safe harbor, pas de hall of fame.
- **DX** : les scripts (`scripts/validate_endpoints.py`, etc.) émettent des caractères
  non-cp1252 → échec sur console Windows sans `set PYTHONIOENCODING=utf-8` (contournement
  documenté dans les sessions de travail, jamais réparé à la source). Certains exemples de
  `docs/*/endpoints.md` contiennent des mentions de redaction au lieu de placeholders.

## 3. Plan brut

1. **Providers** — 6 classes dérivées d'`AbstractOAuthProvider` : GitLab (OIDC), LinkedIn
   (OIDC), Slack (OIDC), Discord (OAuth2), X/Twitter (OAuth2 + PKCE obligatoire), Bitbucket
   (OAuth2). Settings `TENXYTE_<PROVIDER>_*` dans `conf/social.py` (pattern Apple),
   enregistrement dans le registre de providers, endpoints sociaux existants inchangés
   (`/social/<provider>/`). Tests : conformité au dict normalisé par provider (réponses API
   fixturées), property test du contrat, non-régression des 5 providers en place.
2. **SMS** — `VonageBackend` et `MessageBirdBackend` en HTTP pur (requests, timeout,
   masquage), `SNSBackend` via boto3 (extra `[sns]`) ; extras `[vonage]`, `[messagebird]`
   dans `pyproject.toml` (Vonage/MessageBird HTTP pur : extra = marqueur de doc, aucune dep
   nouvelle) ; settings par backend ; sélection par le setting de backend SMS existant.
3. **Bug bounty léger** — section « Vulnerability Disclosure Program » dans SECURITY.md :
   périmètre (in : le package, les connecteurs z_aud_2 ; out : instances de démo, déni de
   service volumétrique, ingénierie sociale), safe harbor, engagement de réponse (réutilise
   le SLA z_aud_1), reconnaissance (hall of fame `docs/security/hall-of-fame.md` +
   récompenses discrétionnaires non monétaires). Processus de triage documenté côté
   mainteneur.
4. **DX** — les scripts de validation reconfigurent stdout/stderr en UTF-8 au démarrage
   (`sys.stdout.reconfigure(encoding="utf-8")`, garde version) ; audit des exemples de doc
   pour éliminer les artefacts de redaction (placeholders `<YOUR_...>`) ; re-validation
   complète.

## 4. Contraintes héritées

- Zéro modification des providers/backends existants ; migrations : aucune (aucun modèle
  nouveau) ; install par défaut inchangée (aucune dépendance ajoutée hors extras).
- Anti-énumération et non-régression des formes de réponses sociales existantes.
- Secrets de test : concaténations ; fixtures d'API providers dans l'allowlist gitleaks si
  nécessaire.
- Docs bilingues EN/FR pour chaque provider et backend ; `validate_endpoints.py` vert.
