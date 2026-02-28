# RAPPORT D'AUDIT DE SÉCURITÉ
## Package Django — Tenxyte

**Date de l'audit :** 27 février 2026  
**Version analysée :** v1.0 (pré-publication)  
**Classification : CONFIDENTIEL**

---

> **Périmètre de l'audit**
>
> Revue de la stratégie de sécurité, de l'architecture des middlewares, des mécanismes d'authentification (JWT, 2FA, OAuth, WebAuthn, AIRS), de la gestion des mots de passe, du RBAC, du rate limiting, de la conformité RGPD et des recommandations de déploiement.

---

## 1. Synthèse exécutive

Tenxyte est un package Django d'authentification multi-tenant qui affiche un niveau de maturité sécurité globalement élevé pour un projet pré-publication. L'architecture en défense en profondeur, la rigueur sur la gestion des secrets, l'implémentation de mécanismes avancés comme le circuit breaker AIRS ou le k-anonymity HIBP témoignent d'une réflexion approfondie.

Cependant, l'audit a identifié **17 findings dont 3 de sévérité critique** qui doivent impérativement être corrigés avant toute publication publique du package.

### Scores par domaine

| Domaine | Score |
|---|---|
| Authentification | 8.5 / 10 |
| Gestion des secrets | 8.0 / 10 |
| Isolation multi-tenant | 9.0 / 10 |
| Agents IA (AIRS) | 8.0 / 10 |
| Rate limiting & anti-abus | 9.0 / 10 |
| Audit & conformité | 8.5 / 10 |
| Configuration & hardening | 7.0 / 10 |
| **Score global estimé** | **8.1 / 10** |

### Distribution des findings

| Sévérité | Nombre | Résumé |
|---|---|---|
| **CRITIQUE** | 3 | Correction obligatoire avant publication |
| **ÉLEVÉ** | 4 | Correction fortement recommandée avant publication |
| **MOYEN** | 5 | À traiter dans les premières versions correctives |
| **FAIBLE** | 3 | Améliorations souhaitables |
| **INFO** | 2 | Observations documentaires |

---

## 2. Points forts de l'architecture

Avant de détailler les findings, il est important de souligner les nombreux choix d'architecture sécurisés qui distinguent Tenxyte d'une implémentation naïve.

| Point positif | Justification sécurité |
|---|---|
| **Pipeline défense en profondeur** | 9 couches indépendantes, compromission d'une seule = non critique |
| **bcrypt pour mots de passe** | Sel automatique, résistant au brute force sur hash volé |
| **Comparaison à temps constant** | `verify_secret()` via bcrypt empêche les timing attacks |
| **JWT blacklist + rotation refresh** | Invalidation immédiate à la déconnexion, fenêtre de vol réduite |
| **k-anonymity HIBP** | Le mot de passe en clair ne quitte jamais le serveur |
| **RBAC hiérarchique** | Permissions implicites via héritage, contrôle fin |
| **AIRS double-passe RBAC** | Permission agent ET permission humain vérifiées en temps réel |
| **Dead Man's Switch** | Heartbeat obligatoire pour les agents autonomes |
| **ContextVar tenant isolation** | Pas de contamination entre requêtes concurrentes (vs thread-local) |
| **Soft delete RGPD** | Anonymisation PII + conservation AuditLog pour conformité |
| **HITL avec token 384 bits** | `secrets.token_urlsafe(64)` — entropie cryptographiquement sûre |
| **Progressive login throttle** | Backoff exponentiel jusqu'à 1h, réinitialisé après succès |
| **OTP à usage unique** | Codes invalidés à la réutilisation et à chaque nouvelle génération |
| **Audit log exhaustif** | Traçabilité LLM via `prompt_trace_id`, `agent_id`, IP, User-Agent |
| **Secrets hors presets** | Clés JWT, OAuth, Twilio jamais dans les presets de configuration |

---

## 3. Tableau récapitulatif des findings

