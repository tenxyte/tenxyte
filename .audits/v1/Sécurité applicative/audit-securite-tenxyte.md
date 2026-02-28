# Audit de Sécurité Applicative — Tenxyte
## Module d'Authentification

---

| Champ | Valeur |
|-------|--------|
| **Produit audité** | Tenxyte — Package d'authentification Django |
| **Version** | `0.9.1.7` |
| **Date d'audit** | 2026-02-27 |
| **Classification** | CONFIDENTIEL |
| **Périmètre** | OWASP Top 10 (2021) · Flux d'authentification · En-têtes HTTP & TLS |
| **Statut global** | ⚠️ **NON PRÊT POUR PRODUCTION** — 4 vulnérabilités critiques à corriger |

---

## Résumé Exécutif

Tenxyte est un module d'authentification Django complet couvrant l'authentification par email/mot de passe, TOTP/2FA, magic links, OAuth social, WebAuthn/FIDO2 et les agents IA (AIRS). L'audit révèle une architecture globalement solide avec une bonne couverture des risques classiques (injection, enumeration, brute force), mais identifie **4 vulnérabilités critiques** et **11 points de risque élevé** qui doivent impérativement être adressés avant toute mise en production.

Les points forts incluent : l'utilisation de bcrypt pour les mots de passe, un système de rate limiting multicouche, un audit trail exhaustif, et des mécanismes anti-énumération. Les faiblesses majeures concernent des flags de désactivation globale de l'authentification, la falsifiabilité de tous les rate limits via `X-Forwarded-For`, et l'absence de protections cryptographiques sur les tokens en base de données.

---

## Tableau de Bord des Vulnérabilités

| ID | Catégorie | Titre | Sévérité | Statut |
|----|-----------|-------|----------|--------|
| T-01 | A01 | Flag `JWT_AUTH_ENABLED=False` — bypass total d'authentification | 🔴 CRITIQUE | Non corrigé |
| T-02 | C4 | `X-Forwarded-For` forgeable — bypass de tous les rate limits | 🔴 CRITIQUE | Non corrigé |
| T-03 | B6 | Account takeover via fusion OAuth sans vérification email | 🔴 CRITIQUE | Non corrigé |
| T-04 | A08 | Absence de lock de dépendances — risque supply chain | 🔴 CRITIQUE | Non corrigé |
| T-05 | A02 | Refresh tokens stockés en clair en base de données | 🟠 ÉLEVÉ | Non corrigé |
| T-06 | A02 | Secret TOTP stocké en clair en base de données | 🟠 ÉLEVÉ | Non corrigé |
| T-07 | B3 | Absence d'anti-replay TOTP (même code réutilisable) | 🟠 ÉLEVÉ | Non corrigé |
| T-08 | A01 | Mass assignment potentiel via `PATCH /me/` | 🟠 ÉLEVÉ | À vérifier |
| T-09 | A01 | IDOR potentiel sur endpoints admin | 🟠 ÉLEVÉ | À vérifier |
| T-10 | A05 | `CORS_ALLOW_ALL_ORIGINS` activable sans garde-fou | 🟠 ÉLEVÉ | Non corrigé |
| T-11 | C1 | `Strict-Transport-Security` absent par défaut | 🟠 ÉLEVÉ | Non corrigé |
| T-12 | A06 | `Pillow` et `py_webauthn` versions non contraintes | 🟡 MOYEN | Non corrigé |
| T-13 | B4 | Rotation de refresh token désactivable | 🟡 MOYEN | À vérifier |
| T-14 | A09 | Aucune purge automatique des audit logs | 🟡 MOYEN | Non corrigé |
| T-15 | B2 | Token magic link exposable via header `Referer` | 🟡 MOYEN | À vérifier |

---

## Partie 1 — Analyse OWASP Top 10 (2021)

---

### A01 — Broken Access Control

**Niveau de risque global : 🟠 ÉLEVÉ**

#### Mécanismes en place

Tenxyte implémente un contrôle d'accès en profondeur avec plusieurs couches distinctes : authentification applicative (X-Access-Key + X-Access-Secret via bcrypt), JWT Bearer (HS256), RBAC avec rôles et permissions, isolation multi-tenant par organisation, et un double mécanisme de vérification pour les agents IA (AIRS).

L'architecture est logiquement bien conçue. Cependant, plusieurs vecteurs d'exploitation potentiels méritent une attention immédiate.

#### Vulnérabilité T-01 — Bypass total d'authentification (CRITIQUE)

```python
# decorators.py:63
if not auth_settings.JWT_AUTH_ENABLED:
    request.user = None   # Aucune authentification requise
    return _call_view(...)
```

