"""
Tenxyte - Standard pagination classes.

Provides consistent pagination across all list endpoints with:
- Page number pagination (default)
- Configurable page size via query param
- Total count and total pages in response
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict


class TenxytePagination(PageNumberPagination):
    """
    Standard pagination for all Tenxyte list endpoints.

    Usage:
        GET /api/auth/users/?page=1&page_size=20

    Query params:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)

    Response format:
        {
            "count": 150,
            "page": 1,
            "page_size": 20,
            "total_pages": 8,
            "next": "http://.../users/?page=2",
            "previous": null,
            "results": [...]
        }
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('page', self.page.number),
            ('page_size', self.get_page_size(self.request)),
            ('total_pages', self.page.paginator.num_pages),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data),
        ]))

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'required': ['count', 'results'],
            'properties': {
                'count': {
                    'type': 'integer',
                    'description': 'Total number of items',
                    'example': 150,
                },
                'page': {
                    'type': 'integer',
                    'description': 'Current page number',
                    'example': 1,
                },
                'page_size': {
                    'type': 'integer',
                    'description': 'Items per page',
                    'example': 20,
                },
                'total_pages': {
                    'type': 'integer',
                    'description': 'Total number of pages',
                    'example': 8,
                },
                'next': {
                    'type': 'string',
                    'nullable': True,
                    'format': 'uri',
                    'description': 'URL to the next page',
                },
                'previous': {
                    'type': 'string',
                    'nullable': True,
                    'format': 'uri',
                    'description': 'URL to the previous page',
                },
                'results': schema,
            },
        }


class SmallPagination(TenxytePagination):
    """Pagination with smaller default page size (10 items)."""
    page_size = 10


class LargePagination(TenxytePagination):
    """Pagination with larger default page size (50 items)."""
    page_size = 50