| ID | Sévérité | Titre |
|---|---|---|
| **F-01** | **CRITIQUE** | bcrypt 72 octets — mots de passe > 72 chars silencieusement tronqués |
| **F-02** | **CRITIQUE** | Agent tokens stockés en clair en base de données |
| **F-03** | **CRITIQUE** | Fusion de compte OAuth sans vérification `email_verified` |
| **F-04** | **ÉLEVÉ** | Backup codes hachés en SHA-256 (algorithme rapide) |
| **F-05** | **ÉLEVÉ** | X-Forwarded-For sans validation du nombre de proxies de confiance |
| **F-06** | **ÉLEVÉ** | `bypass_tenant_filtering` : absence de garde-fous d'architecture |
| **F-07** | **ÉLEVÉ** | `APPLICATION_AUTH_ENABLED=False` peut être activé en production |
| **F-08** | **MOYEN** | CORS désactivé par défaut : risque d'omission en production |
| **F-09** | **MOYEN** | HITL `confirmation_token` transmis en URL (journaux serveur) |
| **F-10** | **MOYEN** | `prompt_trace_id` non validé côté serveur |
| **F-11** | **MOYEN** | SMS OTP vulnérable au SIM swapping (non documenté) |
| **F-12** | **MOYEN** | Magic link : pas de binding IP/User-Agent |
| **F-13** | **FAIBLE** | `BlacklistedToken.cleanup_expired()` sans automatisation garantie |
| **F-14** | **FAIBLE** | `AuditLog.details` sans limite de taille documentée |
| **F-15** | **FAIBLE** | X-XSS-Protection header obsolète (navigateurs modernes) |
| **F-16** | **INFO** | Pas de mention de la protection CSRF explicite |
| **F-17** | **INFO** | `TENXYTE_CORS_ALLOW_ALL_ORIGINS` : footgun documenté mais existant |

---

## 4. Findings critiques

### F-01 [CRITIQUE] — Troncature silencieuse des mots de passe > 72 octets (bcrypt)

**Composant :** `PasswordValidator`, `AbstractUser.set_password()`

#### Constat

bcrypt traite au maximum 72 octets en entrée. Tout caractère au-delà est silencieusement ignoré. Or, Tenxyte autorise des mots de passe jusqu'à 128 caractères via le `PasswordValidator`, sans que cette limite ne soit documentée ni compensée. Un utilisateur définissant `"MonMotDePasse123!@#[...73 chars+]"` croira avoir un mot de passe fort, alors que bcrypt n'en verra que les 72 premiers octets — réduisant drastiquement l'entropie effective.

#### Risque

Un attaquant connaissant les 72 premiers caractères d'un mot de passe long peut s'authentifier avec n'importe quel suffixe. Ce comportement est contre-intuitif et contraire aux attentes de l'utilisateur. Il peut aussi constituer un vecteur de contournement sur des applications qui imposent des mots de passe très longs.

#### Recommandation

Soit limiter la longueur maximale à 72 caractères (ou 72 octets UTF-8) et l'indiquer clairement à l'utilisateur. Soit pré-hacher le mot de passe avec SHA-256 ou BLAKE2 avant de le passer à bcrypt (solution "bcrypt + pepper" ou "bcrypt-sha256" utilisée par `passlib`), permettant ainsi de préserver l'entropie complète sans limitation. La bibliothèque `passlib` propose `django_bcrypt_sha256` clé en main.

---

### F-02 [CRITIQUE] — Agent tokens (AIRS) potentiellement stockés en clair en base de données

**Composant :** `AgentTokenService`, `AgentTokenMiddleware`, modèle `AgentToken`

#### Constat

Le document décrit que la validation de l'AgentBearer token vérifie son "existence en base de données" sans mentionner de hachage du token côté stockage. Si le token est stocké en clair (pratique courante avec les implémentations simples), une compromission de la base de données expose immédiatement tous les tokens actifs de tous les agents sur tous les tenants.

#### Risque

Les tokens d'agents ont des permissions déléguées et peuvent exécuter des mutations POST/PUT/PATCH/DELETE. Un accès en lecture à la base de données suffirait à un attaquant pour usurper l'identité de n'importe quel agent IA actif, potentiellement dans des contextes fintech ou santé (preset `robust`). L'impact est critique dans des architectures multi-tenants car un seul leak compromet tous les tenants.

#### Recommandation

Stocker les agent tokens hachés en base de données (SHA-256 ou BLAKE2b suffisent pour des tokens à haute entropie). Le token en clair n'est affiché qu'une seule fois à la création (pattern identique aux backup codes déjà implémentés). Ajouter une note explicite dans la documentation AIRS et dans le `SKILL.md` si applicable.

---

### F-03 [CRITIQUE] — Fusion de compte OAuth sans vérification du flag `email_verified`

