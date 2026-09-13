# RUNBOOK : Procédure de release PyPI

**Public :** mainteneurs avec accès push sur `tenxyte/tenxyte` et propriété du projet PyPI.
**Couvre :** la coupe d'une release, le flow Trusted Publishing / attestations, et la vérification
de la provenance d'un artefact publié côté consommateur. Voir `SECURITY.md` pour le processus de
release corrective en cas de vulnérabilité, et `specs/z_aud_1` (Requirement 4) pour la
justification de conception.

## 1. Checklist pré-release

- [ ] `CHANGELOG.md` a une entrée pour la version publiée (pas seulement `[Unreleased]`).
- [ ] Le `version` de `pyproject.toml` correspond à la release visée et, pour un `1.x`, le
      classifieur `Development Status :: 5 - Production/Stable` est présent (voir
      `tests/core/test_packaging.py::test_version_and_classifier_consistency`).
- [ ] La suite de tests complète est verte : `pytest tests/core/ -p no:django` et
      `pytest tests/integration/django/`.
- [ ] `docs/en/stability.md` / `docs/fr/stability.md` sont synchronisés avec `tenxyte.__all__` (le
      test de snapshot dans `tests/core/test_public_api_snapshot.py` l'impose).
- [ ] Pour une release MAJOR : le guide de migration a la section « X → Y » correspondante, et
      toute dépréciation annoncée depuis une version MINOR complète peut désormais être retirée.

## 2. Taguer la release

Les releases sont déclenchées par le push d'un tag correspondant à `v*` (voir
`.github/workflows/publish.yml` `on.push.tags`). Taguez des commits/tags **signés** :

```bash
git tag -s v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0
```

`-s` nécessite une clé de signature GPG (ou SSH) configurée pour votre identité git
(`git config user.signingkey ...`). Un tag signé permet aux consommateurs de vérifier que le tag
lui-même a été créé par un mainteneur, indépendamment des attestations côté PyPI décrites ci-dessous.

## 3. Ce qui se passe automatiquement (`publish.yml`)

Le push du tag déclenche trois jobs, dans l'ordre :

1. **`test-core`** / **`test-django`** — la suite de tests complète est rejouée sur le commit
   tagué (ceinture et bretelles en plus de la checklist pré-release ci-dessus).
2. **`publish`** — s'exécute dans l'environnement GitHub protégé `pypi` (nécessite une approbation
   manuelle d'un reviewer configuré — voir §4), construit le sdist + wheel, et publie sur PyPI via
   le **Trusted Publishing (OIDC)**. Aucun token API PyPI n'est utilisé ni stocké nulle part : le
   job déclare `permissions: id-token: write` et s'authentifie via l'identité OIDC de GitHub pour
   ce dépôt + ce workflow exacts, que PyPI a été configuré pour reconnaître (voir §4).
   `attestations: true` demande en plus des **attestations de provenance PEP 740 / Sigstore** pour
   les artefacts publiés, les liant cryptographiquement à ce run GitHub Actions précis.

Une approbation du déploiement de l'environnement `pypi` vous sera demandée dans l'interface
GitHub Actions avant que le job `publish` ne s'exécute — c'est intentionnel (voir §4).

## 4. Configuration ponctuelle (déjà réalisée ; documentée pour référence / reprise après sinistre)

Ce sont des actions manuelles, ponctuelles, sur PyPI et GitHub — pas une étape de chaque release.
Tracées comme `[MT-5]` dans `specs/z_aud_1/manual_tests.md`.

- **Trusted Publisher PyPI** : projet `tenxyte` → *Publishing* → ajouter un Trusted Publisher avec
  Owner `tenxyte`, Repository `tenxyte`, Workflow `publish.yml`, Environment `pypi`.
- **Environnement GitHub** : dépôt → *Settings → Environments* → `pypi`, avec **Required
  reviewers** (au moins un mainteneur) pour qu'une approbation manuelle soit requise à chaque
  publication.
- Aucun secret `PYPI_API_TOKEN` (ou équivalent) ne doit exister sur le dépôt — le Trusted
  Publishing le remplace entièrement. S'il en existait un avant cette configuration, le supprimer.

## 5. Vérifier la provenance d'un artefact publié (mainteneurs et consommateurs)

N'importe qui peut vérifier qu'un wheel/sdist sur PyPI a effectivement été construit par le
workflow `publish.yml` de `tenxyte/tenxyte`, et non altéré ou téléversé depuis ailleurs :

```bash
pip download tenxyte==<version> --no-deps -d /tmp/tenxyte-verify
python -m pip install pypi-attestations
python -m pypi_attestations verify pypi \
  --repository https://github.com/tenxyte/tenxyte \
  /tmp/tenxyte-verify/tenxyte-<version>-*.whl
```

Une vérification réussie confirme que l'attestation Sigstore de l'artefact remonte à un run GitHub
Actions de `publish.yml` dans `tenxyte/tenxyte`. La même commande avec
`--repository https://github.com/<un-autre-org>/<un-autre-depot>` **doit échouer** — c'est le
contrôle négatif confirmant que la vérification discrimine réellement, et n'est pas un no-op. La
page du projet PyPI (`https://pypi.org/project/tenxyte/#files`) affiche également un badge
« Verified details » / provenance sur chaque fichier pour une vérification visuelle rapide sans CLI.

## 6. Post-release

- [ ] Vérifier que la nouvelle version s'installe proprement :
      `pip install tenxyte[django]==<version>` dans un venv jetable.
- [ ] Vérifier la provenance selon §5.
- [ ] Annoncer la release (notes de release GitHub générées depuis `CHANGELOG.md` ; post
      Discussions pour tout changement visible utilisateur, ex. une version MAJOR).
- [ ] Pour une release corrective de sécurité : publier l'advisory GitHub correspondant (voir
      `SECURITY.md` « Internal Advisory-to-CVE Process ») une fois le correctif en production.

## Rollback

PyPI ne permet pas d'écraser ou de supprimer les fichiers d'une version déjà publiée. Si une
release est cassée :

1. Corriger en avant avec une nouvelle version PATCH aussi vite que possible — ne jamais tenter de
   réutiliser le numéro de version cassé.
2. Si la release est activement nuisible (ex. elle casse toutes les installations), envisager de
   **yank** (retirer) la release cassée sur PyPI (*Manage* → *Yank release*) — cela la masque de
   la résolution par défaut sans la supprimer ; les épinglages existants la résolvent toujours
   (avec un avertissement).
3. Voir `docs/fr/runbooks/rollback.md` pour la procédure générale de rollback en cas d'incident
   causé par la release en production.