Ce flag de développement constitue une **porte dérobée systémique**. Si `TENXYTE_JWT_AUTH_ENABLED = False` est activé en production (par erreur de configuration, variables d'environnement mal héritées, ou mauvaise pratique DevOps), l'intégralité de la couche d'authentification JWT est silencieusement bypassée. Le même risque existe pour `TENXYTE_APPLICATION_AUTH_ENABLED`.

**Recommandation :** Ces flags doivent être **supprimés** ou, à défaut, protégés par une validation qui lève une exception explicite si `DEBUG=False` et que le flag est désactivé. En production, ils ne doivent jamais pouvoir être positionnés à `False`.

#### Vulnérabilité T-08 — Mass Assignment via `PATCH /me/` (ÉLEVÉ)

Un serializer trop permissif sur l'endpoint de mise à jour du profil pourrait permettre à un utilisateur de s'auto-promouvoir en modifiant des champs privilégiés (`is_staff`, `is_superuser`, `is_banned`).

**Recommandation :** Vérifier explicitement que le serializer `UserUpdateSerializer` (ou équivalent) utilise `read_only_fields` ou une liste `fields` restrictive excluant tout attribut de privilège.

#### Vulnérabilité T-09 — IDOR sur les endpoints admin (ÉLEVÉ)

Les endpoints suivants doivent faire l'objet de tests d'isolation :

```
GET /admin/users/<str:user_id>/      → Un non-staff peut-il accéder aux données d'un autre user ?
GET /admin/audit-logs/<str:log_id>/  → Les logs d'un utilisateur A sont-ils visibles par B ?
GET /users/<str:user_id>/roles/      → Isolation horizontale vérifiée ?
GET /applications/<str:app_id>/      → Filtrage strict par owner ?
```

**Recommandation :** Chaque vue admin doit vérifier `request.user.is_staff` en premier. Les vues non-admin doivent filtrer systématiquement par `owner=request.user` ou `user=request.user`, et ne jamais se contenter d'un lookup par ID sans vérification de propriété.

#### Bypass de l'isolation multi-tenant

```python
# Si X-Org-Slug absent → request.organization = None
# Les endpoints sans @require_org_context restent accessibles sans contexte org
```

**Recommandation :** Auditer exhaustivement chaque endpoint pour vérifier que la protection `@require_org_context` est appliquée partout où des données organisationnelles sont exposées.

---

### A02 — Cryptographic Failures

**Niveau de risque global : 🟠 ÉLEVÉ**

#### Évaluation cryptographique

| Donnée | Traitement | Évaluation |
|--------|-----------|------------|
| Mots de passe | bcrypt | ✅ Conforme — irréversible, résistant au brute force |
| Secrets applicatifs | bcrypt + base64 | ✅ Conforme |
| Tokens JWT | HS256 HMAC-SHA256 | ✅ Acceptable — RS256 recommandé si architecture microservices |
| Codes OTP | SHA-256, entropie élevée, TTL court | ✅ Conforme |
| Codes backup 2FA | SHA-256 avant stockage | ✅ Conforme |
| Magic link tokens | SHA-256 du token CSPRNG | ✅ Conforme |

#### Vulnérabilité T-05 — Refresh tokens en clair en base de données (ÉLEVÉ)

Les refresh tokens (64 caractères CSPRNG) sont stockés **en clair** en base de données. En cas de compromission de la base (SQL dump, backup non chiffré, accès interne malveillant), l'attaquant obtient immédiatement **tous les refresh tokens actifs**, lui permettant d'usurper l'identité de tous les utilisateurs connectés sans connaître leurs mots de passe.

**Recommandation :** Stocker uniquement le hash SHA-256 du refresh token. À la vérification, hasher le token reçu et comparer au hash stocké. Le surcoût est négligeable.

```python
# À l'émission
token_raw = secrets.token_urlsafe(48)
token_hash = hashlib.sha256(token_raw.encode()).hexdigest()
RefreshToken.objects.create(token_hash=token_hash, ...)

# À la vérification
token_hash = hashlib.sha256(received_token.encode()).hexdigest()
RefreshToken.objects.get(token_hash=token_hash, is_revoked=False, ...)
```

#### Vulnérabilité T-06 — Secret TOTP en clair en base de données (ÉLEVÉ)

Le secret TOTP est le matériau cryptographique qui permet de générer tous les codes 2FA d'un utilisateur à l'infini. Stocké en clair, une compromission de la base invalide entièrement la protection 2FA de tous les utilisateurs.

**Recommandation :** Chiffrer le secret TOTP avec AES-256-GCM en utilisant une clé dérivée d'un secret applicatif distinct (ex : `TENXYTE_TOTP_ENCRYPTION_KEY`). La clé de chiffrement ne doit jamais être stockée en base de données.

#### Note sur HS256 vs RS256

Pour une architecture monolithique, HS256 est acceptable. Si Tenxyte est déployé dans un contexte microservices où plusieurs services consomment les JWT, RS256 est fortement recommandé pour éviter la nécessité de partager le secret HMAC avec tous les consumers.

---

### A03 — Injection

**Niveau de risque global : ✅ FAIBLE**

Tenxyte utilise exclusivement l'ORM Django pour toutes les interactions avec la base de données. Aucun appel `raw()`, `cursor.execute()` ou interpolation de chaîne SQL n'a été identifié. Les tests de la suite `TestInjectionProtection` couvrent les payloads SQL classiques (OR 1=1, DROP TABLE, UNION SELECT) avec des assertions sur l'absence de réponses 200 ou 500.

L'injection NoSQL est non applicable (l'ORM Django paramétrise les requêtes MongoDB via `django-mongodb-backend`). L'injection de commandes OS est absente (pas de `subprocess`, `os.system()`, ou `eval()`). L'injection de templates est non applicable (API JSON pure, pas de rendu de templates côté serveur).