**Composant :** `SocialAuthService.handle_social_login()`

#### Constat

Le document indique que l'authentification sociale fusionne automatiquement un compte OAuth avec un compte existant "si l'email correspond". Cependant, plusieurs providers OAuth (GitHub notamment, mais aussi certains comptes Google anciens ou Microsoft) peuvent retourner des adresses email non vérifiées sans que le champ `email_verified` ne soit contrôlé côté Tenxyte.

#### Risque

Un attaquant peut créer un compte OAuth chez un provider permissif avec l'adresse email d'une victime (même non vérifiée), puis se connecter à Tenxyte et fusionner avec le compte existant de la victime. Il obtient alors un accès complet au compte sans connaître le mot de passe. Ce vecteur d'attaque est documenté (Account Takeover via OAuth) et exploité en production sur des dizaines d'applications.

#### Recommandation

Avant toute fusion, vérifier obligatoirement que `email_verified == true` dans le payload OAuth. Si le flag est absent ou `false`, refuser la fusion et afficher un message indiquant que l'email n'a pas pu être vérifié auprès du provider. Documenter explicitement ce comportement par provider. Considérer également l'ajout d'une confirmation par email lors de la première fusion.

---

## 5. Findings de sévérité élevée

### F-04 [ÉLEVÉ] — Backup codes hachés avec SHA-256 (algorithme non adapté aux secrets)

**Composant :** `TOTPService`, modèle `User` (`backup_codes`)

#### Constat

Les backup codes de récupération 2FA sont hachés avec SHA-256 avant stockage. SHA-256 est un algorithme de hachage cryptographique général, conçu pour être rapide. Sa vitesse est une qualité pour les checksums, mais un défaut pour la protection de secrets : un attaquant ayant accès à la base de données peut tenter des milliards de combinaisons par seconde sur du hardware moderne (GPU).

#### Risque

Bien que les backup codes soient générés via `secrets.token_hex()` et aient une entropie théoriquement suffisante, en pratique leur format (hex court) les rend vulnérables à une attaque par dictionnaire accélérée GPU si la base est compromise. Un attaquant avec 100 millions de hashs/seconde sur GPU peut explorer l'espace d'entropie effective bien plus rapidement qu'avec bcrypt.

#### Recommandation

