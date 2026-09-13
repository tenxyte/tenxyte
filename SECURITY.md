# Security Policy

Tenxyte is an authentication and access-control library. We take its security seriously and
welcome responsible disclosure from the community.

## Supported Versions

| Version | Supported |
|---|---|
| 1.0.x | ✅ Fully supported |
| 0.9.x | ⚠️ Critical fixes only, for 6 months after the 1.0.0 release |
| < 0.9 | ❌ Not supported |

Once the 6-month window for 0.9.x critical fixes closes, all users are expected to have upgraded
to `1.0.x`. Security fixes for `0.9.x` during that window are limited to **critical** severity
issues (see severity definitions below); high/medium/low issues found in `0.9.x` are fixed in
`1.0.x` only.

## Reporting a Vulnerability

**Do not open a public GitHub issue for a security vulnerability.** Public issues are for bugs and
feature requests only, and disclosing a vulnerability there puts every Tenxyte user at risk before
a fix exists.

Report vulnerabilities exclusively through **[GitHub Private Vulnerability Reporting](https://github.com/tenxyte/tenxyte/security/advisories/new)**
(repository → **Security** tab → **Report a vulnerability**). This opens a private advisory visible
only to you and the maintainers, with its own discussion thread.

If you believe Private Vulnerability Reporting is unavailable for any reason, do not fall back to
a public channel — wait and retry, or check the repository's Security tab for an alternative
contact method that may be listed there at that time.

### What to include

- A description of the vulnerability and its impact.
- Steps to reproduce, or a minimal proof-of-concept (code, request, or config).
- The affected version(s) and, if known, the affected module/function.
- Your assessment of severity (optional — we triage independently).

## Response SLA

| Milestone | Target |
|---|---|
| Acknowledgment of report | Within **72 hours** |
| Triage (severity assigned, scope confirmed) | Within **7 days** |
| Fix — Critical severity | Within **14 days** |
| Fix — High severity | Within **30 days** |
| Fix — Medium / Low severity | Within **90 days** |

Severity is assessed using [CVSS 3.1](https://www.first.org/cvss/calculator/3.1) as a guideline,
adjusted for real-world exploitability in a typical Tenxyte deployment (e.g. authentication bypass
or privilege escalation reachable without prior credentials is Critical; an issue requiring an
already-authenticated malicious admin is generally High or below).

These targets are for the availability of a fix (patch release or documented mitigation), not
necessarily a merged commit — coordination with the reporter and downstream release timing may
shift the exact publication date within the embargo below.

## Coordinated Disclosure

We follow a coordinated-disclosure model with an embargo of **at most 90 days** from the initial
report, or until a fix is released and users have had a reasonable window to upgrade — whichever
comes first, at the maintainers' discretion in consultation with the reporter. We will:

- Keep the reporter informed of progress throughout triage and remediation.
- Credit the reporter (by name or handle, or anonymously if preferred) in the published advisory
  and the CHANGELOG entry for the fix, unless the reporter asks not to be credited.
- Request a CVE via GitHub's advisory workflow for issues that warrant one, and publish the
  advisory once a fix is available.

We ask reporters to honor the same embargo and not disclose publicly (blog posts, social media,
public issues, conference talks) before the advisory is published or the embargo expires.

## Scope

**In scope:**

- Vulnerabilities in Tenxyte's own code: `tenxyte.core`, `tenxyte.ports`, the Django and FastAPI
  adapters, views, serializers, services, models, migrations, and management commands.
- Vulnerabilities introduced by how Tenxyte *uses* a third-party dependency (e.g. an insecure
  default, a missing signature check, an unvalidated redirect), even if the dependency itself is
  not at fault.
- Coordinated version pinning fixes when a Tenxyte dependency has a known vulnerability that
  affects Tenxyte's usage of it.

**Out of scope:**

- Vulnerabilities that exist exclusively within a third-party dependency's own code, with no
  Tenxyte-specific exposure — report these upstream to the dependency's maintainers.
- Vulnerabilities requiring physical access to a user's device, a compromised OS, or a compromised
  dependency supply chain outside of Tenxyte's own release process.
- Denial-of-service reports based purely on resource exhaustion from a deliberately misconfigured
  deployment (e.g. rate limiting explicitly disabled via `TENXYTE_RATE_LIMITING_ENABLED = False`).
- Social engineering, or reports without a credible technical vector.

## Internal Advisory-to-CVE Process

For maintainers, the internal workflow from report to public advisory is:

1. **Intake** — a GitHub draft security advisory is opened from the private report (or created
   directly by a maintainer for internally-found issues).
2. **Triage** — severity assessed, affected versions confirmed, reporter notified (within the
   72-hour SLA above).
3. **Private fix** — the fix is developed on a private fork/branch associated with the draft
   advisory, never on a public branch, to avoid disclosing the vulnerability before release.
4. **Patch release** — the fix ships in a new patch (or minor) release across all supported
   version lines (`1.0.x`, and `0.9.x` if critical and within the support window).
5. **Advisory publication** — the draft advisory is published, referencing the fixed version(s)
   and crediting the reporter.
6. **CVE request** — a CVE identifier is requested via GitHub's advisory workflow (GitHub is a CVE
   Numbering Authority) at publication time.

## Security-Relevant Documentation

- [Threat model](docs/security-audit/threat-model.md) — protected assets, threat actors, and
  attack surfaces per domain.
- [Audit scope](docs/security-audit/audit-scope.md) — the perimeter proposed to external security
  auditors.
- [Pre-audit checklist](docs/security-audit/pre-audit-checklist.md) — our OWASP ASVS L2
  self-assessment.
- [Stability contract](docs/en/stability.md) — what is covered by our compatibility and support
  guarantees.
- [Security guide](docs/en/security.md) — security features and configuration guidance for
  integrators (account lockout, breach checking, security headers, etc.).

## Questions

For questions about this policy that are **not** a vulnerability report, open a regular
[GitHub Discussion](https://github.com/tenxyte/tenxyte/discussions).
