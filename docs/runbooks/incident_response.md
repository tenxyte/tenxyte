# RUNBOOK : Compromission Suspectée du Module Auth

**Niveau :** CRITIQUE — RÉPONSE IMMÉDIATE

## 1. Détection & Confinement (T+0)
- [ ] Confirmer l'anomalie via les métriques (Prometheus/Grafana) et logs JSON structurés.
- [ ] Alerter les membres de l'équipe sécurité (ex. sur un canal dédié Slack/Teams).
- [ ] Bloquer les adresses IP suspectes au niveau WAF / Pare-feu.
- [ ] (Optionnel) Basculer l'API d'authentification en mode maintenance (Code 503).

## 2. Évaluation (T+15m)
- [ ] Identifier la source et l'heure du premier événement (Vecteur d'attaque).
- [ ] Identifier les comptes, clés JWT ou données potentiellement compromises.
- [ ] Évaluer l'opportunité de déclencher un shutdown partiel.

## 3. Remédiation (T+30m)
- [ ] Effectuer une rotation immédiate de tous les secrets compromis (JWT private keys, Database).
- [ ] Invalider la session de l'ensemble des utilisateurs actifs (Clear JWT Refresh Tokens).
- [ ] Appliquer le correctif de code si possible.
- [ ] Effectuer une restauration depuis la dernière sauvegarde saine si la base de données a été altérée.

## 4. Communication & Résilience (T+2h)
- [ ] Informer les clients impactés (dans le cadre de la réglementation RGPD, sous 72h max).
- [ ] Rédiger et envoyer un rapport d'étape à la direction.

## 5. Post-mortem
- [ ] Organiser un Post-Mortem sous 5 jours ouvrés avec toutes les parties prenantes.
- [ ] Mettre à jour les scripts de détection et ce runbook.
