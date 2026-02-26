# Plan d'Exécution : Résolution des Problèmes de Documentation et Schémas

Ce plan définit les phases nécessaires pour corriger les erreurs rencontrées lors de l'exécution des scripts de génération de la documentation et des schémas OpenAPI.

La racine du problème vient de l'échec de la génération initiale du schéma (`openapi_schema.json`), ce qui provoque l'échec en cascade de tous les autres scripts qui en dépendent ([optimize_schemas.py](file:///C:/Users/bobop/Documents/own/tenxyte/scripts/optimize_schemas.py), [generate_postman_collection.py](file:///c:/Users/bobop/Documents/own/tenxyte/scripts/generate_postman_collection.py), [generate_docs_site.py](file:///C:/Users/bobop/Documents/own/tenxyte/scripts/generate_docs_site.py)).

## Phase 1 : Réparer la génération du schéma OpenAPI
*Cette phase réglera la majorité des erreurs bloquantes en cascade.*

### Scripts ciblés
#### [MODIFY] [scripts/validate_openapi_spec.py](file:///C:/Users/bobop/Documents/own/tenxyte/scripts/validate_openapi_spec.py)
- **Résoudre l'erreur d'import de module** (`No module named 'tenxyte.settings'`) : Mettre à jour la configuration initiale dans le script pour s'assurer que le système PYTHONPATH inclut le répertoire `src` avant d'importer l'environnement Django.
- **Résoudre l'erreur `SchemaGenerator` is not defined** : Importer explicitement la classe requise (probablement `SchemaGenerator` depuis `drf_spectacular.generators`) en haut de ce script.

> [!IMPORTANT]
> L'échec de ce script bloque complètement les autres ; il est fondamental que `openapi_schema.json` soit créé avec succès à la fin de cette phase.

## Phase 2 : Corriger le bug interne de [scripts/optimize_schemas.py](file:///C:/Users/bobop/Documents/own/tenxyte/scripts/optimize_schemas.py)
*Même si la Phase 1 résout la source, il est important que ce script gère l'absence de fichier avec grâce sans provoquer de crash.*

### Scripts ciblés
#### [MODIFY] [scripts/optimize_schemas.py](file:///C:/Users/bobop/Documents/own/tenxyte/scripts/optimize_schemas.py)
- **Résoudre le `KeyError: 'size_reduction_bytes'`** (à la ligne 462 dans [generate_recommendations()](file:///C:/Users/bobop/Documents/own/tenxyte/scripts/validate_documentation.py#254-278)). 
- S'assurer que le dictionnaire `self.stats` possède toutes les clés primaires initialisées avec des valeurs par défaut (ex: `size_reduction_bytes: 0`) dès le setup, ou sécuriser l'accès à ces clés via `.get()`.

## Phase 3 : Améliorer la couverture de la documentation API
*Cette phase vise à traiter les avertissements relevés par [validate_documentation.py](file:///C:/Users/bobop/Documents/own/tenxyte/scripts/validate_documentation.py) et ainsi atteindre un score de qualité plus élevé.*

### Scripts et Vues ciblés
#### [MODIFY] [src/tenxyte/views/user_views.py](file:///C:/Users/bobop/Documents/own/tenxyte/src/tenxyte/views/user_views.py)
- **Corriger l'avertissement multi-tenant** : S'assurer que le header tenant `X-Org-Slug` est bien documenté (probablement via un décorateur `@extend_schema` de drf-spectacular) sur les endpoints d'utilisateurs le nécessitant.

#### [MODIFY] Documentations globales/Codebase
- **Augmenter la couverture des codes d'erreur** : Ajouter des réponses documentées et des `OpenApiExample` pour les codes d'erreur HTTP manquants pointés par le rapport (400, 401, 403, 404, 409, 423, 429, 500). Cette intégration pourra se faire au niveau des exceptions personnalisées ou via une logique applicable globalement aux ViewSets.

## Phase 4 : Validation de bout en bout
Exécuter l'intégralité du workflow des scripts pour confirmer que plus aucun goulot d'étranglement ou message d'alerte critique n'apparaît.

### Commandes à vérifier
```bash
python scripts/validate_openapi_spec.py
python scripts/validate_documentation.py
python scripts/optimize_schemas.py
python scripts/generate_postman_collection.py
python scripts/generate_docs_site.py
```

## Phase 5 : Corriger le script [validate_documentation.py](file:///C:/Users/bobop/Documents/own/tenxyte/scripts/validate_documentation.py) et les erreurs restantes
*Le script de validation ne détecte pas correctement les codes d'erreur renseignés sous forme d'entiers (ex: `400: {`) ou via les constantes DRF (`status.HTTP_400_BAD_REQUEST`). Ceci engendre de fausses alertes concernant le manque de documentation pour les erreurs (400, 401, 403, etc).*

### Scripts ciblés
#### [MODIFY] [scripts/validate_documentation.py](file:///C:/Users/bobop/Documents/own/tenxyte/scripts/validate_documentation.py)
- Modifier [validate_error_documentation()](file:///C:/Users/bobop/Documents/own/tenxyte/scripts/validate_documentation.py#138-154) pour rechercher également `f"{code}:"` ou `f"HTTP_{code}"` au lieu de se limiter aux chaînes de caractères `'{code}'`.

#### [MODIFY] [src/tenxyte/docs/schemas.py](file:///c:/Users/bobop/Documents/own/tenxyte/src/tenxyte/docs/schemas.py) et Vues
- S'assurer que les codes d'erreur *réellement* manquants (comme 409, 423, 500) sont bien documentés là où c'est pertinent, afin d'atteindre 100% de couverture sur les codes d'erreurs.

## Phase 6 : Documentation des Endpoints
- Compléter de manière exhaustive [docs/endpoints.md](file:///C:/Users/bobop/Documents/own/tenxyte/docs/endpoints.md) avec toutes les requêtes et réponses JSON, pour chaque module et fonctionnalité de Tenxyte.

## Phase 7 : Remplacement dynamique du préfixe des URLs API
*La configuration sera mise à jour pour utiliser les clés de configuration modulables dans `TENXYTE_*` afin que l'utilisateur final puisse personnaliser les URLs du package.*

### Fichiers ciblés
#### [MODIFY] [src/tenxyte/conf.py](file:///C:/Users/bobop/Documents/own/tenxyte/src/tenxyte/conf.py)
- Ajouter les propriétés suivantes dans [TenxyteSettings](file:///C:/Users/bobop/Documents/own/tenxyte/src/tenxyte/conf.py#124-783) :
  - [BASE_URL](file:///C:/Users/bobop/Documents/own/tenxyte/src/tenxyte/conf.py#536-540) : Valeur par défaut `http://127.0.0.1:8000`
  - `API_VERSION` : Valeur par défaut `1`
  - `API_PREFIX` : Valeur par défaut `/api/v{self.API_VERSION}`
- L'utilisateur pourra alors définir `TENXYTE_BASE_URL`, `TENXYTE_API_VERSION`, ou `TENXYTE_API_PREFIX` dans son fichier settings de Django.

#### [MODIFY] [tests/settings.py](file:///C:/Users/bobop/Documents/own/tenxyte/tests/settings.py) (ainsi que les apps_showcase éventuelles)
- Configurer ces variables (ex: `TENXYTE_API_PREFIX = '/api/v1'`) pour tester et valider le comportement.

#### [MODIFY] [tests/urls.py](file:///C:/Users/bobop/Documents/own/tenxyte/tests/urls.py)
- Importer `auth_settings` (depuis `tenxyte.conf`) et utiliser `auth_settings.API_PREFIX` pour router `tenxyte.urls` en conservant bien le `/auth/` comme point de montage (ex: [path(f'{auth_settings.API_PREFIX.strip("/")}/auth/', include('tenxyte.urls'))](file:///C:/Users/bobop/Documents/own/tenxyte/scripts/validate_openapi_spec.py#123-131)).

#### [MODIFY] `tests/unit/` et `tests/integration/`
- Modifier nos appels codés en dur depuis `/api/v1/auth/...` vers une résolution dynamique `f"{auth_settings.API_PREFIX}/auth/..."` afin que la suite de test valide la construction des URLs.

#### [MODIFY] Docstrings (`src/tenxyte/views/`)
- Mettre à jour les documentations des vues (docstrings) pour remplacer les URLs strictes par `{API_PREFIX}/auth/...`.
