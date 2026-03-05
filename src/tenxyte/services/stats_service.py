"""
Stats aggregation service for dashboard endpoints.

Provides cross-model aggregate queries for admin dashboards.
"""

from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from ..models import (
    get_user_model,
    AuditLog,
    BlacklistedToken,
    RefreshToken,
    LoginAttempt,
    AccountDeletionRequest,
)

User = get_user_model()


class StatsService:
    """Centralized statistics aggregation."""

    # =========================================================================
    # Global Dashboard
    # =========================================================================

    def get_global_stats(self):
        """GET /dashboard/stats/ — cross-module summary."""
        return {
            "users": self._user_stats(),
            "auth": self._auth_summary(),
            "applications": self._application_stats(),
            "security": self._security_summary(),
            "gdpr": self._gdpr_summary(),
        }

    # =========================================================================
    # User Stats
    # =========================================================================

    def _user_stats(self):
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        qs = User.objects.all()
        agg = qs.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(is_active=True)),
            locked=Count("id", filter=Q(is_locked=True)),
            banned=Count("id", filter=Q(is_banned=True)),
            deleted=Count("id", filter=Q(is_deleted=True)),
            verified_email=Count("id", filter=Q(is_email_verified=True)),
            verified_phone=Count("id", filter=Q(is_phone_verified=True)),
            with_2fa=Count("id", filter=Q(is_2fa_enabled=True)),
            new_today=Count("id", filter=Q(created_at__gte=today)),
            new_this_week=Count("id", filter=Q(created_at__gte=week_ago)),
            new_this_month=Count("id", filter=Q(created_at__gte=month_ago)),
        )
        return agg

    # =========================================================================
    # Auth Stats
    # =========================================================================

    def get_auth_stats(self):
        """GET /dashboard/auth/ — detailed auth metrics."""
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        return {
            "login_stats": {
                "today": self._login_period_stats(today),
                "this_week": self._login_period_stats(week_ago),
                "this_month": self._login_period_stats(month_ago),
            },
            "login_by_method": self._login_by_method(today),
            "registration_stats": {
                "today": User.objects.filter(created_at__gte=today).count(),
                "this_week": User.objects.filter(created_at__gte=week_ago).count(),
                "this_month": User.objects.filter(created_at__gte=month_ago).count(),
            },
            "token_stats": self._token_stats(today),
            "top_login_failure_reasons": self._top_failure_reasons(month_ago),
            "charts": {
                "logins_per_day_7d": self._logins_per_day(7),
            },
        }

    def _login_period_stats(self, since):
        agg = LoginAttempt.objects.filter(created_at__gte=since).aggregate(
            total=Count("id"),
            success_count=Count("id", filter=Q(success=True)),
            failed_count=Count("id", filter=Q(success=False)),
        )
        return {
            "total": agg["total"],
            "success": agg["success_count"],
            "failed": agg["failed_count"],
        }

    def _login_by_method(self, since):
        """Count logins by action type from audit logs."""
        methods = (
            AuditLog.objects.filter(action="login", created_at__gte=since)
            .values("details__method")
            .annotate(count=Count("id"))
        )
        result = {}
        for entry in methods:
            method = entry.get("details__method") or "unknown"
            result[method] = entry["count"]

        # Fallback if no method detail — just count total logins
        if not result:
            result["total"] = AuditLog.objects.filter(action="login", created_at__gte=since).count()
        return result

    def _token_stats(self, today):
        now = timezone.now()
        return {
            "active_refresh_tokens": RefreshToken.objects.filter(is_revoked=False, expires_at__gt=now).count(),
            "tokens_refreshed_today": AuditLog.objects.filter(action="token_refresh", created_at__gte=today).count(),
            "tokens_revoked_today": RefreshToken.objects.filter(is_revoked=True, last_used_at__gte=today).count(),
        }

    def _top_failure_reasons(self, since, limit=5):
        reasons = (
            LoginAttempt.objects.filter(success=False, created_at__gte=since)
            .exclude(failure_reason="")
            .values("failure_reason")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit]
        )
        return [{"reason": r["failure_reason"], "count": r["count"]} for r in reasons]

    def _logins_per_day(self, days):
        from django.db.models.functions import TruncDate

        since = timezone.now() - timedelta(days=days)
        data = (
            LoginAttempt.objects.filter(created_at__gte=since)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(
                success_count=Count("id", filter=Q(success=True)),
                failed_count=Count("id", filter=Q(success=False)),
            )
            .order_by("date")
        )
        return [
            {
                "date": str(entry["date"]),
                "success": entry["success_count"],
                "failed": entry["failed_count"],
            }
            for entry in data
        ]

    # =========================================================================
    # Auth Summary (for global dashboard)
    # =========================================================================

    def _auth_summary(self):
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return {
            "total_logins_today": LoginAttempt.objects.filter(success=True, created_at__gte=today).count(),
            "failed_logins_today": LoginAttempt.objects.filter(success=False, created_at__gte=today).count(),
            "active_refresh_tokens": RefreshToken.objects.filter(is_revoked=False, expires_at__gt=now).count(),
        }

    # =========================================================================
    # Application Stats
    # =========================================================================

    def _application_stats(self):
        from ..models import Application

        return {
            "total": Application.objects.count(),
            "active": Application.objects.filter(is_active=True).count(),
        }

    # =========================================================================
    # Security Stats
    # =========================================================================

    def get_security_stats(self):
        """GET /dashboard/security/ — security metrics."""
        now = timezone.now()
        day_ago = now - timedelta(hours=24)
        week_ago = now - timedelta(days=7)

        return {
            "audit_summary_24h": self._audit_summary(day_ago),
            "blacklisted_tokens": self._blacklisted_token_stats(now),
            "suspicious_activity": {
                "last_24h": AuditLog.objects.filter(
                    action__in=["suspicious_activity", "session_limit_exceeded", "device_limit_exceeded"],
                    created_at__gte=day_ago,
                ).count(),
                "last_7d": AuditLog.objects.filter(
                    action__in=["suspicious_activity", "session_limit_exceeded", "device_limit_exceeded"],
                    created_at__gte=week_ago,
                ).count(),
                "top_ips": list(
                    AuditLog.objects.filter(
                        action__in=["login_failed", "suspicious_activity"],
                        created_at__gte=day_ago,
                    )
                    .values("ip_address")
                    .annotate(events=Count("id"))
                    .order_by("-events")[:5]
                ),
            },
            "account_security": {
                "locked_accounts": User.objects.filter(is_locked=True).count(),
                "banned_accounts": User.objects.filter(is_banned=True).count(),
                "2fa_adoption_rate": self._2fa_rate(),
                "password_changes_today": AuditLog.objects.filter(
                    action="password_change", created_at__gte=now.replace(hour=0, minute=0, second=0, microsecond=0)
                ).count(),
            },
        }

    def _security_summary(self):
        now = timezone.now()
        return {
            "blacklisted_tokens": BlacklistedToken.objects.filter(expires_at__gt=now).count(),
            "suspicious_activity_24h": AuditLog.objects.filter(
                action__in=["suspicious_activity", "session_limit_exceeded", "device_limit_exceeded"],
                created_at__gte=now - timedelta(hours=24),
            ).count(),
        }

    def _audit_summary(self, since):
        by_action = (
            AuditLog.objects.filter(created_at__gte=since)
            .values("action")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return {
            "total_events": sum(a["count"] for a in by_action),
            "by_action": {a["action"]: a["count"] for a in by_action},
        }

    def _blacklisted_token_stats(self, now):
        by_reason = BlacklistedToken.objects.filter(expires_at__gt=now).values("reason").annotate(count=Count("id"))
        return {
            "total_active": sum(r["count"] for r in by_reason),
            "by_reason": {r["reason"] or "unknown": r["count"] for r in by_reason},
            "expired_pending_cleanup": BlacklistedToken.objects.filter(expires_at__lt=now).count(),
        }

    def _2fa_rate(self):
        total = User.objects.filter(is_active=True).count()
        if total == 0:
            return 0.0
        with_2fa = User.objects.filter(is_active=True, is_2fa_enabled=True).count()
        return round((with_2fa / total) * 100, 1)

    # =========================================================================
    # GDPR Stats
    # =========================================================================

    def _gdpr_summary(self):
        """Compact GDPR summary for global dashboard."""
        now = timezone.now()
        week_ahead = now + timedelta(days=7)
        return {
            "pending": AccountDeletionRequest.objects.filter(status="pending").count(),
            "confirmed": AccountDeletionRequest.objects.filter(status="confirmed").count(),
            "expiring_7d": AccountDeletionRequest.objects.filter(
                status="confirmed",
                grace_period_ends_at__lte=week_ahead,
                grace_period_ends_at__gt=now,
            ).count(),
        }

    def get_gdpr_stats(self):
        """GET /dashboard/gdpr/ — GDPR compliance metrics."""
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_ago = today - timedelta(days=30)
        week_ahead = now + timedelta(days=7)

        by_status = AccountDeletionRequest.objects.values("status").annotate(count=Count("id"))
        status_map = {s["status"]: s["count"] for s in by_status}

        return {
            "deletion_requests": {
                "total": sum(status_map.values()),
                "by_status": status_map,
                "grace_period_expiring_7d": AccountDeletionRequest.objects.filter(
                    status="confirmed",
                    grace_period_ends_at__lte=week_ahead,
                    grace_period_ends_at__gt=now,
                ).count(),
            },
            "data_exports": {
                "total_today": AuditLog.objects.filter(action="data_exported", created_at__gte=today).count(),
                "total_this_month": AuditLog.objects.filter(action="data_exported", created_at__gte=month_ago).count(),
            },
        }

    # =========================================================================
    # Organizations Stats
    # =========================================================================

    def get_organization_stats(self):
        """GET /dashboard/organizations/ — org metrics (if enabled)."""
        from ..conf import org_settings

        if not org_settings.ORGANIZATIONS_ENABLED:
            return {"enabled": False}

        from ..models import Organization, OrganizationMembership

        total = Organization.objects.count()
        active = Organization.objects.filter(is_active=True).count()

        members_agg = OrganizationMembership.objects.aggregate(
            total=Count("id"),
        )

        by_role = OrganizationMembership.objects.values("role__name").annotate(count=Count("id"))
        role_map = {r["role__name"] or "unknown": r["count"] for r in by_role}

        top_orgs = Organization.objects.annotate(member_count=Count("memberships")).order_by("-member_count")[:5]

        return {
            "enabled": True,
            "total_organizations": total,
            "active": active,
            "with_sub_orgs": Organization.objects.filter(parent__isnull=False).count(),
            "members": {
                "total": members_agg["total"],
                "avg_per_org": round(members_agg["total"] / total, 1) if total > 0 else 0,
                "by_role": role_map,
            },
            "top_organizations": [
                {
                    "name": org.name,
                    "slug": org.slug,
                    "members": org.member_count,
                }
                for org in top_orgs
            ],
        }
