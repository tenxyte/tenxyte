# RUNBOOK : Retour arrière (Rollback) du module d'authentification

**Objectif :** Restaurer le service vers une version stable en moins de 15 minutes en cas de déploiement défectueux.

## 1. Préparation (Identification du problème)
- [ ] Observer l'erreur (Échecs consécutifs des tests de santé `/health` en production, pic rapide d'erreurs 5xx sur `/auth/login`).
- [ ] Identifier la dernière version fonctionnelle connue (Hachage du commit).

## 2. Exécution du retour arrière (Kubernetes / Docker)

### Via Kubernetes
```bash
# Identifier l'historique de déploiement
kubectl rollout history deployment/auth-service --namespace=production

# Restaurer la révision précédente (n-1)
kubectl rollout undo deployment/auth-service --namespace=production
```

### Via Docker Compose
```bash
# Modifier le tag de l'image YAML (dans docker-compose.yml) vers la version précédente
docker-compose up -d --build
```

## 3. Vérifications (Post-rollback)
- [ ] Vérifier que les Pods K8s (ou conteneurs Docker) redémarrent et atteignent l'état 'Running'.
- [ ] Appeler manuellement le point de terminaison de test de santé (`curl -sf https://api.example.com/health`).
- [ ] Confirmer l'absence d'erreurs via les logs.
- [ ] Valider avec un test de fumée de connexion basique que l'authentification est revenue à la normale.

## 4. Investigation
- [ ] Extraire les logs ayant conduit au crash (avant nettoyage).
- [ ] Créer un ticket d'incident de priorité haute pour corriger la "nouvelle" version instable.
