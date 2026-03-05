# RUNBOOK: Authentication Module Rollback

**Objective:** Restore the service to a stable version in less than 15 minutes in case of a broken deployment.

## 1. Preparation (Problem Identification)
- [ ] Observe the error (Consecutive failing health checks `/health` in production, rapid spikes of 5xx errors on `/auth/login`).
- [ ] Identify the last known working version (Commit hash).

## 2. Rollback Execution (Kubernetes / Docker)

### Via Kubernetes
```bash
# Identify deployment history
kubectl rollout history deployment/auth-service --namespace=production

# Restore previous revision (n-1)
kubectl rollout undo deployment/auth-service --namespace=production
```

### Via Docker Compose
```bash
# Modify the YAML image tag (in docker-compose.yml) to the previous version
docker-compose up -d --build
```

## 3. Verifications (Post-rollback)
- [ ] Verify that K8s Pods (or Docker containers) restart and reach 'Running' status.
- [ ] Manually call the health check endpoint (`curl -sf https://api.example.com/health`).
- [ ] Confirm the absence of errors via logs.
- [ ] Validate with a basic login smoke test that authentication has returned to normal.

## 4. Investigation
- [ ] Extract the logs that led to the crash (before cleanup).
- [ ] Create a high-priority incident ticket to fix the "new" unstable version.
