import pytest
from rest_framework import status

from tenxyte.conf import auth_settings
api_prefix = auth_settings.API_PREFIX
from tenxyte.models import User, Application  # noqa: E402

@pytest.mark.django_db
class TestIDORSecurity:
    """Tests IDOR sur les endpoints /users/ et /applications/"""
    
    def test_idor_patch_other_user_forbidden(self, authenticated_client, user):
        """Un utilisateur standard ne doit pas pouvoir modifier les rôles d'un autre utilisateur."""
        other_user = User.objects.create(email="other@example.com", first_name="Other")
        response = authenticated_client.post(f'{api_prefix}/auth/users/{other_user.id}/roles/', {
            'roles': ['admin']
        })
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
        
    def test_idor_get_other_user_forbidden(self, authenticated_client, user):
        """Un utilisateur standard ne doit pas pouvoir lire les rôles d'un autre utilisateur."""
        other_user = User.objects.create(email="other2@example.com")
        response = authenticated_client.get(f'{api_prefix}/auth/users/{other_user.id}/roles/')
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
        
    def test_idor_application_modification_forbidden(self, app_api_client, authenticated_client, user):
        """Un utilisateur sans permissions app ne doit pas modifier une application."""
        # On crée une autre application au hasard.
        other_app, _ = Application.create_application(name="Other App")
        response = authenticated_client.patch(f'{api_prefix}/auth/applications/{other_app.id}/', {
            'name': 'Hacked App'
        })
        # Soit 404, soit 403
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


@pytest.mark.django_db
class TestMassAssignmentSecurity:
    """Tests pour le mass assignment sur PATCH /me/"""
    
    def test_mass_assignment_is_staff_rejected(self, authenticated_client, user):
        """Une tentative d'élévation de privilèges via PATCH /me/ doit échouer."""
        assert not user.is_staff
        assert not user.is_superuser
        
        response = authenticated_client.patch(f'{api_prefix}/auth/me/', {
            'first_name': 'Test',
            'is_staff': True,
            'is_superuser': True,
            'is_active': False
        })
        
        assert response.status_code == status.HTTP_200_OK
        
        # Recharger l'utilisateur de la BD
        user.refresh_from_db()
        assert not user.is_staff
        assert not user.is_superuser
        assert user.is_active  # Ne devrait pas pouvoir se désactiver lui-même via PATCH
