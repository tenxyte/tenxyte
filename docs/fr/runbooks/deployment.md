# RUNBOOK : Déploiement du Module d'Authentification

**Durée estimée :** 30 minutes
**Approbateurs requis :** 2 (Responsable technique + Responsable sécurité)

## 1. Pré-déploiement (J-1)
- [ ] Passer en revue le journal des modifications (changelog) et les ruptures de compatibilité d'API (`CHANGELOG.md`).
- [ ] Valider l'environnement de Pré-production (Staging) avec zéro incident pendant au moins 24h.
- [ ] Envoyer une notification aux équipes via Slack/Email.
- [ ] S'assurer que la sauvegarde (snapshot) de la base de données est terminée.

## 2. Déploiement (J-0)
- [ ] Lancer le déploiement via GitHub Actions (Rolling Deployment).
- [ ] Vérifier le statut sur ArgoCD / Kubernetes.
- [ ] Valider les tests de santé (`/health` et `/ready`).
- [ ] Exécuter des tests de fumée (smoke tests) sur les points de terminaison vitaux (`/auth/login`).

## 3. Post-déploiement
- [ ] Surveiller les pics d'erreurs ou les échecs de connexion sur Grafana/Datadog (pendant 30 minutes).
- [ ] Passer en revue les logs de l'application (niveaux WARNING/ERROR).
- [ ] Informer de la réussite du déploiement dans les canaux de communication.
