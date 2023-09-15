import pytest
import requests
from unittest.mock import patch, Mock

from sama.client import Client, RetriableHTTPExceptions

def test_raise_for_error_code():
    # Test for raising exception on error code in list
    with pytest.raises(RetriableHTTPExceptions, match="Retriable HTTP Error: 429"):
        RetriableHTTPExceptions.raise_for_error_code(429, Mock())

    # Test for not raising exception on error code not in list
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    RetriableHTTPExceptions.raise_for_error_code(400, mock_response)
    mock_response.raise_for_status.assert_called_once()

def test_call_and_retry_http_method_connection_error():
    
    # Mock the requests.get to always raise a ConnectionError
    with patch.object(requests, "get", side_effect=ConnectionError()) as mocked_get:
        
        instance = Client("test_api_key") 
        
        # Since the method has a retry decorator, 
        # the ConnectionError should be raised after MAX_TRIES.
        with pytest.raises(ConnectionError):
            instance._call_and_retry_http_method("some_url", method="GET")

        # Check the number of times the mocked function was called
        expected_retries = RetriableHTTPExceptions.MAX_TRIES
        assert mocked_get.call_count == expected_retries    

@pytest.mark.parametrize(
    "http_method, expected_request_call",
    [("POST", "post"), ("PUT", "put"), ("GET", "get")]
)
@patch('sama.client.requests')
def test_call_and_retry_http_method(mock_requests, http_method, expected_request_call):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "sample response"
    mock_response.json.return_value = {"key": "value"}
    getattr(mock_requests, expected_request_call).return_value = mock_response

    client = Client(api_key="sample_key")

    result = client._call_and_retry_http_method(
        url="http://sample.com",
        payload={},
        params={},
        headers={},
        method=http_method
    )

    assert result == {"key": "value"}
    getattr(mock_requests, expected_request_call).assert_called_once()

@pytest.mark.parametrize(
    "http_method, expected_request_call",
    [("POST", "post"), ("PUT", "put"), ("GET", "get")]
)
@patch('sama.client.requests')
def test_call_and_retry_http_method_empty_response(mock_requests, http_method, expected_request_call):
    mock_response = Mock()
    mock_response.status_code = 204
    mock_response.text = None
    mock_response.json.return_value = None
    getattr(mock_requests, expected_request_call).return_value = mock_response

    client = Client(api_key="sample_key")

    result = client._call_and_retry_http_method(
        url="http://sample.com",
        payload={},
        params={},
        headers={},
        method=http_method
    )

    assert result == None
    getattr(mock_requests, expected_request_call).assert_called_once()

@pytest.mark.parametrize(
    "http_method, expected_request_call",
    [("POST", "post"), ("PUT", "put"), ("GET", "get")]
)
@patch('sama.client.requests')
def test_call_and_retry_http_method_array_response(mock_requests, http_method, expected_request_call):
    mock_response = Mock()
    mock_response.status_code = 202
    mock_response.text = []
    mock_response.json.return_value = []
    getattr(mock_requests, expected_request_call).return_value = mock_response

    client = Client(api_key="sample_key")

    result = client._call_and_retry_http_method(
        url="http://sample.com",
        payload={},
        params={},
        headers={},
        method=http_method
    )

    assert result == []
    getattr(mock_requests, expected_request_call).assert_called_once()


def test_call_and_retry_http_method_retried():
    response_502 = Mock(status_code=502)
    response_200 = Mock(status_code=200)
    response_200.json.return_value = {"success": True}

    client = Client(api_key="sample_key")
    # Mock the requests.post method to return the 502 response first and then the 200 response
    with patch('requests.post', side_effect=[response_502, response_200]) as mock_post:
        result = client._call_and_retry_http_method(url="http://test.com", method="POST")

    assert result == {"success": True}
    assert mock_post.call_count == 2

@pytest.fixture
def client():
    return Client(api_key='test_key')

def test_fetch_paginated_results_no_results(client):
    # Mocked data
    mock_data = {
    }

    with patch.object(client, '_call_and_retry_http_method', return_value=mock_data) as mock_method:
        results = list(client._fetch_paginated_results(
            "https://api.sama.com/test_endpoint",
            payload={},
            params={},
            headers={},
            method="GET"
        ))

        # Check if the results are correctly retrieved
        assert len(results) == 0

        # Check if the mock method was called only once (since it's only one page of data)
        mock_method.assert_called_once()

