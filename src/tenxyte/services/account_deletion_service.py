"""
Service pour la gestion des suppressions de compte (RGPD).
"""

from datetime import timedelta
from typing import Tuple, Optional, Dict, Any
from django.utils import timezone
from django.conf import settings

from .email_service import EmailService
from ..models import get_user_model, AccountDeletionRequest, AuditLog

User = get_user_model()


class AccountDeletionService:
    """Service pour gérer le workflow de suppression de compte."""
    
    def __init__(self):
        self.email_service = EmailService()
        self.grace_period_days = getattr(settings, 'TENXYTE_ACCOUNT_DELETION_GRACE_PERIOD_DAYS', 30)
    
    def request_deletion(
        self, 
        user: User, 
        password: str,
        ip_address: str = None,
        user_agent: str = '',
        otp_code: str = '',
        reason: str = ''
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Créer une demande de suppression de compte.
        
        Args:
            user: L'utilisateur qui demande la suppression
            password: Mot de passe pour vérification
            ip_address: IP de la demande
            user_agent: User agent
            reason: Raison optionnelle
            
        Returns:
            Tuple[success, data, error_message]
        """
        # Vérifier le mot de passe
        if not user.check_password(password):
            self._audit_log('deletion_request_failed', user, ip_address, {
                'reason': 'invalid_password',
                'user_agent': user_agent
            })
            return False, None, 'Invalid password'
        
        # Vérifier 2FA si activé
        if user.is_2fa_enabled:
            # Pour la suppression de compte, on exige une vérification 2FA forte
            # L'utilisateur doit fournir un code OTP valide avec sa demande
            
            if not otp_code:
                self._audit_log('deletion_request_failed', user, ip_address, {
                    'reason': 'missing_2fa',
                    'user_agent': user_agent
                })
                return False, None, 'Two-factor authentication code required'
            
            from .otp_service import OTPService
            otp_service = OTPService()
            
            if not otp_service.verify_otp(user, otp_code, otp_type='login_2fa'):
                self._audit_log('deletion_request_failed', user, ip_address, {
                    'reason': 'invalid_2fa',
                    'otp_code': otp_code[:6] + '...' if len(otp_code) > 6 else otp_code
                })
                return False, None, 'Invalid two-factor authentication code'
        
        # Créer la demande
        try:
            deletion_request = AccountDeletionRequest.create_request(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                reason=reason
            )
            
            # Envoyer l'email de confirmation
            deletion_request.send_confirmation_email()
            
            self._audit_log('deletion_request_created', user, ip_address, {
                'request_id': deletion_request.id,
                'token': deletion_request.confirmation_token,
                'user_agent': user_agent,
                'reason': reason
            })
            
            return True, {
                'request_id': deletion_request.id,
                'message': 'Deletion request created. Please check your email for confirmation.',
                'grace_period_days': self.grace_period_days
            }, ''
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error creating deletion request: {e}", exc_info=True)
            self._audit_log('deletion_request_error', user, ip_address, {
                'error': 'Internal server error',
                'user_agent': user_agent
            })
            return False, None, 'An unexpected error occurred while creating the deletion request.'
    
    def confirm_deletion(self, token: str, ip_address: str = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Confirmer une demande de suppression via token.
        
        Args:
            token: Token de confirmation
            ip_address: IP de la confirmation
            
        Returns:
            Tuple[success, data, error_message]
        """
        try:
            deletion_request = AccountDeletionRequest.objects.get(
                confirmation_token=token,
                status='confirmation_sent'
            )
            
            # Confirmer la demande
            deletion_request.confirm_request(self.grace_period_days)
            
            self._audit_log('deletion_request_confirmed', deletion_request.user, ip_address, {
                'request_id': deletion_request.id,
                'grace_period_ends_at': deletion_request.grace_period_ends_at.isoformat()
            })
            
            # Envoyer email de confirmation de la demande
            try:
                self.email_service.send_account_deletion_confirmed(deletion_request)
            except Exception as e:
                # Log l'erreur mais ne pas échouer la demande
                self._audit_log('deletion_confirmation_email_failed', deletion_request.user, ip_address, {
                    'request_id': deletion_request.id,
                    'error': str(e)
                })
            
            return True, {
                'message': 'Deletion request confirmed. Your account will be deleted after the grace period.',
                'grace_period_ends_at': deletion_request.grace_period_ends_at.isoformat(),
                'days_remaining': self.grace_period_days
            }, ''
            
        except AccountDeletionRequest.DoesNotExist:
            return False, None, 'Invalid or expired confirmation token'
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error confirming deletion request: {e}", exc_info=True)
            self._audit_log('deletion_confirmation_error', None, ip_address, {
                'token': token,
                'error': 'Internal server error'
            })
            return False, None, 'An unexpected error occurred while confirming the deletion request.'
    
    def cancel_deletion(
        self, 
        user: User, 
        password: str,
        ip_address: str = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Annuler une demande de suppression.
        
        Args:
            user: L'utilisateur qui annule
            password: Mot de passe pour vérification
            ip_address: IP de l'annulation
            
        Returns:
            Tuple[success, data, error_message]
        """
        # Vérifier le mot de passe
        if not user.check_password(password):
            self._audit_log('deletion_cancel_failed', user, ip_address, {
                'reason': 'invalid_password'
            })
            return False, None, 'Invalid password'
        
        # Trouver les demandes actives
        active_requests = AccountDeletionRequest.objects.filter(
            user=user,
            status__in=['pending', 'confirmation_sent', 'confirmed']
        )
        
        if not active_requests.exists():
            return False, None, 'No active deletion requests found'
        
        # Annuler toutes les demandes actives
        cancelled_count = 0
        for request in active_requests:
            request.cancel_request()
            cancelled_count += 1
        
        self._audit_log('deletion_request_cancelled', user, ip_address, {
            'cancelled_requests': cancelled_count
        })
        
        return True, {
            'message': f'Cancelled {cancelled_count} deletion request(s).',
            'cancelled_count': cancelled_count
        }, ''
    
    def get_user_requests(self, user: User) -> Dict[str, Any]:
        """
        Obtenir l'historique des demandes de suppression d'un utilisateur.
        
        Args:
            user: L'utilisateur
            
        Returns:
            Dict avec les informations sur les demandes
        """
        requests = AccountDeletionRequest.objects.filter(user=user).order_by('-requested_at')
        
        active_request = requests.filter(
            status__in=['pending', 'confirmation_sent', 'confirmed']
        ).first()
        
        return {
            'total_requests': requests.count(),
            'active_request': {
                'id': active_request.id,
                'status': active_request.status,
                'requested_at': active_request.requested_at.isoformat(),
                'grace_period_ends_at': active_request.grace_period_ends_at.isoformat() if active_request.grace_period_ends_at else None,
                'days_remaining': (
                    (active_request.grace_period_ends_at - timezone.now()).days
                    if active_request.grace_period_ends_at else None
                )
            } if active_request else None,
            'history': [
                {
                    'id': req.id,
                    'status': req.status,
                    'requested_at': req.requested_at.isoformat(),
                    'confirmed_at': req.confirmed_at.isoformat() if req.confirmed_at else None,
                    'completed_at': req.completed_at.isoformat() if req.completed_at else None,
                    'reason': req.reason
                }
                for req in requests
            ]
        }
    
    def process_expired_requests(self) -> int:
        """
        Traiter les demandes expirées (tâche cron).
        
        Returns:
            Nombre de demandes traitées
        """
        expired_requests = AccountDeletionRequest.get_expired_requests()
        processed_count = 0
        
        for request in expired_requests:
            if request.execute_deletion():
                processed_count += 1
                self._audit_log('deletion_request_processed', request.user, None, {
                    'request_id': request.id,
                    'processed_at': timezone.now().isoformat()
                })
        
        return processed_count
    
    def get_pending_requests(self, limit: int = 50) -> Dict[str, Any]:
        """
        Obtenir les demandes de suppression en attente pour admin.
        
        Args:
            limit: Nombre maximum de résultats
            
        Returns:
            Dict avec les demandes et statistiques
        """
        requests = AccountDeletionRequest.objects.filter(
            status__in=['pending', 'confirmation_sent', 'confirmed']
        ).order_by('-requested_at')[:limit]
        
        return {
            'pending_count': AccountDeletionRequest.objects.filter(status='pending').count(),
            'confirmation_sent_count': AccountDeletionRequest.objects.filter(status='confirmation_sent').count(),
            'confirmed_count': AccountDeletionRequest.objects.filter(status='confirmed').count(),
            'expired_count': AccountDeletionRequest.get_expired_requests().count(),
            'requests': [
                {
                    'id': req.id,
                    'user_id': req.user.id,
                    'user_email': req.user.email,
                    'status': req.status,
                    'requested_at': req.requested_at.isoformat(),
                    'confirmed_at': req.confirmed_at.isoformat() if req.confirmed_at else None,
                    'grace_period_ends_at': req.grace_period_ends_at.isoformat() if req.grace_period_ends_at else None,
                    'ip_address': req.ip_address,
                    'reason': req.reason,
                    'days_remaining': (
                        (req.grace_period_ends_at - timezone.now()).days
                        if req.grace_period_ends_at else None
                    )
                }
                for req in requests
            ]
        }
    
    def admin_process_request(
        self, 
        request_id: int, 
        action: str, 
        admin_user: User,
        admin_notes: str = ''
    ) -> Tuple[bool, str]:
        """
        Traiter une demande de suppression (admin).
        
        Args:
            request_id: ID de la demande
            action: 'approve', 'reject', 'cancel', 'execute'
            admin_user: Admin qui traite
            admin_notes: Notes admin
            
        Returns:
            Tuple[success, message]
        """
        try:
            deletion_request = AccountDeletionRequest.objects.get(id=request_id)
        except AccountDeletionRequest.DoesNotExist:
            return False, 'Deletion request not found'
        
        # Ajouter les notes admin
        if admin_notes:
            deletion_request.admin_notes = admin_notes
        
        if action == 'approve':
            if deletion_request.status != 'confirmation_sent':
                return False, 'Can only approve requests with confirmation_sent status'
            
            deletion_request.confirm_request(self.grace_period_days)
            deletion_request.processed_by = admin_user
            deletion_request.save()
            
            self._audit_log('deletion_request_approved', deletion_request.user, None, {
                'request_id': request_id,
                'admin_id': admin_user.id,
                'admin_email': admin_user.email
            })
            
            return True, 'Deletion request approved and grace period started'
        
        elif action == 'reject':
            if deletion_request.status not in ['pending', 'confirmation_sent']:
                return False, 'Can only reject pending or confirmation_sent requests'
            
            deletion_request.status = 'cancelled'
            deletion_request.processed_by = admin_user
            deletion_request.save()
            
            self._audit_log('deletion_request_rejected', deletion_request.user, None, {
                'request_id': request_id,
                'admin_id': admin_user.id,
                'admin_email': admin_user.email,
                'admin_notes': admin_notes
            })
            
            # TODO: Envoyer email de rejet
            # self.email_service.send_deletion_request_rejected(deletion_request)
            
            return True, 'Deletion request rejected'
        
        elif action == 'cancel':
            if deletion_request.status not in ['pending', 'confirmation_sent', 'confirmed']:
                return False, 'Can only cancel active requests'
            
            deletion_request.cancel_request()
            deletion_request.processed_by = admin_user
            deletion_request.save()
            
            self._audit_log('deletion_request_cancelled_admin', deletion_request.user, None, {
                'request_id': request_id,
                'admin_id': admin_user.id,
                'admin_email': admin_user.email
            })
            
            return True, 'Deletion request cancelled'
        
        elif action == 'execute':
            if deletion_request.status != 'confirmed':
                return False, 'Can only execute confirmed requests'
            
            success = deletion_request.execute_deletion(processed_by=admin_user)
            
            if success:
                self._audit_log('deletion_request_executed_admin', deletion_request.user, None, {
                    'request_id': request_id,
                    'admin_id': admin_user.id,
                    'admin_email': admin_user.email
                })
                
                return True, 'Account deletion executed successfully'
            else:
                return False, 'Failed to execute account deletion'
        
        else:
            return False, 'Invalid action'
    
    def get_deletion_statistics(self) -> Dict[str, Any]:
        """
        Obtenir les statistiques de suppression de compte.
        
        Returns:
            Dict avec les statistiques
        """
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta
        
        # Statistiques générales
        total_requests = AccountDeletionRequest.objects.count()
        completed_requests = AccountDeletionRequest.objects.filter(status='completed').count()
        cancelled_requests = AccountDeletionRequest.objects.filter(status='cancelled').count()
        
        # Statistiques récentes (30 derniers jours)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_requests = AccountDeletionRequest.objects.filter(requested_at__gte=thirty_days_ago)
        
        # Demandes par statut
        status_counts = AccountDeletionRequest.objects.values('status').annotate(count=Count('id'))
        
        return {
            'total_requests': total_requests,
            'completed_requests': completed_requests,
            'cancelled_requests': cancelled_requests,
            'completion_rate': (completed_requests / total_requests * 100) if total_requests > 0 else 0,
            'recent_requests_30_days': recent_requests.count(),
            'requests_by_status': {item['status']: item['count'] for item in status_counts},
            'expired_pending': AccountDeletionRequest.get_expired_requests().count()
        }
    
    def _audit_log(self, action: str, user: User, ip_address: str = None, details: Dict[str, Any] = None):
        """Créer un log d'audit."""
        AuditLog.objects.create(
            action=action,
            user=user,
            ip_address=ip_address or '127.0.0.1',
            details=details or {}
        )
