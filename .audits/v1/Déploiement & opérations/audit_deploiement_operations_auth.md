# Audit Professionnel — Déploiement & Opérations
## Module d'Authentification

---

| Champ | Détail |
|---|---|
| **Type d'audit** | Déploiement & Opérations |
| **Périmètre** | Module d'Authentification |
| **Date** | Février 2026 |
| **Statut** | Pré-publication |
| **Référentiels** | OWASP ASVS v4.0 · NIST SP 800-63B · ISO/IEC 27001:2022 · CWE Top 25 |
| **Niveau de criticité global** | 🔴 À traiter avant publication |

---

## Table des Matières

1. [Résumé Exécutif](#1-résumé-exécutif)
2. [Méthodologie](#2-méthodologie)
3. [Architecture & Infrastructure de Déploiement](#3-architecture--infrastructure-de-déploiement)
4. [Configuration des Environnements](#4-configuration-des-environnements)
5. [Gestion des Secrets & Credentials](#5-gestion-des-secrets--credentials)
6. [Sécurité Réseau & Exposition](#6-sécurité-réseau--exposition)
7. [Pipeline CI/CD](#7-pipeline-cicd)
8. [Monitoring, Logging & Alerting](#8-monitoring-logging--alerting)
9. [Gestion des Sessions & Tokens](#9-gestion-des-sessions--tokens)
10. [Résilience & Haute Disponibilité](#10-résilience--haute-disponibilité)
11. [Procédures Opérationnelles](#11-procédures-opérationnelles)
12. [Conformité & Réglementation](#12-conformité--réglementation)
13. [Plan de Remédiation Priorisé](#13-plan-de-remédiation-priorisé)
14. [Checklist Pré-Publication](#14-checklist-pré-publication)

---

## 1. Résumé Exécutif

Ce rapport présente les résultats de l'audit de déploiement et d'opérations du module d'authentification avant sa mise en production. L'objectif est d'évaluer la robustesse de l'infrastructure de déploiement, la sécurité opérationnelle, la traçabilité des accès et la capacité de réponse aux incidents.

### Synthèse des Constats

| Sévérité | Nombre | Description |
|---|---|---|
| 🔴 **Critique** | À compléter | Bloquerait une mise en production |
| 🟠 **Élevée** | À compléter | Risque opérationnel important |
| 🟡 **Moyenne** | À compléter | Dégradation potentielle de service |
| 🔵 **Faible** | À compléter | Recommandations de bonne pratique |

> **⚠️ Note :** Les colonnes "Nombre" sont à compléter après exécution des tests. Ce document constitue le référentiel d'évaluation structuré.

---

## 2. Méthodologie

### 2.1 Approche

L'audit suit une approche en quatre phases :

1. **Revue statique** — analyse de la configuration, des IaC (Infrastructure as Code), des Dockerfiles, des fichiers de déploiement et des manifestes Kubernetes/Compose.
2. **Revue dynamique** — vérification des endpoints exposés, comportement des tokens, timeouts, réponses aux erreurs.
3. **Revue opérationnelle** — procédures de déploiement, runbooks, rotation des secrets, gestion des incidents.
4. **Revue de conformité** — alignement avec les standards réglementaires applicables.

### 2.2 Périmètre de l'Audit

| Composant | Inclus | Notes |
|---|---|---|
| Service d'authentification (API) | ✅ | Endpoints login, logout, refresh, register |
| Base de données des identités | ✅ | Stockage credentials, politique de mots de passe |
| Gestionnaire de tokens (JWT/OAuth) | ✅ | Signature, expiration, révocation |
| Infrastructure de déploiement | ✅ | Docker, K8s, VM, Cloud |
| Pipeline CI/CD | ✅ | Build, test, scan, déploiement |
| Monitoring & Logs | ✅ | Observabilité, alertes |
| Procédures de runbook | ✅ | Rotation secrets, incident, rollback |

---

## 3. Architecture & Infrastructure de Déploiement

### 3.1 Analyse de l'Architecture Cible

#### ✅ Points à Vérifier

- [ ] **Isolation du service** — Le module d'authentification est-il isolé dans son propre conteneur/service distinct des autres modules applicatifs ?
- [ ] **Principe du moindre privilège** — Le service s'exécute-t-il avec un utilisateur non-root ?
- [ ] **Séparation des environnements** — Les environnements dev / staging / production sont-ils strictement séparés (réseaux, bases de données, secrets) ?
- [ ] **Suppression des surfaces d'attaque** — Les ports inutiles sont-ils fermés ? Le mode debug est-il désactivé en production ?

#### 🔴 Contrôle Critique : Exécution Non-Root

```dockerfile
# ❌ MAUVAISE PRATIQUE — À ne jamais utiliser
FROM node:18
RUN npm install
CMD ["node", "server.js"]
# Le processus s'exécute en tant que root

# ✅ BONNE PRATIQUE
FROM node:18-alpine
WORKDIR /app
COPY --chown=node:node . .
RUN npm ci --only=production
USER node
CMD ["node", "server.js"]
```

**Vérification :** `docker inspect <container> | grep -i user`

#### 🟠 Contrôle Élevé : Surface d'Attaque Réseau

```yaml
# ✅ Exemple de configuration réseau sécurisée (docker-compose)
services:
  auth-service:
    networks:
      - internal_net
    # Pas d'exposition directe sur le port hôte
    expose:
      - "3000"
  
  nginx-gateway:
    ports:
      - "443:443"
    networks:
      - internal_net
      - external_net

networks:
  internal_net:
    internal: true
  external_net:
```

### 3.2 Matrice de Flux Réseau

| Source | Destination | Port | Protocole | Justification |
|---|---|---|---|---|
| Client externe | API Gateway / Reverse Proxy | 443 | HTTPS/TLS 1.3 | ✅ Seul point d'entrée |
| API Gateway | Auth Service | 3000 | HTTP (interne) | ✅ Réseau privé uniquement |
| Auth Service | Base de données | 5432 | PostgreSQL/TLS | ✅ Chiffré en transit |
| Auth Service | Cache (Redis) | 6379 | Redis/TLS | ✅ Sessions & blacklist tokens |
| Auth Service | SMTP/Email | 587 | STARTTLS | ✅ Notifications MFA |

> **🔴 Alerte :** Tout flux direct `client → auth-service` sans proxy est une vulnérabilité critique.

---

## 4. Configuration des Environnements

### 4.1 Variables d'Environnement

#### 🔴 Contrôle Critique : Aucun Secret en Dur

```bash
# ❌ INTERDIT — Secrets dans le code ou les Dockerfiles
ENV JWT_SECRET="mysupersecret123"
ENV DB_PASSWORD="admin"

# ✅ REQUIS — Injection par variables d'environnement ou vault
ENV JWT_SECRET="" # Injecté au runtime via secrets manager
```

**Checklist de contrôle :**

- [ ] Aucun fichier `.env` contenant des secrets n'est commité dans le dépôt Git
- [ ] Le fichier `.gitignore` exclut explicitement `.env`, `*.key`, `*.pem`, `config/secrets.*`
- [ ] Les variables sensibles sont injectées depuis un gestionnaire de secrets (Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault)
- [ ] Un scan de secrets est intégré au pipeline CI/CD (ex : `git-secrets`, `truffleHog`, `gitleaks`)

#### 4.2 Durcissement de Configuration par Environnement

| Paramètre | Développement | Staging | Production |
|---|---|---|---|
| `DEBUG` | `true` | `false` | `false` |
| `LOG_LEVEL` | `debug` | `info` | `warn` / `error` |
| `CORS_ORIGIN` | `*` | URL staging | URL(s) production strictes |
| `RATE_LIMITING` | Désactivé | Activé (souple) | Activé (strict) |
| `MFA` | Optionnel | Obligatoire | Obligatoire |
| `JWT_EXPIRY` | 24h | 15min | 15min |
| `HTTPS_ONLY` | Non | Oui | Oui |
| `SECURE_COOKIES` | Non | Oui | Oui |

---

## 5. Gestion des Secrets & Credentials

### 5.1 Inventaire des Secrets du Module

| Secret | Type | Rotation Recommandée | Stockage Recommandé |
|---|---|---|---|
| `JWT_SECRET` / Clé privée RSA | Clé de signature | 90 jours | Secret Manager + HSM idéalement |
| `REFRESH_TOKEN_SECRET` | Clé de signature | 90 jours | Secret Manager |
| `DB_PASSWORD` | Credential BDD | 30 jours | Secret Manager |
| `SMTP_PASSWORD` | Credential email | 60 jours | Secret Manager |
| `MFA_TOTP_ISSUER_KEY` | Clé TOTP | 180 jours | HSM / Secret Manager |
| `OAUTH_CLIENT_SECRET` | OAuth 2.0 | 60 jours | Secret Manager |
| Certificats TLS/SSL | PKI | 90 jours (Let's Encrypt) | Cert Manager |

### 5.2 Procédure de Rotation des Secrets

```mermaid
flowchart TD
    A[Déclenchement rotation\n(manuelle ou automatique)] --> B[Génération nouveau secret]
    B --> C[Déploiement en mode\ndouble-secret actif]
    C --> D[Validation tokens existants\navec ancien ET nouveau secret]
    D --> E[Migration progressive\n(rolling update)]
    E --> F[Désactivation ancien secret]
    F --> G[Audit log de la rotation]
    G --> H[Notification équipe sécurité]
```

#### 🔴 Contrôle Critique : Rotation Sans Interruption de Service

La rotation d'une clé JWT **doit** être effectuée sans invalider les tokens actifs des utilisateurs connectés. La stratégie recommandée est le **JWKS (JSON Web Key Set)** avec support multi-clés :

```json
{
  "keys": [
    { "kid": "key-2026-02", "use": "sig", "alg": "RS256", ... },
    { "kid": "key-2026-01", "use": "sig", "alg": "RS256", ... }
  ]
}
```

### 5.3 Contrôles de Sécurité des Mots de Passe Stockés

- [ ] Algorithme de hachage : **bcrypt** (coût ≥ 12), **Argon2id** (recommandé NIST 2024), ou **scrypt**
- [ ] Aucun stockage en clair, aucun MD5/SHA1/SHA256 seul
- [ ] Sel unique par utilisateur généré aléatoirement
- [ ] Politique de complexité : minimum 12 caractères, vérification contre liste de mots de passe courants (HaveIBeenPwned API)

---

## 6. Sécurité Réseau & Exposition

### 6.1 Configuration TLS

#### 🔴 Contrôle Critique : Protocoles & Ciphers

```nginx
# ✅ Configuration NGINX recommandée
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;

# Headers de sécurité obligatoires
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'none'; frame-ancestors 'none';" always;
```

**Vérification :** `testssl.sh <domain>` ou `ssllabs.com/ssltest/`

### 6.2 Rate Limiting & Protection Brute Force

| Endpoint | Limite Recommandée | Fenêtre | Action |
|---|---|---|---|
| `POST /auth/login` | 5 tentatives | 15 minutes par IP | Blocage IP + alerte |
| `POST /auth/register` | 3 créations | 1 heure par IP | Blocage temporaire |
| `POST /auth/forgot-password` | 3 demandes | 1 heure | Rate limit silencieux |
| `POST /auth/refresh` | 10 appels | 1 minute | 429 Too Many Requests |
| `POST /auth/verify-mfa` | 5 tentatives | 10 minutes | Verrouillage compte |

```javascript
// ✅ Exemple avec express-rate-limit
const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5,
  skipSuccessfulRequests: true,
  keyGenerator: (req) => req.ip + ':' + req.body?.email,
  handler: (req, res) => {
    // Log security event
    logger.security('brute_force_detected', { ip: req.ip, email: req.body?.email });
    res.status(429).json({ error: 'Too many attempts, try again later.' });
  }
});
```

### 6.3 CORS Policy

- [ ] `Access-Control-Allow-Origin` ne doit **jamais** être `*` en production
- [ ] Liste blanche explicite des origines autorisées
- [ ] `credentials: true` uniquement si strictement nécessaire
- [ ] Méthodes HTTP limitées aux besoins réels

---

## 7. Pipeline CI/CD

### 7.1 Exigences du Pipeline

```yaml
# ✅ Pipeline de sécurité recommandé (GitHub Actions exemple)
stages:
  - lint_and_test:
      - Linting & formatage
      - Tests unitaires (couverture ≥ 80%)
      - Tests d'intégration authentification

  - security_scan:
      - SAST (analyse statique) : Semgrep, SonarQube, CodeQL
      - Scan des dépendances : npm audit / Snyk / Dependabot
      - Scan de secrets : gitleaks, truffleHog
      - Scan image Docker : Trivy, Grype

  - build:
      - Build image Docker (reproducible)
      - Signature de l'image (cosign / Notary)
      - Push vers registry privé

  - staging_deploy:
      - Déploiement automatique en staging
      - Tests de smoke (endpoints critiques)
      - Tests de performance (k6, Gatling)

  - production_deploy:
      - Approbation manuelle obligatoire (2 approbateurs minimum)
      - Déploiement rolling / blue-green
      - Health checks automatiques post-déploiement
      - Rollback automatique si health check échoue
```

### 7.2 Contrôles de Qualité Pré-Déploiement

| Contrôle | Outil Recommandé | Seuil d'Échec | Bloquant |
|---|---|---|---|
| Tests unitaires | Jest / Mocha | Couverture < 80% | ✅ Oui |
| SAST | Semgrep / SonarQube | Sévérité HIGH | ✅ Oui |
| Scan dépendances | npm audit / Snyk | CVE Critical | ✅ Oui |
| Scan secrets | gitleaks | Toute détection | ✅ Oui |
| Scan image Docker | Trivy | CVE Critical | ✅ Oui |
| Tests de charge | k6 | p95 > 500ms | 🟡 Recommandé |
| Lint sécurité | ESLint-security | Toute détection | ✅ Oui |

### 7.3 Gestion des Images Docker

- [ ] Images basées sur des distributions minimales (Alpine, Distroless)
- [ ] Multi-stage builds pour éliminer les outils de build en production
- [ ] Aucun secret dans les layers Docker (vérifier avec `docker history`)
- [ ] Images taggées avec SHA256 immuable (pas de `latest` en production)
- [ ] Registry privé avec contrôle d'accès (AWS ECR, GCR, ACR, Harbor)
- [ ] Politique de rétention des images (supprimer les images > 90 jours)

---

## 8. Monitoring, Logging & Alerting

### 8.1 Événements à Journaliser Obligatoirement

| Événement | Niveau | Données à Logger | Retention |
|---|---|---|---|
| Connexion réussie | INFO | userId, IP, user-agent, timestamp | 90 jours |
| Échec de connexion | WARN | IP, email (haché), tentatives, timestamp | 1 an |
| Blocage brute-force | SECURITY | IP, cible, nb tentatives, durée blocage | 1 an |
| Déconnexion | INFO | userId, sessionId, timestamp | 90 jours |
| Création de compte | INFO | userId, IP, méthode, timestamp | 1 an |
| Changement de mot de passe | SECURITY | userId, IP, source (user/admin/reset), timestamp | 2 ans |
| Réinitialisation mot de passe | SECURITY | userId, IP, token_hash, timestamp | 1 an |
| Connexion MFA réussie/échouée | SECURITY | userId, méthode MFA, IP, timestamp | 1 an |
| Invalidation/Révocation token | SECURITY | tokenId, userId, raison, timestamp | 1 an |
| Rotation de secrets | SECURITY | keyId, opérateur, timestamp | 5 ans |
| Tentative accès avec token révoqué | SECURITY | tokenId (haché), IP, timestamp | 2 ans |

#### 🔴 Contrôle Critique : Format de Log Structuré

```json
{
  "timestamp": "2026-02-28T14:32:01.123Z",
  "level": "SECURITY",
  "event": "LOGIN_FAILURE",
  "requestId": "req_7f3a9b2c",
  "ip": "203.0.113.42",
  "userAgent": "Mozilla/5.0...",
  "email": "sha256:8d9e0f...",
  "attempts": 3,
  "service": "auth-module",
  "version": "1.2.3",
  "environment": "production"
}
```

> **⚠️ JAMAIS logger :** mots de passe en clair, tokens JWT complets, numéros de carte, données personnelles non masquées.

### 8.2 Alertes Critiques à Configurer

| Alerte | Seuil | Canal | Priorité |
|---|---|---|---|
| Taux d'échec login > 20% sur 5min | > 20% | PagerDuty / Slack #security | 🔴 P1 |
| Brute-force depuis nouvelle IP | > 10 tentatives | Slack #security | 🟠 P2 |
| Service auth DOWN | 2 health checks consécutifs | PagerDuty | 🔴 P1 |
| Latence p95 > 1s | Sur 5 minutes | Slack #ops | 🟠 P2 |
| Certificat TLS expire dans < 14 jours | — | Email + Slack | 🟠 P2 |
| Déploiement en production | Tout déploiement | Slack #deployments | 🔵 Info |
| Erreur de rotation secret | Toute erreur | PagerDuty | 🔴 P1 |
| Pic inhabituels de créations de comptes | > 3x baseline | Slack #security | 🟠 P2 |

### 8.3 Métriques Clés à Exposer (via `/metrics` ou Prometheus)

```
# Métriques d'authentification
auth_login_attempts_total{status="success|failure", method="password|oauth|mfa"}
auth_token_issued_total{type="access|refresh"}
auth_token_revoked_total{reason="logout|expired|admin|suspicious"}
auth_active_sessions_gauge
auth_blocked_ips_gauge
auth_mfa_challenges_total{method="totp|sms|email", status="success|failure"}

# Métriques de performance
auth_request_duration_seconds{endpoint, method, status_code}
auth_db_query_duration_seconds{operation}
```

---

## 9. Gestion des Sessions & Tokens

### 9.1 Configuration JWT

| Paramètre | Valeur Recommandée | Anti-pattern à Éviter |
|---|---|---|
| Algorithme | `RS256` ou `ES256` | ❌ `HS256` en multi-service / `none` interdit |
| Access Token TTL | 15 minutes | ❌ > 1 heure |
| Refresh Token TTL | 7 jours (rotation) | ❌ Non renouvelé, TTL illimité |
| `iss` (Issuer) | URL de votre service | ❌ Absent |
| `aud` (Audience) | Service(s) consommateur(s) | ❌ Absent |
| `jti` (JWT ID) | UUID v4 unique | ❌ Absent (nécessaire pour révocation) |
| Stockage côté client | `httpOnly` + `Secure` cookie **ou** mémoire JS | ❌ `localStorage` |

### 9.2 Stratégie de Révocation

- [ ] **Blacklist en Redis** pour les tokens révoqués avant expiration
- [ ] Nettoyage automatique des entrées expirées (TTL Redis = durée de vie du token)
- [ ] Support de la révocation de **toutes les sessions** d'un utilisateur (rotation `userId secret`)
- [ ] Endpoint `POST /auth/logout` invalide immédiatement le refresh token

### 9.3 Refresh Token Rotation

```
[Access Token expiré]
       │
       ▼
POST /auth/refresh
  + Refresh Token A
       │
       ▼
┌─────────────────────────┐
│  Vérifier RT-A en BDD   │
│  RT-A non révoqué ?     │
└─────────┬───────────────┘
          │ Oui
          ▼
 Émettre Access Token B'
 Émettre Refresh Token B
 Révoquer Refresh Token A
          │
          ▼
   [Si RT-A réutilisé]
    → Invalider TOUTE
      la famille de tokens
    → Alerte sécurité
```

---

## 10. Résilience & Haute Disponibilité

### 10.1 Configuration de Résilience

| Mécanisme | Recommandation | Criticité |
|---|---|---|
| Health checks | `GET /health` et `GET /ready` distincts | 🔴 Obligatoire |
| Replicas minimum | ≥ 2 instances en production | 🔴 Obligatoire |
| Circuit breaker | Sur les appels BDD et Redis | 🟠 Élevée |
| Retry avec backoff | Connexions BDD (max 3 tentatives) | 🟠 Élevée |
| Graceful shutdown | Drain des connexions actives | 🟡 Moyenne |
| Timeout global | 5s maximum par requête d'auth | 🟠 Élevée |
| Connection pool BDD | Min: 5, Max: 20 connexions | 🟡 Moyenne |

### 10.2 Endpoints de Santé Obligatoires

```javascript
// ✅ Health check complet
GET /health
{
  "status": "healthy",
  "version": "1.2.3",
  "uptime": 3600,
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "secretsManager": "healthy"
  }
}

// ✅ Readiness (pour K8s)
GET /ready
→ 200 si prêt à recevoir du trafic
→ 503 si en cours de démarrage ou de shutdown
```

### 10.3 Stratégie de Backup & Recovery

| Donnée | Fréquence Backup | RTO | RPO | Chiffrement |
|---|---|---|---|---|
| Base utilisateurs | Toutes les 6h | 4h | 6h | ✅ AES-256 |
| Sessions Redis | Pas de backup (éphémère) | 0 (sans état) | N/A | ✅ TLS |
| Configuration | Versionnée dans Git | 30min | 0 | ✅ Secrets chiffrés |
| Clés JWT | Backed up + HSM | 2h | 0 | ✅ HSM |

---

## 11. Procédures Opérationnelles

### 11.1 Runbook : Déploiement en Production

```markdown
## RUNBOOK : Déploiement Auth Module
Durée estimée : 30 minutes
Approbateurs requis : 2 (Tech Lead + Security Officer)

### Pré-déploiement (J-1)
- [ ] Revue du changelog et des breaking changes
- [ ] Validation staging ≥ 24h sans incidents
- [ ] Notification aux équipes (email + Slack)
- [ ] Vérification du plan de rollback
- [ ] Snapshot base de données

### Déploiement (J0)
- [ ] Ouvrir une fenêtre de maintenance si nécessaire
- [ ] Lancer le déploiement rolling via pipeline CI/CD
- [ ] Surveiller les métriques en temps réel (Grafana)
- [ ] Vérifier les health checks post-déploiement
- [ ] Exécuter la smoke test suite (5 minutes)
- [ ] Confirmer succès → fermer la fenêtre de maintenance

### Post-déploiement
- [ ] Surveiller les métriques 30 minutes post-déploiement
- [ ] Vérifier les logs pour erreurs inattendues
- [ ] Confirmer aux équipes concernées
- [ ] Mettre à jour la documentation
```

### 11.2 Runbook : Incident de Sécurité

```markdown
## RUNBOOK : Compromission Suspectée du Module Auth
Niveau : CRITIQUE — RÉPONSE IMMÉDIATE

### T+0 : Détection & Confinement
- [ ] Confirmer la compromission (logs, métriques)
- [ ] Alerter l'équipe sécurité via canal dédié
- [ ] Si compromission confirmée : BLOQUER les IPs suspectes
- [ ] Activer le mode maintenance si nécessaire

### T+15min : Évaluation
- [ ] Identifier le vecteur d'attaque
- [ ] Évaluer le périmètre impacté (nb comptes, données)
- [ ] Décision : confinement partiel ou shutdown total

### T+30min : Remédiation
- [ ] Rotation IMMÉDIATE de tous les secrets JWT
- [ ] Invalidation de TOUTES les sessions actives
- [ ] Déploiement du patch si disponible
- [ ] Restoration depuis backup si nécessaire

### T+2h : Communication
- [ ] Notification aux utilisateurs impactés (RGPD : 72h max)
- [ ] Rapport préliminaire à la direction
- [ ] Notification CNIL si données personnelles compromises

### Post-incident
- [ ] Post-mortem dans les 5 jours ouvrés
- [ ] Mise à jour des runbooks
- [ ] Amélioration des détections
```

### 11.3 Runbook : Rollback

```bash
#!/bin/bash
# RUNBOOK : Rollback du module d'authentification

# 1. Identifier la dernière version stable
PREVIOUS_VERSION=$(kubectl rollout history deployment/auth-service \
  --namespace=production | tail -2 | head -1 | awk '{print $1}')

# 2. Exécuter le rollback
kubectl rollout undo deployment/auth-service \
  --namespace=production \
  --to-revision=$PREVIOUS_VERSION

# 3. Vérifier le succès
kubectl rollout status deployment/auth-service \
  --namespace=production \
  --timeout=120s

# 4. Valider les health checks
curl -sf https://api.example.com/health || \
  echo "ALERTE: Health check échoué post-rollback"
```

---

## 12. Conformité & Réglementation

### 12.1 RGPD / GDPR

| Exigence | Statut | Notes |
|---|---|---|
| Minimisation des données | À vérifier | Collecter uniquement les données nécessaires à l'auth |
| Droit à l'effacement | À implémenter | Endpoint `DELETE /auth/account` avec purge complète |
| Portabilité des données | À vérifier | Export des données d'authentification possibles |
| Chiffrement des données au repos | À vérifier | BDD chiffrée, logs anonymisés |
| DPO notifié | À confirmer | Documentation du traitement |
| Registre des traitements | À compléter | Module auth = traitement à risque élevé |
| Notification de violation < 72h | Procédure | Runbook incident doit intégrer ce délai |

### 12.2 OWASP ASVS — Contrôles d'Authentification

| Contrôle ASVS | Niveau | Description | Statut |
|---|---|---|---|
| 2.1.1 | L1 | Mots de passe ≥ 12 caractères | ☐ À vérifier |
| 2.1.7 | L1 | Vérification contre listes de passe compromis | ☐ À vérifier |
| 2.1.12 | L1 | Indicateur de force du mot de passe | ☐ À vérifier |
| 2.2.1 | L1 | Anti-automation (rate limiting) | ☐ À vérifier |
| 2.3.1 | L1 | Mots de passe générés ≥ 6 chars, aléatoires | ☐ À vérifier |
| 2.5.2 | L1 | Réinitialisation sans indice sur l'existence du compte | ☐ À vérifier |
| 2.6.1 | L2 | Tokens de récupération à usage unique | ☐ À vérifier |
| 2.8.4 | L2 | MFA résistant au phishing (TOTP/FIDO2) | ☐ À vérifier |
| 3.2.1 | L1 | Nouveau token de session post-authentification | ☐ À vérifier |
| 3.3.1 | L1 | Déconnexion invalide la session côté serveur | ☐ À vérifier |

### 12.3 NIST SP 800-63B — Niveaux d'Assurance

| AAL (Authentication Assurance Level) | Exigences | Recommandation |
|---|---|---|
| **AAL1** (faible) | Single-factor, mémorized secret | Applications peu sensibles |
| **AAL2** (moyen) | MFA obligatoire, résistance phishing | **Recommandé pour la majorité** |
| **AAL3** (élevé) | Authenticateur hardware, FIDO2/WebAuthn | Applications critiques, accès admin |

---

## 13. Plan de Remédiation Priorisé

### 🔴 Priorité 1 — Bloquant (À corriger avant publication)

| ID | Constat | Action | Responsable | Délai |
|---|---|---|---|---|
| REM-001 | Aucun secret ne doit être dans les images Docker ou le code source | Audit complet + migration vers Secret Manager | Dev / DevSecOps | Immédiat |
| REM-002 | Rate limiting absent ou insuffisant sur les endpoints critiques | Implémenter rate limiting par IP + par compte | Dev | Immédiat |
| REM-003 | Logs sans format structuré ou avec données sensibles | Refactoring du système de logging | Dev | Immédiat |
| REM-004 | Absence de révocation des tokens (blacklist) | Implémenter Redis blacklist + jti | Dev | Immédiat |
| REM-005 | Exécution Docker en tant que root | Modifier Dockerfile + user non-root | DevOps | Immédiat |

### 🟠 Priorité 2 — Élevée (Dans les 7 jours)

| ID | Constat | Action | Responsable | Délai |
|---|---|---|---|---|
| REM-006 | Absence d'alertes sécurité sur événements critiques | Configurer alertes Grafana/PagerDuty | DevOps | J+7 |
| REM-007 | Pipeline CI/CD sans scan SAST ni scan de secrets | Intégrer Semgrep + gitleaks | DevSecOps | J+7 |
| REM-008 | Absence de runbooks opérationnels documentés | Rédiger runbooks (déploiement, incident, rollback) | Tech Lead | J+7 |
| REM-009 | TLS < 1.2 ou ciphers faibles possibles | Audit config TLS + durcissement | DevOps | J+7 |

### 🟡 Priorité 3 — Moyenne (Dans les 30 jours)

| ID | Constat | Action | Responsable | Délai |
|---|---|---|---|---|
| REM-010 | Absence de MFA pour les comptes administrateurs | Implémenter TOTP obligatoire pour admins | Dev | J+30 |
| REM-011 | Politique de rotation des secrets non définie | Documenter et automatiser la rotation | DevSecOps | J+30 |
| REM-012 | Backup de la base utilisateurs non chiffré | Implémenter chiffrement AES-256 des backups | DevOps | J+30 |
| REM-013 | Absence de tests de charge | Créer suite k6 et l'intégrer au pipeline | QA / Dev | J+30 |

---

## 14. Checklist Pré-Publication

### 🔐 Sécurité

- [ ] Aucun secret en dur dans le code, la configuration ou les images Docker
- [ ] Tous les endpoints sont protégés par HTTPS (TLS 1.2+ minimum, TLS 1.3 recommandé)
- [ ] Rate limiting activé sur tous les endpoints d'authentification
- [ ] Révocation des tokens implémentée (blacklist Redis)
- [ ] Hachage des mots de passe avec Argon2id ou bcrypt (coût ≥ 12)
- [ ] Logs sécurisés sans données sensibles en clair
- [ ] Headers de sécurité HTTP configurés (HSTS, CSP, X-Frame-Options, etc.)
- [ ] CORS policy restrictive (aucun `*` en production)
- [ ] Protection CSRF si cookies utilisés
- [ ] Scan de sécurité du code (SAST) sans vulnérabilités critiques
- [ ] Scan des dépendances sans CVE critiques

### 🏗️ Infrastructure

- [ ] Service d'authentification isolé dans son propre conteneur / service
- [ ] Conteneur exécuté en utilisateur non-root
- [ ] Variables d'environnement injectées depuis un Secret Manager
- [ ] Environnements dev / staging / prod strictement séparés
- [ ] Images Docker signées et stockées dans un registry privé
- [ ] Minimum 2 replicas configurés en production
- [ ] Health checks `/health` et `/ready` opérationnels

### 🔄 CI/CD

- [ ] Pipeline de build automatisé et reproductible
- [ ] Scan SAST intégré et bloquant
- [ ] Scan de secrets intégré et bloquant
- [ ] Scan d'images Docker intégré
- [ ] Tests unitaires avec couverture ≥ 80%
- [ ] Approbation manuelle obligatoire avant déploiement en production
- [ ] Rollback automatique en cas d'échec des health checks post-déploiement

### 📊 Observabilité

- [ ] Logging structuré (JSON) activé en production
- [ ] Métriques Prometheus exposées
- [ ] Dashboard de monitoring configuré (Grafana ou équivalent)
- [ ] Alertes critiques configurées et testées
- [ ] Rétention des logs conforme aux obligations légales

### 📋 Documentation & Opérations

- [ ] Runbook de déploiement documenté et validé
- [ ] Runbook d'incident de sécurité documenté
- [ ] Procédure de rollback documentée et testée
- [ ] Procédure de rotation des secrets documentée
- [ ] Documentation API à jour (Swagger / OpenAPI)
- [ ] Registre RGPD mis à jour
- [ ] Équipe formée aux procédures opérationnelles

### ✅ Validation Finale

- [ ] Tests de charge validés en staging (p95 < 500ms)
- [ ] Tests de sécurité (DAST) passés en staging
- [ ] Smoke tests post-déploiement staging réussis
- [ ] Validation par le Security Officer
- [ ] Validation par le Tech Lead
- [ ] Date de déploiement communiquée aux équipes concernées

---

## Annexes

### Annexe A — Références Normatives

| Référentiel | Description | URL |
|---|---|---|
| OWASP ASVS 4.0 | Application Security Verification Standard | [owasp.org](https://owasp.org/www-project-application-security-verification-standard/) |
| NIST SP 800-63B | Digital Identity Guidelines | [pages.nist.gov](https://pages.nist.gov/800-63-3/sp800-63b.html) |
| ISO/IEC 27001:2022 | Système de Management de la Sécurité | ISO Store |
| OWASP Top 10 | Risques de sécurité web les plus critiques | [owasp.org](https://owasp.org/www-project-top-ten/) |
| CWE Top 25 | Faiblesses logicielles les plus dangereuses | [cwe.mitre.org](https://cwe.mitre.org/top25/) |
| RGPD (GDPR) | Règlement général sur la protection des données | [cnil.fr](https://www.cnil.fr) |

### Annexe B — Outils de Sécurité Recommandés

| Catégorie | Outil | Usage |
|---|---|---|
| SAST | Semgrep, SonarQube, CodeQL | Analyse statique du code |
| Scan secrets | gitleaks, truffleHog | Détection de secrets dans Git |
| Scan dépendances | Snyk, npm audit, Dependabot | CVE dans les librairies |
| Scan Docker | Trivy, Grype | Vulnérabilités dans les images |
| TLS Audit | testssl.sh, SSLLabs | Vérification de la config TLS |
| DAST | OWASP ZAP, Burp Suite | Tests dynamiques en staging |
| Charge | k6, Gatling | Tests de performance |
| Secrets Manager | HashiCorp Vault, AWS SM, GCP SM | Gestion des secrets |
| Monitoring | Prometheus + Grafana, Datadog | Observabilité |

---

*Document généré le 28 Février 2026 — Audit Déploiement & Opérations — Module d'Authentification*
*Ce document doit être révisé à chaque modification majeure du module ou de l'infrastructure.*
