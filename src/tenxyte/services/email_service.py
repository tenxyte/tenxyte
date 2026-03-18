"""
Email service wrapper for backward compatibility.

This module re-exports EmailService from the adapters layer to maintain
compatibility with existing imports in the services layer.
"""

from tenxyte.adapters.django.email_service import DjangoEmailService as EmailService

__all__ = ['EmailService']