**Recommandation :** Maintenir cette bonne pratique. Documenter explicitement l'interdiction de SQL brut dans les conventions de développement du projet.

---

### A04 — Insecure Design

**Niveau de risque global : 🟡 MOYEN**

La conception de Tenxyte intègre plusieurs bonnes pratiques de sécurité par défaut : période de grâce de 30 jours avant suppression de compte, double confirmation pour les actions irréversibles (email + mot de passe + 2FA), budget tracking pour les agents IA, et audit trail complet.

**Lacune principale :** L'absence de modélisation formelle des menaces (threat model) documentée est un manque significatif pour un package de sécurité destiné à être publié. Les intégrateurs ont besoin de comprendre le modèle de confiance du système.

**Recommandation :** Rédiger un document `THREAT_MODEL.md` décrivant les acteurs (utilisateurs légitimes, attaquants externes, insiders, agents IA), les assets à protéger (tokens JWT, secrets TOTP, refresh tokens), les vecteurs d'attaque anticipés, et les contrôles correspondants. Ce document est essentiel pour un package de sécurité open source.

---

### A05 — Security Misconfiguration

**Niveau de risque global : 🟠 ÉLEVÉ**

#### Flags de désactivation dangereux

Plusieurs flags permettent de désactiver des mécanismes de sécurité fondamentaux. Sans garde-fous, ces flags constituent un risque de misconfiguration élevé en production :

| Flag | Impact si mal configuré |
|------|------------------------|
| `TENXYTE_JWT_AUTH_ENABLED = False` | Authentification JWT entièrement bypassée |
| `TENXYTE_APPLICATION_AUTH_ENABLED = False` | Couche applicative (X-Access-Key) désactivée |
| `TENXYTE_RATE_LIMITING_ENABLED = False` | Brute force et credential stuffing non protégés |
| `TENXYTE_ACCOUNT_LOCKOUT_ENABLED = False` | Lockout progressif désactivé |
| `TENXYTE_CORS_ALLOW_ALL_ORIGINS = True` | CORS ouvert à tous les domaines |
| `TENXYTE_AUDIT_LOGGING_ENABLED = False` | Aucune traçabilité des actions sensibles |

**Recommandation :** Implémenter une fonction `check_production_settings()` appelée au démarrage Django (dans `AppConfig.ready()`) qui lève un `ImproperlyConfigured` si `DEBUG=False` et qu'un flag critique est désactivé.

#### Chemins exemptés de l'authentification

Les chemins `/admin/`, `/health/`, et `/docs/` sont exemptés de `ApplicationAuthMiddleware` par défaut. Le endpoint `/docs/` mérite une attention particulière : si la documentation Swagger/OpenAPI est exposée en production, elle révèle l'intégralité de la surface d'attaque.

**Recommandation :** Documenter explicitement que `/docs/` doit être retiré des exemptions ou protégé par une authentification séparée en production.

---

### A06 — Vulnerable and Outdated Components

**Niveau de risque global : 🟡 MOYEN**

#### Vulnérabilité T-04 — Absence de lock de dépendances (CRITIQUE)

Tenxyte ne dispose pas de `poetry.lock`, `requirements.txt` ou équivalent contraignant les versions exactes des dépendances transitives. Une compromission d'une dépendance sur PyPI (supply chain attack) pourrait introduire du code malveillant lors d'une installation fresh.

**Recommandation :** Générer et committer un `poetry.lock` (ou `pip-compile` + `requirements.txt` hashé). Activer les alertes de sécurité Dependabot/Renovate sur le dépôt.

#### Vulnérabilité T-12 — Versions non contraintes (MOYEN)

