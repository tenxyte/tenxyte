# Audit Conformité & Privacy
## Tenxyte — Package d'Authentification Python/Django
### Version auditée : `0.9.1.7` · Date : 2026-02-28 · Confidentialité : Diffusion restreinte

---

> **Périmètre de l'audit** : Conformité réglementaire (RGPD/GDPR, CCPA, NIST SP 800-63B, OWASP ASVS), protection des données personnelles, Privacy by Design, droits des personnes concernées, gestion des tiers, politique de rétention, analyse des risques privacy.
>
> **Méthodologie** : Analyse documentaire du brief technique, cartographie des flux de données personnelles, revue des mécanismes de conformité implémentés, évaluation par rapport aux référentiels RGPD Arts. 5–25, NIST SP 800-63B, OWASP ASVS L2, CCPA §1798.
>
> **Positionnement juridique** : Tenxyte est une **bibliothèque open-source** (MIT), non un service déployé. Son éditeur fournit des mécanismes techniques de conformité. La **responsabilité du traitement** (RGPD Art. 4.7) incombe exclusivement aux **intégrateurs** qui déploient Tenxyte dans leurs applications. Cet audit distingue rigoureusement ce que le package **permet** de faire de ce que les intégrateurs **doivent** faire.

---

## Tableau de bord exécutif

| Domaine | Statut | Niveau de risque |
|---------|--------|-----------------|
| Droit à l'effacement (Art. 17) | ✅ Implémenté avec workflow 5 états | 🟢 Faible |
| Droit à la portabilité (Art. 20) | ⚠️ Partiellement implémenté | 🟡 Moyen |
| Droit d'accès (Art. 15) | ⚠️ Partiellement implémenté | 🟡 Moyen |
| Privacy by Design (Art. 25) | ✅ Mesures substantielles en place | 🟢 Faible |
| Minimisation des données | ✅ Bonne pratique respectée | 🟢 Faible |
| Secrets sensibles en clair (DB) | ❌ `totp_secret`, refresh/agent tokens non chiffrés | 🔴 Critique |
| Politique de rétention des logs | ❌ Aucune suppression automatique | 🔴 Critique |
| Fusion OAuth sans confirmation | ⚠️ Risque d'account takeover | 🟠 Élevé |
| Tiers sous-traitants (DPA) | ⚠️ Non adressé par le package | 🟠 Élevé |
| Export RGPD incomplet | ⚠️ Manques substantiels | 🟡 Moyen |
| Droits Art. 18 & 21 | ❌ Non implémentés | 🟡 Moyen |
| Révocation des tokens à la suppression | ⚠️ Insuffisance partielle | 🟡 Moyen |
| Traçabilité AIRS / Prompt trace ID | ⚠️ Risque de croisement PII | 🟡 Moyen |
| NIST SP 800-63B | ✅ Largement conforme | 🟢 Faible |
| CCPA | ⚠️ Couverture indirecte | 🟡 Moyen |

---

## Sommaire

