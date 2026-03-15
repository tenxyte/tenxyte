# Architecture Tenxyte : Noyau (Core) et Adaptateurs

Tenxyte repose sur une architecture de **Noyau Agnostique au Framework**, spécifiquement conçue selon le modèle de l'Architecture Hexagonale (également connue sous le nom de Ports et Adaptateurs). Cela garantit que la logique d'authentification et de sécurité centrale est découplée de tout framework web, base de données ou service tiers spécifique.

## Le Noyau (`tenxyte.core`)
Le Noyau contient toute la logique métier du package. Il ne sait pas si vous utilisez Django ou FastAPI, et il ne se soucie pas de savoir si vous utilisez PostgreSQL, MongoDB, Twilio ou SendGrid.

Il gère strictement :
- La génération, la signature et la vérification des jetons (JWT).
- La validation des règles RBAC, des mots de passe, des OTP et des Passkeys.
- La définition des interfaces attendues ("Ports") pour les bases de données, les caches, l'envoi d'e-mails, etc.

En ne dépendant que des bibliothèques Python standard (et d'outils minimaux comme Pydantic), le Noyau reste extrêmement stable et hautement testable.

## Les Ports (`tenxyte.ports`)
Les Ports sont des classes de base abstraites ou des protocoles qui définissent comment le Noyau s'attend à interagir avec le monde extérieur. Exemples :
- `UserRepository` : Interface pour trouver/créer des utilisateurs.
- `CacheService` : Interface pour définir/récupérer des valeurs en cache (utilisée pour la limitation de débit, la mise sur liste noire, etc.).
- `EmailService` : Interface pour l'envoi d'e-mails (ex: liens magiques).

## Les Adaptateurs (`tenxyte.adapters`)
Les Adaptateurs sont les implémentations des Ports adaptées à des technologies ou frameworks spécifiques.

### Adaptateurs de Framework Web
Tenxyte propose des "Adaptateurs primaires" (Adaptateurs de conduite) pré-construits qui enveloppent la logique centrale et exposent des points de terminaison HTTP :
- **Adaptateur Django** (`tenxyte.adapters.django`) : Se connecte aux vues, signaux, ORM et au système de cache de Django. Il préserve une compatibilité ascendante totale pour les utilisateurs des versions précédentes de Tenxyte.
- **Adaptateur FastAPI** (`tenxyte.adapters.fastapi`) : Se connecte aux routeurs FastAPI et à l'injection de dépendances.

### Adaptateurs d'Infrastructure
Ces "Adaptateurs secondaires" (Adaptateurs pilotés) se connectent à l'infrastructure externe :
- **Bases de données** : Prises en charge via l'ORM spécifique utilisé par votre framework web (ex : intégrations Django ORM).
- **Communication** : Implémentations telles que `DjangoEmailService` (utilisant `django.core.mail`), `ConsoleEmailService` (pour le développement) ou des adaptateurs personnalisés que vous écrivez vous-même.

## Avantages
1. **Portabilité du Framework** : Passez de Django à FastAPI (ou d'autres à l'avenir) tout en utilisant exactement la même logique métier d'authentification.
2. **Zéro rupture de compatibilité** : Pour les utilisateurs Django existants, l'Adaptateur Django conserve exactement les mêmes points de terminaison, modèles et paramètres qu'auparavant.
3. **Extensibilité facile** : Vous pouvez facilement remplacer le service de cache ou d'e-mail en écrivant une seule petite classe d'adaptateur qui implémente le port correspondant, sans modifier le code d'authentification interne.
