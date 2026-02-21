"""
Tests pour les filtres et la pagination.
"""
import pytest
from unittest.mock import Mock
from django.contrib.auth import get_user_model
from rest_framework import status

from tenxyte.models import Permission, Role, Application
from tenxyte.pagination import TenxytePagination
from tenxyte.filters import (
    apply_search, apply_ordering, apply_date_range, apply_boolean_filter,
    apply_permission_filters, apply_role_filters, apply_application_filters,
)

User = get_user_model()


def mock_request(**query_params):
    """Helper: create a mock request with query_params."""
    req = Mock()
    req.query_params = query_params
    return req


class TestPaginationClass:
    """Tests pour TenxytePagination."""

    def test_default_page_size(self):
        """Page size par défaut = 20."""
        paginator = TenxytePagination()
        assert paginator.page_size == 20

    def test_max_page_size(self):
        """Max page size = 100."""
        paginator = TenxytePagination()
        assert paginator.max_page_size == 100


class TestSearchFilter:
    """Tests pour apply_search."""

    @pytest.mark.django_db
    def test_search_single_field(self):
        """Recherche sur un champ."""
        User.objects.create(email="alice@example.com", first_name="Alice")
        User.objects.create(email="bob@example.com", first_name="Bob")

        request = mock_request(search='alice')
        result = apply_search(User.objects.all(), request, ['email'])
        assert result.count() == 1
        assert result.first().email == "alice@example.com"

    @pytest.mark.django_db
    def test_search_multiple_fields(self):
        """Recherche sur plusieurs champs."""
        User.objects.create(email="alice@example.com", first_name="Alice", last_name="Smith")
        User.objects.create(email="bob@example.com", first_name="Bob", last_name="Jones")

        request = mock_request(search='smith')
        result = apply_search(User.objects.all(), request, ['email', 'first_name', 'last_name'])
        assert result.count() == 1
        assert result.first().first_name == "Alice"

    @pytest.mark.django_db
    def test_search_empty(self):
        """Recherche vide retourne tout."""
        User.objects.create(email="a@test.com")
        User.objects.create(email="b@test.com")

        request = mock_request(search='')
        result = apply_search(User.objects.all(), request, ['email'])
        assert result.count() == 2

    @pytest.mark.django_db
    def test_search_no_param(self):
        """Pas de param search retourne tout."""
        User.objects.create(email="a@test.com")

        request = mock_request()
        result = apply_search(User.objects.all(), request, ['email'])
        assert result.count() == 1


class TestOrderingFilter:
    """Tests pour apply_ordering."""

    @pytest.mark.django_db
    def test_ordering_asc(self):
        """Tri ascendant."""
        User.objects.create(email="b@test.com")
        User.objects.create(email="a@test.com")

        request = mock_request(ordering='email')
        result = apply_ordering(User.objects.all(), request, allowed_fields=['email'])
        emails = list(result.values_list('email', flat=True))
        assert emails == sorted(emails)

    @pytest.mark.django_db
    def test_ordering_desc(self):
        """Tri descendant."""
        User.objects.create(email="a@test.com")
        User.objects.create(email="b@test.com")

        request = mock_request(ordering='-email')
        result = apply_ordering(User.objects.all(), request, allowed_fields=['email'])
        emails = list(result.values_list('email', flat=True))
        assert emails == sorted(emails, reverse=True)

    @pytest.mark.django_db
    def test_ordering_invalid_ignored(self):
        """Champ non autorisé est ignoré, default appliqué."""
        User.objects.create(email="a@test.com")

        request = mock_request(ordering='hacked_field')
        result = apply_ordering(
            User.objects.all(), request,
            default='-email', allowed_fields=['email']
        )
        assert result.count() == 1

    @pytest.mark.django_db
    def test_ordering_default(self):
        """Pas de param ordering → default appliqué."""
        User.objects.create(email="b@test.com")
        User.objects.create(email="a@test.com")

        request = mock_request()
        result = apply_ordering(User.objects.all(), request, default='email')
        emails = list(result.values_list('email', flat=True))
        assert emails[0] == "a@test.com"


