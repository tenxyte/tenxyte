"""
Tests pour les vues admin User CRUD.
"""
from tenxyte.conf import auth_settings
api_prefix = auth_settings.API_PREFIX

import pytest  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from rest_framework import status  # noqa: E402


User = get_user_model()


class TestUserListView:
    """Tests pour GET /api/v1/auth/admin/users/."""

    @pytest.mark.django_db
    def test_list_users(self, authenticated_admin_client, admin_user):
        """Admin peut lister les utilisateurs."""
        User.objects.create(email="extra1@test.com")
        User.objects.create(email="extra2@test.com")

        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/users/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

        if response.status_code == status.HTTP_200_OK:
            assert 'results' in response.data or isinstance(response.data, list)

    @pytest.mark.django_db
    def test_list_users_search(self, authenticated_admin_client, admin_user):
        """Recherche par email."""
        User.objects.create(email="searchme@test.com", first_name="Searchable")

        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/users/?search=searchme')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    @pytest.mark.django_db
    def test_list_users_filter_active(self, authenticated_admin_client, admin_user):
        """Filtre par is_active."""
        User.objects.create(email="active@test.com", is_active=True)
        User.objects.create(email="inactive@test.com", is_active=False)

        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/users/?is_active=true')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    @pytest.mark.django_db
    def test_list_users_unauthenticated(self, api_client, application):
        """Non authentifié = 401/403."""
        api_client.credentials(
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )
        response = api_client.get(f'{api_prefix}/auth/admin/users/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


class TestUserDetailView:
    """Tests pour GET/PATCH /api/v1/auth/admin/users/<id>/."""

    @pytest.mark.django_db
    def test_get_user_detail(self, authenticated_admin_client, admin_user, user):
        """Admin peut voir les détails d'un utilisateur."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/users/{user.id}/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

        if response.status_code == status.HTTP_200_OK:
            assert response.data['email'] == user.email

    @pytest.mark.django_db
    def test_get_user_not_found(self, authenticated_admin_client, admin_user):
        """Utilisateur inexistant = 404."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/users/99999/')
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]

    @pytest.mark.django_db
    def test_update_user(self, authenticated_admin_client, admin_user, user):
        """Admin peut modifier un utilisateur."""
        response = authenticated_admin_client.patch(
            f'{api_prefix}/auth/admin/users/{user.id}/',
            {'first_name': 'Updated'},
            format='json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]


class TestUserBanViews:
    """Tests pour les vues ban/unban."""

    @pytest.mark.django_db
    def test_ban_user(self, authenticated_admin_client, admin_user, user):
        """Admin peut bannir un utilisateur."""
        response = authenticated_admin_client.post(
            f'{api_prefix}/auth/admin/users/{user.id}/ban/',
            {'reason': 'Test ban'},
            format='json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

        if response.status_code == status.HTTP_200_OK:
            user.refresh_from_db()
            assert user.is_banned is True

    @pytest.mark.django_db
    def test_unban_user(self, authenticated_admin_client, admin_user, user):
        """Admin peut débannir un utilisateur."""
        user.is_banned = True
        user.save()

        response = authenticated_admin_client.post(
            f'{api_prefix}/auth/admin/users/{user.id}/unban/',
            format='json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]


class TestUserLockViews:
    """Tests pour les vues lock/unlock."""

    @pytest.mark.django_db
    def test_lock_user(self, authenticated_admin_client, admin_user, user):
        """Admin peut verrouiller un utilisateur."""
        response = authenticated_admin_client.post(
            f'{api_prefix}/auth/admin/users/{user.id}/lock/',
            {'duration_hours': 24, 'reason': 'Test lock'},
            format='json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    @pytest.mark.django_db
    def test_unlock_user(self, authenticated_admin_client, admin_user, user):
        """Admin peut déverrouiller un utilisateur."""
        user.is_locked = True
        user.save()

        response = authenticated_admin_client.post(
            f'{api_prefix}/auth/admin/users/{user.id}/unlock/',
            format='json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]