1. [Positionnement réglementaire et responsabilités](#1-positionnement-réglementaire-et-responsabilités)
2. [Cartographie des données personnelles](#2-cartographie-des-données-personnelles)
3. [Bases légales du traitement — RGPD Art. 6](#3-bases-légales-du-traitement--rgpd-art-6)
4. [Analyse des droits des personnes concernées](#4-analyse-des-droits-des-personnes-concernées)
5. [Privacy by Design — RGPD Art. 25](#5-privacy-by-design--rgpd-art-25)
6. [Protection des données sensibles au repos](#6-protection-des-données-sensibles-au-repos)
7. [Politique de rétention des données](#7-politique-de-rétention-des-données)
8. [Sous-traitants tiers et transferts internationaux](#8-sous-traitants-tiers-et-transferts-internationaux)
9. [Authentification OAuth — Risques privacy spécifiques](#9-authentification-oauth--risques-privacy-spécifiques)
10. [Module AIRS — Agents IA et protection des données](#10-module-airs--agents-ia-et-protection-des-données)
11. [Audit Logging — Conformité et traçabilité](#11-audit-logging--conformité-et-traçabilité)
12. [Analyse de conformité JWT — Minimisation des données](#12-analyse-de-conformité-jwt--minimisation-des-données)
13. [Droit à l'effacement — Invalidation des sessions actives](#13-droit-à-leffacement--invalidation-des-sessions-actives)
14. [Conformité NIST SP 800-63B](#14-conformité-nist-sp-800-63b)
15. [Conformité CCPA](#15-conformité-ccpa)
16. [Conformité SOC 2 Type II](#16-conformité-soc-2-type-ii)
17. [Matrice des risques privacy](#17-matrice-des-risques-privacy)
18. [Plan de remédiation priorisé](#18-plan-de-remédiation-priorisé)
19. [Checklist de conformité — Responsabilités partagées](#19-checklist-de-conformité--responsabilités-partagées)

---

## 1. Positionnement réglementaire et responsabilités

### 1.1 Nature juridique et double responsabilité

Tenxyte occupe une position réglementaire singulière : en tant que **bibliothèque open-source** distribuée sur PyPI, elle n'est pas elle-même un responsable du traitement au sens du RGPD Art. 4.7. Elle se positionne comme un **outil de conformité mis à disposition d'intégrateurs** qui, eux, endossent la responsabilité du traitement.

Cette architecture de responsabilité doit être **explicitement documentée** dans le README et la documentation officielle, sous peine d'exposer les intégrateurs à un risque de non-conformité par méconnaissance de leurs obligations.

La séparation des responsabilités s'établit comme suit :

**Ce que Tenxyte (éditeur) garantit :**
- La conception technique des mécanismes de conformité (outils RGPD, anonymisation, audit logging, PIIRedaction)
- La qualité et la robustesse cryptographique des implémentations
- La documentation des lacunes connues et des actions attendues de l'intégrateur
- La mise à jour des mécanismes en cas d'évolution réglementaire

**Ce que l'intégrateur (responsable du traitement) doit assurer :**
- L'activation et la configuration correcte des mécanismes fournis
- La rédaction du Registre des activités de traitement (RGPD Art. 30)
- La réalisation d'une DPIA si nécessaire (Art. 35)
- La rédaction de la politique de confidentialité et des mentions légales
- La conclusion de DPA avec les sous-traitants (Twilio, SendGrid, Google, etc.)
- La définition et l'application d'une politique de rétention des données
- La gestion des notifications de violations de données (Art. 33-34)
- La configuration de l'hébergement conforme (localisation des données, chiffrement au repos)

### 1.2 Référentiels réglementaires couverts

| Réglementation | Couverture Tenxyte | Niveau de conformité |
|---------------|-------------------|---------------------|
| **RGPD (UE) 2016/679** | Arts. 15, 17, 20, 25 implémentés ; Arts. 18, 21 absents | ⚠️ Partielle |
| **CCPA (Californie)** | Couverture indirecte via mécanismes RGPD | ⚠️ Indirecte |
| **NIST SP 800-63B** | Politique de mots de passe, 2FA, breach check, session management | ✅ Substantielle |
| **OWASP ASVS L2** | Authentification, sessions, logs, chiffrement | ✅ Substantielle |
| **SOC 2 Type II** | Briques fournies (AuditLog, RBAC) — conformité globale = intégrateur | ⚠️ Partielle |
| **ISO 27001** | Contrôles techniques fournis — SMSI = intégrateur | ⚠️ Partielle |

> **Observation** : Tenxyte ne peut pas afficher une conformité totale à un référentiel réglementaire qui s'applique à l'entité déployant le service, non à la bibliothèque elle-même. La documentation doit clairement établir ce périmètre pour éviter toute allégation trompeuse de "package RGPD-compliant".

---

## 2. Cartographie des données personnelles

### 2.1 Inventaire complet des données collectées

#### Données d'identité et d'authentification

| Donnée | Champ DB | Catégorie RGPD | Base légale probable | Obligatoire | Durée de vie |
|--------|----------|----------------|---------------------|-------------|--------------|
| Adresse email | `users.email` | Ordinaire — identifiant direct | Exécution du contrat (Art. 6.1.b) | Conditionnelle | Durée du compte |
| Prénom | `users.first_name` | Ordinaire | Exécution du contrat | Non | Durée du compte |
| Nom de famille | `users.last_name` | Ordinaire | Exécution du contrat | Non | Durée du compte |
| Numéro de téléphone | `users.phone_country_code` + `phone_number` | Ordinaire | Exécution du contrat | Conditionnelle | Durée du compte |
| Mot de passe (bcrypt) | `users.password` | Sécurité — non exploitable | Exécution du contrat | Oui | Durée du compte |
| Secret TOTP | `users.totp_secret` | Sécurité sensible — **en clair** ⚠️ | Intérêt légitime (Art. 6.1.f) | Non | Durée activation 2FA |
| Codes backup 2FA (SHA-256) | `users.backup_codes` | Sécurité — hashé | Intérêt légitime | Non | Durée activation 2FA |
| Date dernière connexion | `users.last_login` | Administrative | Intérêt légitime | Oui | Durée du compte |
| Date de création | `users.created_at` | Administrative | Exécution du contrat | Oui | Durée du compte |

#### Données de sessions et de sécurité

| Donnée | Champ DB | Caractère PII | Risque privacy | Durée de vie |
|--------|----------|---------------|----------------|--------------|
| Refresh token (**en clair** ⚠️) | `refresh_tokens.token` | Pseudo-PII — identifiant de session | Élevé si dump DB | 7–30 jours |
| Adresse IP de session | `refresh_tokens.ip_address` | Identifiant indirect (RGPD) | Moyen | 7–30 jours |
| Device fingerprint (User-Agent) | `refresh_tokens.device_info` | Identifiant indirect | Faible | 7–30 jours |
| IP de tentative de login | `login_attempts.ip_address` | Identifiant indirect | Moyen | **Indéfini ⚠️** |
| User-Agent de tentative | `login_attempts.user_agent` | Identifiant indirect | Faible | **Indéfini ⚠️** |
| IP d'audit log | `audit_logs.ip_address` | Identifiant indirect | Moyen | **Indéfini ⚠️** |
| User-Agent d'audit log | `audit_logs.user_agent` | Identifiant indirect | Faible | **Indéfini ⚠️** |
| JTI de token blacklisté | `blacklisted_tokens.jti` | Pseudo-anonyme | Très faible | Durée du JWT |

#### Données OAuth (Social Login)

| Provider | Données importées | Stockage | Fraîcheur |
|----------|------------------|----------|-----------|
| **Google** | email, prénom, nom, `sub` (ID Google), `picture` (URL), `email_verified` | `social_accounts` | Snapshot au login — non mis à jour |
| **GitHub** | email (primary+verified), prénom, nom, ID GitHub, `avatar_url` | `social_accounts` | Snapshot au login |
| **Microsoft** | email (`mail` ou `userPrincipalName`), prénom, nom, ID Microsoft | `social_accounts` | Snapshot au login |
| **Facebook** | email, prénom, nom, ID Facebook, `picture.url` | `social_accounts` | Snapshot au login |

> **Observation critique** : Les données OAuth sont des **copies figées au moment du login** — elles ne se synchronisent pas avec le provider. Un utilisateur qui modifie son email ou son nom chez Google aura des données obsolètes dans `social_accounts`. Cette désynchronisation doit être documentée et une stratégie de rafraîchissement devrait être envisagée.

> **Observation sur les `avatar_url`** : Les URLs d'images de profil sont stockées dans `social_accounts` et pointent vers les CDN des providers (Google, GitHub, Facebook). Ces URLs peuvent contenir des identifiants opaques permettant un suivi cross-service potentiel. Bien qu'elles ne soient pas considérées comme des données biométriques au sens de l'Art. 9, elles constituent des données personnelles à part entière et doivent figurer dans les mentions légales.

#### Données des agents IA (module AIRS)

| Donnée | Table | Caractère PII | Risque privacy spécifique |
|--------|-------|---------------|---------------------------|
| `prompt_trace_id` | `audit_logs`, `agent_pending_actions` | Pseudo-PII — identifiant LLM | Croisement possible avec logs LLM contenant des PII |
| `agent_id` | `agent_tokens`, `audit_logs` | Identifiant d'agent | Identification de l'agent et de l'humain délégant |
| Payload des actions en attente | `agent_pending_actions.payload` | **Potentiellement très sensible** | Peut contenir n'importe quelle donnée métier |
| Agent token (**en clair** ⚠️) | `agent_tokens.token` | Pseudo-PII — credential | Risque d'usurpation si dump DB |

### 2.2 Flux de données — Schéma de circulation des PII

```
┌─────────────────────────────────────────────────────────────────┐
│                    SOURCES DE DONNÉES ENTRANTES                 │
├──────────────┬──────────────────┬───────────────┬──────────────┤
│ Inscription  │  OAuth Providers │   2FA Setup   │  API Clients │
│ (email/tel)  │  (G/GH/MS/FB)    │   (TOTP/OTP)  │   (AIRS)     │
└──────┬───────┴────────┬─────────┴───────┬───────┴──────┬───────┘
       │                │                 │              │
       ▼                ▼                 ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TENXYTE — COUCHE APPLICATIVE                 │
│                                                                 │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌───────────┐  │
│  │  users   │  │social_accounts│  │  tokens  │  │audit_logs │  │
│  │(identité)│  │(OAuth data)   │  │(sessions)│  │(traçab.)  │  │
│  └──────────┘  └──────────────┘  └──────────┘  └───────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
┌────────────┐         ┌─────────────────┐      ┌───────────────┐
│  BASE DE   │         │  SERVICES TIERS │      │  INTÉGRATEUR  │
│  DONNÉES   │         │  (Twilio,       │      │  (logs nginx, │
│  (PII au   │         │   SendGrid,     │      │   backups,    │
│   repos)   │         │   HIBP, OAuth)  │      │   monitoring) │
└────────────┘         └─────────────────┘      └───────────────┘
```

---

## 3. Bases légales du traitement — RGPD Art. 6

> **Rappel important** : Tenxyte ne définit pas les bases légales — c'est la responsabilité exclusive de l'intégrateur/responsable du traitement. Le tableau ci-dessous indique les bases légales **probables** sur lesquelles l'intégrateur devrait s'appuyer. L'auditeur doit vérifier que ces bases sont formellement documentées dans le Registre des activités de traitement (Art. 30).

| Traitement | Base légale recommandée | Article RGPD | Justification | Risque si non documenté |
|-----------|------------------------|--------------|---------------|------------------------|
| Création et gestion du compte utilisateur | Exécution du contrat | Art. 6.1.b | Sans compte, pas de service | Élevé — fondement de la relation |
| Hachage et vérification du mot de passe | Exécution du contrat | Art. 6.1.b | Authentification = service core | Élevé |
| Logs d'audit de sécurité | Intérêt légitime | Art. 6.1.f | Sécurité du service, détection d'intrusions | Moyen — test d'équilibre requis |
| Logs de tentatives de login | Intérêt légitime | Art. 6.1.f | Prévention du brute force | Moyen — proportionnalité à documenter |
| Device fingerprinting (User-Agent passif) | Intérêt légitime | Art. 6.1.f | Détection des accès suspects | Moyen — doit rester passif |
| Liaison de compte OAuth | Consentement explicite | Art. 6.1.a | Action volontaire de l'utilisateur | Élevé — le consentement doit être informé |
| Secret TOTP et 2FA | Intérêt légitime (sécurité renforcée) | Art. 6.1.f | Protection du compte à la demande de l'utilisateur | Faible |
| Historique des mots de passe | Intérêt légitime | Art. 6.1.f | Prévention de la réutilisation | Faible — durée de conservation à limiter |
| Données des agents IA (AIRS) | Exécution du contrat + Intérêt légitime | Art. 6.1.b/f | Service B2B de délégation | Élevé — nouveau type de traitement à documenter |
| Export de données (RGPD Art. 20) | Obligation légale | Art. 6.1.c | Réponse à un droit de la personne | Très faible |
| Suppression de compte (RGPD Art. 17) | Obligation légale | Art. 6.1.c | Réponse à un droit de la personne | Très faible |

### 3.1 Point d'attention : Traitement des données AIRS

Le module AIRS représente un **nouveau type de traitement** pour lequel les bases légales sont moins établies réglementairement. La délégation d'actions à des agents IA autonomes soulève des questions spécifiques au regard de l'Art. 22 RGPD (décisions automatisées).

Si un agent IA prend des décisions ayant des effets juridiques ou significatifs sur des personnes physiques via les permissions AIRS, l'intégrateur devra :
- Documenter ce traitement comme décision automatisée (Art. 22)
- Garantir le droit à l'intervention humaine (le circuit HITL de Tenxyte couvre partiellement ce point)
- Prévoir une information claire dans la politique de confidentialité

---

## 4. Analyse des droits des personnes concernées

### 4.1 Art. 15 — Droit d'accès

**Couverture Tenxyte :** `GET /me/` + `POST /export-user-data/`

**Évaluation :** Le droit d'accès est **partiellement implémenté**. `GET /me/` retourne les données du profil utilisateur en temps réel. L'export `POST /export-user-data/` (protégé par mot de passe) fournit un export JSON complet.

**Lacunes identifiées :**

La structure de l'export ne couvre pas l'intégralité des données détenues :

| Données détenues | Dans l'export | Commentaire |
|-----------------|---------------|-------------|
| Profil utilisateur | ✅ | email, nom, téléphone, vérification, 2FA |
| Rôles et permissions | ✅ | code, name, assigned_at |
| Applications liées | ✅ | name, created_at |
| Audit logs | ✅ Partiel | **100 entrées seulement** — les logs plus anciens sont exclus |
| Sessions actives (`RefreshToken`) | ❌ Absent | Données de session = données personnelles |
| Connexions OAuth (`SocialAccount`) | ❌ Absent | Données reçues des providers = données personnelles |
| Tentatives de login (`LoginAttempt`) | ❌ Absent | IP + timestamps = données personnelles |
| Historique des mots de passe | ❌ Absent | Hashes — à inclure ou à exclure explicitement |
| Demandes de suppression passées | ❌ Absent | Traçabilité RGPD |
| Tokens d'agents IA (AIRS) | ❌ Absent | Si l'utilisateur est le sujet d'actions agents |

**Impact réglementaire :** L'Art. 15 exige de fournir **toutes** les données détenues sur la personne. La limite arbitraire à 100 logs et l'absence de sessions et connexions OAuth constituent une **non-conformité partielle**.

**Recommandations :**
- Supprimer la limite des 100 logs (ou la rendre configurable par l'intégrateur)
- Ajouter `refresh_tokens` (sessions actives + expirées récentes) à l'export
- Ajouter `social_accounts` (connexions OAuth) à l'export
- Ajouter `login_attempts` (dernières N tentatives) à l'export
- Documenter explicitement ce qui est exclu de l'export et pourquoi (hashes, backup codes)

### 4.2 Art. 16 — Droit de rectification

**Couverture Tenxyte :** `PUT/PATCH /me/` — partiellement dépendant de l'implémentation de l'intégrateur.

**Évaluation :** Tenxyte expose une route `PATCH /me/` permettant la modification du profil. Cependant, la couverture effective dépend de ce que l'intégrateur autorise à modifier via le serializer. Il n'existe pas de mécanisme standardisé et documenté pour la modification de tous les champs soumis au droit de rectification.

**Recommandation :** Documenter explicitement les champs modifiables via `PATCH /me/` et ceux nécessitant un flux dédié (changement d'email avec re-vérification, changement de téléphone avec OTP de confirmation).

### 4.3 Art. 17 — Droit à l'effacement ✅

**Couverture Tenxyte :** Workflow à 5 états complet — **c'est le mécanisme le mieux implémenté du package.**

```
PENDING → CONFIRMATION_SENT → CONFIRMED → COMPLETED
                                   ↓
                              CANCELLED (pendant la période de grâce)
```

**Points forts :**
- Double confirmation (mot de passe + OTP si 2FA activé + token email CSPRNG)
- Période de grâce de 30 jours avec possibilité d'annulation
- Anonymisation exhaustive lors de `soft_delete()` :
  - `email → "deleted_<id>@deleted.local"`
  - `first_name`, `last_name → ""`
  - `phone_*, google_id, totp_secret, backup_codes → null/[]`
  - `is_active, is_staff, is_superuser → False`
  - `anonymization_token → secrets.token_urlsafe(48)` (pour audit sans PII)
- Token d'anonymisation cryptographiquement sûr (CSPRNG, 48 chars)

**Lacune résiduelle — Rétention des audit_logs après suppression :**

Après l'exécution du `soft_delete()`, les entrées `AuditLog` associées à l'utilisateur **conservent l'`ip_address` et le `user_agent`**. Ces données constituent des données pseudo-anonymes au sens du RGPD.

**Analyse :** La conservation des logs d'audit après suppression est généralement **légalement justifiée** par l'intérêt légitime à la sécurité et la prévention de la fraude (Art. 6.1.f), sous réserve que :
1. La durée de conservation soit définie et documentée
2. Les logs ne permettent pas de réidentifier l'utilisateur (la FK `user` est anonymisée — ✅)
3. L'intégrateur ait documenté cet intérêt légitime dans son Registre Art. 30

**Recommandation :** Fournir un mécanisme optionnel pour purger l'`ip_address` des `AuditLog` lors de la suppression du compte, activable via `TENXYTE_PURGE_IP_ON_DELETION = True`.

### 4.4 Art. 18 — Droit à la limitation du traitement ❌

**Couverture Tenxyte :** Non implémenté.

Le droit à la limitation (gel du traitement sans suppression) est absent du périmètre Tenxyte. Il n'existe pas d'état intermédiaire entre "compte actif" et "compte supprimé" permettant de geler les traitements tout en conservant les données.

**Recommandation :** Implémenter un état `is_restricted` sur le modèle `User`, avec un workflow dédié `POST /request-account-restriction/`. Cet état devrait :
- Bloquer toutes les authentifications (retour 403 avec message spécifique)
- Bloquer les exports de données
- Maintenir les données intactes
- Être réversible sur demande de l'utilisateur ou de l'autorité de contrôle

### 4.5 Art. 20 — Droit à la portabilité ⚠️

**Couverture Tenxyte :** `POST /export-user-data/` — export JSON.

**Points forts :**
- Export en format JSON (interopérable, machine-readable)
- Protégé par mot de passe (évite l'export par tiers non autorisé)
- Tracé dans `AuditLog` via l'action `data_exported`

**Lacunes :** Voir section 4.1 — les mêmes lacunes d'exhaustivité s'appliquent au droit à la portabilité. L'Art. 20 exige un format "structuré, couramment utilisé et lisible par machine" — JSON satisfait cette exigence.

**Lacune supplémentaire :** L'export n'est pas transmissible directement à un autre responsable de traitement (portabilité active). Tenxyte ne fournit pas de mécanisme d'export vers un tiers désigné. Ce point est généralement accepté pour les bibliothèques back-end, mais doit être documenté.

### 4.6 Art. 21 — Droit d'opposition ❌

**Couverture Tenxyte :** Non implémenté.

Le droit d'opposition au traitement basé sur l'intérêt légitime (Art. 6.1.f) — notamment pour les logs d'audit et le device fingerprinting — n'est pas adressé. C'est une responsabilité de l'intégrateur, mais Tenxyte devrait fournir les mécanismes techniques nécessaires (possibilité de désactiver le device fingerprinting par utilisateur, granularité des logs).

### 4.7 Art. 22 — Décisions automatisées

**Couverture Tenxyte :** Partiellement adressé via le circuit HITL du module AIRS.

Le verrouillage automatique de compte (`account_locked` via `ACCOUNT_LOCKOUT_ENABLED`) constitue une **décision automatisée** ayant un effet significatif sur l'utilisateur (impossibilité d'accéder au service). Ce mécanisme doit être documenté dans la politique de confidentialité de l'intégrateur, qui doit garantir une voie de recours humain (déblocage via `POST /admin/users/{id}/unlock/`).

Le circuit breaker AIRS et la révocation automatique d'agents constituent également des décisions automatisées à documenter.

---

## 5. Privacy by Design — RGPD Art. 25

### 5.1 Évaluation des 7 principes fondateurs

| Principe (Art. 5 RGPD) | Implémentation Tenxyte | Évaluation |
|------------------------|------------------------|-----------|
| **Licéité, loyauté, transparence** | Mécanismes techniques fournis — transparence = responsabilité intégrateur | ⚠️ Partielle |
| **Limitation des finalités** | Données collectées uniquement pour l'authentification | ✅ Respecté |
| **Minimisation des données** | Seul email OU téléphone requis ; prénom/nom optionnels | ✅ Fort |
| **Exactitude** | `PATCH /me/` disponible ; données OAuth figées au login | ⚠️ Partielle |
| **Limitation de la conservation** | Rétention automatique absente pour logs et tokens expirés | ❌ Lacune majeure |
| **Intégrité et confidentialité** | bcrypt, SHA-256, JWT signé, HTTPS via intégrateur | ⚠️ Partielle (totp_secret en clair) |
| **Responsabilité** | Documentation des responsabilités à compléter | ⚠️ À renforcer |

### 5.2 Mesures Privacy by Default implémentées

**Collecte minimale :** Tenxyte requiert uniquement l'email **ou** le numéro de téléphone comme identifiant. Les champs `first_name` et `last_name` sont optionnels. Cette approche respecte le principe de minimisation.

**Pseudonymisation :** Le `soft_delete()` remplace les identifiants directs par des données synthétiques non traçables, en conservant un `anonymization_token` opaque pour les besoins d'audit. Cette approche constitue une pseudonymisation robuste au sens du Considérant 26 du RGPD.

**Chiffrement en transit :** Tenxyte injecte le header `Strict-Transport-Security (HSTS)` via `SecurityHeadersMiddleware` si configuré — cela force l'utilisation de HTTPS sans action supplémentaire de l'intégrateur.

**Contrôle d'accès granulaire (RBAC) :** Le système RBAC hiérarchique implémente le principe du moindre privilège — chaque entité (utilisateur, application, agent IA) n'accède qu'aux données strictement nécessaires à ses attributions.

**Isolation multi-tenant :** L'utilisation de `ContextVar` Python pour l'isolation des données par organisation (tenant) constitue une mesure technique solide de Privacy by Design pour les architectures B2B. Le `BaseTenantModel` force automatiquement l'attribution de l'organisation courante lors des opérations `save()` et `delete()`, rendant les fuites cross-tenant architecturalement impossibles via l'API.

**Masquage PII pour les agents IA :** La `PIIRedactionMiddleware` masque 10 champs sensibles (`email`, `phone`, `ssn`, `date_of_birth`, `address`, `credit_card`, `password`, `totp_secret`, `backup_codes`) dans les réponses JSON aux agents. Ce mécanisme constitue une mesure de Privacy by Default innovante, particulièrement adaptée aux architectures intégrant des LLMs.

### 5.3 Lacunes Privacy by Design

**Absence de Privacy Enhancing Technologies (PET) pour les logs :** Les adresses IP stockées dans `AuditLog` et `LoginAttempt` pourraient être pseudonymisées à la source (hachage HMAC de l'IP avec une clé rotatoire) plutôt que stockées en clair. Cette approche permettrait la détection de patterns d'attaque tout en limitant la capacité à identifier des individus spécifiques.

**Absence de differential privacy pour les statistiques :** Le module `dashboard_views.py` expose des statistiques d'authentification. Si ces statistiques sont basées sur des données individuelles non agrégées, elles pourraient permettre des inférences sur le comportement d'utilisateurs spécifiques.

---

## 6. Protection des données sensibles au repos

### 6.1 Inventaire complet de la protection cryptographique

| Donnée | Protection actuelle | Standard recommandé | Écart |
|--------|--------------------|--------------------|-------|
| Mot de passe | ✅ bcrypt (irréversible) | bcrypt / Argon2id | Conforme |
| Secret application | ✅ bcrypt + base64 | bcrypt | Conforme |
| Token OTP | ✅ SHA-256 | HMAC-SHA256 de préférence | Acceptable |
| Token magic link | ✅ SHA-256 | HMAC-SHA256 | Acceptable |
| Codes backup 2FA | ✅ SHA-256 | HMAC-SHA256 | Acceptable |
| **Secret TOTP** | ❌ **En clair** | AES-256-GCM (chiffrement symétrique) | **Critique** |
| **Refresh token** | ❌ **En clair** | SHA-256 (même pattern que OTP) | **Critique** |
| **Agent token** | ❌ **En clair** | SHA-256 | **Élevé** |
| **OAuth access_token** | ❌ **En clair** | AES-256-GCM | **Élevé** |
| **OAuth refresh_token** | ❌ **En clair** | AES-256-GCM | **Élevé** |
| Adresses IP | ❌ En clair | HMAC-SHA256 rotatoire (optionnel) | Moyen |
| User-Agent | ❌ En clair | Acceptable en clair | Conforme |
| IDs externes OAuth (Google sub, etc.) | ❌ En clair | Acceptable (pseudo-anonyme) | Acceptable |

### 6.2 🔴 Analyse critique — `totp_secret` en clair

Le secret TOTP est stocké en clair dans `users.totp_secret`. Ce champ est **nécessairement réversible** car le serveur doit être capable de calculer le code TOTP courant pour le comparer à celui fourni par l'utilisateur.

**Scénario d'attaque :** Un attaquant obtenant un dump de la table `users` dispose immédiatement des secrets TOTP de tous les utilisateurs ayant activé le 2FA. Il peut reproduire les codes TOTP en temps réel avec n'importe quelle application TOTP standard, rendant le 2FA entièrement inopérant comme second facteur d'authentification.

**Impact réglementaire :** La compromission du 2FA constitue une **violation de données personnelles** au sens de l'Art. 4.12 du RGPD, déclenchant les obligations de notification des Arts. 33-34.

**Solution recommandée :**

```python
# Approche 1 : chiffrement AES-256-GCM avec django-cryptography
from django_cryptography.fields import encrypt

class User(AbstractBaseUser):
    totp_secret = encrypt(models.CharField(max_length=64, null=True, blank=True))
    # Transparent pour le code existant — chiffrement/déchiffrement automatique

# Approche 2 : champ custom avec clé applicative dédiée
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

TOTP_ENCRYPTION_KEY = os.environ['TENXYTE_TOTP_ENCRYPTION_KEY']  # 32 bytes

def encrypt_totp_secret(secret: str) -> str:
    key = bytes.fromhex(TOTP_ENCRYPTION_KEY)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, secret.encode(), None)
    return (nonce + ct).hex()
```

### 6.3 🔴 Analyse critique — Refresh tokens en clair

Les refresh tokens (64 chars, `secrets.token_urlsafe(64)`) sont stockés en clair dans `refresh_tokens.token`. Un dump de cette table permet l'usurpation de toutes les sessions actives sans nécessiter le mot de passe.

**Incohérence architecturale majeure :** Les `OTPCode`, `MagicLinkToken`, et codes backup sont hashés en SHA-256 — mais pas les refresh tokens, qui ont une durée de vie bien plus longue (7-30 jours vs 10 minutes pour les OTP). Cette incohérence est inexplicable d'un point de vue sécurité.

**Solution recommandée :** Appliquer le même pattern SHA-256 déjà utilisé pour les OTP :

```python
# models/operational.py
import hashlib

class RefreshToken(models.Model):
    token_hash = models.CharField(max_length=64, unique=True)  # SHA-256 du token

    @classmethod
    def create(cls, user, application, **kwargs):
        raw_token = secrets.token_urlsafe(64)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        instance = cls.objects.create(token_hash=token_hash, user=user, ...)
        return raw_token, instance  # Le token raw n'est retourné qu'une seule fois

    @classmethod
    def verify(cls, raw_token):
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        return cls.objects.filter(token_hash=token_hash, is_revoked=False).first()
```

---

## 7. Politique de rétention des données

### 7.1 État actuel — Analyse par table

| Table | Données personnelles | Durée actuelle | Suppression auto | Conformité RGPD |
|-------|---------------------|----------------|-----------------|-----------------|
| `users` | Élevée (PII directes) | Durée du compte | Via `soft_delete()` workflow | ✅ Correct |
| `audit_logs` | Moyenne (IP, UA) | **Indéfinie ⚠️** | Aucune | ❌ Non conforme |
| `login_attempts` | Moyenne (IP, UA) | **Indéfinie ⚠️** | Aucune | ❌ Non conforme |
| `refresh_tokens` | Faible (ID de session) | 7-30 jours (TTL) | Rotation + `cleanup_expired()` | ✅ Acceptable |
| `otp_codes` | Très faible (hash) | 10-15 min (TTL) | Non supprimé auto après expiration ⚠️ | ⚠️ À améliorer |
| `magic_link_tokens` | Très faible (hash) | 15 min (TTL) | Non supprimé auto ⚠️ | ⚠️ À améliorer |
| `webauthn_challenges` | Nulle (aléatoire) | 5 min (TTL) | Non supprimé auto ⚠️ | ⚠️ Faible risque |
| `agent_pending_actions` | Potentiellement élevée (payload) | 10 min (TTL) | **Persiste en DB ⚠️** | ❌ Non conforme |
| `password_history` | Nulle (hashes) | **Indéfinie ⚠️** | Partielle (lors d'un nouveau hash) | ⚠️ À documenter |
| `blacklisted_tokens` | Nulle (JTI UUID) | Durée du JWT | Via `cleanup_expired()` | ✅ Acceptable |
| `social_accounts` | Moyenne (email, noms, IDs) | Durée du compte | Via `soft_delete()` | ✅ Acceptable |
| `account_deletion_requests` | Administrative | Post-COMPLETED persist ⚠️ | Aucune | ⚠️ À limiter |

### 7.2 🔴 Non-conformité critique — `AuditLog` et `LoginAttempt`

L'accumulation indéfinie de `AuditLog` et `LoginAttempt` contenant des adresses IP et des User-Agents constitue une **violation du principe de limitation de la conservation** (RGPD Art. 5.1.e).

**Durées de conservation recommandées (alignées sur les pratiques sectorielles) :**

| Type de log | Durée recommandée | Justification |
|-------------|------------------|---------------|
| Logs de tentatives de login échouées | 90 jours | Durée suffisante pour investigation post-incident |
| Logs de connexions réussies | 12 mois | Détection de compromission à long terme |
| Logs d'actions de sécurité critiques (changement de mot de passe, 2FA) | 3 ans | Obligations légales potentielles |
| Logs d'export RGPD et de suppression de compte | 5 ans | Preuve de conformité |
| Logs d'actions agents IA (AIRS) | 12 mois | Traçabilité des actions automatisées |

**Implémentation recommandée :**

```python
# tasks/cleanup.py — tâches Celery à fournir dans le package
from django.utils import timezone
from datetime import timedelta

@shared_task
def cleanup_audit_logs(retention_days=None):
    """
    Purge les AuditLog selon la politique de rétention configurée.
    Respecte les durées différenciées par type d'action.
    """
    settings = TenxyteSettings()
    cutoff = timezone.now() - timedelta(days=retention_days or settings.AUDIT_LOG_RETENTION_DAYS)

    # Conserver les logs critiques (suppression de compte, export) plus longtemps
    critical_actions = ['data_exported', 'deletion_confirmation_email_failed', 'account_created']
    critical_cutoff = timezone.now() - timedelta(days=settings.AUDIT_LOG_CRITICAL_RETENTION_DAYS)

    AuditLog.objects.filter(
        created_at__lt=cutoff
    ).exclude(
        action__in=critical_actions
    ).delete()

    AuditLog.objects.filter(
        action__in=critical_actions,
        created_at__lt=critical_cutoff
    ).delete()

@shared_task
def cleanup_login_attempts(retention_days=90):
    cutoff = timezone.now() - timedelta(days=retention_days)
    LoginAttempt.objects.filter(created_at__lt=cutoff).delete()
```

### 7.3 Paramètres de rétention recommandés

```python
# Nouveaux settings à ajouter dans conf.py
TENXYTE_AUDIT_LOG_RETENTION_DAYS = 365          # 12 mois par défaut
TENXYTE_AUDIT_LOG_CRITICAL_RETENTION_DAYS = 1095 # 3 ans pour les logs critiques
TENXYTE_LOGIN_ATTEMPT_RETENTION_DAYS = 90        # 3 mois
TENXYTE_EXPIRED_TOKEN_CLEANUP_DAYS = 7           # OTP, WebAuthn challenges expirés
TENXYTE_AGENT_PENDING_ACTION_RETENTION_DAYS = 30 # Actions AIRS complétées/expirées
```

---

## 8. Sous-traitants tiers et transferts internationaux

### 8.1 Inventaire des sous-traitants recevant des données personnelles

| Sous-traitant | Données transférées | Localisation | DPA disponible | Transfert UE → US |
|---------------|--------------------|--------------|----------------|-------------------|
| **HaveIBeenPwned (Troy Hunt)** | SHA-1 prefix (5 chars) — **pas de PII réelles** | US / CDN global | N/A — k-anonymity | ✅ Pas de PII |
| **Google (OAuth + API)** | Email, prénom, nom, `sub` | US (avec clauses EU) | ✅ DPA Google Cloud | ⚠️ SCCs requises |
| **GitHub (OAuth + API)** | Email, nom, ID GitHub | US | ✅ DPA GitHub | ⚠️ SCCs requises |
| **Microsoft (OAuth + Graph API)** | Email, prénom, nom, ID Microsoft | US (avec EU Data Boundary) | ✅ DPA Microsoft | ✅ EU Data Boundary |
| **Facebook (OAuth + Graph API)** | Email, prénom, nom, ID Facebook | US | ✅ DPA Meta | ⚠️ SCCs requises |
| **Twilio (SMS OTP)** | Numéro de téléphone, corps OTP | US | ✅ DPA Twilio | ⚠️ SCCs requises |
| **SendGrid (Email OTP)** | Adresse email, corps du message | US | ✅ DPA Twilio/SendGrid | ⚠️ SCCs requises |

> **Point positif — HaveIBeenPwned :** L'implémentation k-anonymity est exemplaire. Seuls 5 caractères hexadécimaux (20 bits) du hash SHA-1 sont transmis. Le mot de passe en clair et le hash complet ne quittent **jamais** le serveur. Ce mécanisme est conforme aux meilleures pratiques Privacy by Design et ne génère aucun transfert de données personnelles.

### 8.2 Obligations de l'intégrateur pour les transferts internationaux

Les intégrateurs déployant Tenxyte avec des providers OAuth ou les backends Twilio/SendGrid effectuent des **transferts de données personnelles vers des pays tiers** (principalement les États-Unis) au sens du RGPD Chapitre V.

Depuis l'invalidation du Privacy Shield (Schrems II, 2020) et l'adoption du Data Privacy Framework (DPF, 2023), les transferts vers les États-Unis peuvent être encadrés par :

1. **Data Privacy Framework (DPF)** — pour les organisations américaines certifiées (Google, Microsoft, Twilio sont certifiés)
2. **Clauses Contractuelles Types (SCCs)** de la Commission européenne (version 2021)
3. **Règles d'entreprise contraignantes (BCR)** pour les groupes multinationaux

**Recommandation pour Tenxyte :** Inclure dans la documentation une section dédiée aux transferts internationaux, listant les certifications DPF de chaque provider et les clauses contractuelles à mettre en place. Fournir un template de DPA pour chaque sous-traitant optionnel.

### 8.3 Données envoyées aux providers OAuth — Analyse détaillée

**Risque de sur-collecte chez Facebook :** L'API Facebook Graph est appelée avec `fields=id,email,first_name,last_name,picture`. La `picture` (URL vers le CDN Facebook) est une donnée personnelle stockée dans `social_accounts`. Si cette donnée n'est pas utilisée fonctionnellement par l'intégrateur, elle constitue une collecte excessive contraire au principe de minimisation.

**Recommandation :** Rendre les champs demandés aux providers OAuth configurables via `TENXYTE_SOCIAL_REQUESTED_FIELDS` pour permettre à l'intégrateur d'appliquer le principe de minimisation selon ses besoins.

---

## 9. Authentification OAuth — Risques privacy spécifiques

### 9.1 Fusion automatique de comptes — Risque de privacy et de sécurité

**Mécanisme actuel :**

```
Connexion OAuth (email: alice@example.com)
    │
    ├─ SocialConnection existante ? → Utilisateur existant (OK)
    │
    └─ Non → Recherche par email (case-insensitive)
                    │
                    ├─ Email trouvé → FUSION AUTOMATIQUE ⚠️
                    │
                    └─ Non trouvé → Création d'un nouveau compte
```

**Risque privacy :** La fusion automatique sans confirmation explicite de l'utilisateur peut lier à son insu un compte OAuth externe à un compte existant. Du point de vue du droit à l'information (Art. 13-14 RGPD), cette liaison doit être notifiée à l'utilisateur.

**Risque de sécurité (Account Takeover) :** Si un attaquant contrôle un compte OAuth avec le même email qu'une victime (email non vérifié chez GitHub notamment), il peut accéder au compte de la victime. GitHub peut retourner un email non vérifié si l'utilisateur a configuré un email primaire non public.

**Recommandations :**

```python
# Option 1 : Notification obligatoire lors de la première fusion
TENXYTE_SOCIAL_NOTIFY_ON_ACCOUNT_LINK = True

# Option 2 : Exiger un email vérifié pour la fusion automatique
TENXYTE_SOCIAL_REQUIRE_VERIFIED_EMAIL = True  # Rejette les providers sans email_verified

# Option 3 : Demander une confirmation explicite (recommandée)
TENXYTE_SOCIAL_LINK_REQUIRE_CONFIRMATION = True
# → Envoie un email de confirmation avant la liaison
```

### 9.2 Fraîcheur et exactitude des données OAuth

Les données OAuth (email, prénom, nom, avatar) sont des **snapshots au moment du login** et ne se synchronisent pas automatiquement avec le provider. Un utilisateur qui modifie son email chez Google aura des données obsolètes dans `social_accounts`.

Cette situation peut créer une violation du principe d'exactitude (Art. 5.1.d RGPD) si l'intégrateur utilise ces données pour des communications ou des traitements critiques.

**Recommandation :** Implémenter un rafraîchissement automatique des données OAuth à chaque reconnexion, configurable via `TENXYTE_SOCIAL_REFRESH_ON_LOGIN = True`.

---

## 10. Module AIRS — Agents IA et protection des données

### 10.1 Analyse privacy du module AIRS

Le module AIRS (Agent AI Restriction System) représente un **traitement de données personnelles de nouvelle génération** dont les implications réglementaires sont encore en cours d'établissement dans la doctrine RGPD. Cette analyse constitue une évaluation prospective basée sur les principes existants.

### 10.2 Payload des `AgentPendingAction` — Risque de stockage non contrôlé

Le champ `agent_pending_actions.payload` stocke les données des actions en attente de confirmation humaine (HITL). Ce champ JSON peut contenir **n'importe quelle donnée métier** transmise par l'agent IA — y compris des données personnelles de tiers, des informations commerciales sensibles, ou des données de catégorie spéciale (Art. 9 RGPD).

**Risque :** L'absence de durée de rétention automatique (les actions expirées persistent en DB) signifie que des données potentiellement très sensibles s'accumulent sans limitation.

**Recommandation :** Implémenter une purge automatique des `AgentPendingAction` expirées (TTL 10 min + nettoyage périodique) et documenter que l'intégrateur est responsable de ne pas faire transiter de données de catégorie spéciale dans les payloads agents sans base légale appropriée.

### 10.3 `prompt_trace_id` — Risque de croisement inter-systèmes

Le `prompt_trace_id` stocké dans `AuditLog` et `agent_pending_actions` est un identifiant de traçabilité LLM. Dans une architecture typique, cet identifiant permet de relier un audit log Tenxyte à la trace correspondante dans le système LLM (logs du provider OpenAI/Anthropic/autre).

**Risque de croisement :** Si le prompt LLM correspondant contient des données personnelles (ce qui est fréquent : noms, emails, numéros de téléphone mentionnés dans des requêtes), le croisement entre les logs Tenxyte et les logs LLM reconstituent un profil de l'utilisateur concerné.

**Recommandation :** Documenter explicitement que :
- Le `prompt_trace_id` ne doit contenir que des identifiants opaques (UUID), jamais de données en clair
- L'intégrateur est responsable de la conformité des données transmises aux LLMs via les agents AIRS
- Une DPIA est recommandée pour les déploiements AIRS impliquant des données personnelles de tiers

### 10.4 PIIRedactionMiddleware — Évaluation de l'efficacité

**Points forts :**
- Masquage de 10 champs sensibles prédéfinis dans les réponses JSON
- Récursif (objets imbriqués et listes couverts)
- Conditionnel au token `AgentBearer` — n'impacte pas les réponses aux utilisateurs humains

**Limitations :**

Le masquage est **côté transport (HTTP response) uniquement**. Il ne protège pas contre :
- L'accès direct à la base de données par l'agent (hors API Tenxyte)
- Les données transmises dans les requêtes entrantes de l'agent (corps de requête, headers)
- Les données dans les `AgentPendingAction.payload`
- Les données que l'agent aurait mémorisées dans le contexte LLM avant le masquage

**Recommandation :** Documenter clairement dans la documentation AIRS que la `PIIRedactionMiddleware` est une mesure de défense en profondeur côté réponse HTTP, et non une protection complète contre l'accès aux PII par les agents.

---

## 11. Audit Logging — Conformité et traçabilité

### 11.1 Évaluation de la couverture des événements audités

La couverture des actions auditées est exhaustive et va au-delà des exigences minimales RGPD. Elle couvre notamment :
- Tous les événements d'authentification (login, échecs, logout, refresh)
- Les modifications de sécurité (changement de mot de passe, 2FA, rôles)
- Les événements RGPD (export de données, suppression de compte)
- Les actions des agents IA (AIRS)

**Point fort notable :** L'audit log conserve l'`on_behalf_of` pour les actions AIRS, permettant de tracer qui (humain) a délégué quelle action à quel agent. Cette traçabilité est essentielle pour le respect du principe d'imputabilité (Art. 5.2 RGPD) dans les architectures agentic.

### 11.2 Lacunes de l'audit logging

**Absence de signature cryptographique :** Les entrées `AuditLog` peuvent être modifiées ou supprimées par quiconque dispose d'un accès en écriture à la base de données. Pour les cas d'usage où les logs constituent une preuve (contentieux, investigation forensique), l'absence de signature cryptographique est une lacune.

**Recommandation :** Pour les déploiements à haute exigence de conformité, documenter la nécessité d'exporter les logs vers un système immuable (CloudWatch Logs, Azure Monitor, Loki avec append-only) ou d'implémenter un mécanisme de chaînage cryptographique des entrées (hash du log N-1 inclus dans le log N).

**Absence de rétention différenciée :** Tous les logs ont la même durée de rétention par défaut (indéfinie). Une rétention différenciée selon la sensibilité de l'action serait plus conforme au principe de minimisation.

### 11.3 Device fingerprinting — Analyse privacy

Le fingerprinting de devices repose exclusivement sur le `User-Agent` HTTP (OS, navigateur, type d'appareil). C'est un **fingerprinting passif**, qui ne recourt à aucune technique active (canvas fingerprinting, WebGL, AudioContext, etc.).

**Évaluation RGPD :** Le User-Agent est une donnée personnelle indirecte (identifiant indirect) au sens du Considérant 30 du RGPD. Sa collecte est justifiable par l'intérêt légitime à la sécurité (détection de nouveaux appareils, limitation du nombre de sessions), sous réserve que l'intégrateur le documente dans sa politique de confidentialité.

**Point positif :** L'absence de cookies et de fingerprinting actif (canvas, WebGL) limite significativement l'impact privacy par rapport aux solutions de fingerprinting classiques.

---

## 12. Analyse de conformité JWT — Minimisation des données

### 12.1 Évaluation du payload JWT

```json
{
  "type": "access",
  "jti": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "app_id": "7b3c2e1d-...",
  "iat": 1709035200,
  "exp": 1709036100
}
```

**Évaluation :** Le payload JWT Tenxyte est **exemplaire du point de vue de la minimisation**. Aucune donnée nominale (email, nom, téléphone) n'y figure. Seuls des identifiants opaques (UUIDs pseudo-anonymes) sont inclus.

Cette approche est conforme aux recommandations OWASP JWT Security Cheat Sheet et au principe de minimisation RGPD Art. 5.1.c.

### 12.2 Risques résiduels

**JWT non chiffré (JWE) :** Le JWT est signé (JWS/HS256) mais non chiffré (JWE). Le payload est lisible par quiconque en base64-décode le token, sans nécessiter la clé de signature. Bien que le `user_id` soit un UUID pseudo-anonyme, sa présence dans des logs d'infrastructure (nginx, load balancer) qui capturent le header `Authorization` constitue un risque résiduel.

**Recommandation :** Documenter explicitement que les logs d'infrastructure ne doivent pas capturer le header `Authorization`. Fournir une configuration nginx example qui masque ce header dans les logs d'accès.

**Vérification des claims custom :** L'audit doit vérifier qu'aucun intégrateur n'a ajouté de PII directes dans le payload JWT via des claims custom. Documenter l'interdiction de tels claims.

---

## 13. Droit à l'effacement — Invalidation des sessions actives

### 13.1 Analyse de l'exécution du `soft_delete()`

**Comportement actuel :**

| Ressource | Invalidée ? | Mécanisme | Conformité |
|-----------|------------|-----------|-----------|
| JWT access token en cours | ✅ Oui (indirect) | `is_active = False` → 401 au prochain check | Conforme |
| Refresh tokens en DB | ⚠️ Non révoqués | Bloqués fonctionnellement par `is_active = False` | Risque résiduel |
| Agent tokens (AIRS) | ⚠️ Non révoqués | Bloqués par `is_active = False` | Risque résiduel |
| Magic Link tokens | ⚠️ Non révoqués | Restent en DB jusqu'à expiration TTL | Risque faible (TTL 15 min) |
| WebAuthn challenges | ⚠️ Non révoqués | TTL 5 min — risque négligeable | Acceptable |

**Évaluation RGPD Art. 17 :** L'effet fonctionnel du `soft_delete()` est **suffisant pour la conformité immédiate** — un utilisateur supprimé ne peut plus s'authentifier ni obtenir de nouveaux tokens. Le check `is_active = False` dans `JWTAuthentication` garantit le blocage effectif.

**Risque résiduel — Scénario de réactivation accidentelle :** Si le compte est réactivé (`is_active = True` directement en DB, par exemple par une erreur d'administration), les refresh tokens et agent tokens non révoqués seraient à nouveau fonctionnels. Ce scénario, bien que improbable, constitue une **fuite de données potentielle** post-suppression.

**Recommandation RGPD Art. 17 — Bonne pratique :**

```python
# models/gdpr.py — execute_deletion() amélioré
def execute_deletion(self, processed_by=None):
    if self.status != 'confirmed':
        return False

    with transaction.atomic():
        # Révocation explicite de tous les tokens actifs
        RefreshToken.objects.filter(user=self.user, is_revoked=False).update(
            is_revoked=True,
            revoked_at=timezone.now(),
            revocation_reason='account_deleted'
        )
        AgentToken.objects.filter(user=self.user, status='ACTIVE').update(
            status='REVOKED',
            revoked_at=timezone.now()
        )
        MagicLinkToken.objects.filter(user=self.user, is_used=False).update(
            is_used=True
        )

        success = self.user.soft_delete()

        if success:
            self.status = 'completed'
            self.save()

    return success
```

---

## 14. Conformité NIST SP 800-63B

### 14.1 Évaluation par critère

| Critère NIST 800-63B | Implémentation Tenxyte | Niveau |
|---------------------|----------------------|--------|
| **Longueur minimale** | 8 chars minimum (configurable) | AAL1 ✅ |
| **Longueur maximale** | 128 chars maximum | ✅ |
| **Caractères spéciaux** | Supportés, configurables | ✅ |
| **Vérification des mots de passe compromis (HIBP)** | `breach_check_service.py` avec k-anonymity | ✅ Conforme |
| **Pas de restrictions de composition arbitraires** | Score 0-100, règles configurables | ✅ |
| **Pas de rotation forcée périodique** | Non imposé par Tenxyte | ✅ (NIST 800-63B déconseille la rotation périodique) |
| **Historique des mots de passe** | `PasswordHistory` (N derniers, configurable) | ✅ |
| **2FA TOTP** | `pyotp`, fenêtre configurable | AAL2 ✅ |
| **2FA FIDO2/WebAuthn** | `py_webauthn` | AAL3 ✅ |
| **Verrouillage après N échecs** | `ACCOUNT_LOCKOUT_ENABLED`, configurable | ✅ |
| **Throttling progressif** | `ProgressiveLoginThrottle` (backoff exponentiel) | ✅ Excellent |
| **Notification de sécurité** | Via `AuditLog` — email notification = intégrateur | ⚠️ Partielle |
| **Sessions limitées** | `SESSION_LIMIT_ENABLED`, `DEVICE_LIMIT_ENABLED` | ✅ |

**Évaluation globale :** Tenxyte atteint le niveau **AAL2** (Authentication Assurance Level 2) du NIST SP 800-63B avec activation du 2FA, et fournit les mécanismes nécessaires pour atteindre le niveau **AAL3** avec WebAuthn/FIDO2.

### 14.2 Points de conformité NIST à améliorer

**Notification proactive de sécurité :** NIST 800-63B §5.2.2 recommande de notifier l'utilisateur lors d'événements de sécurité critiques (nouveau device, changement de mot de passe). Tenxyte loggue ces événements mais ne fournit pas de backend de notification email natif pour ces alertes — c'est à la charge de l'intégrateur.

**Recommandation :** Intégrer des hooks de notification email dans les événements `new_device_detected`, `password_change`, `account_locked` via le système de signals Django.

---

## 15. Conformité CCPA

### 15.1 Mapping CCPA → Mécanismes Tenxyte

| Droit CCPA | Section | Mécanisme Tenxyte | Couverture |
|-----------|---------|------------------|-----------|
| Droit à l'information (quelles données collectées) | §1798.100 | Documentation + `GET /me/` | ⚠️ Partielle |
| Droit d'accès | §1798.110 | `POST /export-user-data/` | ⚠️ Partielle (voir §4.1) |
| Droit à la suppression | §1798.105 | Workflow Art. 17 | ✅ Couvert |
| Droit d'opposition à la vente | §1798.120 | N/A — Tenxyte ne vend pas de données | N/A |
| Non-discrimination | §1798.125 | N/A | N/A |
| Droit à la correction | §1798.106 | `PATCH /me/` | ⚠️ Partielle |
| Droit à la limitation | §1798.121 | Non implémenté | ❌ |

**Évaluation :** La couverture CCPA est essentiellement assurée par les mécanismes RGPD. Les droits fondamentaux (accès, suppression) sont couverts. Le droit à la limitation (§1798.121, "sensitive personal information") est absent, bien que son applicabilité dépende de la nature des données traitées par l'intégrateur.

---

## 16. Conformité SOC 2 Type II

### 16.1 Mapping Trust Services Criteria → Tenxyte

| Critère SOC 2 | Composante | Couverture Tenxyte | Note |
|--------------|-----------|-------------------|------|
| **CC6.1** — Contrôle d'accès logique | Authentification, RBAC | ✅ Fort | JWT, RBAC hiérarchique, 2FA |
| **CC6.2** — Gestion des accès utilisateurs | Création/révocation de comptes | ✅ Couvert | Workflows complets |
| **CC6.3** — Accès aux données basé sur le besoin | RBAC, moindre privilège | ✅ Fort | Permissions granulaires |
| **CC6.6** — Protection contre les menaces | Rate limiting, breach check, lockout | ✅ Fort | 12 classes de throttling |
| **CC6.7** — Transmission sécurisée | HTTPS (intégrateur) + HSTS | ⚠️ Partielle | Dépend de l'intégrateur |
| **CC6.8** — Prévention des malwares | N/A pour une bibliothèque | N/A | — |
| **CC7.2** — Monitoring de sécurité | AuditLog complet | ✅ Couvert | 30+ types d'événements |
| **CC7.3** — Réponse aux incidents | Notifications = intégrateur | ⚠️ Partielle | Mécanismes fournis, orchestration = intégrateur |
| **CC9.2** — Gestion des fournisseurs tiers | DPA providers = intégrateur | ⚠️ À documenter | — |

**Évaluation :** Tenxyte fournit les **briques techniques nécessaires** à une certification SOC 2 Type II pour l'intégrateur. La certification elle-même requiert des éléments organisationnels (politiques, procédures, formation) qui sont par définition la responsabilité de l'intégrateur.

---

## 17. Matrice des risques privacy

| # | Risque | Probabilité | Impact | Criticité | Mitigation existante | Recommandation |
|---|--------|-------------|--------|-----------|---------------------|----------------|
| R1 | Dump DB → totp_secret en clair | Faible | Très élevé | 🔴 Critique | Accès DB protégé | Chiffrement AES-256-GCM |
| R2 | Dump DB → refresh tokens en clair | Faible | Très élevé | 🔴 Critique | Accès DB protégé | Hachage SHA-256 (cohérence OTP) |
| R3 | AuditLog sans rétention → profilage comportemental | Élevée | Élevé | 🔴 Critique | Aucune | Purge automatique configurable |
| R4 | OAuth account takeover (email non vérifié) | Faible | Élevé | 🟠 Élevé | email_verified Google/MS | `SOCIAL_REQUIRE_VERIFIED_EMAIL` |
| R5 | Données OAuth figées → inexactitude RGPD Art. 5.1.d | Élevée | Moyen | 🟠 Élevé | Aucune | Rafraîchissement au login |
| R6 | Transferts internationaux sans DPA | Variable | Élevé | 🟠 Élevé | Documentation à créer | Guide DPA par provider |
| R7 | Export RGPD incomplet (Art. 15/20) | Certaine | Moyen | 🟡 Moyen | Export partiel fourni | Extension de l'export |
| R8 | Payload AIRS contenant des données non contrôlées | Moyenne | Variable | 🟡 Moyen | TTL 10 min | Purge auto + documentation |
| R9 | Prompt trace ID → croisement PII avec logs LLM | Faible | Moyen | 🟡 Moyen | UUID opaque recommandé | Documentation obligatoire |
| R10 | Tokens non révoqués à la suppression | Très faible | Moyen | 🟡 Moyen | is_active = False bloque | Révocation explicite recommandée |
| R11 | JWT dans logs infrastructure | Moyenne | Faible | 🟢 Faible | Payload minimal | Documentation nginx |
| R12 | Déconnexion forcée sans notification (session limit) | Élevée | Faible | 🟢 Faible | Configurable | Signal Django recommandé |

---

## 18. Plan de remédiation priorisé

### 🔴 P0 — Blocants pour publication v1.0 (avant release)

| # | Action | Effort | Responsable |
|---|--------|--------|-------------|
| A1 | Implémenter le hachage SHA-256 des `refresh_tokens` (cohérence architecturale avec OTP) | Moyen | Tenxyte |
| A2 | Implémenter le chiffrement AES-256-GCM du `totp_secret` (clé applicative dédiée) | Moyen | Tenxyte |
| A3 | Implémenter la purge automatique des `AuditLog` et `LoginAttempt` (tâches Celery + settings de rétention) | Moyen | Tenxyte |
| A4 | Ajouter l'option `TENXYTE_SOCIAL_REQUIRE_VERIFIED_EMAIL` pour prévenir les fusions OAuth non sécurisées | Faible | Tenxyte |
| A5 | Documenter les obligations DPA pour chaque provider tiers (guide dans la documentation) | Faible | Tenxyte |

### 🟠 P1 — Haute priorité (v1.0 ou correctif rapide)

| # | Action | Effort |
|---|--------|--------|
| A6 | Étendre l'export RGPD (`/export-user-data/`) pour inclure sessions, connexions OAuth, tentatives de login | Moyen |
| A7 | Implémenter la révocation explicite de tous les tokens actifs lors du `soft_delete()` | Faible |
| A8 | Hacher les `agent_tokens` en DB (cohérence architecturale) | Faible |
| A9 | Ajouter la purge automatique des `AgentPendingAction` expirées | Faible |
| A10 | Supprimer la limite de 100 entrées dans l'export audit logs | Très faible |

### 🟡 P2 — Recommandations (v1.1)

| # | Action | Effort |
|---|--------|--------|
| A11 | Implémenter le droit à la limitation du traitement (Art. 18) — état `is_restricted` | Élevé |
| A12 | Ajouter des signals Django sur les événements de sécurité critiques (pour notifications intégrateur) | Moyen |
| A13 | Rendre les champs OAuth demandés configurables (`SOCIAL_REQUESTED_FIELDS`) | Faible |
| A14 | Implémenter le rafraîchissement des données OAuth à la reconnexion | Moyen |
| A15 | Documenter la configuration nginx pour masquer le header `Authorization` dans les logs | Très faible |
| A16 | Ajouter `TENXYTE_PURGE_IP_ON_DELETION` pour anonymiser les IPs dans les logs après suppression | Faible |

---

## 19. Checklist de conformité — Responsabilités partagées

### Ce que Tenxyte v0.9.1.7 implémente ✅

- [x] Workflow complet de droit à l'effacement (Art. 17) avec double confirmation et période de grâce
- [x] Export de données JSON (Art. 20) — partiellement exhaustif
- [x] Anonymisation des PII lors du `soft_delete()` (email, nom, téléphone, secrets 2FA)
- [x] Conservation des `AuditLog` après suppression avec FK anonymisée (obligation légale)
- [x] Privacy by Design — minimisation à l'inscription (email OU téléphone, prénom/nom optionnels)
- [x] Chiffrement des mots de passe (bcrypt, irréversible) — conforme NIST 800-63B
- [x] k-anonymity pour la vérification HIBP — zéro PII transmise
- [x] Masquage PII dans les réponses aux agents IA (PIIRedactionMiddleware, 10 champs)
- [x] Traçabilité complète des actions sensibles (AuditLog, 30+ types d'événements)
- [x] Isolation des données multi-tenant via ContextVar (Art. 25 RGPD)
- [x] Contrôle d'accès RBAC granulaire (principe du moindre privilège)
- [x] Payload JWT minimal (UUIDs pseudo-anonymes uniquement, aucune PII nominale)
- [x] HSTS via SecurityHeadersMiddleware (chiffrement en transit)
- [x] Throttling progressif et verrouillage de compte (NIST 800-63B §5.2)
- [x] FIDO2/WebAuthn pour AAL3 (NIST 800-63B)

### Ce que l'intégrateur (responsable du traitement) doit assurer ⚠️

- [ ] **Registre des activités de traitement** (RGPD Art. 30) — documenter tous les traitements Tenxyte
- [ ] **Analyse d'impact (DPIA)** — RGPD Art. 35 si traitement à risque élevé (ex : déploiement AIRS)
- [ ] **Politique de confidentialité** complète mentionnant Tenxyte, les providers OAuth, Twilio, SendGrid
- [ ] **DPA avec chaque sous-traitant** : Google, GitHub, Microsoft, Facebook, Twilio, SendGrid
- [ ] **Encadrement des transferts internationaux** : SCCs ou DPF pour les providers US
- [ ] **Politique de rétention documentée** avec durées définies pour chaque type de log
- [ ] **Configuration des tâches de purge** (Celery Beat ou cron) une fois A3 implémenté
- [ ] **Hébergement conforme** : chiffrement au repos des disques, TLS pour les connexions DB
- [ ] **Procédure de notification de violation** (RGPD Arts. 33-34) dans les 72h
- [ ] **Base légale documentée** pour chaque traitement — test d'équilibre pour l'intérêt légitime
- [ ] **Activation du preset `robust`** en production (`TENXYTE_SHORTCUT_SECURE_MODE = 'robust'`)
- [ ] **Redis en production** pour le rate limiting multi-workers
- [ ] **Clé JWT dédiée** (`TENXYTE_JWT_SECRET_KEY` ≠ `SECRET_KEY` Django)
- [ ] **Configuration `TRUSTED_PROXIES`** pour la validation des IP derrière proxy
- [ ] **Notification des utilisateurs** lors d'événements de sécurité critiques (nouveau device, changement de mot de passe)
- [ ] **Droit à la limitation** (Art. 18) — à implémenter en attendant A11

---

*Audit réalisé le 2026-02-28 · Tenxyte v0.9.1.7 · Référentiels : RGPD 2016/679, CCPA §1798, NIST SP 800-63B, OWASP ASVS L2, SOC 2 Trust Services Criteria*

*Ce document est un audit technique de conformité. Il ne constitue pas un avis juridique. Pour toute question réglementaire spécifique, consulter un délégué à la protection des données (DPO) ou un avocat spécialisé en droit du numérique.*