`Pillow` (dépendance transitive de `qrcode`) a un historique de CVE sévères (buffer overflow, parsing d'images malformées). `py_webauthn` n'est pas listé dans `pyproject.toml`, sa version installée est donc inconnue et non contrôlée.

**Recommandation :** Ajouter `Pillow>=X.Y.Z` avec une borne inférieure contraignant une version sans CVE connue. Ajouter `py_webauthn` à `pyproject.toml` avec une version minimale explicite.

#### Commandes de vérification recommandées

```bash
pip audit                           # Détection CVE dans l'environnement installé
safety check                        # Base OSV + PyPA Advisory
pip list --outdated                 # Composants dépassés
bandit -r src/tenxyte/ -f json      # Analyse statique de sécurité
```

---

### A07 — Identification and Authentication Failures

**Niveau de risque global : 🟠 ÉLEVÉ**

#### Points conformes

Tenxyte adresse correctement la majorité des risques A07 : politique de mot de passe configurable avec score de force (1–10), rate limiting multicouche (5/min + 20/h + verrouillage progressif exponentiel), vérification des mots de passe compromis via HIBP, historique des mots de passe, gestion des sessions avec blacklist JTI, réponse uniforme sur le reset de mot de passe (anti-énumération), et tokens CSPRNG pour tous les flux sensibles.

#### Vulnérabilité T-07 — Absence d'anti-replay TOTP (ÉLEVÉ)

```python
# pyotp.TOTP.verify(code, valid_window=1) valide :
# → code actuel (30s)
# → valid_window codes passés/futurs
# Si valid_window ≥ 1 : un même code peut être soumis deux fois dans la fenêtre
```

Le code TOTP actuellement utilisé peut être **soumis plusieurs fois** pendant sa fenêtre de validité de 30 secondes. Combiné à une interception réseau (ex : MitM), un attaquant peut rejouer un code TOTP capturé.

**Recommandation :** Implémenter un cache Redis (ou un champ DB `last_used_totp_code`) enregistrant le dernier code validé par utilisateur. Toute tentative de soumettre un code identique dans la même fenêtre doit retourner une erreur 400.

```python
# Exemple d'implémentation anti-replay
last_code = cache.get(f"totp_last:{user.id}")
if last_code == submitted_code:
    raise ValidationError("Code TOTP déjà utilisé")
# Après vérification réussie
cache.set(f"totp_last:{user.id}", submitted_code, timeout=60)
```

#### Point à vérifier : ordre des checks dans le flux de login

L'ordre des vérifications dans `AuthService.authenticate_by_email()` est important. La vérification TOTP (`g.`) doit impérativement intervenir **avant** la génération des tokens JWT (`j.`, `k.`). Si l'ordre est inversé, un attaquant ayant le mot de passe peut obtenir un token JWT sans passer la 2FA.

---

### A08 — Software and Data Integrity Failures

**Niveau de risque global : 🟡 MOYEN**

L'intégrité des tokens JWT (whitelist d'algorithme HS256, prévention de `alg:none`) est correctement gérée. L'intégrité des magic links (SHA-256 du token CSPRNG 256 bits) et des codes backup 2FA (hashés SHA-256) est satisfaisante.

Le risque principal est la supply chain (détaillé en T-04). L'absence de `requirements.txt` hashé signifie qu'une dépendance peut être modifiée entre deux installations sans que l'intégrité soit vérifiée.

---

### A09 — Security Logging and Monitoring Failures

**Niveau de risque global : 🟡 MOYEN**

#### Points conformes

Le modèle `AuditLog` trace exhaustivement : action, utilisateur (FK nullable), adresse IP, User-Agent, application cliente, agent IA, délégant humain (AIRS), prompt trace ID, timestamp, et détails contextuels en JSONField. La couverture des événements sensibles semble complète.

#### Lacunes identifiées

**Absence de purge automatique :** Les audit logs s'accumulent indéfiniment en base de données. Sans politique de rétention, la base peut croître jusqu'à dégrader les performances, et surtout, une rétention infinie peut être problématique au regard du RGPD (données personnelles dans les logs IP/User-Agent).

**Absence d'alerting temps-réel :** Aucune intégration SIEM, webhook, ou système d'alerte n'est prévu. Une attaque de brute force en cours, une série d'IDOR ou une compromission de compte ne déclencherait aucune notification.

**Exposition de détails techniques :** Les appels `logger.error(str(e))` dans les services peuvent logger des informations techniques (stack traces, données de requêtes) dans les logs applicatifs. Bien que distincts des AuditLogs, ces informations pourraient contenir des données sensibles.

**Recommandations :** Implémenter une tâche Celery périodique (ou une commande management) pour archiver/purger les logs selon une politique de rétention configurable. Documenter un exemple d'intégration webhook pour les événements critiques (ex : login depuis une nouvelle IP, modification de 2FA, suppression de compte).

---

### A10 — Server-Side Request Forgery (SSRF)