Utiliser bcrypt (déjà une dépendance de Tenxyte) ou argon2 pour hacher les backup codes. Le coût est négligeable en UX (la vérification d'un backup code est une opération rare) et augmente exponentiellement le coût d'une attaque offline.

---

### F-05 [ÉLEVÉ] — X-Forwarded-For sans validation du nombre de proxies de confiance

**Composant :** `throttles.IPBasedThrottle`

#### Constat

Le module `IPBasedThrottle` résout l'IP réelle du client via `HTTP_X_FORWARDED_FOR`. Sans configuration du nombre exact de proxies de confiance (`TRUSTED_PROXY_COUNT` ou équivalent), un attaquant peut forger ce header pour usurper n'importe quelle adresse IP et contourner les throttles. Il suffit d'envoyer `"X-Forwarded-For: 127.0.0.1"` pour apparaître comme une requête locale et esquiver les limites de rate limiting.

#### Risque

Tous les mécanismes de protection basés sur l'IP (brute force, progressive throttle, `LoginThrottle`, `OTPVerifyThrottle`, etc.) peuvent être contournés. Un attaquant peut effectuer un nombre illimité de tentatives de connexion, d'OTP, de magic links en changeant l'IP forgée à chaque requête.

#### Recommandation

Implémenter `TENXYTE_NUM_PROXIES` ou `TENXYTE_TRUSTED_PROXY_IPS`. Utiliser uniquement le dernier IP dans la chaîne X-Forwarded-For correspondant aux proxies de confiance. Documenter cette configuration comme obligatoire en production derrière un load balancer ou CDN. Considérer également le support de `CF-Connecting-IP` (Cloudflare) et `X-Real-IP`.

---

### F-06 [ÉLEVÉ] — `_bypass_tenant_filtering` : absence de garde-fous architecturaux

**Composant :** `tenxyte/tenant_context.py`, `_bypass_tenant_filtering`

#### Constat

La ContextVar `_bypass_tenant_filtering` est exposée dans `tenant_context.py` et peut techniquement être activée depuis n'importe quel code accédant au module. Le document indique qu'elle "ne doit être activée que dans du code d'administration interne supervisé", mais cette contrainte est documentaire, pas architecturale. Il n'existe pas de mécanisme technique empêchant un développeur intégrant Tenxyte de l'utiliser accidentellement.

#### Risque

Si un développeur tiers active `_bypass_tenant_filtering` dans un contexte non sécurisé (vue API, tâche Celery partagée, etc.), l'isolation complète du système multi-tenant est rompue. Toutes les données de tous les tenants deviennent accessibles. Dans un SaaS B2B, cela constitue une violation de données potentiellement catastrophique.

#### Recommandation

Plusieurs mesures complémentaires :
1. Renommer en `_INTERNAL_bypass_tenant_filtering` et ne pas l'exporter dans `__init__.py`.
2. Ajouter une vérification de la call stack ou un flag de contexte "admin_only" à l'activation.
3. Émettre un warning de sécurité dans les logs à chaque activation.
4. Créer un décorateur `@require_internal_context` qui force le passage par un code path validé.
5. Ajouter un test automatisé qui vérifie que le bypass n'est jamais appelé depuis les views publiques.

---

### F-07 [ÉLEVÉ] — `TENXYTE_APPLICATION_AUTH_ENABLED=False` : risque de déploiement accidentel

**Composant :** `tenxyte/conf.py`, `ApplicationAuthMiddleware`, `AppConfig`

#### Constat

Le paramètre `TENXYTE_APPLICATION_AUTH_ENABLED=False` désactive complètement la couche 3 (`ApplicationAuthMiddleware`), supprimant la vérification `X-Access-Key`/`X-Access-Secret`. Le document précise "Dev uniquement" mais aucun mécanisme ne prévient si ce flag est actif en production (pas de check au démarrage, pas de warning dans les logs).

#### Risque

Une application déployée avec ce flag désactivé accepte des requêtes sans authentification applicative, ouvrant l'API à n'importe qui connaissant les endpoints. Dans un SaaS multi-tenant, cela expose les données de tous les clients. Ce type d'erreur de configuration est documenté dans de nombreuses breaches (misconfigured staging → production).

#### Recommandation

Ajouter un check de démarrage Django (`AppConfig.ready()`) qui vérifie si `APPLICATION_AUTH_ENABLED=False` et que `DEBUG=False` simultanément, et dans ce cas émet un avertissement rouge dans les logs, voire lève une `ImproperlyConfigured` exception. Documenter clairement que ce flag ne doit jamais être `False` en dehors d'un environnement de développement isolé.

---

## 6. Findings de sévérité moyenne

### F-08 [MOYEN] — CORS désactivé par défaut : risque d'omission en production

**Composant :** `CORSMiddleware`, `TENXYTE_CORS_ENABLED`

#### Constat

`TENXYTE_CORS_ENABLED=False` est le défaut. Un développeur qui oublie de l'activer en production déploie sans protection CORS. Contrairement à `APPLICATION_AUTH_ENABLED` qui a un impact immédiat visible, l'absence de CORS peut passer inaperçue pendant des semaines car les requêtes fonctionnent normalement depuis les clients non-browser.

#### Risque

Sans CORS, un site malveillant peut effectuer des requêtes cross-origin authentifiées si des cookies sont utilisés pour la session, facilitant les attaques CSRF côté navigateur. L'impact dépend de l'utilisation de cookies vs. tokens Authorization, mais le risque existe.

#### Recommandation

Considérer l'inverse : activer CORS par défaut avec une politique restrictive (`allowed_origins = []` par défaut = blocage total), ce qui est plus sûr que désactivé. Ajouter une vérification de démarrage qui avertit si CORS est désactivé en production (`DEBUG=False`). Documenter clairement le comportement par défaut dans le README.

---

### F-09 [MOYEN] — HITL : `confirmation_token` transmis en URL (exposition dans les journaux)

**Composant :** `AgentPendingAction`, `confirmation_token`, endpoint HITL

#### Constat

Le token de confirmation Human-In-The-Loop est un `secrets.token_urlsafe(64)` de haute entropie — c'est excellent. Cependant, ce token est très probablement transmis dans l'URL pour l'endpoint de confirmation (pattern standard `/confirm/<token>/`). Les URLs sont loggées par défaut dans les access logs nginx/Apache/Django, les CDN, et potentiellement dans les en-têtes Referer.

#### Risque

Si le serveur est compromis ou si les logs sont exfiltrés, les tokens HITL non encore consommés peuvent être utilisés pour confirmer ou refuser des actions d'agents à l'insu de l'utilisateur. Dans un contexte fintech (preset `robust`), cela peut signifier valider des virements ou des modifications de données critiques.

#### Recommandation

Transmettre le token dans le corps de la requête POST plutôt qu'en GET dans l'URL. Si une URL est nécessaire (email de confirmation), tronquer le token dans les logs via une configuration de logging Django (`LOGGING` avec `filters`). Ajouter une expiration courte (déjà 10 min, mais vérifier que le log rotation soit < 10 min ou que les tokens soient invalidés à la consommation — ce qui semble être le cas).

---

### F-10 [MOYEN] — `prompt_trace_id` non validé côté serveur

**Composant :** `AgentTokenMiddleware`, `AuditLog.prompt_trace_id`

#### Constat

Le `prompt_trace_id` est enregistré dans `AuditLog` pour la traçabilité LLM. Le document ne précise pas si ce champ provient du client (header HTTP) ou est généré côté serveur. S'il provient du client, un agent malveillant ou mal configuré peut injecter des valeurs arbitraires, compromettant l'intégrité de l'audit trail et potentiellement injecter du contenu dans les logs (log injection).

#### Risque

Un audit trail falsifié rend impossible la reconstruction fidèle d'un incident. Dans un contexte AIRS, attribuer de fausses actions à de vrais agents ou dissimuler des activités malveillantes est une attaque réaliste si le `prompt_trace_id` n'est pas contrôlé. Des caractères de contrôle dans ce champ peuvent aussi corrompre des systèmes de log aggregation (Splunk, ELK).

#### Recommandation

Définir explicitement la source du `prompt_trace_id` (si header client, valider le format UUID ou longueur max + sanitization). Générer le `trace_id` côté serveur si la source est le client, et conserver le `trace_id` client dans un champ séparé `client_trace_id`. Ajouter une validation de format dans le middleware AIRS. Documenter la provenance dans l'architecture.

---

### F-11 [MOYEN] — OTP SMS : vulnérabilité SIM swapping non documentée ni mitigée

**Composant :** `OTPService`, documentation presets

#### Constat

Tenxyte supporte l'OTP par SMS pour la vérification de téléphone et potentiellement la 2FA. Le SIM swapping (ou SIM hijacking) est une attaque documentée et fréquente permettant à un attaquant de transférer le numéro de téléphone d'une victime sur sa propre SIM. Une fois le numéro détourné, l'attaquant reçoit tous les SMS OTP.

#### Risque

Le SIM swapping est activement utilisé pour contourner la 2FA SMS et compromettre des comptes bancaires, crypto et SaaS. Des incidents notables (Twitter, Coinbase...) ont popularisé ce vecteur. Pour les presets `medium` et `robust`, recommander SMS OTP comme facteur secondaire peut créer une fausse impression de sécurité.

#### Recommandation

Documenter explicitement la faiblesse du SMS OTP face au SIM swapping dans la documentation AIRS et dans les commentaires du code. Recommander TOTP (déjà implémenté) ou WebAuthn (déjà implémenté) comme alternatives plus sûres. Dans le preset `robust`, désactiver par défaut l'OTP SMS ou le reléguer à un facteur d'enregistrement seulement (pas d'authentification).

---

### F-12 [MOYEN] — Magic link : absence de binding IP / User-Agent

**Composant :** `MagicLinkService`

#### Constat

Le magic link est un token à usage unique de 15 minutes de validité. Cependant, rien dans le document n'indique que le token est lié à l'IP ou au User-Agent de la requête initiale. Si le lien est intercepté (email compromis, proxy transparent, Man-in-the-Middle), il peut être consommé depuis n'importe quel client.

#### Risque

Un magic link intercepté offre un accès complet au compte sans connaissance du mot de passe. Même si le magic link est "désactivé dans le preset `robust`", c'est le preset par défaut (`starter`, `medium`) qui est concerné. Dans le preset `medium` (SaaS B2C), l'interception d'email est un vecteur réaliste.

#### Recommandation

Enregistrer l'IP et le User-Agent au moment de la génération du magic link. Au moment de la consommation, avertir l'utilisateur (et optionnellement bloquer) si ces valeurs diffèrent significativement. Alternativement, implémenter un mécanisme de device fingerprint léger. Réduire l'expiration à 10 minutes pour le preset `medium`.

---

## 7. Findings de sévérité faible

### F-13 [FAIBLE] — `BlacklistedToken.cleanup_expired()` sans automatisation garantie

**Composant :** `BlacklistedToken.cleanup_expired()`, `tenxyte/tasks.py`

#### Constat

La table `BlacklistedToken` peut croître indéfiniment si la tâche de nettoyage n'est pas configurée. Le document recommande Celery pour la planification mais ne fournit pas de configuration prête à l'emploi ni de valeur seuil d'alerte.

#### Risque

Une table de blacklist non nettoyée peut devenir un goulot d'étranglement de performance en production (requêtes de validation JWT plus lentes, migrations plus longues). Au bout de plusieurs années en production intensive, la table peut contenir des dizaines de millions de lignes.

#### Recommandation

Fournir une tâche Celery prête à l'emploi dans `tenxyte/tasks.py` avec la configuration `CELERYBEAT_SCHEDULE` recommandée. Ajouter une commande de management Django (`manage.py tenxyte_cleanup`) comme alternative sans Celery. Documenter la fréquence recommandée (toutes les heures ou quotidiennement selon le volume).

---

### F-14 [FAIBLE] — `AuditLog.details` sans limite de taille documentée

**Composant :** `AuditLog.details`, `AgentPendingAction`

#### Constat

Le champ `details` de `AuditLog` est un JSON payload contextuel dont la taille maximale n'est pas documentée. Dans le contexte AIRS, ce champ peut contenir le payload complet d'une action en attente, potentiellement incluant des données utilisateur volumineuses.

#### Risque

Sans limite, un agent IA mal configuré pourrait générer des entrées d'audit de plusieurs Mo, causant une croissance non contrôlée de la base de données. Les entrées volumineuses peuvent également contenir accidentellement des données PII que le `PIIRedactionMiddleware` ne redacte pas (car il agit sur les réponses HTTP, pas sur les données persistées).

#### Recommandation

Documenter et imposer une limite de taille sur `details` (ex : 10 Ko). Ajouter une validation côté modèle. Considérer une politique de redaction des PII également pour les données persistées dans `AuditLog`, en particulier pour les payloads HITL (`AgentPendingAction`).

---

### F-15 [FAIBLE] — X-XSS-Protection header inclus par défaut (header obsolète)

**Composant :** `SecurityHeadersMiddleware`, `TENXYTE_SECURITY_HEADERS`

#### Constat

`SecurityHeadersMiddleware` injecte `X-XSS-Protection: 1; mode=block` par défaut. Ce header est obsolète depuis 2019 : Chrome 78+ l'a supprimé, Firefox ne l'a jamais supporté, Edge l'a retiré. Pire, des chercheurs ont démontré que ce header peut en réalité introduire des vecteurs XSS sur certains navigateurs anciens dans certaines configurations.

#### Risque

Risque faible (le header est ignoré par les navigateurs modernes), mais sa présence dans les defaults peut induire un faux sentiment de sécurité XSS chez les développeurs intégrant Tenxyte, et peut créer une surface d'alerte dans des audits de sécurité automatisés.

#### Recommandation

Retirer `X-XSS-Protection` des headers par défaut (ou le définir à `0` qui est la valeur recommandée par OWASP pour désactiver explicitement le filtre bugué). Documenter dans les notes de migration. La protection XSS doit être assurée par une `Content-Security-Policy` robuste, dont l'ajout devrait être promu dans les recommandations de déploiement.

---

## 8. Observations et recommandations complémentaires

### F-16 [INFO] — Protection CSRF : interaction avec Django non documentée

**Composant :** Documentation, `CORSMiddleware`, Django CSRF

#### Constat

Tenxyte implémente CORS mais ne documente pas explicitement l'interaction avec le middleware CSRF de Django. Pour les APIs JSON avec JWT Bearer, le CSRF n'est généralement pas un risque direct (un attaquant cross-origin ne peut pas lire la réponse pour récupérer le token). Cependant, si Tenxyte est utilisé avec des cookies de session en parallèle du JWT, le CSRF devient pertinent.

#### Risque

Risque informationnel. Une intégration mal documentée peut conduire un développeur à désactiver le CSRF Django sans comprendre les implications, ou à croire qu'il est protégé sans l'être.

#### Recommandation

Documenter explicitement la relation entre le CORS middleware, le CSRF Django et les modes d'authentification (JWT Bearer vs. cookies). Fournir une configuration d'exemple pour les cas d'usage hybrides. Mentionner que `django.middleware.csrf.CsrfViewMiddleware` est recommandé si des cookies de session sont utilisés en complément.

---

### F-17 [INFO] — `TENXYTE_CORS_ALLOW_ALL_ORIGINS` : paramètre footgun documenté mais existant

**Composant :** `CORSMiddleware`, `TENXYTE_CORS_ALLOW_ALL_ORIGINS`

#### Constat

Le paramètre `TENXYTE_CORS_ALLOW_ALL_ORIGINS=True` est documenté comme "dangereux en prod" mais demeure disponible dans l'API. Son existence même dans le code est un footgun potentiel pour des développeurs pressés qui ne liront pas la documentation.

#### Risque

Risque informationnel. La présence du paramètre normalise l'idée qu'il est acceptable dans certains contextes.

#### Recommandation

Envisager de retirer complètement ce paramètre du code (breaking change mineur) ou d'émettre un `DeprecationWarning` + un log `ERROR` lors de son activation. Si conservé, ajouter un check de démarrage qui refuse ce paramètre si `DEBUG=False`.

---

## 9. Plan d'action recommandé

| ID | Sévérité | Effort | Action |
|---|---|---|---|
| **F-01** | **CRITIQUE** | Moyen (2–4h) | Implémenter bcrypt-sha256 via passlib (pre-hash → bcrypt) |
| **F-02** | **CRITIQUE** | Faible (1–2h) | Hacher les agent tokens en SHA-256 au stockage |
| **F-03** | **CRITIQUE** | Faible (1h) | Vérifier `email_verified=true` avant fusion OAuth |
| **F-05** | **ÉLEVÉ** | Moyen (3–5h) | Ajouter `TENXYTE_NUM_PROXIES` + validation XFF |
| **F-07** | **ÉLEVÉ** | Faible (1h) | Check démarrage : `APPLICATION_AUTH_ENABLED` + `DEBUG` |
| **F-04** | **ÉLEVÉ** | Faible (1h) | Migrer backup codes vers bcrypt (déjà une dépendance) |
| **F-06** | **ÉLEVÉ** | Moyen (3h) | Restreindre l'export de `_bypass_tenant_filtering` |
| **F-11** | **MOYEN** | Faible (2h) | Documenter SIM swapping dans `OTPService` |
| **F-09** | **MOYEN** | Faible (1h) | HITL : passer le token en body POST |
| **F-13** | **FAIBLE** | Faible (1h) | Fournir `tenxyte/tasks.py` avec la tâche Celery |
| **F-15** | **FAIBLE** | Trivial (15min) | Retirer `X-XSS-Protection` des defaults |

---

## 10. Conclusion

Tenxyte est un package de sécurité qui témoigne d'une réflexion sérieuse et d'une connaissance approfondie des best practices de sécurité modernes. La grande majorité des décisions architecturales sont correctes, voire exemplaires : utilisation de bcrypt, k-anonymity HIBP, ContextVar pour l'isolation multi-tenant, circuit breaker AIRS avec double-passe RBAC, audit trail exhaustif.

Les **3 findings critiques** sont toutefois bloquants pour une publication responsable :

- **F-01** (bcrypt 72 octets) : peut conduire les utilisateurs à croire avoir des mots de passe forts alors qu'ils ne le sont pas.
- **F-02** (agent tokens en clair) : une compromission DB expose tous les agents actifs sur tous les tenants.
- **F-03** (OAuth sans `email_verified`) : vecteur d'Account Takeover documenté, exploitable sans connaissance du mot de passe.

Ces trois corrections représentent un effort total estimé à **4–7 heures de développement**. Une fois corrigées, et avec les findings élevés traités, Tenxyte atteindra un niveau de sécurité tout à fait supérieur à la majorité des packages d'authentification Django disponibles sur PyPI.

---

> *La prochaine révision devrait également intégrer une suite de tests de sécurité automatisés (tests d'intégration couvrant les bypass de tenant, les forgeries XFF, les JWT altérés) pour prévenir toute régression sécurité dans les futures versions.*

---

*Ce rapport est confidentiel et destiné à l'équipe de développement Tenxyte uniquement.*