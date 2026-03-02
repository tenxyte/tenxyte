# RUNBOOK : Déploiement Auth Module

**Durée estimée :** 30 minutes
**Approbateurs requis :** 2 (Tech Lead + Security Officer)

## 1. Pré-déploiement (J-1)
- [ ] Revue du changelog et des breaking changes de l'API (`CHANGELOG.md`).
- [ ] Validation de l'environnement Staging avec zéro incident sur au moins 24h.
- [ ] Notification transmise aux équipes via Slack/Email.
- [ ] Snapshot de la base de données effectif.

## 2. Déploiement (J0)
- [ ] Initiation du déploiement via GitHub Actions (Rolling Deployment).
- [ ] Vérification du statut sur ArgoCD / Kubernetes.
- [ ] Validation des health checks `/health` et `/ready`.
- [ ] Exécution des tests de fumée (Smoke tests) sur les endpoints vitaux (`/auth/login`).

## 3. Post-déploiement
- [ ] Surveillance des pics d'erreur ou d'échecs de login sur Grafana/Datadog (pendant 30 minutes).
- [ ] Revue des logs de l'application (niveau WARNING/ERROR).
- [ ] Notification de succès dans les canaux de communication.
