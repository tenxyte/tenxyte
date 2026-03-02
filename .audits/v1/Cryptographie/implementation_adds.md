# Implémentations Cryptographiques - Résumé

Suite à l'audit cryptographique (v1.0), les modifications suivantes ont été apportées :

## P0 : Troncature silencieuse bcrypt
- **Problème :** bcrypt tronque les mots de passe à 72 octets, permettant potentiellement à un attaquant de s'authentifier s'il connaît les 72 premiers caractères d'un mot de passe long.
- **Solution (implémentée) :** `src/tenxyte/models/auth.py` et `src/tenxyte/models/security.py` pré-hashent désormais chaque `raw_password` via `hashlib.sha256(raw_password).hexdigest()` (génère 64 octets hex) avant de l'envoyer à `bcrypt.hashpw` ou `bcrypt.checkpw`.

## P1 : Fallback JWT Secret Key
- **Problème :** L'application pouvait s'appuyer sur la `SECRET_KEY` de Django pour signer les JWT si `TENXYTE_JWT_SECRET_KEY` n'était pas définie.
- **Solution (implémentée) :** `src/tenxyte/conf/jwt.py` exige désormais de manière stricte la variable d'environnement `TENXYTE_JWT_SECRET_KEY` (lève `ImproperlyConfigured` dans le cas contraire), ce qui découple la sécurité des sessions Django des JWT.

## P1 : Chiffrement du secret TOTP
- **Problème :** Les secrets TOTP étaient stockés en clair (string brute) car la dépendance optionnelle `django-cryptography` n'était pas un pré-requis strict.
- **Solution (implémentée) :** `src/tenxyte/services/totp_service.py` utilise la bibliothèque Python standard `cryptography.fernet.Fernet` alimentée par `TENXYTE_TOTP_ENCRYPTION_KEY`. Tous les secrets sont chiffrés manuellement avant d'être envoyés aux modèles `User` et déchiffrés à la volée en mémoire lors de la validation (`verify_code`).

## P2 : Pratiques de défense
- **Solution (implémentée) :** `hmac.compare_digest` a été ajouté à `src/tenxyte/services/totp_service.py` pour valider les codes de secours 2FA (protection timing-attack).
- **Solution (implémentée) :** L'entropie des codes de secours a été doublée en modifiant l'appel à 64-bits (`secrets.token_hex(8)`).
- **Solution (implémentée) :** Le Timeout HIBP a été réduit de 5 secondes à 3 secondes dans `src/tenxyte/services/breach_check_service.py`.
- **Solution (implémentée) :** `BCRYPT_ROUNDS` a été externalisé dans les paramètres configurables (`src/tenxyte/conf/auth.py`).
