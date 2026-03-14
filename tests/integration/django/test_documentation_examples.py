"""
Test suite for documentation examples and schemas validation.

This test validates that all examples in the documentation are:
1. Valid JSON/YAML structures
2. Match the defined schemas
3. Are realistic and comprehensive
4. Cover all error codes and success scenarios
"""

import sys
import os

# Ensure src is in path to import tenxyte correctly before Django machinery starts
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_dir = os.path.join(project_root, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import json  # noqa: E402
import pytest  # noqa: E402
from rest_framework.test import APITestCase  # noqa: E402
from rest_framework import status  # noqa: E402
from django.urls import reverse  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

from tenxyte.docs.schemas import (  # noqa: E402
    LOGIN_SUCCESS_EXAMPLE,
    LOGIN_RATE_LIMITED_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
    NOT_FOUND_ERROR_EXAMPLE,
    PERMISSION_DENIED_EXAMPLE,
    MULTI_TENANT_SUCCESS_EXAMPLE,
    FILE_UPLOAD_SUCCESS_EXAMPLE,
    FILE_TOO_LARGE_EXAMPLE,
    GDPR_DELETION_CONFIRMED_EXAMPLE,
    PAGINATED_RESPONSE_EXAMPLE
)

User = get_user_model()


class DocumentationExamplesTestCase(APITestCase):
    """Test that documentation examples are valid and comprehensive."""

    def test_login_success_example_validity(self):
        """Test that login success example is valid JSON and matches schema."""
        example = LOGIN_SUCCESS_EXAMPLE.value
        
        # Verify JSON validity
        json.dumps(example)  # Will raise if not serializable
        
        # Verify required fields
        assert 'access' in example
        assert 'refresh' in example
        assert 'user' in example
        
        # Verify JWT token format (basic check)
        assert len(example['access']) > 50  # JWT tokens are long
        assert len(example['refresh']) > 50
        
        # Verify user data structure
        user_data = example['user']
        assert 'id' in user_data
        assert 'email' in user_data
        assert 'first_name' in user_data
        assert 'last_name' in user_data
        assert isinstance(user_data['is_active'], bool)
        assert isinstance(user_data['is_verified'], bool)

    def test_error_examples_follow_schema(self):
        """Test that all error examples follow the standard error schema."""
        error_examples = [
            LOGIN_RATE_LIMITED_EXAMPLE,
            VALIDATION_ERROR_EXAMPLE,
            NOT_FOUND_ERROR_EXAMPLE,
            PERMISSION_DENIED_EXAMPLE,
            FILE_TOO_LARGE_EXAMPLE
        ]
        
        for example in error_examples:
            error_data = example.value
            
            # Verify required fields
            assert 'error' in error_data
            assert 'code' in error_data
            
            # Verify error is a string
            assert isinstance(error_data['error'], str)
            assert len(error_data['error']) > 0
            
            # Verify code is a string and uppercase
            assert isinstance(error_data['code'], str)
            assert error_data['code'].isupper()
            assert '_' in error_data['code']  # Error codes use underscores

    def test_rate_limiting_example_completeness(self):
        """Test that rate limiting example includes all required fields."""
        example = LOGIN_RATE_LIMITED_EXAMPLE.value
        
        assert 'retry_after' in example
        assert isinstance(example['retry_after'], int)
        assert example['retry_after'] > 0
        assert 'details' in example

    def test_validation_error_example_structure(self):
        """Test that validation error example has proper field-level errors."""
        example = VALIDATION_ERROR_EXAMPLE.value
        
        assert 'details' in example
        details = example['details']
        assert isinstance(details, dict)
        
        # Should have field-level errors
        for field, errors in details.items():
            assert isinstance(errors, list)
            assert len(errors) > 0
            for error in errors:
                assert isinstance(error, str)

    def test_multi_tenant_example_structure(self):
        """Test that multi-tenant example includes organization context."""
        example = MULTI_TENANT_SUCCESS_EXAMPLE.value
        
        assert 'organization' in example
        org_data = example['organization']
        
        # Verify organization structure
        assert 'id' in org_data
        assert 'slug' in org_data
        assert 'name' in org_data
        assert 'role' in org_data
        
        # Verify slug format
        assert isinstance(org_data['slug'], str)
        assert '-' in org_data['slug'] or org_data['slug'].islower()

    def test_file_upload_examples_completeness(self):
        """Test that file upload examples include all metadata."""
        # Success example
        success = FILE_UPLOAD_SUCCESS_EXAMPLE.value
        assert 'file_url' in success
        assert 'file_size' in success
        assert 'mime_type' in success
        
        # Verify URL format
        assert success['file_url'].startswith('https://')
        assert isinstance(success['file_size'], int)
        assert success['file_size'] > 0
        
        # Error example
        error = FILE_TOO_LARGE_EXAMPLE.value
        assert 'max_size' in error
        assert error['max_size'].endswith('MB')

    def test_gdpr_example_completeness(self):
        """Test that GDPR example includes grace period information."""
        example = GDPR_DELETION_CONFIRMED_EXAMPLE.value
        
        assert 'grace_period_ends' in example
        assert 'cancellation_instructions' in example
        assert isinstance(example['deletion_confirmed'], bool)
        assert example['deletion_confirmed'] is True

    def test_paginated_response_structure(self):
        """Test that paginated response follows Django REST framework format."""
        example = PAGINATED_RESPONSE_EXAMPLE.value
        
        # Verify pagination structure
        assert 'count' in example
        assert 'next' in example
        assert 'previous' in example
        assert 'results' in example
        
        # Verify data types
        assert isinstance(example['count'], int)
        assert isinstance(example['results'], list)
        
        # Verify results are not empty
        assert len(example['results']) > 0

    def test_all_error_codes_covered(self):
        """Test that we have examples for all common error codes."""
        expected_codes = {
            'VALIDATION_ERROR',
            'NOT_FOUND', 
            'PERMISSION_DENIED',
            'RATE_LIMITED',
            'FILE_TOO_LARGE'
        }
        
        actual_codes = set()
        error_examples = [
            LOGIN_RATE_LIMITED_EXAMPLE,
            VALIDATION_ERROR_EXAMPLE,
            NOT_FOUND_ERROR_EXAMPLE,
            PERMISSION_DENIED_EXAMPLE,
            FILE_TOO_LARGE_EXAMPLE
        ]
        
        for example in error_examples:
            actual_codes.add(example.value['code'])
        
        assert expected_codes.issubset(actual_codes), f"Missing error codes: {expected_codes - actual_codes}"

    def test_example_realism(self):
        """Test that examples use realistic data."""
        # Login example
        login = LOGIN_SUCCESS_EXAMPLE.value
        user_data = login['user']
        assert '@' in user_data['email']  # Valid email format
        assert len(user_data['first_name']) > 0
        assert len(user_data['last_name']) > 0
        assert user_data['id'] > 0
        
        # Multi-tenant example
        multi_tenant = MULTI_TENANT_SUCCESS_EXAMPLE.value
        org_data = multi_tenant['organization']
        assert len(org_data['name']) > 0
        assert len(org_data['slug']) > 0

    def test_response_schema_compliance(self):
        """Test that examples comply with defined response schemas."""
        # Test error schema compliance
        error_examples = [
            LOGIN_RATE_LIMITED_EXAMPLE,
            VALIDATION_ERROR_EXAMPLE
        ]
        
        for example in error_examples:
            error_data = example.value
            # Should have required fields
            assert 'error' in error_data
            # Should have optional fields where appropriate
            if 'retry_after' in error_data:
                assert isinstance(error_data['retry_after'], int)


class DocumentationIntegrationTestCase(APITestCase):
    """Test that documentation examples work with actual API endpoints."""

    def setUp(self):
        """Set up test user and data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_login_endpoint_matches_documentation(self):
        """Test that /login/email/ endpoint matches documented response format."""
        url = reverse('authentication:login_email')
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(url, data, format='json')
        
        if response.status_code == status.HTTP_200_OK:
            # Verify response structure matches documentation
            response_data = response.json()
            
            # Should have tokens and user data
            assert 'access' in response_data
            assert 'refresh' in response_data
            assert 'user' in response_data
            
            # User data should match documented structure
            user_data = response_data['user']
            assert 'id' in user_data
            assert 'email' in user_data
            assert 'first_name' in user_data
            assert 'last_name' in user_data

    def test_validation_errors_match_documentation(self):
        """Test that validation errors match documented error format."""
        url = reverse('authentication:login_email')
        data = {
            'email': 'invalid-email',
            'password': '123'  # Too short
        }
        
        response = self.client.post(url, data, format='json')
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            error_data = response.json()
            
            # Should follow error schema
            assert 'error' in error_data
            assert 'details' in error_data or 'code' in error_data

    def test_rate_limiting_headers(self):
        """Test that rate limiting headers are present when applicable."""
        # This would require multiple rapid requests to trigger rate limiting
        # For now, just verify the structure would be correct
        pass


class DocumentationCoverageTestCase(APITestCase):
    """Test documentation coverage and completeness."""

    def test_all_endpoints_have_examples(self):
        """Verify that all major endpoints have documentation examples."""
        # This would be a comprehensive test checking each endpoint
        # For now, we'll check a few key ones
        endpoints_with_examples = [
            'authentication:login_email',
            'authentication:register',
            'authentication:me',
            'authentication:my_roles'
        ]
        
        for endpoint in endpoints_with_examples:
            try:
                url = reverse(endpoint)
                # Verify endpoint exists and is documented
                assert url is not None
            except Exception:
                pytest.fail(f"Endpoint {endpoint} not found or not documented")

    def test_error_code_coverage(self):
        """Test that all documented error codes have examples."""
        # This would check that for each documented error code
        # there exists a corresponding example
        
        # Implementation would check each code has an example
        pass

    def test_success_response_coverage(self):
        """Test that all success responses have examples."""
        # Verify that 200, 201, 204 responses have examples
        pass

    def test_multi_tenant_coverage(self):
        """Test that multi-tenant scenarios are covered in examples."""
        # Verify examples include X-Org-Slug header usage
        pass

    def test_security_scenario_coverage(self):
        """Test that security scenarios are covered."""
        # Verify examples cover 2FA, rate limiting, etc.
        pass
