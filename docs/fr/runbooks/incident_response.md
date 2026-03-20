# RUNBOOK : Compromission présumée du module d'authentification

**Niveau :** CRITIQUE — RÉPONSE IMMÉDIATE

## 1. Détection et Confinement (T+0)
- [ ] Confirmer l'anomalie via les métriques (Prometheus/Grafana) et les logs JSON structurés.
- [ ] Alerter les membres de l'équipe de sécurité (ex: sur un canal Slack/Teams dédié).
- [ ] Bloquer les adresses IP suspectes au niveau du WAF / Pare-feu.
- [ ] (Optionnel) Basculer l'API d'authentification en mode maintenance (Code 503).

## 2. Évaluation (T+15m)
- [ ] Identifier la source et l'heure du premier événement (Vecteur d'attaque).
- [ ] Identifier les comptes potentiellement compromis, les clés JWT ou les données.
- [ ] Évaluer la nécessité de déclencher un arrêt partiel.

## 3. Remédiation (T+30m)
- [ ] Faire pivoter (rotate) immédiatement tous les secrets compromis (clés privées JWT, base de données).
- [ ] Invalider toutes les sessions utilisateur actives (Effacer les Refresh Tokens JWT).
- [ ] Appliquer un correctif de code si possible.
- [ ] Restaurer à partir de la dernière sauvegarde saine connue si la base de données a été altérée.

## 4. Communication et Résilience (T+2h)
- [ ] Informer les clients impactés (selon la réglementation RGPD, sous 72 heures max).
- [ ] Rédiger et envoyer un rapport de situation à la direction.

## 5. Post-mortem
- [ ] Organiser un Post-Mortem dans les 5 jours ouvrables avec toutes les parties prenantes.
- [ ] Mettre à jour les scripts de détection et ce runbook.
