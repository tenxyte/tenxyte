# Next Steps for Tenxyte

## Fondation

### Algorithm de signature JWT disponibles

#### HMAC

- HS256
- HS384
- HS512

#### RSA

- RS256
- RS384
- RS512

#### ECDSA

- ES256
- ES384
- ES512

#### EdDSA

- EdDSA

- Champ kid supporté et implémenté ?
- Le Payload contient t'il actuellement:
  - iss
  - sub
  - aud
  - exp
  - nbf
  - iat
  - jti

  - Études Taille et Performance du corps du JWT
  - Études Taille et Performance des Headers du JWT
  - Études Taille et Performance de la signature du JWT

### Signature

- Intégrité ?
- Authenticité ?

### Types de JWT supportés

- JWS
- JWE
- Embedded JWT JWS + JWE

### Sécurité de la clé

- Ne jamais logguer la clé
- Ne jamais inclure dans le code source
- Conseiller le stockage des tokens dans les variables d'environnement
- Longueur des clé respecté > 256 bits
- Rotation regulière des clés avec kid ?

## Cruptographie

- Algo Symétriques (HMAC)
  - SHA256
  - SHA384
  - SHA512
- Algo Asymétriques
  - RSA
    - RS256
    - RS384
    - RS512
  - RSA-PSS (À préférer à RSA corriger les faiblesses PKCS#1 v1.5)
    - PS256
    - PS384
    - PS512
  - ECDSA
    - ES256
    - ES384
    - ES512
  - EdDSA
    - EdDSA

### Signature

- Hash calculé avec les meilleures méthodes ?
- Signature et déchiffrement des tokens sécurisés ?
- Vérification des signatures sécurisée ?
- Gestion des clés sécurisée ?
- Taille des clés Symétriques -> 256 bits minimum
- Taille des clés Asymétriques -> 2048 bits minimum

### Recommendations pour les choix de configurations

- ES256 pour les nouvelles implémentations (Expliquer pourquoi ! Compact, Rapide, Secure)
- RS256 pour la compatibilité maximum
- HS256 pour la performance et pour les systèmes mono-acteur ou micro-services internes

### Cas d'usage OAUTH2 / OIDC / SSO

- Identity Provider (IdP) pour signer les tokens EC P-256 ?
- Gestion des clé Publics
   - Support des PEM déjà sur le package, s'assurer des meilleures pratiques et de la sécurité
   - Préférer JWKS (JSON Web Key Set) sur /.well-known/jwks.json au lieu de manipuler des PEM
      - Exemple de corps
         - kty
         - crv
         - x
         - y
         - kid
         - alg
         - use
         - n
         - e
         - d
      - Flux de vérification
         - reçois le JWT
         - lit le kid du header
         - cherche dans le cache local pour retrouver la clé
            - OUI ? Utiliser la clé en cache
            - NON ? Requeter /.well-known/jwks.json pour récupérer les clés publiques
         - Filtre les clés pour trouver celle qui correspond au kid
         - Vérifie la signature du JWT avec la clé trouvée
         - Valider les claims (iss, aud, exp, nbf, iat, etc.)
         - Valide
            - OUI ? Accorde l'accès
            - NON ? Refuse l'accès
      - Implémenter le caching des clés publiques pour éviter les requêtes répétées à /.well-known/jwks.json
         - Ne jamais faire confiance au jku du JWT pour récupérer les clés, toujours utiliser une URL de confiance pour le JWKS
         - Durée de vie du cache configurable (ex: 1 heure)
         - Invalidation du cache en cas de rotation des clés
      - Implémenter la rotation des clés avec kid
         - Pdoduction standard 90Jrs
         - Haute sécurité (finance, santé) 30Jrs
         - Suspicion de compromission immédiate
         - Processus de rotation
            - Générer une nouvelle paire de clés (privée et publique)
            - Ajouter la nouvelle clé publique au JWKS avec un nouveau kid
            - Configurer le système pour signer les nouveaux JWT avec la nouvelle clé privée
            - Maintenir l'ancienne clé publique dans le JWKS pendant une période de transition (ex: 1 semaine) pour permettre la validation des JWT signés avec l'ancienne clé
            - Retirer l'ancienne clé publique du JWKS après la période de transition
      - Implémenter la conversion entre PEM et JWK pour faciliter l'intégration avec les systèmes existants
         - Utiliser des bibliothèques de cryptographie pour gérer la conversion de manière sécurisée
         - Fournir des outils ou des scripts pour aider les utilisateurs à convertir leurs clés PEM en JWK et vice versa
- Algorithmes de chifrement pour les JWE
   - RSA-OAEP-256 pour le chiffrement de la clé de session
      - Support des algorithmes de chiffrement de clé de session recommandés pour les JWE
         - RSA
            - RSA-OAEP-256 (RSAES OAEP avec SHA-256)
            - RSA-OAEP-384 (RSAES OAEP avec SHA-384)
            - RSA-OAEP-512 (RSAES OAEP avec SHA-512)
         - AES Key Wrap
            - A128KW (AES Key Wrap avec une clé de 128 bits)
            - A192KW (AES Key Wrap avec une clé de 192 bits)
            - A256KW (AES Key Wrap avec une clé de 256 bits)
         - ECDH-ES (Elliptic Curve Diffie-Hellman Ephemeral Static)
            - ECDH-ES avec les courbes P-256, P-384, P-521
   - A256GCM pour le chiffrement du contenu du JWT
      - Support des algorithmes de chiffrement de contenu recommandés pour les JWE
         - AES GCM
            - A128GCM (AES GCM avec une clé de 128 bits)
            - A192GCM (AES GCM avec une clé de 192 bits)
            - A256GCM (AES GCM avec une clé de 256 bits)
         - AES CBC + HMAC
            - A128CBC-HS256 (AES CBC avec une clé de 128 bits et HMAC SHA-256)
            - A192CBC-HS384 (AES CBC avec une clé de 192 bits et HMAC SHA-384)
            - A256CBC-HS512 (AES CBC avec une clé de 256 bits et HMAC SHA-512)
   - Header JWE Complet
      - alg
      - enc
      - kid
      - typ
      - cty
   - Implémenter la combinaison optimale JWE + JWS pour les cas d'usage nécessitant à la fois confidentialité et intégrité/authenticité
      - Signer le JWT avec JWS pour garantir l'intégrité et l'authenticité (Respecter les meilleures pratiques de signature recommandées)
      - Chiffrer le JWT avec JWE pour garantir la confidentialité (Respecter les meilleures pratiques de chiffrement recommandées)

## Flux d'authentification et d'authorisation

### Vue d'ensemble
- POST /login
   - Vérifie les credentials de l'utilisateur
   - Emet access_token (15 min)
   - Emet refresh_token (7 jours)
      - return { access_token, refresh_token, token_type: "Bearer", expires_in: 900 }
         - Client stocke et utilise les tokens pour accéder aux ressources protégées
- GET /protected-resource
   - Vérifie sig,
   - Vérifie claims (exp, nbf, aud, iss, etc.)
   - Accorde ou refuse l'accès
- POST /refresh (refresh_token)
   - Vérifie le refresh_token
   - Emet un nouveau access_token (15 min)
   - Optionnellement émet un nouveau refresh_token (7 jours)
      - return { access_token, refresh_token, token_type: "Bearer", expires_in: 900 }
         - Client remplace les anciens tokens par les nouveaux
- Payload type d'un access_token
   - iss: "https://my-auth-server.com"
   - sub: "user123"
   - aud: "my-api"
   - exp: 1710000000
   - nbf: 1700000000
   - iat: 1700000000
   - jti: "unique-token-id"
   - roles: ["admin", "user"]
- Payload type d'un refresh_token
   - iss: "https://my-auth-server.com"
   - sub: "user123"
   - aud: "https://my-auth-server.com"
   - exp: 1710000000
   - nbf: 1700000000
   - iat: 1700000000
   - jti: "unique-refresh-token-id"
   - type: "refresh"

### Stockage du token coté client
- Approches
   - access_token
      - Simple variable en mémoire pour les applications SPA modernes (ex: React, Vue, Angular) (Meilleure recommandation pour les applications modernes)
      - Mémoire de l'application (ex: React state, Vuex, etc.) pour éviter les vulnérabilités XSS
      - Ne jamais stocker les tokens dans le localStorage ou sessionStorage en raison des risques de sécurité associés
   - refresh_token
      - HttpOnly Secure Cookie pour les applications web traditionnelles (Meilleure recommandation pour les applications web traditionnelles)
      - Stockage sécurisé côté serveur pour les applications mobiles ou desktop (ex: Keychain sur iOS, Keystore sur Android, etc.)
      - Ne jamais exposer les refresh_tokens au client pour éviter les risques de sécurité associés

### Validation coté serveur
- Format du token
   - Vérifier que le token est un JWT valide (3 parties séparées par des points)
   - Vérifier que les parties du token sont correctement encodées en Base64URL
- Algorithme de signature
   - Vérifier que l'algorithme de signature utilisé est supporté et sécurisé (ex: ES256, RS256, HS256)
   - Refuser les tokens utilisant des algorithmes faibles ou non supportés (ex: none, HS512 sans clé suffisamment longue, etc.)
- Signature (Validité cryptographique)
   - Vérifier la signature du token en utilisant la clé appropriée (symétrique ou asymétrique)
   - Utiliser des bibliothèques de cryptographie sécurisées pour la vérification de la signature
- Claims standard
   - Expiration (exp)
      - Vérifier que le token n'est pas expiré (exp > current_time)
      - Tolérance de temps configurable pour éviter les problèmes de synchronisation d'horloge (ex: 60 secondes ~ 5 minutes)
   - Not Before (nbf)
      - Vérifier que le token est valide à partir de la date actuelle (nbf <= current_time)
   - Issueur (iss)
      - Vérifier que le token a été émis par une source de confiance (ex: "https://my-auth-server.com")
   - Audience (aud)
      - Vérifier que le token est destiné à l'audience correcte (ex: "my-api")
      - En cas d'audience multiple, vérifier que l'audience attendue est présente dans la liste des audiences du token
   - Type (type)
      - Vérifier que le type de token est correct pour le contexte d'utilisation (ex: "access" pour les access_tokens, "refresh" pour les refresh_tokens)

### Refresh Token Rotation
- Client -> RT_1 -> Server
   - Vérifie RT_1
   - Invalide RT_1
   - Emettre AT-2 + RT_2
      - Client <- AT_2 + RT_2
   - Prochaine rotation etc.
- Implémenter reuse detection
   - Reuse detecté (Révoquer toute la famille de tokens associés à l'utilisateur)
      - Famille de token issue d'une meme session d'authentification
      - Eviter les faux positifs
         - Ajouter une tolérance de temps pour les tokens révoqués (ex: 5 minutes) pour éviter les problèmes de synchronisation d'horloge ou les requêtes simultanées
         - Fenêtre de déduplication par jti

### Supporter OAUTH2.0 ?
- Acteurs
   - Resource Owner (User)
   - Client (Application qui demande l'accès aux ressources)
   - Authorization Server (Serveur qui émet les tokens)
   - Resource Server (Serveur qui héberge les ressources protégées)
- Grants Types
   - client_credentials (Machine-to-Machine) taches planifiées cron, micro-services, webhook sortants, workers, etc.
      - client_id et client_secret -> access_token
         - client(service backend) ex.
            - POST /oauth/token
               - grant_type=client_credentials
               - client_id=your_client_id
               - client_secret=your_client_secret
               - scope=read:contracts write:contracts
                  - reponse
                     - { access_token, token_type: "Bearer", expires_in: 3600 }
            - GET /api/contracts -> resource server
               - Authorization: Bearer <access_token>
               - payload typique:
                  - iss: "https://my-auth-server.com"
                  - sub: "client_id_123"
                  - aud: "my-api"
                  - scope: "read:contracts write:contracts"
                  - exp: 1710000000
                  - iat: 1700000000
                  - jti: "unique-token-id"
   - authorization_code (User Authentication)
      - Navigator -> Authorization Server
         - GET /oauth/authorize
            - response_type=code
            - client_id=your_client_id
            - redirect_uri=https://your-app.com/callback
            - scope=openid profile email
            - code_chalenge=S256(code_verifier) (PKCE)
            - state=random_csrf_token
               - User Authentifie et autorise le client
         - Authorization Server redirige (302) -> https://your-app.com/callback avec les paramètres
            - code=authorization_code
            - state=random_csrf_token
         - POST /oauth/token
            - grant_type=authorization_code
            - code=authorization_code
            - code_verifier=original_code_verifier (PKCE)
            - redirect_uri=https://your-app.com/callback
            - client_id=your_client_id
               - reponse
                  - { access_token, refresh_token, id_token, token_type: "Bearer", expires_in: 3600 }
         - GET /api/protected-resource
            - Authorization: Bearer <access_token>
   - device_flow (User Authentication sur des appareils sans navigateur)
      - Device -> Authorization Server
         - POST /oauth/device/code
            - client_id=your_client_id
            - scope=openid profile email
               - reponse
                  - { device_code, user_code, verification_uri, expires_in: 900, interval: 5 }
         - User navigue vers verification_uri et entre user_code pour authentifier et autoriser le client
         - Device -> Authorization Server
            - POST /oauth/token
               - grant_type=urn:ietf:params:oauth:grant-type:device_code
               - device_code=device_code
               - client_id=your_client_id
                  - reponse
                     - { access_token, refresh_token, id_token, token_type: "Bearer", expires_in: 3600 }
         - GET /api/protected-resource
            - Authorization: Bearer <access_token>

#### Introspection
- Opération simple Vérification simple locale
- Opération complexe, faire l'introspection vérifier de l'état de révocation, etc. (ex: token révoqué, token compromis, etc.)
   - POST /oauth/introspect
      - token=access_token
      - client_id=your_client_id
      - client_secret=your_client_secret
         - reponse
            - { active: true, scope: "read:contracts write:contracts", client_id: "client_id_123", username: "user123", exp: 1710000000, iat: 1700000000, sub: "user123", aud: "my-api", iss: "https://my-auth-server.com", jti: "unique-token-id" }

### Supporter OIDC ?
- Tokens
   - Access Token (JWT ou opaque)
      - Durée de vie courte (5 - 15 min)
      - Accéder aux ressources protégées sur le Resource Server
   - ID Token (JWT)
      - Claims spécifiques OIDC
         - nonce (protection contre les attaques de replay)
            - Generation cote client d'un nonce unique avant de rediriger vers l'Authorization Server
            - Inclusion du nonce la requete authorize
            - l'auth server inclut le même nonce dans l'ID token émis
            - Validation du nonce dans l'ID token pour s'assurer qu'il correspond à celui généré côté client
         - at_hash (Hash de l'access token pour vérifier que l'ID token est lié à l'access token) protection contre substitution d'access token
            - Calcul de l'at_hash en prenant les 16 premiers octets du hash SHA-256 de l'access token et en les encodant en Base64URL
            - Inclusion de l'at_hash dans le ID token émis
            - Validation de l'at_hash dans le ID token pour s'assurer qu'il correspond à l'access token reçu
         - azp (Authorized Party) pour indiquer le client qui a demandé l'authentification - protection contre Confusion d'identité entre clients
            - Inclusion de l'azp dans le ID token pour indiquer le client qui a demandé l'authentification
            - Validation de l'azp dans le ID token pour s'assurer qu'il correspond au client attendu
         - auth_time (Timestamp de l'authentification de l'utilisateur pour permettre la gestion de la session et la détection d'inactivité)
            - Inclusion de l'auth_time dans le ID token pour indiquer le moment de l'authentification de l'utilisateur
            - Validation de l'auth_time dans le ID token pour gérer la session utilisateur et détecter les périodes d'inactivité
   - Refresh Token (JWT ou opaque)
      - Durée de vie plus longue que l'access token (7 - 30 jours)
      - Renouveler l'access ou l'ID token sans nécessiter une nouvelle authentification de l'utilisateur
- Flux complet OIDC
   - App reçoit AT +  IDT + RT
   - App valide IDT (Utilisation strictement au cote client pour vérifier l'identité de l'utilisateur, ne pas utiliser pour accéder aux ressources protégées)
      - Decoder sans appel reseau pour extraire les claims de l'ID token
      - Vérifier les claims standard (iss, aud, exp, nbf, iat, nonce, at_hash, azp, auth_time, etc.)
      - Vérifier la signature de l'ID token pour s'assurer de son intégrité et de son authenticité
   - App utilise l'AT pour accéder aux ressources protégées sur le Resource Server
      - Inclure l'access token dans les requêtes au Resource Server (ex: Authorization: Bearer <access_token>)
      - Validation strictement coté serveur et lit les scopes/roles etc. pour accorder ou refuser l'accès aux ressources protégées
      - L'App cliente traite l'AT comme opaque et ne tente pas de le décoder ou de l'utiliser pour vérifier l'identité de l'utilisateur
   - App utilise le RT pour renouveler l'AT et l'IDT lorsque nécessaire
      - Utilisé strictement pour renouveler les tokens sans nécessiter une nouvelle authentification de l'utilisateur
      - Ne jamais envoyer le refresh token à l'API Métier ou au Resource Server, il doit être utilisé uniquement pour obtenir de nouveaux tokens auprès de l'Authorization Server
- Discovery Endpoint
   - Supporter le endpoint de découverte OIDC pour permettre aux clients de découvrir automatiquement les configurations de l'Authorization Server
      - GET /.well-known/openid-configuration
         - reponse
            - { 
               issuer: "https://my-auth-server.com",
               authorization_endpoint: "https://my-auth-server.com/oauth/authorize",
               token_endpoint: "https://my-auth-server.com/oauth/token",
               userinfo_endpoint: "https://my-auth-server.com/userinfo",
               jwks_uri: "https://my-auth-server.com/.well-known/jwks.json",
               introspection_endpoint: "https://my-auth-server.com/oauth/introspect",
               revocation_endpoint: "https://my-auth-server.com/oauth/revoke",
               end_session_endpoint: "https://my-auth-server.com/oauth/logout",
               device_authorization_endpoint: "https://my-auth-server.com/oauth/device/code",
               response_types_supported: ["code", "token", "id_token", "code token", "code id_token", "token id_token"],
               grant_types_supported: ["authorization_code", "client_credentials", "refresh_token", "urn:ietf:params:oauth:grant-type:device_code"],
               subject_types_supported: ["public", "pairwise"],
               id_token_signing_alg_values_supported: ["ES256", "RS256"],
               token_endpoint_auth_methods_supported: ["client_secret_basic", "client_secret_post", "client_secret_jwt", "private_key_jwt"],
               scopes_supported: ["openid", "profile", "email", "offline_access"],
               claims_supported: ["sub", "iss", "aud", "exp", "nbf", "iat", "jti", "name", "email", "email_verified", "locale", "picture", "nonce", "at_hash", "azp", "auth_time"],
               code_challenge_methods_supported: ["S256", "plain"],
               require_pkce: true
            }
   -  Implémenter l'utilisation du discovery endpoint dans les clients pour découvrir automatiquement les configurations de l'Authorization Server
      - Permettre aux clients de récupérer dynamiquement les URLs des endpoints, les algorithmes supportés, les scopes disponibles, etc. à partir du discovery endpoint
      - Faciliter l'intégration avec différents Authorization Servers sans nécessiter de configuration manuelle spécifique pour chaque serveur
-  Valider id_token (Spec OIDC)
   -  JWT bien formé (3 parties séparées par des points, encodage Base64URL correct)
   -  Algorithme de signature supporté et sécurisé (ex: ES256, RS256)
   -  Signature valide en utilisant la clé appropriée (symétrique ou asymétrique)
   -  Claims standard
      -  Expiration (exp > current_time)
      -  Not Before (nbf <= current_time)
      -  Issueur (iss correspond à l'Authorization Server de confiance)
      -  Audience (aud correspond au client attendu)
      -  Nonce (nonce correspond à celui généré côté client pour protéger contre les attaques de replay)
      -  at_hash (at_hash correspond à l'access token reçu pour protéger contre la substitution d'access token)
      -  azp (azp correspond au client qui a demandé l'authentification pour protéger contre la confusion d'identité entre clients)
      -  auth_time (auth_time est utilisé pour gérer la session utilisateur et détecter les périodes d'inactivité)

## Sécurité JWT: Attaques et contre-mesures

### Algorithme confusion
- Attaque: Un attaquant modifie le header du JWT pour utiliser un algorithme de signature faible ou non supporté (ex: none) pour contourner la vérification de la signature
- Contre-mesure: Refuser les tokens utilisant des algorithmes faibles ou non supportés et s'assurer que le serveur de validation vérifie que l'algorithme de signature utilisé est bien celui attendu et sécurisé (ex: ES256, RS256)

### RS256 - HS256 confusion
- Attaque: Un attaquant modifie le header du JWT pour indiquer que l'algorithme de signature est HS256 au lieu de RS256, ce qui peut amener le serveur à utiliser la clé publique RSA comme clé HMAC pour vérifier la signature, permettant ainsi à l'attaquant de créer des tokens valides avec une signature HMAC
- Contre-mesure: S'assurer que le serveur de validation vérifie que l'algorithme de signature utilisé correspond au type de clé attendu (ex: RS256 doit utiliser une clé publique RSA, HS256 doit utiliser une clé secrète symétrique) et refuser les tokens qui ne respectent pas cette correspondance

### Brute Force sur les clés HMAC
- Attaque: Un attaquant tente de deviner la clé secrète utilisée pour signer les tokens HMAC en essayant différentes combinaisons jusqu'à trouver la bonne, ce qui peut permettre de créer des tokens valides
- Contre-mesure: Utiliser des clés secrètes suffisamment longues (au moins 256 bits) pour rendre les attaques de brute force impraticables, et éviter d'utiliser des clés faibles ou facilement devinables

### JWT avec exp absent ou mal configuré
- Attaque: Un attaquant crée un token JWT sans claim exp ou avec une date d'expiration très lointaine, ce qui peut permettre au token de rester valide indéfiniment et d'être utilisé pour accéder aux ressources protégées sans limite de temps
- Contre-mesure: S'assurer que tous les tokens JWT émis incluent un claim exp avec une date d'expiration raisonnable (ex: 15 minutes pour les access_tokens) et refuser les tokens qui n'incluent pas de claim exp ou qui ont une date d'expiration trop lointaine

### Vol de token (XSS, CSRF, MITM)
-  XSS
   - Attaque: Un attaquant exploite une vulnérabilité XSS dans l'application pour injecter du code malveillant qui vole les tokens JWT stockés côté client (ex: localStorage, sessionStorage) et les envoie à un serveur contrôlé par l'attaquant
   - Contre-mesure: Ne jamais stocker les tokens JWT dans le localStorage ou sessionStorage en raison des risques de sécurité associés, et préférer des méthodes de stockage plus sécurisées (ex: HttpOnly Secure Cookies pour les applications web traditionnelles, stockage sécurisé côté serveur pour les applications mobiles ou desktop)
-  CSRF
   - Attaque: Un attaquant crée une requête malveillante à l'aide d'un token JWT volé et incite un utilisateur authentifié à exécuter cette requête, ce qui peut entraîner des actions non autorisées sur les ressources protégées
   - Contre-mesure: Utiliser des tokens JWT avec une durée de vie courte (ex: 15 minutes pour les access_tokens) pour limiter la fenêtre d'opportunité pour les attaques CSRF, et implémenter des mécanismes de protection contre les CSRF (ex: tokens CSRF, SameSite cookies, etc.) pour empêcher les requêtes malveillantes d'être exécutées
-  MITM
   - Attaque: Un attaquant intercepte les communications entre le client et le serveur pour voler les tokens JWT en transit, ce qui peut permettre à l'attaquant d'accéder aux ressources protégées en utilisant les tokens volés
   - Contre-mesure: Utiliser HTTPS pour toutes les communications entre le client et le serveur afin de chiffrer les données en transit et empêcher les attaques MITM, et s'assurer que les certificats SSL/TLS sont correctement configurés et à jour pour garantir la sécurité des communications, http-only secure cookies pour les applications web traditionnelles, stockage sécurisé côté serveur pour les applications mobiles ou desktop, et implémenter des mécanismes de détection d'intrusion pour identifier les tentatives d'attaque MITM, HSTS (HTTP Strict Transport Security) pour forcer l'utilisation de HTTPS, et des mécanismes de rotation des clés pour limiter les risques en cas de compromission des tokens, CSP (Content Security Policy) pour limiter les sources de contenu et réduire les risques de XSS, et implémenter des mécanismes de surveillance et d'alerte pour détecter les activités suspectes liées à l'utilisation des tokens JWT.

### Replay Attack
- Attaque: Un attaquant capture un token JWT valide et le réutilise pour accéder aux ressources protégées, même après que le token ait été utilisé une première fois, ce qui peut entraîner des actions non autorisées
- Contre-mesure: Utiliser des tokens JWT avec une durée de vie courte (ex: 15 minutes pour les access_tokens) pour limiter la fenêtre d'opportunité pour les attaques de replay, et implémenter des mécanismes de détection de replay (ex: jti claim avec une liste de tokens utilisés, nonce claim pour les ID tokens, etc.) pour identifier et refuser les tokens qui ont déjà été utilisés, et implémenter des mécanismes de surveillance et d'alerte pour détecter les activités suspectes liées à l'utilisation des tokens JWT, tels que les tentatives de réutilisation de tokens ou les accès simultanés avec le même token.

### Injection dans les claims
- Attaque: Un attaquant injecte des données malveillantes dans les claims d'un token JWT, ce qui peut entraîner des comportements inattendus ou des vulnérabilités dans les applications qui consomment ces tokens
- Contre-mesure: Valider et assainir les données des claims avant de les utiliser dans l'application, et éviter d'inclure des données sensibles ou non nécessaires dans les claims pour réduire les risques d'injection, et implémenter des mécanismes de surveillance et d'alerte pour détecter les activités suspectes liées à l'utilisation des tokens JWT, tels que les tentatives d'injection de données malveillantes dans les claims.

### SSRF via jku/x5u
- Attaque: Un attaquant exploite les champs jku (JSON Web Key URL) ou x5u (X.509 URL) dans le header d'un token JWT pour forcer le serveur de validation à faire des requêtes vers des ressources contrôlées par l'attaquant, ce qui peut entraîner des fuites d'informations sensibles ou des attaques de type SSRF (Server-Side Request Forgery)
- Contre-mesure: Ne jamais faire confiance aux champs jku ou x5u du header d'un token JWT pour récupérer les clés de validation, et toujours utiliser une URL de confiance pour récupérer les clés publiques (ex: un endpoint JWKS sur le serveur de validation), et implémenter des mécanismes de validation stricts pour s'assurer que les URLs utilisées pour récupérer les clés sont bien celles attendues et ne pointent pas vers des ressources contrôlées par des attaquants, et implémenter des mécanismes de surveillance et d'alerte pour détecter les activités suspectes liées à l'utilisation des tokens JWT, tels que les tentatives d'exploitation des champs jku ou x5u pour faire des requêtes vers des ressources non autorisées.

### Checklist de sécurité pour les JWT (Production Ready)
   -  Algorithme whitelisté et sécurisé (ex: ES256, RS256, HS256 avec clé suffisamment longue)
   -  Secret HMAC suffisamment long (au moins 256 bits) généré par CSPRNG de manière sécurisée
   -  Claims exp toujours presents et validés pour éviter les tokens valides indéfiniment
   -  Access token <= 15 minutes pour limiter la fenêtre d'opportunité pour les attaques de replay et de vol de token
   -  Refresh token <= 7 jours pour limiter les risques en cas de compromission du token stocké côté client cookie http-only + secure + SameSite pour les applications web traditionnelles, stockage sécurisé côté serveur pour les applications mobiles ou desktop
   -  HTTPS strict et HSTS pour protéger les tokens en transit contre les attaques MITM
   -  CSP défini et restrictive pour réduire les risques de XSS
   -  jti présent + mecanisme de revocation pour les tokens JWT pour permettre la détection de replay et la révocation des tokens compromis (logout, blaCKlist, etc.)
   -  Signature vérifiée avec des bibliothèques de cryptographie sécurisées pour garantir l'intégrité et l'authenticité des tokens
   -  jku/x5u ignorés ou whitelistés strictement pour éviter les attaques de type SSRF
   -  Bibliothèques de validation robustes pour vérifier les claims standard (iss, aud, exp, nbf, iat, nonce, at_hash, azp, auth_time, etc.) et refuser les tokens qui ne respectent pas les critères de validation (CVE Monitorés pour les bibliothèques de validation JWT)
   -  Logs d'accès et de validation des tokens pour permettre la détection d'activités suspectes liées à l'utilisation des tokens JWT, tout en veillant à ne pas logguer les tokens eux-mêmes ou les secrets utilisés pour les signer

## JWT Advance Use Cases

### JWT pour les micro-services
-  Implémenter Token Exchange (RFC 8693) pour permettre aux micro-services d'échanger des tokens JWT avec des scopes ou des audiences spécifiques pour accéder à d'autres micro-services, tout en respectant les principes de sécurité et de séparation des responsabilités entre les services
   -  Service A reçoit un access_token avec des scopes limités (ex: read:serviceA)
   -  Service A échange ce token contre un nouveau access_token avec des scopes spécifiques pour accéder à Service B (ex: read:serviceB) en appelant le endpoint de token exchange de l'Authorization Server
   -  Service A utilise le nouveau access_token pour accéder à Service B, qui valide le token et accorde ou refuse l'accès en fonction des scopes et des claims présents dans le token
      -  Exemple de structure typique
         -  {
               "sub": "user_42",
               "act": {
                  "sub": "serviceA",
                  "scope": "read:serviceB"
               },
               "aud": "serviceB",
               "scope": "read:resource",
               "exp": 1710000000,
               "iat": 1700000000,
         }
-  Implémenter mTLS + JWT pour renforcer la sécurité des communications entre les micro-services en utilisant à la fois l'authentification mutuelle TLS et les tokens JWT pour garantir l'identité et les autorisations des services qui communiquent entre eux
   -  Service A présente un certificat client lors de l'établissement de la connexion TLS avec Service B pour s'authentifier mutuellement
   -  Service A inclut un access_token JWT dans les requêtes envoyées à Service B pour fournir des informations sur les autorisations et les claims associés à la requête
   -  Service B valide à la fois le certificat client présenté par Service A et le token JWT pour accorder ou refuser l'accès aux ressources protégées, en s'assurant que les deux mécanismes d'authentification sont correctement configurés et sécurisés
-  Implémenter JWT & Webhooks (Approches)
   -  JWT Token dans le query string de l'URL du webhook (ex: https://webhook-receiver.com/endpoint?token=jwt_token) pour permettre au serveur émetteur de signer les requêtes de webhook avec un token JWT, que le serveur récepteur peut valider pour s'assurer de l'authenticité et de l'intégrité des requêtes reçues
   -  JWT Token dans le handshake initial du webhook (ex: lors de l'enregistrement du webhook, le serveur émetteur fournit un token JWT que le serveur récepteur doit inclure dans les en-têtes des requêtes de webhook pour validation) pour permettre une validation plus sécurisée des requêtes de webhook en utilisant des tokens JWT signés et vérifiés à chaque requête pour garantir que seules les requêtes authentiques et autorisées sont traitées par le serveur récepteur
   -  JWT Token dans le premier message du webhook (ex: lors de l'établissement de la connexion du webhook, le serveur émetteur envoie un message initial contenant un token JWT que le serveur récepteur doit valider avant d'accepter les requêtes de webhook suivantes) pour permettre une validation sécurisée des requêtes de webhook en utilisant un token JWT initial pour établir la confiance entre le serveur émetteur et le serveur récepteur, et en validant ce token avant d'accepter les requêtes de webhook suivantes pour garantir que seules les requêtes authentiques et autorisées sont traitées par le serveur récepteur.
   -  Gestion de l'expiration sur une connexion de webhook longue durée (ex: 24h) en utilisant des tokens JWT avec une durée de vie courte (ex: 15 minutes) et en implémentant un mécanisme de renouvellement de token pour permettre au serveur émetteur de fournir de nouveaux tokens JWT valides au serveur récepteur avant l'expiration du token actuel, afin de maintenir la validité des requêtes de webhook sur une période prolongée tout en garantissant la sécurité et la validité des tokens utilisés pour l'authentification et l'autorisation des requêtes de webhook.
-  Federated Identity
   -  Implémenter la fédération d'identité avec JWT pour permettre aux utilisateurs de s'authentifier auprès de différents fournisseurs d'identité (ex: Google, Facebook, etc.) en utilisant des tokens JWT émis par ces fournisseurs d'identité, et en validant ces tokens pour accorder l'accès aux ressources protégées dans votre application
      -  L'utilisateur s'authentifie auprès du fournisseur d'identité (ex: Google) et reçoit un token JWT émis par ce fournisseur
      -  L'utilisateur présente ce token JWT à votre application pour accéder à des ressources protégées
      -  Votre application valide le token JWT en vérifiant la signature, les claims standard (iss, aud, exp, etc.) et les claims spécifiques au fournisseur d'identité (ex: email, name, etc.) pour accorder ou refuser l'accès aux ressources protégées en fonction des autorisations associées au token JWT émis par le fournisseur d'identité.
      -  Implémenter la prise en charge de plusieurs fournisseurs d'identité en configurant votre application pour valider les tokens JWT émis par différents fournisseurs d'identité, et en gérant les différentes configurations de validation (ex: clés de signature, claims spécifiques, etc.) pour chaque fournisseur d'identité pris en charge.
-  Implémenter et respecter le modèle Zero trust et JWT
-  Implmenter SPIFFE/SPIRE
-  Implémenter Envoy + SPIFFE






