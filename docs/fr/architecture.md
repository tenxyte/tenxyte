# Architecture Tenxyte : Noyau (Core) et Adaptateurs

Tenxyte repose sur une architecture de **Noyau Agnostique au Framework**, spécifiquement conçue selon le modèle de l'Architecture Hexagonale (également connue sous le nom de Ports et Adaptateurs). Cela garantit que la logique d'authentification et de sécurité centrale est découplée de tout framework web, base de données ou service tiers spécifique.

---

## Vue d'ensemble des couches

```
┌─────────────────────────────────────────────────────────────┐
│                     HTTP / WebSocket                        │
├─────────────────────────────────────────────────────────────┤
│  views/          │  middleware/       │  serializers/        │
│  (endpoints)     │  (AIRS, PII,       │  (validation DRF)    │
│                  │   tenant, auth)    │                      │
├─────────────────────────────────────────────────────────────┤
│  services/       │  decorators.py     │  conf/               │
│  (AgentToken,    │  (@require_perm,   │  (auth, jwt, airs,   │
│   logique métier)│   @require_agent)  │   org settings)      │
├──────────────────┴───────────────────┴──────────────────────┤
│                     tenxyte.core                            │
│  jwt_service · totp_service · webauthn_service              │
│  magic_link_service · cache_service · email_service         │
│  session_service · schemas · settings                       │
├─────────────────────────────────────────────────────────────┤
│                     tenxyte.ports                           │
│  UserRepository · OrganizationRepository · RoleRepository   │
│  AuditLogRepository · EmailService · CacheService           │
├─────────────────────────────────────────────────────────────┤
│                     tenxyte.adapters                        │
│  adapters/django/  │  adapters/fastapi/                     │
│  (ORM, cache,      │  (routers, models,                     │
│   email, TOTP,     │   repositories)                        │
│   WebAuthn)        │                                        │
├─────────────────────────────────────────────────────────────┤
│  Django ORM / PostgreSQL │ django.core.cache │ SMTP / SES   │
└─────────────────────────────────────────────────────────────┘
```

---

## Le Noyau (`tenxyte.core`)

Le Noyau contient toute la logique métier du package. Il ne sait pas si vous utilisez Django ou FastAPI, et il ne se soucie pas de savoir si vous utilisez PostgreSQL, MongoDB, Twilio ou SendGrid.

Il gère strictement :
- La génération, la signature et la vérification des jetons (`JWTService`).
- La 2FA TOTP : configuration, vérification et codes de secours (`TOTPService`).
- L'enregistrement et l'authentification WebAuthn/Passkey (`WebAuthnService`).
- La connexion sans mot de passe via liens magiques (`MagicLinkService`).
- Les abstractions de cache et les fallbacks en mémoire (`CacheService`, `InMemoryCacheService`).
- Les abstractions d'envoi d'e-mails (`EmailService`, `ConsoleEmailService`).
- La gestion du cycle de vie des sessions (`SessionService`).
- Les schémas Pydantic pour les données utilisateur, organisation et jetons (`schemas`).

En ne dépendant que des bibliothèques Python standard (et d'outils minimaux comme Pydantic), le Noyau reste extrêmement stable et hautement testable.

---

## Les Ports (`tenxyte.ports`)

Les Ports sont des classes de base abstraites ou des protocoles qui définissent comment le Noyau s'attend à interagir avec le monde extérieur.

### Ports de Dépôt (ABC)

| Port | Responsabilité |
|---|---|
| `UserRepository` | Opérations CRUD sur les utilisateurs, secrets MFA, vérification d'email |
| `OrganizationRepository` | CRUD des organisations, gestion des membres, traversée hiérarchique |
| `RoleRepository` | CRUD des rôles, assignation utilisateur-rôle, rôles par organisation |
| `AuditLogRepository` | Création de journaux d'audit, requêtes par utilisateur/org/ressource, nettoyage |

### Ports de Service (Protocol)

| Port | Responsabilité |
|---|---|
| `CacheService` | Get/set/delete des valeurs en cache, gestion de la liste noire des jetons |
| `EmailService` | Envoi d'e-mails, liens magiques et codes 2FA |

---

## Les Adaptateurs (`tenxyte.adapters`)

Les Adaptateurs sont les implémentations des Ports adaptées à des technologies ou frameworks spécifiques.

### Adaptateurs de Framework Web

Tenxyte propose des « Adaptateurs primaires » (Adaptateurs de conduite) pré-construits qui enveloppent la logique centrale et exposent des points de terminaison HTTP :

| Adaptateur | Module | Composants |
|---|---|---|
| **Django** | `tenxyte.adapters.django` | Dépôts ORM, `DjangoCacheService`, `DjangoEmailService`, stockage TOTP/WebAuthn, fournisseur de paramètres, middleware |
| **FastAPI** | `tenxyte.adapters.fastapi` | Modèles SQLAlchemy, dépôts, routeurs, service de tâches |

### Adaptateurs d'Infrastructure

Ces « Adaptateurs secondaires » (Adaptateurs pilotés) se connectent à l'infrastructure externe :
- **Bases de données** : Prises en charge via l'ORM spécifique utilisé par votre framework web (ex : intégrations Django ORM).
- **Communication** : Implémentations telles que `DjangoEmailService` (utilisant `django.core.mail`), `ConsoleEmailService` (pour le développement) ou des adaptateurs personnalisés que vous écrivez vous-même.

---

## Couches de Support

Au-delà du noyau hexagonal, Tenxyte inclut plusieurs couches de support :

| Couche | Chemin | Objectif |
|---|---|---|
| **Configuration** | `tenxyte.conf` | Mixins de paramètres modulaires (`auth`, `jwt`, `airs`, `org`) avec fallback `_get()` vers les settings Django |
| **Services** | `tenxyte.services` | Services métier de haut niveau (ex : `AgentTokenService` pour le cycle de vie des jetons AIRS) |
| **Middleware** | `tenxyte.middleware` | Traitement des requêtes : disjoncteur AIRS, caviardage PII, contexte tenant, authentification application |
| **Tâches** | `tenxyte.tasks` | Maintenance périodique : nettoyage des jetons, purge de la liste noire, traitement des suppressions expirées |
| **Sérialiseurs** | `tenxyte.serializers` | Couche de sérialisation DRF pour la validation des requêtes et le formatage des réponses |
| **Décorateurs** | `tenxyte.decorators` | Gardes de permission (`@require_permission`), autorisation d'agent (`@require_agent_clearance`) |

---

## Avantages

1. **Portabilité du Framework** : Passez de Django à FastAPI (ou d'autres à l'avenir) tout en utilisant exactement la même logique métier d'authentification.
2. **Zéro rupture de compatibilité** : Pour les utilisateurs Django existants, l'Adaptateur Django conserve exactement les mêmes points de terminaison, modèles et paramètres qu'auparavant.
3. **Extensibilité facile** : Vous pouvez facilement remplacer le service de cache ou d'e-mail en écrivant une seule petite classe d'adaptateur qui implémente le port correspondant, sans modifier le code d'authentification interne.
4. **Testabilité** : Le Noyau peut être testé en isolation complète de tout framework web grâce aux implémentations en mémoire (`InMemoryCacheService`, `ConsoleEmailService`).
