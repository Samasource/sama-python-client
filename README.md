

## Sama Python SDK and Databricks Connector

This is the Python Client for the [Sama API endpoints](https://docs.sama.com/reference/documentation) and Databricks Connector.

See our [Python SDK tutorial](https://github.com/Samasource/sama-python-client/blob/main/Sama_Python_SDK_Tutorial.ipynb) and [Databricks Connector tutorial](https://github.com/Samasource/sama-python-client/blob/main/Sama_Databricks_Connector_Tutorial.ipynb).

### Usage

#### Python Client
```python
from sama import Client

client = Client("your_api_key")
client.create_task_batch("project_id", [{"url": "https://yoururl.com/img.jpg", "input2": "value2"}])
client.get_delivered_tasks("project_id", from_timestamp="2023-09-02T10:23:36.536167366Z")
```

#### Databricks Connector
```python
from sama.databricks import Client

client = Client("your_api_key")
client.create_task_batch_from_table("project_id", spark_df) # spark_df contains inputs to tasks
spark_df = client.get_delivered_tasks_to_table(spark, "project_id", from_timestamp="2023-09-02T10:23:36.536167366Z")

```

---

## sama Client

This class provides methods to interact with SamaHub API endpoints.

### `__init__` method

This method is the constructor to initialize the SamaHub API client.

#### Parameters

- `api_key` (str): The API key to use for authentication.
- `silent` (bool, optional): Whether to suppress all print/log statements. Defaults to `True`.
- `logger` (Logger, optional): The logger to use for logging. Defaults to `None`.
- `log_level` (int, optional): The log level to use for logging. Defaults to `logging.INFO`.

---

### `create_task_batch`

This method creates a batch of tasks on SamaHub using the asynchronous batch task creation API endpoints, specifically the tasks file upload approach.

#### Parameters

- `proj_id (str)`: The project ID on SamaHub where tasks will be created.
  
- `task_data_records (List[Dict[str, Any]])`: A list of task "data" dictionaries which can contain inputs and pre-annotations.

- `batch_priority (int, default=0)`: The priority of the batch. A negative number indicates a higher priority.

- `notification_email (Union[str, None], default=None)`: An email address where SamaHub will send notifications about the batch creation status. 

- `submit (bool, default=False)`: A flag determining whether to create the tasks in a submitted state.

#### Returns

- A JSON response from the last `create a batch of tasks from an uploaded file` endpoint call.

#### Description

The method first constructs a tasks list with data, priority, and submission status. It then calls the 'create a batch of tasks' endpoint without providing the actual tasks list. This initial call returns a batch ID and a tasks_put_url (a pre-signed AWS S3 URL), which allows for the tasks to be uploaded directly to S3. This method bypasses the 1000 tasks limit. After uploading the tasks to S3, a subsequent API call is made to notify the system that the tasks are uploaded and to begin the task creation process.

---

### `cancel_batch_creation_job`

Cancels an ongoing batch creation job.

**Parameters:**
- `proj_id (str)`: The project ID on SamaHub where the task exists.
- `batch_id (str)`: The ID of the batch to cancel.

**Returns:**
- Response from the API endpoint.

---


---

### `reject_task`

Rejects a task on SamaHub to send it back for rework.

**Parameters:**
- `proj_id (str)`: The project ID on SamaHub where the task exists.
- `task_id (str)`: The ID of the task to reject.
- `reasons (List[str])`: List of reasons for rejecting the task.

**Returns:**
- Response from the API endpoint.

---

Updates priority of tasks

**Parameters:**
- `project_id (str)`: The project ID on SamaHub where the task exists.
- `task_ids (List[str])`: The IDs of the tasks to update priority.
- `priority (int)`: The priority.

**Returns:**
- Response from the API endpoint.

---

Delete tasks

**Parameters:**
- `project_id (str)`: The project ID on SamaHub where the task exists.
- `task_ids (List[str])`: The IDs of the tasks to delete.

**Returns:**
- Response from the API endpoint.

---

### `get_task_status`

Fetches the status and details of a single task. More details can be found in the [Sama documentation](https://docs.sama.com/reference/singletaskstatus).

**Parameters:**
- `proj_id`: The project ID on SamaHub.
- `task_id`: The ID of the task to fetch.
- `same_as_delivery (default=True)`: Whether to fetch the task as it would be delivered.

**Returns:**
- Task details from the API.

---

### `get_multi_task_status`

Fetches status and details for multiple tasks. Returns a generator object. More details can be found in the [Sama documentation](https://docs.sama.com/reference/multitaskstatus).

**Parameters:**
- `proj_id (str)`: The unique identifier of the project on SamaHub. This parameter specifies the project under which the tasks reside.
- `batch_id (str, optional)`: The identifier for a batch within the project. If provided, it filters tasks that belong to this specific batch.
- `client_batch_id (str, optional)`: The client-specific identifier for a batch. This is useful for filtering tasks based on client-defined batches.
- `client_batch_id_match_type (str, optional)`: This parameter specifies how the `client_batch_id` should be matched. Common options might include "exact" or "contains".
- `date_type (str, optional)`: Determines which date to use for the timestamp filters. Examples might include "creation_date" or "completion_date".
- `from_timestamp (str, optional)`: Filters tasks that have a date (specified by `date_type`) after this timestamp.
- `to_timestamp (str, optional)`: Filters tasks that have a date (specified by `date_type`) before this timestamp.
- `state (TaskStates, optional)`: An enum value that specifies the desired status of the tasks to filter. For example, "delivered" or "acknowledged".
- `omit_answers (bool, optional)`: Flag to determine if answers related to tasks should be omitted from the response. Defaults to True.

**Returns:**
- An iterable generator object with task details.

---

### `get_delivered_tasks`

Get all task deliveries since a given timestamp (RFC3339 format).

**Parameters**:
- `proj_id (str)`: The unique identifier of the project on SamaHub. It specifies the project under which the deliveries reside.
- `batch_id (str, optional)`: The identifier for a batch within the project. If provided, it filters deliveries that belong to this specific batch.
- `client_batch_id (str, optional)`: The client-specific identifier for a batch. This is useful for filtering deliveries based on client-defined batches.
- `client_batch_id_match_type (str, optional)`: Specifies how the `client_batch_id` should be matched. Common options might include "exact" or "contains".
- `from_timestamp (str, optional)`: Filters deliveries that have a date after this timestamp.
- `task_id (str, optional)`: The unique identifier for a specific task. If provided, it fetches deliveries related to this specific task.

**Returns:**
- An iterable generator object with task deliveries.

---

### `get_deliveried_tasks_since_last_call`

Fetches all task deliveries since the last call based on a consumer token.

**Parameters**:
- `proj_id (str)`: The unique identifier of the project on SamaHub. It specifies the project under which the deliveries reside.
- `batch_id (str, optional)`: The identifier for a batch within the project. If provided, it filters deliveries that belong to this specific batch.
- `client_batch_id (str, optional)`: The client-specific identifier for a batch. This is useful for filtering deliveries based on client-defined batches.
- `client_batch_id_match_type (str, optional)`: Specifies how the `client_batch_id` should be matched. Common options might include "exact" or "contains".
- `consumer (str, optional)``: Token that identifies the caller, so different consumers can be in different places of the delivered tasks list.

**Returns:**
- An iterable generator object with task deliveries.

---

### `get_status_batch_creation_job`

Fetches information about a batch creation job.

**Parameters:**
- `proj_id`: The project ID on SamaHub.
- `batch_id`: The ID of the batch to fetch details for.
- `omit_failed_task_data (default=False)`: Whether to omit data about failed tasks.

**Returns:**
- Batch creation job details.

---

### `get_creation_task_schema`

Fetches the JSON schema for task creation on SamaHub.

**Parameters:**
- `project_id (str)`: The project ID on SamaHub.

**Returns:**
- A dictionary containing the JSON schema for task creation.

---

### `get_delivery_task_schema`

Fetches the JSON schema for task deliveries on SamaHub.

**Parameters:**
- `project_id (str)`: The project ID on SamaHub.

**Returns:**
- A dictionary containing the JSON schema for task deliveries.

---

### `get_project_information`

Fetches high-level information about a project from SamaHub.

**Parameters:**
- `project_id (str)`: The project ID on SamaHub.

**Returns:**
- A dictionary containing information about the project.

---

### `get_project_stats`

Fetches high-level statistics about a project's tasks within a specified time frame from SamaHub.

**Parameters:**
- `project_id (str)`: The project ID on SamaHub.
- `from_timestamp (str, optional)`: Filters tasks that have a date after this timestamp.
- `to_timestamp (str, optional)`: Filters tasks that have a date before this timestamp.

**Returns:**
- A dictionary containing project statistics.

---

## sama.databricks Client

### `create_task_batch_from_table` method

Creates a batch of tasks using data from a DataFrame.
Each DataFrame column will be used as an input to the task creation, e.g. url='https://wiki.com/img.jpg', client_batch_id='batch1'
Prepend 'output_' to column to specify pre-annotations
Return JSON - batch_id if successful

**Parameters:**

- `spark_dataframe (DataFrame)`: The Spark DataFrame to be converted to task data records.
- `project_id (str)`: The project ID on SamaHub where tasks are to be created.
- `batch_priority (int)`: The priority of the batch. Defaults to 0. Negative numbers indicate higher priority
- `notification_email (Union[str, None])`: The email address where SamaHub should send notifications about the batch creation status. Defaults to None
- `submit (bool)`: Whether to create the tasks in submitted state. Defaults to False

**Returns:**
JSON - batch_id if successful

---

### `get_delivered_tasks_to_table` method

This method fetches all deliveries since a given timestamp

**Parameters:**

- `spark (SparkSession)` : A spark session
- `project_id (str)`: The unique identifier of the project on SamaHub. Specifies the project under which the deliveries reside.
- `batch_id (str, optional)`: The identifier for a batch within the project. If provided, filters deliveries that belong to this batch.
- `client_batch_id (str, optional)`: The client-specific identifier for a batch. Useful for filtering deliveries based on client-defined batches.
- `client_batch_id_match_type (str, optional)`: Specifies how the `client_batch_id` should be matched. Common options might include "exact" or "contains".
- `from_timestamp (str, optional)`: Filters deliveries that have a date after this timestamp.
- `task_id (str, optional)`: The unique identifier for a specific task. If provided, fetches deliveries related to this specific task.

**Returns:**

Returns deliveries in a DataFrame.

---

### `get_delivered_tasks_since_last_call_to_table` method

Fetches all deliveries since the last call based on a consumer token. 

**Parameters:**

- `spark (SparkSession)` : A spark session
- `project_id (str)`: The unique identifier of the project on SamaHub. Specifies the project under which the deliveries reside.
- `batch_id (str, optional)`: The identifier for a batch within the project. If provided, filters deliveries that belong to this batch.
- `client_batch_id (str, optional)`: The client-specific identifier for a batch. Useful for filtering deliveries based on client-defined batches.
- `client_batch_id_match_type (str, optional)`: Specifies how the `client_batch_id` should be matched. Common options might include "exact" or "contains".
- `consumer (str, optional)`: Token that identifies the caller, so different consumers can be in different places of the delivered tasks list.

**Returns:**

Returns deliveries in a DataFrame.

---

### `get_task_status_to_table`

Fetches the status and details of a single task. More details can be found in the [Sama documentation](https://docs.sama.com/reference/singletaskstatus).

**Parameters:**
- `spark (SparkSession)` : A spark session
- `project_id`: The project ID on SamaHub.
- `task_id`: The ID of the task to fetch.
- `same_as_delivery (default=True)`: Whether to fetch the task as it would be delivered.

**Returns:**
- A DataFrame containing the task status

---

### `get_multi_task_status_to_table`

Fetches status and details for multiple tasks. More details can be found in the [Sama documentation](https://docs.sama.com/reference/multitaskstatus).

**Parameters:**
- `spark (SparkSession)` : A spark session
- `project_id (str)`: The unique identifier of the project on SamaHub. This parameter specifies the project under which the tasks reside.
- `batch_id (str, optional)`: The identifier for a batch within the project. If provided, it filters tasks that belong to this specific batch.
- `client_batch_id (str, optional)`: The client-specific identifier for a batch. This is useful for filtering tasks based on client-defined batches.
- `client_batch_id_match_type (str, optional)`: This parameter specifies how the `client_batch_id` should be matched. Common options might include "exact" or "contains".
- `date_type (str, optional)`: Determines which date to use for the timestamp filters. Examples might include "creation_date" or "completion_date".
- `from_timestamp (str, optional)`: Filters tasks that have a date (specified by `date_type`) after this timestamp.
- `to_timestamp (str, optional)`: Filters tasks that have a date (specified by `date_type`) before this timestamp.
- `state (TaskStates, optional)`: An enum value that specifies the desired status of the tasks to filter. For example, "delivered" or "acknowledged".
- `omit_answers (bool, optional)`: Flag to determine if answers related to tasks should be omitted from the response. Defaults to True.

**Returns:**
- A DataFrame with tasks and their status

 
