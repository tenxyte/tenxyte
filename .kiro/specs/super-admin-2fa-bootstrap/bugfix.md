# Document d'Exigences Bugfix

## Introduction

Ce document décrit le correctif pour le paradoxe de bootstrap 2FA des super admins dans Tenxyte. Actuellement, les utilisateurs avec le rôle `super_admin` sont obligés d'avoir 2FA activé pour se connecter (comme indiqué dans la documentation : "Admin and super_admin users are required to enable 2FA before logging in"), mais l'activation de 2FA nécessite d'être connecté avec un token valide. Cela crée un blocage circulaire qui empêche tout accès initial au compte super admin.

**Impact** : Les super admins nouvellement créés (via `createsuperuser` ou élévation de rôle) sont complètement bloqués et ne peuvent ni se connecter ni activer 2FA, rendant le compte inutilisable sans intervention manuelle en base de données.

## Analyse du Bug

### Comportement Actuel (Défaut)

1.1 QUAND un super admin tente de se connecter ET que 2FA n'est pas activé sur son compte ALORS le système refuse la connexion avec l'erreur `403 ADMIN_2FA_SETUP_REQUIRED`

1.2 QUAND un super admin tente d'appeler l'endpoint `POST /2fa/setup/` sans token d'authentification valide ALORS le système rejette la requête avec `401 Unauthorized`

1.3 QUAND un super admin est créé via `createsuperuser` ALORS le système crée le compte avec `is_superuser=True` MAIS sans 2FA activé

1.4 QUAND un utilisateur régulier est élevé au rôle `super_admin` via l'API ALORS le système assigne le rôle MAIS ne vérifie pas si 2FA est déjà activé

### Comportement Attendu (Correct)

2.1 QUAND un super admin tente de se connecter ET que 2FA n'est pas activé sur son compte ALORS le système DOIT retourner un token temporaire à usage unique avec portée restreinte `2fa_setup_only` ET inclure `requires_2fa_setup: true` dans la réponse

2.2 QUAND un super admin utilise le token à portée restreinte `2fa_setup_only` pour appeler `POST /2fa/setup/` ALORS le système DOIT autoriser la requête ET retourner le QR code et les codes de secours

2.3 QUAND un super admin confirme 2FA via `POST /2fa/confirm/` avec le token `2fa_setup_only` ET un code TOTP valide ALORS le système DOIT activer 2FA sur le compte ET retourner un token complet avec toutes les permissions

2.4 QUAND un super admin tente d'utiliser le token `2fa_setup_only` pour accéder à un endpoint autre que `/2fa/setup/` ou `/2fa/confirm/` ALORS le système DOIT rejeter la requête avec `403 INSUFFICIENT_SCOPE`

2.5 QUAND le token temporaire `2fa_setup_only` est créé ALORS le système DOIT le limiter à une durée de validité courte (15 minutes maximum)

### Comportement Inchangé (Prévention de Régression)

3.1 QUAND un super admin tente de se connecter ET que 2FA est déjà activé sur son compte ALORS le système DOIT CONTINUER À exiger un code TOTP valide dans la requête de connexion

3.2 QUAND un utilisateur non-admin (rôle standard) se connecte sans 2FA ALORS le système DOIT CONTINUER À permettre la connexion sans exiger 2FA

3.3 QUAND un super admin avec 2FA activé tente de désactiver 2FA ALORS le système DOIT CONTINUER À refuser l'opération (les admins ne peuvent pas désactiver 2FA une fois activé)

3.4 QUAND un super admin avec 2FA activé se connecte avec un code TOTP valide ALORS le système DOIT CONTINUER À retourner un token complet avec toutes les permissions

3.5 QUAND un super admin utilise un code de secours pour se connecter ALORS le système DOIT CONTINUER À permettre la connexion ET marquer le code comme utilisé

3.6 QUAND le token de refresh d'un super admin est utilisé ALORS le système DOIT CONTINUER À vérifier que 2FA est activé ET retourner un nouveau token d'accès complet

## Condition du Bug (C(X))

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type LoginRequest
  OUTPUT: boolean
  
  // Identifie les entrées qui déclenchent le bug
  RETURN (X.user.is_superuser = true OR X.user.has_role("super_admin") OR X.user.has_role("admin"))
         AND X.user.totp_enabled = false
         AND X.attempting_login = true
END FUNCTION
```

## Propriété du Correctif (P(result))

```pascal
// Propriété : Vérification du Correctif - Bootstrap 2FA pour Super Admin
FOR ALL X WHERE isBugCondition(X) DO
  result ← login'(X)
  ASSERT result.success = true
         AND result.token_scope = "2fa_setup_only"
         AND result.requires_2fa_setup = true
         AND result.token_lifetime <= 900  // 15 minutes
         AND can_access(result.token, "/2fa/setup/") = true
         AND can_access(result.token, "/2fa/confirm/") = true
         AND (FOR ALL endpoint WHERE endpoint NOT IN ["/2fa/setup/", "/2fa/confirm/"] DO
              can_access(result.token, endpoint) = false)
END FOR
```

## Préservation du Comportement (¬C(X))

```pascal
// Propriété : Vérification de Préservation
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT login(X) = login'(X)
END FOR
```

**Définitions** :
- **login** : Fonction de connexion originale (avant correctif)
- **login'** : Fonction de connexion corrigée (après correctif)
- **C(X)** : Condition de bug identifiant les entrées problématiques
- **¬C(X)** : Entrées qui ne déclenchent PAS le bug (doivent être préservées)

## Contre-exemple Concret

**Scénario de reproduction** :

```bash
# 1. Créer un super admin
$ python manage.py createsuperuser
Email: admin@tenxyte.com
Password: SecurePass123!
Superuser created successfully.

# 2. Tenter de se connecter
$ curl -X POST http://localhost:8000/api/v1/auth/login/email/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@tenxyte.com","password":"SecurePass123!"}'

# ACTUEL : 403 {"error":"2FA setup required","code":"ADMIN_2FA_SETUP_REQUIRED"}
# ATTENDU : 200 {"access_token":"...", "token_scope":"2fa_setup_only", "requires_2fa_setup":true}

# 3. Tenter d'activer 2FA sans token
$ curl -X POST http://localhost:8000/api/v1/auth/2fa/setup/

# ACTUEL : 401 Unauthorized
# ATTENDU : Cette étape ne devrait pas être nécessaire - le token du step 2 devrait fonctionner
```

## Solution Proposée (Vue d'ensemble)

La solution introduit un **flux de bootstrap 2FA** spécifique aux super admins :

1. **Nouvelle portée de token** : `2fa_setup_only` - token temporaire limité aux endpoints 2FA
2. **Modification du login** : Au lieu de rejeter, émettre le token restreint si l'utilisateur est admin sans 2FA
3. **Validation de portée** : Middleware vérifiant que les tokens `2fa_setup_only` ne peuvent accéder qu'à `/2fa/setup/` et `/2fa/confirm/`
4. **Transition automatique** : Après confirmation 2FA réussie, émettre un token complet et invalider le token restreint

Cette approche maintient la sécurité (le token restreint ne peut rien faire d'autre qu'activer 2FA) tout en résolvant le paradoxe de bootstrap.
