"""
Tenxyte - Exception handling.

Provides a custom DRF exception handler to ensure that all API errors
strictly follow the canonical `ErrorResponse` schema:
{
  "error": "Human-readable message",
  "code": "MACHINE_READABLE_CODE",
  "details": {
    "field_name": ["List of errors for this field"]
  }
}
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException
from django.core.exceptions import PermissionDenied
from django.http import Http404

def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that formats errors according to
    the tenxyte generic ErrorResponse schema.
    """
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Standardize non-DRF exceptions
    if isinstance(exc, Http404):
        exc = APIException("Not found.")
        exc.status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, PermissionDenied):
        exc = APIException("Permission denied.")
        exc.status_code = status.HTTP_403_FORBIDDEN

    if response is not None:
        # Default properties
        error_message = "An error occurred"
        error_code = "UNKNOWN_ERROR"
        details = {}

        # If it's a known DRF exception, extract data
        if hasattr(exc, "get_codes"):
            codes = exc.get_codes()
            if isinstance(codes, dict):
                # Validation error on fields
                error_code = "VALIDATION_ERROR"
                error_message = "Invalid input."
                details = response.data
            elif isinstance(codes, list) and len(codes) > 0:
                error_code = str(codes[0]).upper()
                if isinstance(response.data, dict) and "detail" in response.data:
                    error_message = str(response.data["detail"])
            elif isinstance(codes, str):
                error_code = codes.upper()
                if isinstance(response.data, dict) and "detail" in response.data:
                    error_message = str(response.data["detail"])
        
        # Override for built-in or mapped known cases
        if response.status_code == 401:
            error_code = getattr(exc, "auth_code", "UNAUTHORIZED")
            if isinstance(response.data, dict) and "detail" in response.data:
                error_message = str(response.data["detail"])
        elif response.status_code == 403:
            if error_code in ["UNKNOWN_ERROR", "PERMISSION_DENIED"]:
                error_code = getattr(exc, "auth_code", "PERMISSION_DENIED")
            if isinstance(response.data, dict) and "detail" in response.data:
                error_message = str(response.data["detail"])
        elif response.status_code == 404:
            error_code = "NOT_FOUND"
            if isinstance(response.data, dict) and "detail" in response.data:
                error_message = str(response.data["detail"])
        elif response.status_code == 429:
            error_code = "RATE_LIMITED"
            if isinstance(response.data, dict) and "detail" in response.data:
                error_message = str(response.data["detail"])
        
        # Build strict canonical response
        canon_response = {
            "error": error_message,
            "code": error_code,
            "details": details if details else {}
        }
        
        response.data = canon_response

    return response