**Niveau de risque global : ✅ FAIBLE**

L'ensemble des appels HTTP sortants (HIBP, OAuth Google/GitHub/Microsoft/Facebook) utilisent des URLs construites statiquement depuis des constantes. Aucun cas n'a été identifié où une URL fournie par l'utilisateur serait utilisée comme destination d'un appel HTTP côté serveur. Le risque SSRF est faible dans l'état actuel du code.

---

## Partie 2 — Audit des Flux d'Authentification

---

### B1. Flux Email + Mot de Passe

**Évaluation : ✅ Globalement conforme — points à vérifier**

La chaîne de traitement est logiquement ordonnée : authentification applicative → rate limiting → vérification bcrypt → checks d'état (actif, banni, verrouillé) → TOTP → génération de tokens. L'utilisation de bcrypt pour les mots de passe et de CSPRNG 64 caractères pour les refresh tokens est correcte.

Points de vigilance à tester :
- Vérifier que la 2FA est validée **avant** la génération JWT (ordre critique, cf. T-07)
- Vérifier le comportement si `is_banned=True` mais `is_active=True` — l'ordre des checks doit s'assurer que le ban est évalué avant l'active check
- Vérifier la valeur par défaut de `TOTP_VALID_WINDOW` : si ≥ 2, la fenêtre d'acceptation d'un code s'étend à 90 secondes, augmentant la surface d'attaque replay

---

### B2. Flux Magic Link (Passwordless)

**Évaluation : 🟡 Conforme avec un risque résiduel**

Le flux est correctement implémenté : génération CSPRNG, stockage du hash SHA-256 uniquement, marquage `is_used=True` après utilisation. Le rate limiting (3 magic links/heure/IP) limite le spam.

#### Vulnérabilité T-15 — Exposition du token via header Referer (MOYEN)

L'URL de vérification du magic link inclut le token en query parameter (`?token=<token>`). Si l'utilisateur clique sur un lien externe depuis la page de confirmation, le header `Referer` envoyé par le navigateur peut exposer le token à des tiers (analytics, CDN, sites partenaires).

**Recommandation :** Utiliser un mécanisme de redirection : la page de vérification doit consommer le token, puis rediriger vers une URL sans token dans la barre d'adresse. Ajouter `Referrer-Policy: no-referrer` spécifiquement sur la réponse de confirmation.

---

### B3. Flux TOTP / 2FA

**Évaluation : 🟠 ÉLEVÉ — anti-replay manquant**

Le flux d'activation (setup + confirmation avec premier code) et de désactivation (mot de passe + code TOTP requis) est correctement conçu. Les codes backup sont hashés avant stockage et supprimés après usage.

La vulnérabilité principale est l'absence d'anti-replay décrite en T-07. De plus, la limite de tentatives de code TOTP erronées doit être vérifiée : sans limitation spécifique sur les tentatives TOTP, une attaque de brute force sur un code à 6 chiffres (10^6 = 1 million de possibilités) est théoriquement possible si le rate limiting général est insuffisant.

---

### B4. Flux Refresh Token

**Évaluation : 🟠 ÉLEVÉ — stockage non sécurisé**

La rotation de refresh token (`REFRESH_TOKEN_ROTATION`) et la blacklist JTI (`TOKEN_BLACKLIST_ENABLED`) sont des mécanismes solides mais leur activation par défaut doit être vérifiée dans `conf.py`. Si la rotation est **désactivée par défaut**, un refresh token compromis reste exploitable pendant toute sa TTL sans possibilité de révocation implicite.

La vulnérabilité critique est le stockage en clair des refresh tokens (T-05). Un dump de la table `RefreshToken` compromet instantanément toutes les sessions actives.

---

### B5. Flux WebAuthn / Passkeys (FIDO2)

**Évaluation : 🟡 MOYEN — version de dépendance non contrôlée**

Le flux FIDO2 est architecturalement correct : challenge CSPRNG avec TTL court (5 min), vérification de la signature ECDSA P-256, et invalidation des challenges après usage. L'utilisation de `py_webauthn` délègue correctement la vérification cryptographique à une bibliothèque spécialisée.

Le risque principal est l'absence de contrainte de version sur `py_webauthn` (T-12). Une version ancienne pourrait ne pas implémenter certaines vérifications de sécurité FIDO2 (validation stricte du `rpId`, vérification du `origin`).

**Point critique :** La vérification stricte du `rpId` doit être confirmée. Un `rpId` trop permissif (ex : accepter `*.example.com` au lieu de `app.example.com`) ouvrirait la voie à une attaque de phishing via sous-domaine.

---

### B6. Flux Social OAuth

**Évaluation : 🔴 CRITIQUE — account takeover possible**

#### Vulnérabilité T-03 — Account Takeover via email matching (CRITIQUE)

