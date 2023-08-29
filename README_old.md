

## Sama SDK

This is the Python Client for the [Sama API endpoints](https://docs.sama.com/reference/documentation) and Databricks Connector.

### Usage

```python
from sama import Client
client = Client("your_api_key")
client.create_task_batch("project_id", [{"input1": "value1", "input2": "value2"}])
client.fetch_deliveries_since_timestamp("project_id", timestamp)
```

```python
from sama.databricks import Client
client = Client("your_api_key")
client.create_task_batch_from_table("project_id", df)
df = client.fetch_deliveries_since_timestamp_to_table("project_id", timestamp)
```

---

## sama Client

This class provides methods to interact with Sama API endpoints.

### `__init__` method

This method is the constructor to initialize the Sama API client.

#### Parameters

- `api_key` (str): The API key to use for authentication.
- `requests_session_keep_alive` (bool, optional): Preference for corresponding requests.session setting. Defaults to `False`.
- `requests_session_stream` (bool, optional): Preference for corresponding requests.session setting. Defaults to `False`.
- `silent` (bool, optional): Whether to suppress all print/log statements. Defaults to `True`.
- `retry_attempts` (int, optional): The number of times to retry a request before giving up. Defaults to `5`.
- `retry_delay` (float, optional): Time in seconds to wait before retrying a request. Defaults to `2`.
- `retry_backoff` (float, optional): Factor by which to increase the retry delay after each attempt. Defaults to `2`.
- `logger` (Union[Logger, None], optional): The logger to use for logging. Defaults to `None`.
- `log_level` (int, optional): The log level to use for logging. Defaults to `logging.INFO`.

### `create_task_batch` method

This method creates a batch of tasks using the two async batch task creation API endpoints (the tasks file upload approach).

#### Parameters

- `proj_id` (str): The project ID on SamaHub where tasks are to be created.
- `task_data_records` (List[Dict[str, Any]]): The list of task "data" dicts (inputs + preannotations).
- `batch_priority` (int, optional): The priority of the batch. Defaults to `0`.
- `notification_email` (Union[str, None], optional): The email address where SamaHub should send notifications about the batch creation status. Defaults to `None`.
- `submit` (bool, optional): Whether to create the tasks in submitted state. Defaults to `False`.

### `reject_task` method

This method rejects a task to send it for rework.

#### Parameters

- `proj_id` (str): The project ID on SamaHub where the task exists.
- `task_id` (str): The ID of the task to reject.
- `reasons` (List[str]): The list of reasons for rejecting the task.

### `fetch_deliveries_since_timestamp` method

This method fetches all deliveries since a given timestamp (in the RFC3339 format).

#### Parameters

- `proj_id` (str): The project ID on SamaHub.
- `timestamp` (str): The RFC3339 formatted timestamp.
- `page_size` (int, optional): The number of deliveries per page. Defaults to `1000`.

### `fetch_deliveries_since_last_call` method

This method fetches all deliveries since the last API call.

#### Parameters

- `proj_id` (str): The project ID on SamaHub.
- `consumer` (str): The name of the consumer.
- `page_size` (int, optional): The number of deliveries per page. Defaults to `1000`.


## sama.databricks Client

### `create_task_batch_from_table` method

This method creates a batch of tasks from a Spark DataFrame.

#### Parameters

- `proj_id` (str): The project ID on SamaHub where tasks are to be created.
- `spark_dataframe` (DataFrame): The Spark DataFrame to be converted to task data records.

### `fetch_deliveries_since_timestamp_to_table` method

This method fetches all deliveries since a given timestamp and converts them to a Spark DataFrame.

#### Parameters

- `proj_id` (str): The project ID on SamaHub.
- `timestamp` (str): The RFC3339 formatted timestamp.
- `page_size` (int, optional): The number of deliveries per page. Defaults to `1000`.