def test_fetch_paginated_results_single_page(client):
    # Mocked data
    mock_data = {
        'tasks': [
            {'id': 'task_1', 'info': 'test_info_1'},
            {'id': 'task_2', 'info': 'test_info_2'}
        ]
    }

    with patch.object(client, '_call_and_retry_http_method', return_value=mock_data) as mock_method:
        results = list(client._fetch_paginated_results(
            "https://api.sama.com/test_endpoint",
            payload={},
            params={},
            headers={},
            method="GET"
        ))

        # Check if the results are correctly retrieved
        assert len(results) == 2
        assert results[0]['id'] == 'task_1'
        assert results[1]['id'] == 'task_2'

        # Check if the mock method was called only once (since it's only one page of data)
        mock_method.assert_called_once()

def test_fetch_paginated_results_multiple_pages_limit(client):
    # Mocked data
    first_page_data = {
        'tasks': [
            {'id': 'task_1', 'info': 'test_info_1'},
            {'id': 'task_2', 'info': 'test_info_2'}
        ]
    }
    second_page_data = {
        
    }
    
    mock_return_values = [first_page_data, second_page_data]

    with patch.object(client, '_call_and_retry_http_method', side_effect=mock_return_values) as mock_method:
        results = list(client._fetch_paginated_results(
            "https://api.sama.com/test_endpoint",
            payload={},
            params={},
            headers={},
            page_size=2,
            method="GET"
        ))

        # Check if the results are correctly retrieved from both pages
        assert len(results) == 2
        assert results[0]['id'] == 'task_1'
        assert results[1]['id'] == 'task_2'

        # Check if the mock method was called twice (for two pages of data)
        assert mock_method.call_count == 2


def test_fetch_paginated_results_multiple_pages(client):
    # Mocked data
    first_page_data = {
        'tasks': [
            {'id': 'task_1', 'info': 'test_info_1'},
            {'id': 'task_2', 'info': 'test_info_2'}
        ]
    }
    second_page_data = {
        'tasks': [
            {'id': 'task_3', 'info': 'test_info_3'}
        ]
    }
    
    mock_return_values = [first_page_data, second_page_data]

    with patch.object(client, '_call_and_retry_http_method', side_effect=mock_return_values) as mock_method:
        results = list(client._fetch_paginated_results(
            "https://api.sama.com/test_endpoint",
            payload={},
            params={},
            headers={},
            page_size=2,
            method="GET"
        ))

        # Check if the results are correctly retrieved from both pages
        assert len(results) == 3
        assert results[0]['id'] == 'task_1'
        assert results[1]['id'] == 'task_2'
        assert results[2]['id'] == 'task_3'

        # Check if the mock method was called twice (for two pages of data)
        assert mock_method.call_count == 2

def test_cancel_batch_creation_job_success():
    # Initialize a Client instance
    client = Client(api_key="fake_api_key")

    # Mock the response returned from the _call_and_retry_http_method method
    mock_response = {"status": "cancelled"}
    
    # Use the patch decorator to mock out the _call_and_retry_http_method call
    with patch.object(client, '_call_and_retry_http_method', return_value=mock_response) as mock_http_method:
        response = client.cancel_batch_creation_job("project123", "batch456")

        # Assert that the mocked response is returned from the method
        assert response == mock_response

        # Assert that the _call_and_retry_http_method method was called with the expected parameters
        mock_http_method.assert_called_once_with(
            "https://api.sama.com/v2/projects/project123/batches/batch456/cancel.json",
            params={"access_key": "fake_api_key"},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST"
        )


def get_mock_response(json_data, status_code=200):
    mock_resp = Mock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.text = json_data
    return mock_resp

# Test the create_task_batch method
def test_create_task_batch():
    # Mock data
    project_id = "test_project"
    task_data_records = [{"input": "test_data"}]
    
    # Mock API responses
    initial_response = {
        "tasks_put_url": "https://mocked_s3_url.com/upload_here",
        "batch_id": "test_batch_id"
    }
    
    final_response = {
        "success": True
    }

    mock_post_responses = [get_mock_response(initial_response), get_mock_response(final_response)]
    
    def side_effect(*args, **kwargs):
        return mock_post_responses.pop(0)

    with patch('requests.post', side_effect=side_effect) as mock_post, \
         patch('requests.put', return_value=get_mock_response({})) as mock_put:

        client = Client(api_key="test_api_key")
        response = client.create_task_batch(project_id, task_data_records)

        # Check the correct methods were called
        assert mock_post.call_count == 2
        mock_put.assert_called()

        # Validate the response
        assert response == final_response