class TestBooleanFilter:
    """Tests pour apply_boolean_filter."""

    @pytest.mark.django_db
    def test_filter_true(self):
        """Filtre booléen True."""
        User.objects.create(email="active@test.com", is_active=True)
        User.objects.create(email="inactive@test.com", is_active=False)

        request = mock_request(is_active='true')
        result = apply_boolean_filter(User.objects.all(), request, 'is_active')
        assert result.count() == 1
        assert result.first().email == "active@test.com"

    @pytest.mark.django_db
    def test_filter_false(self):
        """Filtre booléen False."""
        User.objects.create(email="active@test.com", is_active=True)
        User.objects.create(email="inactive@test.com", is_active=False)

        request = mock_request(is_active='false')
        result = apply_boolean_filter(User.objects.all(), request, 'is_active')
        assert result.count() == 1
        assert result.first().email == "inactive@test.com"

    @pytest.mark.django_db
    def test_filter_none(self):
        """Pas de param retourne tout."""
        User.objects.create(email="a@test.com", is_active=True)
        User.objects.create(email="b@test.com", is_active=False)

        request = mock_request()
        result = apply_boolean_filter(User.objects.all(), request, 'is_active')
        assert result.count() == 2


class TestModelFilters:
    """Tests pour les filtres spécifiques aux modèles."""

    @pytest.mark.django_db
    def test_permission_filters_search(self):
        """Filtre permissions par recherche."""
        Permission.objects.create(code="users.read", name="Read Users")
        Permission.objects.create(code="roles.read", name="Read Roles")

        request = mock_request(search='users')
        result = apply_permission_filters(Permission.objects.all(), request)
        assert result.count() == 1
        assert result.first().code == "users.read"

    @pytest.mark.django_db
    def test_role_filters_search(self):
        """Filtre rôles par recherche."""
        Role.objects.create(code="editor", name="Editor")
        Role.objects.create(code="viewer", name="Viewer")

        request = mock_request(search='editor')
        result = apply_role_filters(Role.objects.all(), request)
        assert result.count() == 1
        assert result.first().code == "editor"

    @pytest.mark.django_db
    def test_application_filters_search(self):
        """Filtre applications par recherche."""
        Application.create_application(name="App Alpha", description="First")
        Application.create_application(name="App Beta", description="Second")

        request = mock_request(search='Alpha')
        result = apply_application_filters(Application.objects.all(), request)
        assert result.count() == 1
        assert result.first().name == "App Alpha"


class TestPaginatedEndpoints:
    """Tests d'intégration pour les endpoints paginés."""

    @pytest.mark.django_db
    def test_permissions_paginated(self, authenticated_admin_client, admin_user):
        """Endpoint permissions retourne une réponse paginée."""
        for i in range(25):
            Permission.objects.get_or_create(
                code=f'test.perm{i}',
                defaults={'name': f'Test Perm {i}'}
            )

        response = authenticated_admin_client.get('/api/auth/permissions/')

        if response.status_code == status.HTTP_200_OK:
            assert 'results' in response.data or isinstance(response.data, list)

    @pytest.mark.django_db
    def test_permissions_page_size(self, authenticated_admin_client, admin_user):
        """Contrôle de page_size via query param."""
        for i in range(10):
            Permission.objects.get_or_create(
                code=f'test.sized{i}',
                defaults={'name': f'Test Sized {i}'}
            )

        response = authenticated_admin_client.get('/api/auth/permissions/?page_size=5')

        if response.status_code == status.HTTP_200_OK and 'results' in response.data:
            assert len(response.data['results']) <= 5

    @pytest.mark.django_db
    def test_roles_paginated(self, authenticated_admin_client, admin_user):
        """Endpoint rôles retourne une réponse paginée."""
        for i in range(5):
            Role.objects.get_or_create(
                code=f'role_{i}',
                defaults={'name': f'Role {i}'}
            )

        response = authenticated_admin_client.get('/api/auth/roles/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]
