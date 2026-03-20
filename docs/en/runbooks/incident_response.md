# RUNBOOK: Suspected Auth Module Compromise

**Level:** CRITICAL — IMMEDIATE RESPONSE

## 1. Detection & Containment (T+0)
- [ ] Confirm the anomaly via metrics (Prometheus/Grafana) and structured JSON logs.
- [ ] Alert security team members (e.g., on a dedicated Slack/Teams channel).
- [ ] Block suspicious IP addresses at the WAF / Firewall level.
- [ ] (Optional) Switch the authentication API to maintenance mode (503 Code).

## 2. Assessment (T+15m)
- [ ] Identify the source and time of the first event (Attack Vector).
- [ ] Identify potentially compromised accounts, JWT keys, or data.
- [ ] Evaluate the need to trigger a partial shutdown.

## 3. Remediation (T+30m)
- [ ] Immediately rotate all compromised secrets (JWT private keys, Database).
- [ ] Invalidate all active user sessions (Clear JWT Refresh Tokens).
- [ ] Apply code fix if possible.
- [ ] Restore from the last known healthy backup if the database has been tampered with.

## 4. Communication & Resilience (T+2h)
- [ ] Inform impacted customers (under GDPR regulations, within 72 hours max).
- [ ] Draft and send a status report to management.

## 5. Post-mortem
- [ ] Organize a Post-Mortem within 5 business days with all stakeholders.
- [ ] Update detection scripts and this runbook.
