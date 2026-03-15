# Guide des Tâches Périodiques

Tenxyte accumule des enregistrements sensibles au temps (jetons, OTP, journaux d'audit) qui doivent être nettoyés régulièrement pour maintenir la santé de la base de données et se conformer aux politiques de rétention des données. Il comprend également des tâches de surveillance active pour les connexions des agents.

Ce guide décrit toutes les tâches périodiques recommandées et comment les automatiser avec **Cron** ou **Celery Beat**.

---

## Table des Matières

- [1. Nettoyage de la Base de Données (`tenxyte_cleanup`)](#1-nettoyage-de-la-base-de-donnees-tenxyte_cleanup)
  - [Ce qu'il nettoie](#ce-quil-nettoie)
  - [Utilisation et Options](#utilisation-et-options)
  - [Exemples d'Automatisation (Cron et Celery)](#exemples-dautomatisation)
- [2. Surveillance des Battements de Cœur des Agents (Heartbeats)](#2-surveillance-des-battements-de-coeur-des-agents-heartbeats)
  - [Configuration Celery](#configuration-celery)
- [3. Tâches Mensuelles / de Sécurité](#3-taches-mensuelles--de-securite)
  - [Rotation des Clés de Chiffrement](#rotation-des-cles-de-chiffrement-tenxyte_totp_encryption_key)
  - [Analyse de Vulnérabilité des Dépendances](#analyse-de-vulnerabilite-des-dependances)
- [Tableau Récapitulatif](#tableau-recapitulatif)

---

## 1. Nettoyage de la Base de Données (`tenxyte_cleanup`)

Au lieu d'écrire des commandes de gestion ou des tâches personnalisées, Tenxyte fournit une commande intégrée pour gérer tout le nettoyage de la base de données en un seul passage.

### Ce qu'il nettoie

Lorsqu'elle est exécutée, la commande `tenxyte_cleanup` supprime :
1. **Jetons sur Liste Noire** : Jetons expirés de la liste noire JWT.
2. **Liens Magiques (Magic Links)** : Liens de connexion sans mot de passe expirés.
3. **Codes OTP** : Codes de vérification 2FA expirés ou utilisés.
4. **Jetons de Rafraîchissement (Refresh Tokens)** : Jetons de rafraîchissement JWT expirés ou explicitement révoqués.
5. **Tentatives de Connexion** : Anciennes tentatives de connexion (utilisées pour la limitation du débit et le verrouillage).
6. **Journaux d'Audit (Audit Logs)** : Anciens événements d'audit de sécurité (selon la politique).

### Utilisation et Options

```bash
python manage.py tenxyte_cleanup
```

Par défaut, la commande conserve les Tentatives de Connexion pendant **90 jours** et les Journaux d'Audit pendant **365 jours**. Vous pouvez modifier ces durées de rétention :

| Option | Défaut | Description |
|---|---|---|
| `--login-attempts-days` | 90 | Jours avant la suppression de LoginAttempt (0 = conserver indéfiniment) |
| `--audit-log-days` | 365 | Jours avant la suppression d'AuditLog (0 = conserver indéfiniment) |
| `--dry-run` | - | Simule le nettoyage sans rien supprimer |

> **Note de Conformité :** Le RGPD / SOC 2 peut imposer une fenêtre de rétention maximale stricte pour les Journaux d'Audit (ex: 90 jours), mais aussi un minimum. Choisissez une valeur conforme aux deux.

### Exemples d'Automatisation

Vous devriez exécuter cette commande **quotidiennement** (ex: à 3h00 du matin) pour garder la taille de la base de données sous contrôle.

**Alternative Cron :**
```cron
# Exécution quotidienne à 03h00 du matin
0 3 * * * /path/to/venv/bin/python manage.py tenxyte_cleanup
```

**Alternative Celery Beat :**
```python
# myapp/tasks.py
from celery import shared_task
from django.core.management import call_command

@shared_task
def run_tenxyte_cleanup():
    call_command('tenxyte_cleanup')
```

---

## 2. Surveillance des Battements de Cœur des Agents (Heartbeats)

Si vous utilisez le **module AIRS** avec des `AgentTokens` qui nécessitent des battements de cœur réguliers (`heartbeat_required_every`), vous devez exécuter la tâche de surveillance en continu.

Sans cette tâche, un agent pourrait se déconnecter brutalement sans envoyer de signal de suspension, et le jeton resterait indéfiniment Actif.

### Configuration Celery

Tenxyte fournit la tâche `@shared_task` directement. Vous devez la programmer pour qu'elle s'exécute **chaque minute** via Celery Beat :

```python
# settings.py ou celery.py schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Exécution chaque minute pour suspendre les agents manquant de battements de cœur
    'check-agent-heartbeats': {
        'task': 'tenxyte.tasks.agent_tasks.check_agent_heartbeats',
        'schedule': crontab(minute='*'),
    },
    
    # Nettoyage quotidien de la base de données
    'daily-db-cleanup': {
        'task': 'myapp.tasks.run_tenxyte_cleanup',
        'schedule': crontab(hour=3, minute=0),
    },
}
```

Lorsque cette tâche s'exécute, elle trouve tous les objets `AgentToken` avec des battements de cœur manquants et change automatiquement leur statut en `SUSPENDED` (suspendu) avec la raison `HEARTBEAT_MISSING`. Elle enregistre également un avertissement de sécurité.

---

## 3. Tâches Mensuelles / de Sécurité

### Rotation des Clés de Chiffrement (`TENXYTE_TOTP_ENCRYPTION_KEY`)

Si vous utilisez `TENXYTE_TOTP_ENCRYPTION_KEY` pour le chiffrement des secrets TOTP, prévoyez une rotation périodique des clés.
Tenxyte utilisant le standard `cryptography.fernet.Fernet` pour les secrets TOTP, vous aurez besoin d'un script personnalisé pour :

1. Déchiffrer tous les champs `totp_secret` du modèle `User` avec l'ancienne clé.
2. Les re-chiffrer avec la nouvelle clé.
3. Mettre à jour `TENXYTE_TOTP_ENCRYPTION_KEY` dans vos variables d'environnement.

### Analyse de Vulnérabilité des Dépendances

À exécuter en CI ou manuellement chaque mois :

```bash
pip-audit
safety check
bandit -r src/tenxyte/
```

---

## Tableau Récapitulatif

| Tâche | Exécution | Fréquence | Impact |
|---|---|---|---|
| Vérifier Heartbeats Agents | `tenxyte.tasks.agent_tasks.check_agent_heartbeats` | Chaque minute | Suspendre les bots déconnectés |
| Nettoyage Base de Données | `python manage.py tenxyte_cleanup` | Quotidien | Confidentialité des données et taille BD |
| Rotation des clés | Script personnalisé | Mensuel / Annuel | Sécurité |
| Analyse dépendances | `pip-audit` | Mensuel ou CI | Sécurité |
