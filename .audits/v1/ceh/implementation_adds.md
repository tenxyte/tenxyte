# Implémentations Audit CEH (v0.9.1.7)

Les correctifs suivants ont été identifiés et planifiés pour résoudre les vulnérabilités du rapport CEH :

1.  **VULN-001 (Attaque temporelle lors de la connexion) :**
    *   **Action :** Ajout d'un appel factice à `bcrypt.checkpw()` dans `authenticate_by_email` et `authenticate_by_phone` si l'utilisateur n'existe pas, afin d'uniformiser le temps de réponse.

2.  **VULN-002 (Énumération de comptes via `/register/`) :**
    *   **Action :** Modification de `RegisterView.post()` pour ne plus retourner l'erreur "Utilisateur déjà existant". Si l'email ou le téléphone existe déjà, l'API renvoie un succès générique (code 201) factice (sans tokens).

3.  **VULN-003 (Bypass du Rate Limiting via `X-Forwarded-For`) :**
    *   **Action :** Sécurisation de `get_client_ip` dans `decorators.py` et `throttles.py`. Si `TENXYTE_NUM_PROXIES > 0` est configuré mais que la liste `TENXYTE_TRUSTED_PROXIES` est vide, l'adresse du header `X-Forwarded-For` est ignorée (fallback sécurisé sur `REMOTE_ADDR`), avec logging d'un warning.

4.  **VULN-005 (Mass Assignment potentiel sur `/me/`) :**
    *   **Action :** Dans `user_views.py` pour le `PATCH /me/`, si l'email ou le téléphone est modifié, les drapeaux `is_email_verified` et `is_phone_verified` sont automatiquement réinitialisés à `False`. Ajout explicite des champs d'administration à `read_only_fields` dans `UserSerializer`.

5.  **VULN-006 (Déni de Service via bcrypt applicatif) :**
    *   **Action :** Mise en place d'un système de cache en mémoire de 60 secondes pour contourner l'exécution continue de bcrypt pour `X-Access-Secret` dans `ApplicationAuthMiddleware` (`middleware.py`).

6.  **VULN-007 (Attaque par rejeu / Anti-replay sur TOTP) :**
    *   **Action :** Implémentation de la persistance temporaire (cache de 60s) des codes validés dans `totp_service.py` via `totp_used_{user_id}_{code}` ; le rejeu immédiat sera bloqué.

> **Note :** Les correctifs pour VULN-004, VULN-008, VULN-009 et VULN-010 étaient déjà implémentés dans la base de code courante (ex: tokens hashés en SHA-256).
