from unittest.mock import patch

from tenxyte.docs.schemas import (
    standard_extend_schema,
    org_extend_schema,
    paginated_extend_schema,
    searchable_extend_schema,
    SUCCESS_RESPONSES,
    STANDARD_ERROR_RESPONSES,
    ORG_HEADER,
    PAGINATION_PARAMS,
    SEARCH_PARAMS
)

@patch('tenxyte.docs.schemas.extend_schema')
def test_standard_extend_schema(mock_extend):
    mock_extend.return_value = 'mock_decorator'
    
    result = standard_extend_schema(tags=['test'])
    
    assert result == 'mock_decorator'
    
    # Assert extend_schema was called with default responses if none provided
    call_args, call_kwargs = mock_extend.call_args
    assert call_kwargs['tags'] == ['test']
    
    expected_responses = SUCCESS_RESPONSES.copy()
    expected_responses.update(STANDARD_ERROR_RESPONSES)
    assert call_kwargs['responses'] == expected_responses
    assert call_kwargs['parameters'] == []

@patch('tenxyte.docs.schemas.extend_schema')
def test_standard_extend_schema_with_custom_responses_and_params(mock_extend):
    mock_extend.return_value = 'mock_decorator'
    
    custom_responses = {200: 'custom'}
    standard_extend_schema(responses=custom_responses, parameters=['param1'])
    
    call_args, call_kwargs = mock_extend.call_args
    assert call_kwargs['responses'] == custom_responses
    assert call_kwargs['parameters'] == ['param1']

@patch('tenxyte.docs.schemas.extend_schema')
def test_org_extend_schema(mock_extend):
    org_extend_schema()
    call_args, call_kwargs = mock_extend.call_args
    assert ORG_HEADER in call_kwargs['parameters']

@patch('tenxyte.docs.schemas.extend_schema')
def test_paginated_extend_schema(mock_extend):
    # Test with existing parameters
    paginated_extend_schema(parameters=['existing'])
    call_args, call_kwargs = mock_extend.call_args
    assert 'existing' in call_kwargs['parameters']
    for param in PAGINATION_PARAMS:
        assert param in call_kwargs['parameters']

@patch('tenxyte.docs.schemas.extend_schema')
def test_searchable_extend_schema(mock_extend):
    searchable_extend_schema()
    call_args, call_kwargs = mock_extend.call_args
    for param in SEARCH_PARAMS:
        assert param in call_kwargs['parameters']
