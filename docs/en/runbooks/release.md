# RUNBOOK: PyPI Release Procedure

**Audience:** maintainers with push access to `tenxyte/tenxyte` and PyPI project ownership.
**Covers:** cutting a release, the Trusted Publishing / attestation flow, and how consumers verify
a published artifact's provenance. See `SECURITY.md` for the vulnerability-driven patch-release
process, and `specs/z_aud_1` (Requirement 4) for the design rationale.

## 1. Pre-release checklist

- [ ] `CHANGELOG.md` has an entry for the version being released (not just `[Unreleased]`).
- [ ] `pyproject.toml` `version` matches the intended release and, for `1.x`, the
      `Development Status :: 5 - Production/Stable` classifier is present (see
      `tests/core/test_packaging.py::test_version_and_classifier_consistency`).
- [ ] Full test suite is green: `pytest tests/core/ -p no:django` and
      `pytest tests/integration/django/`.
- [ ] `docs/en/stability.md` / `docs/fr/stability.md` are in sync with `tenxyte.__all__` (the
      snapshot test in `tests/core/test_public_api_snapshot.py` enforces this).
- [ ] For a MAJOR release: the migration guide has the relevant "X → Y" section, and any
      deprecation announced a full MINOR version ago is now safe to remove.

## 2. Tag the release

Releases are triggered by pushing a tag matching `v*` (see `.github/workflows/publish.yml`
`on.push.tags`). Tag **signed** commits/tags:

```bash
git tag -s v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0
```

`-s` requires a GPG (or SSH) signing key configured for your git identity
(`git config user.signingkey ...`). A signed tag lets consumers verify the tag itself was created
by a maintainer, independent of the PyPI-side attestations described below.

## 3. What happens automatically (`publish.yml`)

Pushing the tag triggers three jobs, in order:

1. **`test-core`** / **`test-django`** — the full test suite runs again against the tagged commit
   (belt-and-braces on top of the pre-release checklist above).
2. **`publish`** — runs in the protected `pypi` GitHub Environment (requires manual approval from
   a configured reviewer — see §4), builds the sdist + wheel, and publishes to PyPI via **Trusted
   Publishing (OIDC)**. No PyPI API token is used or stored anywhere: the job declares
   `permissions: id-token: write` and authenticates using GitHub's OIDC identity for this exact
   repository + workflow, which PyPI has been configured to trust (see §4). `attestations: true`
   additionally requests **PEP 740 / Sigstore provenance attestations** for the published
   artifacts, cryptographically linking them to this GitHub Actions run.

You will be prompted to approve the `pypi` environment's deployment in the GitHub Actions UI
before the `publish` job runs — this is intentional (see §4).

## 4. One-time setup (already done; documented for reference / disaster recovery)

These are manual, one-time actions on PyPI and GitHub — not part of every release. Tracked as
`[MT-5]` in `specs/z_aud_1/manual_tests.md`.

- **PyPI Trusted Publisher**: project `tenxyte` → *Publishing* → add a Trusted Publisher with
  Owner `tenxyte`, Repository `tenxyte`, Workflow `publish.yml`, Environment `pypi`.
- **GitHub Environment**: repo → *Settings → Environments* → `pypi`, with **Required reviewers**
  (at least one maintainer) so every publish needs a manual approval click.
- No `PYPI_API_TOKEN` (or equivalent) secret should exist on the repository — Trusted Publishing
  replaces it entirely. If one exists from before this setup, delete it.

## 5. Verifying a published artifact's provenance (for maintainers and consumers)

Anyone can verify that a wheel/sdist on PyPI was actually built by the `publish.yml` workflow in
`tenxyte/tenxyte`, and not tampered with or uploaded from elsewhere:

```bash
pip download tenxyte==<version> --no-deps -d /tmp/tenxyte-verify
python -m pip install pypi-attestations
python -m pypi_attestations verify pypi \
  --repository https://github.com/tenxyte/tenxyte \
  /tmp/tenxyte-verify/tenxyte-<version>-*.whl
```

A successful verification confirms the artifact's Sigstore attestation traces back to a GitHub
Actions run of `publish.yml` in `tenxyte/tenxyte`. Running the same command with
`--repository https://github.com/<some-other-org>/<some-other-repo>` **must fail** — that is the
negative control confirming the check is actually discriminating, not a no-op. The PyPI project
page (`https://pypi.org/project/tenxyte/#files`) also surfaces a "Verified details" / provenance
badge on each file for a quick visual check without the CLI.

## 6. Post-release

- [ ] Verify the new version installs cleanly: `pip install tenxyte[django]==<version>` in a
      throwaway venv.
- [ ] Verify provenance per §5.
- [ ] Announce the release (GitHub Release notes generated from `CHANGELOG.md`; Discussions post
      for anything user-facing, e.g. a MAJOR version).
- [ ] For a security-fix release: publish the corresponding GitHub Security Advisory (see
      `SECURITY.md` "Internal Advisory-to-CVE Process") once the fix is live.

## Rollback

PyPI does not allow overwriting or deleting a published version's files in place. If a release is
broken:

1. Fix forward with a new PATCH version as fast as possible — do not attempt to reuse the broken
   version number.
2. If the release is actively harmful (e.g. it broke installs entirely), `pip install`s a version
   that is not yanked, so consider **yanking** the broken release on PyPI (*Manage* → *Yank
   release*) — this hides it from default resolution without deleting it, and existing pins still
   resolve it (with a warning).
3. See `docs/en/runbooks/rollback.md` for the general incident-rollback procedure if the release
   caused a production incident downstream.
