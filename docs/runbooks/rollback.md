# RUNBOOK : Rollback du module d'authentification

**Objectif :** Restaurer le service dans une version stable en moins de 15 minutes en cas de déploiement cassé.

## 1. Préparation (Identification du problème)
- [ ] Constater l'erreur (Health checks `/health` échouant consécutivement en production, pics rapides d'erreurs 5xx sur `/auth/login`).
- [ ] Identifier la dernière version fonctionnelle connue (Hash du commit récent).

## 2. Exécution du Rollback (Kubernetes / Docker)

### Via Kubernetes
```bash
# Identifier l'historique de déploiement
kubectl rollout history deployment/auth-service --namespace=production

# Restaurer la révision précédente (n-1)
kubectl rollout undo deployment/auth-service --namespace=production
```

### Via Docker Compose
```bash
# Modifier le tag YAML de l'image (dans docker-compose.yml) vers l'ancienne version
docker-compose up -d --build
```

## 3. Vérifications (Post-rollback)
- [ ] Vérifier que les Pods K8s (ou conteneurs Docker) redémarrent et arrivent en statut 'Running'.
- [ ] Appeler le endpoint de health check manuellement (`curl -sf https://api.example.com/health`).
- [ ] Confirmer via les logs l'absence d'erreurs.
- [ ] Valider avec un smoke test de login basique que l'authentification est revenue à la normale.

## 4. Investigations
- [ ] Extraire les logs ayant mené au crash (avant nettoyage).
- [ ] Créer un ticket incident prioritaire pour fixer la "nouvelle" version instable.
