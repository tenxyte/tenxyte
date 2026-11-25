# Politique de stabilité d'API et de versionnement

Ce document est le **contrat de stabilité** de Tenxyte : il définit précisément ce qui est couvert
par notre garantie de compatibilité ascendante (la **surface d'API publique**), la politique de
versionnement qui régit ses évolutions, et ce qui est explicitement exclu de cette garantie.

Si un élément n'est pas listé ici, considérez-le comme un détail d'implémentation pouvant changer
dans une version MINOR ou PATCH sans préavis.

## Politique SemVer

Tenxyte suit le [Semantic Versioning 2.0.0](https://semver.org/) appliqué à la surface d'API
publique définie ci-dessous :

- **MAJOR** (`X.0.0`) — peut contenir des changements incompatibles (breaking) sur la surface
  d'API publique. Les breaking changes ne sont publiés que dans une version MAJOR.
- **MINOR** (`1.X.0`) — changements additifs uniquement : nouveaux endpoints, nouveaux réglages,
  nouveaux paramètres optionnels, nouveaux décorateurs, nouveaux symboles exportés. Le
  comportement existant est préservé.
- **PATCH** (`1.0.X`) — correctifs de bugs et de sécurité qui ne modifient pas le contrat
  documenté (un correctif qui aligne le comportement sur sa documentation est un PATCH, même s'il
  change un comportement observable qui était auparavant non documenté ou contredisait la doc).

## Politique de dépréciation

Aucun élément de la surface d'API publique n'est retiré sans passer par ce cycle :

1. L'élément est marqué déprécié dans sa docstring/documentation et un `DeprecationWarning` est
   émis au point d'usage pertinent (import, appel de fonction, ou accès au réglage) à partir d'une
   version MINOR.
2. L'élément déprécié reste pleinement fonctionnel pendant **au moins une version MINOR
   complète** après l'introduction de l'avertissement.
3. Le retrait n'intervient que dans la version MAJOR suivante, et est listé dans la section
   « Removed » du CHANGELOG de cette version MAJOR.

Exemple : si un réglage est déprécié en `1.3.0`, il reste fonctionnel sur toute la ligne `1.x` et
ne peut être retiré qu'en `2.0.0`.

## Surface d'API publique

La surface d'API publique se compose exactement des six catégories suivantes.

### 1. Endpoints HTTP

Chaque endpoint documenté dans [`endpoints.md`](endpoints.md) — son chemin, sa méthode HTTP, les
champs de requête, la forme de la réponse et les codes de statut — est couvert. `endpoints.md` est
la source normative et exhaustive ; ce document ne la duplique pas. Au niveau catégorie, cela
inclut : inscription et connexion (email/téléphone), rafraîchissement/déconnexion de token,
connexion sociale (multi-provider), connexion OTP sans mot de passe, magic links, gestion du mot
de passe, 2FA (TOTP), RBAC (rôles/permissions/assignations utilisateur), organisations
(multi-tenant B2B), gestion des applications, et les endpoints de tokens agent AIRS.

Les endpoints non documentés, les champs de réponse non documentés, et les endpoints
internes/admin non listés dans `endpoints.md` ne sont **pas** couverts.

### 2. Réglages (`TENXYTE_*`)

Chaque réglage documenté dans [`settings.md`](settings.md) — son nom, sa valeur par défaut et son
type/valeurs acceptés — est couvert, y compris les presets `TENXYTE_SHORTCUT_SECURE_MODE` et
chaque réglage qu'ils résolvent. `settings.md` est la source normative et exhaustive.

Les réglages non listés dans `settings.md`, ainsi que les *valeurs par défaut numériques/
comportementales précises choisies à l'intérieur* d'un preset `TENXYTE_SHORTCUT_SECURE_MODE` pour
un réglage que le preset ne documente pas individuellement, sont des détails d'implémentation du
preset et peuvent être ajustés dans une version MINOR pour améliorer la posture de sécurité de ce
preset.

### 3. Modèles abstraits

Les classes de base abstraites suivantes, exportées depuis `tenxyte.models`, et leurs champs
actuellement documentés :

- `AbstractUser`
- `AbstractRole`
- `AbstractPermission`
- `AbstractApplication`

Hériter de ces classes et surcharger `TENXYTE_USER_MODEL` / `TENXYTE_ROLE_MODEL` /
`TENXYTE_PERMISSION_MODEL` / `TENXYTE_APPLICATION_MODEL` est un motif d'intégration couvert et
supporté. Les modèles concrets (non abstraits) internes (ex : `RefreshToken`, `AuditLog`,
`SocialConnection`) et leur structure de champs interne ne font **pas** partie de la surface d'API
publique au-delà de ce qui est accessible via les endpoints documentés — ils peuvent gagner des
champs dans une version MINOR.

### 4. Décorateurs publics

Exportés depuis `tenxyte.decorators` :

`require_jwt`, `require_verified_email`, `require_verified_phone`, `rate_limit`, `require_role`,
`require_any_role`, `require_all_roles`, `require_permission`, `require_any_permission`,
`require_all_permissions`, `require_org_context`, `require_org_membership`, `require_org_role`,
`require_org_permission`, `require_org_owner`, `require_org_admin`, `require_agent_clearance`, et
l'utilitaire `get_client_ip`.

Leurs signatures, les exceptions/réponses produites en cas d'échec, et leur comportement documenté
sont couverts.

### 5. Exports de `tenxyte/__init__.py` et `tenxyte.core`

**Niveau racine (`import tenxyte`)** — toujours importable, avec ou sans Django installé :

- `tenxyte.__version__`

**Symboles racine dépendants de Django** — résolus paresseusement ; importables et utilisables une
fois `tenxyte[django]` installé, et levant `TenxyteMissingDependencyError` (une sous-classe
d'`ImportError`) avec un message explicite `pip install tenxyte[django]` sinon :

- `tenxyte.setup`
- `tenxyte.AbstractUser`, `tenxyte.AbstractRole`, `tenxyte.AbstractPermission`,
  `tenxyte.AbstractApplication`
- `tenxyte.get_user_model`, `tenxyte.get_role_model`, `tenxyte.get_permission_model`,
  `tenxyte.get_application_model`

**`tenxyte.core` (`tenxyte.core.__all__`)** — la couche Core framework-agnostique, toujours
importable quel que soit l'adaptateur framework installé. L'ensemble exact des symboles est celui
listé par `tenxyte.core.__all__` à la version courante (`Settings`, `JWTService`, `TOTPService`,
`WebAuthnService`, `MagicLinkService`, `EmailService`, `CacheService`, `TaskService`, et leurs
classes de données/schémas associés). Les ajouts à cette liste sont des changements MINOR ;
l'agencement interne des modules de `tenxyte.core` (quel fichier `.py` définit quel symbole)
n'est **pas** couvert — importez depuis `tenxyte.core` directement, pas depuis un sous-module
spécifique, pour rester dans le contrat.

### 6. Format de réponse d'erreur

Chaque réponse d'erreur retournée par un endpoint documenté suit cette forme :

```json
{
  "error": "Message lisible par un humain",
  "code": "CODE_MACHINE",
  "details": {}
}
```

`error` et `code` sont toujours des chaînes présentes ; `details` est toujours présent et est un
objet (vide `{}` s'il n'y a rien à ajouter, ou une map d'erreurs de validation indexée par champ).
Le libellé exact des messages `error` n'est **pas** couvert (peut être reformulé dans un PATCH) ;
la présence des trois clés, leurs types, et les valeurs `code` documentées pour un endpoint donné
**sont** couvertes.

## Ce qui n'est PAS couvert

Les éléments suivants sont explicitement exclus de la garantie de stabilité et peuvent changer
dans n'importe quelle version, y compris PATCH :

- Tout module, fonction, classe ou attribut dont le nom commence par un underscore (`_`), à tout
  niveau du package (ex : `tenxyte._internal`, `SomeClass._helper`).
- Les helpers et fixtures de tests internes sous `tests/`.
- Le comportement non documenté — c'est-à-dire tout ce qui n'est pas énoncé dans `endpoints.md`,
  `settings.md`, ce document, ou la docstring d'un symbole listé ci-dessus. Si le code fait
  quelque chose que la doc ne décrit pas, la doc (et cette liste) fait foi, pas le comportement
  accidentel.
- L'agencement interne des modules de `tenxyte.core` (voir §5 ci-dessus).
- Les internes des modèles concrets (non abstraits) au-delà des champs visibles via les endpoints
  documentés.
- Les noms/numérotation des fichiers de migration de base de données (le schéma résultant,
  accessible via les modèles documentés, est couvert ; la mécanique d'historique des migrations ne
  l'est pas).
- Le formatage de sortie CLI des commandes de management (`tenxyte_quickstart`, `tenxyte_seed`,
  `tenxyte_cleanup`, `tenxyte_purge_audit_logs`) au-delà de leurs codes de sortie et effets
  documentés.
- Le texte des messages de log et les noms des loggers.

## Vérification de ce contrat

L'ensemble des symboles de la catégorie 5 ci-dessus est vérifié par un test de snapshot automatisé
(`tests/core/test_public_api_snapshot.py`) qui fait échouer le build si un symbole public
précédemment exporté par `tenxyte/__init__.py` disparaît sans passer par le cycle de dépréciation.

## Voir aussi

- [`endpoints.md`](endpoints.md) — référence complète de l'API HTTP.
- [`settings.md`](settings.md) — référence complète des réglages.
- [`SECURITY.md`](../../SECURITY.md) — politique de divulgation de vulnérabilités et versions
  supportées.
- [`MIGRATION_GUIDE.md`](MIGRATION_GUIDE.md) — instructions de migration de version à version, y
  compris le changement de packaging `0.9 → 1.0`.