```python
# SocialAuthService.authenticate()
# b. Si aucune SocialConnection → cherche User par email (case-insensitive)
# c. Si trouvé → fusion automatique → accès au compte existant
```

Si un fournisseur OAuth retourne un email non vérifié (ou si la vérification de `email_verified` n'est pas effectuée côté Tenxyte), un attaquant contrôlant un compte social avec n'importe quel email peut accéder au compte Tenxyte correspondant à cet email **sans connaître le mot de passe**.

**Scénario d'attaque :** L'attaquant crée un compte GitHub avec l'email `victim@example.com` (GitHub ne vérifie pas l'unicité des emails pour l'OAuth). Il s'authentifie via "Continuer avec GitHub" sur une app Tenxyte. Tenxyte trouve un compte existant avec cet email et fusionne automatiquement. L'attaquant a maintenant accès au compte.

**Recommandation :** Vérifier systématiquement le flag `email_verified` dans les données retournées par chaque provider OAuth avant toute fusion. Pour GitHub et Facebook (qui ne retournent pas toujours ce flag), refuser la fusion automatique ou exiger une confirmation par email séparé.

```python
# Vérification recommandée
if not user_info.get('email_verified', False):
    raise AuthenticationFailed("Email OAuth non vérifié — fusion refusée")
```

---

### B7. Flux Réinitialisation de Mot de Passe

**Évaluation : ✅ Conforme**

Le flux de reset est bien conçu : réponse uniforme 200 OK (anti-énumération), token OTP hashé SHA-256, TTL court (15 min), invalidation immédiate après usage, révocation de toutes les sessions actives. Le rate limiting (3/h + 10/j) est approprié.

Un point à surveiller : un attaquant connaissant l'email d'une victime peut déclencher un reset pour invalider ses sessions actives (DoS ciblé). Ce risque est inhérent à tout système de reset avec révocation de sessions et difficile à éliminer complètement.

---

### B8. Flux Agents IA (AIRS)

**Évaluation : 🟡 MOYEN — points de vérification importants**

L'architecture AIRS est innovante et bien pensée : tokens statiques CSPRNG 48 caractères, circuit breaker, Dead Man's Switch (heartbeat), et mécanisme Human-in-the-Loop (HITL) pour les actions sensibles. Le principe de double vérification (permission sur le token ET sur l'utilisateur humain) est une bonne pratique de sécurité.

Points à vérifier impérativement avant production :
- Le `confirmation_token` HITL doit être à **usage unique** avec un TTL strict
- Un agent ne doit pas pouvoir créer d'autres agents (vérifier `@require_agent_clearance` sur `/ai/tokens/`)
- L'héritage de permissions doit être strictement unidirectionnel : un agent ne peut avoir **que** des permissions que l'humain créateur possède lui-même, jamais plus

---

## Partie 3 — En-têtes HTTP et Configuration TLS

---

### C1. En-têtes de Sécurité

**Évaluation : 🟠 ÉLEVÉ — configuration insuffisante par défaut**

#### Headers actuels

| Header | Valeur | Statut |
|--------|--------|--------|
| `X-Content-Type-Options: nosniff` | Par défaut | ✅ Correct |
| `X-Frame-Options: DENY` | Par défaut | ✅ Correct |
| `Referrer-Policy: strict-origin-when-cross-origin` | Par défaut | ✅ Correct |
| `X-XSS-Protection: 1; mode=block` | Par défaut | ⚠️ Déprécié — supprimer |

#### Vulnérabilité T-11 — HSTS absent par défaut (ÉLEVÉ)

`Strict-Transport-Security` est le header le plus critique pour une API d'authentification. Son absence par défaut signifie que les intégrateurs qui ne configurent pas explicitement ce header exposent leurs utilisateurs à des attaques de downgrade HTTP.

#### Headers manquants

| Header | Impact | Valeur recommandée |
|--------|--------|--------------------|
| `Strict-Transport-Security` | Downgrade HTTP, MitM | `max-age=31536000; includeSubDomains` |
| `Content-Security-Policy` | XSS | `default-src 'none'; frame-ancestors 'none'` |
| `Permissions-Policy` | Accès APIs navigateur | `camera=(), microphone=(), geolocation=()` |
| `Cross-Origin-Resource-Policy` | Leakage cross-origin | `same-origin` |
| `Cross-Origin-Opener-Policy` | Side-channel attacks | `same-origin` |

**Configuration de production recommandée :**

```python
TENXYTE_SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'",
    'Cross-Origin-Resource-Policy': 'same-origin',
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
    # Ne pas inclure X-XSS-Protection (déprécié)
}
```

---

### C2. Configuration CORS

**Évaluation : ✅ Conforme par défaut — risque si mal configuré**

La configuration par défaut est sûre : CORS désactivé (`CORS_ENABLED = False`), `CORS_ALLOW_ALL_ORIGINS = False`, `CORS_ALLOW_CREDENTIALS = False`. La liste des headers autorisés est précise et pertinente.

#### Vulnérabilité T-10 — `CORS_ALLOW_ALL_ORIGINS` combiné à `CORS_ALLOW_CREDENTIALS` (ÉLEVÉ)

Si un intégrateur active `CORS_ALLOW_ALL_ORIGINS = True` **et** `CORS_ALLOW_CREDENTIALS = True` simultanément, il s'expose à des attaques CSRF/CORS aggravées où n'importe quel site tiers peut envoyer des requêtes authentifiées au nom de l'utilisateur.

**Recommandation :** Implémenter une validation de configuration qui refuse le démarrage si `CORS_ALLOW_ALL_ORIGINS = True` ET `CORS_ALLOW_CREDENTIALS = True` sont simultanément actifs.

---

### C3. Configuration TLS

**Évaluation : ℹ️ Hors périmètre Tenxyte — responsabilité intégrateur**

Tenxyte délègue correctement la terminaison TLS à l'infrastructure (nginx, Caddy, AWS ALB, Cloudflare). La documentation doit néanmoins inclure la configuration minimale requise.

**Configuration nginx recommandée :**

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:
            ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:
            ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
ssl_prefer_server_ciphers off;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
ssl_stapling on;
ssl_stapling_verify on;
```

**Checklist TLS à vérifier côté infrastructure :**

- [ ] TLS 1.0 et 1.1 désactivés
- [ ] Suites RC4, 3DES, export ciphers absentes
- [ ] Certificat valide avec chaîne de confiance complète
- [ ] OCSP Stapling activé (`openssl s_client -status`)
- [ ] Redirection HTTP → HTTPS en 301 permanent (pas 302)
- [ ] HSTS préchargé (`hstspreload.org`)

---

### C4. Rate Limiting

**Évaluation : 🔴 CRITIQUE — falsifiabilité systémique**

#### Vulnérabilité T-02 — Bypass universel via `X-Forwarded-For` (CRITIQUE)

**Tous les throttles** (`LoginThrottle`, `OTPVerifyThrottle`, `RegisterThrottle`, etc.) déterminent l'identité de l'IP cliente via le header `X-Forwarded-For` **sans liste de proxies de confiance**. Un attaquant peut forger ce header pour se faire passer pour n'importe quelle IP et contourner l'intégralité des mécanismes de rate limiting.

```http
POST /login/email/ HTTP/1.1
X-Forwarded-For: 8.8.8.8   # IP forgée — le throttle identifie "8.8.8.8"
```

Cela invalide entièrement la protection contre le brute force, le credential stuffing, et le spam de création de compte.

**Recommandation :** Configurer une liste de `TRUSTED_PROXIES` (les IPs des load balancers et reverse proxies internes). L'IP réelle du client doit être lue depuis `REMOTE_ADDR` en l'absence de proxy de confiance, et depuis le dernier élément non-trusted de `X-Forwarded-For` sinon. Utiliser `django-ipware` avec `IPWARE_META_PRECEDENCE_ORDER` limité aux interfaces de confiance.

```python
# Exemple avec django-ipware
from ipware import get_client_ip

def get_client_ip_address(request):
    ip, is_routable = get_client_ip(request, 
        proxy_trusted_ips=['10.0.0.0/8', '172.16.0.0/12'])
    return ip if is_routable else None
```

---

## Partie 4 — Plan de Remédiation Prioritaire

---

### Corrections Critiques (bloqueantes avant publication)

**T-01 — Supprimer ou protéger les flags de bypass d'authentification**
Les flags `JWT_AUTH_ENABLED` et `APPLICATION_AUTH_ENABLED` ne doivent pas pouvoir être désactivés en production. Implémenter une vérification au démarrage qui lève une exception si `DEBUG=False` et qu'un flag critique est désactivé.

**T-02 — Corriger la lecture de l'IP cliente dans les throttles**
Remplacer la lecture naïve de `X-Forwarded-For` par une implémentation tenant compte des proxies de confiance. Tous les throttles doivent utiliser la même fonction utilitaire de résolution d'IP.

**T-03 — Vérifier `email_verified` avant toute fusion de compte OAuth**
Ajouter une vérification explicite du statut de vérification de l'email pour chaque provider social. Refuser la fusion automatique si le flag est absent ou `False`.

**T-04 — Générer et committer un fichier de lock de dépendances**
Exécuter `poetry lock` (ou `pip-compile --generate-hashes`) et inclure le fichier généré dans le dépôt. Configurer Dependabot ou Renovate pour les mises à jour automatiques de sécurité.

---

### Corrections Prioritaires (à adresser avant la première release majeure)

**T-05 — Hasher les refresh tokens avant stockage en base de données**
Stocker uniquement le hash SHA-256 du refresh token. Migration de base de données requise.

**T-06 — Chiffrer les secrets TOTP en base de données**
Utiliser AES-256-GCM avec une clé applicative dédiée (`TENXYTE_TOTP_ENCRYPTION_KEY`). Migration de base de données requise.

**T-07 — Implémenter l'anti-replay TOTP**
Enregistrer le dernier code TOTP validé par utilisateur (Redis ou DB) et rejeter toute réutilisation dans la même fenêtre temporelle.

**T-11 — Inclure HSTS dans la configuration par défaut**
Ajouter `Strict-Transport-Security` à la configuration par défaut de `TENXYTE_SECURITY_HEADERS`. Supprimer `X-XSS-Protection` (déprécié).

---

### Améliorations Recommandées (moyen terme)

**T-08 / T-09 — Tests d'isolation IDOR et mass assignment**
Rédiger et exécuter des tests de pénétration sur l'isolation des endpoints admin et les restrictions de serializer.

**T-10 — Guard contre la combinaison CORS dangereuse**
Valider au démarrage l'incompatibilité de `CORS_ALLOW_ALL_ORIGINS=True` avec `CORS_ALLOW_CREDENTIALS=True`.

**T-12 — Contraindre les versions de `Pillow` et `py_webauthn`**
Ajouter des bornes inférieures explicites dans `pyproject.toml`.

**T-13 — Activer la rotation de refresh token par défaut**
Vérifier et documenter la valeur par défaut de `REFRESH_TOKEN_ROTATION`. Une valeur `True` par défaut est préférable pour la sécurité.

**T-14 — Politique de rétention des audit logs**
Implémenter une commande de purge/archivage configurable et documenter les recommandations RGPD.

**T-15 — Protéger le token magic link contre le header Referer**
Utiliser un pattern de redirection post-consommation du token.

---

## Annexe — Checklist de Déploiement Production

### Authentification et Sessions

- [ ] `TENXYTE_JWT_AUTH_ENABLED = True`
- [ ] `TENXYTE_APPLICATION_AUTH_ENABLED = True`
- [ ] `TENXYTE_RATE_LIMITING_ENABLED = True`
- [ ] `TENXYTE_ACCOUNT_LOCKOUT_ENABLED = True`
- [ ] `TENXYTE_AUDIT_LOGGING_ENABLED = True`
- [ ] `TENXYTE_REFRESH_TOKEN_ROTATION = True`
- [ ] Vérifier l'ordre des checks dans `AuthService.authenticate_by_email()` (TOTP avant JWT)
- [ ] Vérifier que l'anti-replay TOTP est en place
- [ ] Vérifier le comportement sur `is_banned=True` / `is_active=True`

### Contrôle d'Accès

- [ ] Tester l'IDOR sur `/admin/users/<id>/`
- [ ] Tester le mass assignment sur `PATCH /me/`
- [ ] Tester l'isolation multi-tenant
- [ ] Vérifier le rejet d'un JWT d'app A par app B

### Cryptographie

- [ ] Refresh tokens hashés avant stockage
- [ ] Secrets TOTP chiffrés
- [ ] `TENXYTE_JWT_SECRET_KEY` différente de `SECRET_KEY` Django
- [ ] Aucun credential hardcodé ou `.env` committé

### Configuration

- [ ] `DEBUG = False`
- [ ] `TENXYTE_CORS_ALLOW_ALL_ORIGINS = False`
- [ ] `TENXYTE_CORS_ALLOWED_ORIGINS` liste blanche stricte
- [ ] `/docs/` retiré des chemins exemptés ou protégé
- [ ] `TRUSTED_PROXIES` configuré pour la résolution d'IP

### En-têtes HTTP

- [ ] `Strict-Transport-Security` présent et configuré
- [ ] `Content-Security-Policy` configuré
- [ ] `X-XSS-Protection` supprimé (déprécié)

### Infrastructure TLS

- [ ] TLS 1.0 et 1.1 désactivés
- [ ] RC4 et 3DES absents de la négociation
- [ ] Certificat valide et chaîne de confiance complète
- [ ] OCSP Stapling activé
- [ ] Redirection HTTP → HTTPS en 301

### Dépendances

- [ ] `poetry.lock` (ou équivalent) généré et committé
- [ ] `pip audit` sans CVE critique
- [ ] `py_webauthn` version contrainte dans `pyproject.toml`
- [ ] `Pillow` version contrainte

---

*Audit réalisé sur la base du brief `Tenxyte — Sécurité Applicative Audit Brief v0.9.1.7` — 2026-02-27*  
*Ce document est confidentiel et destiné à l'équipe de développement Tenxyte.*
