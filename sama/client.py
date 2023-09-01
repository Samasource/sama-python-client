
import logging
from typing import Any, Dict, List, Union

import requests, json
from retry import retry

from sama.constants.tasks import TaskStates

class CustomHTTPException(Exception):
    MAX_TRIES = 5
    DELAY = 1
    BACKOFF = 2
    ERROR_CODES = [429, 502, 503, 504] #429 API Rate limit reached

    @staticmethod
    def raise_for_error_code(response_code, response):
        if response_code in CustomHTTPException.ERROR_CODES:
            raise CustomHTTPException(f"Retriable HTTP Error: {response_code}")
        else:
            response.raise_for_status()

class Client:
    """
    Provides methods to interact with Sama API endpoints.
    Automatically retries http calls using delay, backoff on API rate limit or 502,503,504 errors.
    Streams paginated results
    """

    def __init__(
        self,
        api_key: str,
        silent: bool = True,
        logger: Union[logging.Logger, None] = None,
        log_level: int = logging.INFO,
    ) -> None:
        """
        Constructor to initialise the Sama API client

        Args:
            api_key (str): The API key to use for authentication
            silent (bool): Whether to suppress all print/log statements. Defaults to False
            logger (Union[Logger, None]): The logger to use for logging.
                Defaults to None, meaning API interaction logs are printed to stdout
                (unless silent is True), and retry logs are not recorded.
            log_level (int): The log level to use for logging. Defaults to logging.INFO (20)

        Note: Setting `keep_alive` and `stream` for the requests session to False has
        historically worked best for avoiding the error "RemoteDisconnected: Remote end closed connection without response"
        """

        self.api_key = api_key
        self.silent = silent

        self.logger = logger
        self.log_level = log_level

    def _log_message(self, message: str, prefix: str = "Sama API: ") -> None:
        """
        Logs a message. Currently prints to stdout, may support optionally using logger in the future

        Args:
            message (str): The message to log
            prefix (str): The prefix to add to the message. Defaults to "Sama API: "
        """
        if not self.silent:
            if self.logger is not None:
                self.logger.log(self.log_level, prefix + message)
            else:
                print(prefix + message)

    @retry(CustomHTTPException, tries=CustomHTTPException.MAX_TRIES, delay=CustomHTTPException.DELAY, backoff=CustomHTTPException.BACKOFF)
    def _call_and_retry_http_method(self, url, json=None, params=None, headers=None, method=None):

        if method == "POST":
            response = requests.post(url, json=json, params=params, headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=json, params=params, headers=headers)
        elif method == "GET":
            response = requests.get(url, params=params, headers=headers)

        CustomHTTPException.raise_for_error_code(response.status_code, response)

        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            return None
        
    def _fetch_paginated_results(self, url, json, params, headers, page_size=1000, method=None):
        page_number = 1  # Start from the first page
        
        while True:
            params.update({
                'page': page_number,
                'page_size': page_size
            })
            
            data = self._call_and_retry_http_method(url, json=json, params=params, headers=headers, method=method)

            if not data or not data['tasks']:  # if data is an empty list or equivalent
                break

            for item in data['tasks']:
                yield item

            if len(data['tasks']) < page_size: # nothing in next page
                break

            page_number += 1  # increment to fetch the next page

    def create_task_batch(
        self,
        proj_id: str,
        task_data_records: List[Dict[str, Any]],
        batch_priority: int = 0,
        notification_email: Union[str, None] = None,
        submit: bool = False,
    ):
        """
        Creates a batch of tasks using the two async batch task creation API endpoints
        (the tasks file upload approach)

        Args:
            proj_id (str): The project ID on SamaHub where tasks are to be created
            task_data_records (List[Dict[str, Any]]): The list of task "data" dicts
                (inputs + preannotations)
            batch_priority (int): The priority of the batch. Defaults to 0. Negative numbers indicate higher priority
            notification_email (Union[str, None]): The email address where SamaHub
                should send notifications about the batch creation status. Defaults to None
            submit (bool): Whether to create the tasks in submitted state. Defaults to False
        """

        url = f"https://api.sama.com/v2/projects/{proj_id}/batches.json"
        headers = { "Accept": "application/json", "Content-Type": "application/json"}
        json = { "notification_email": notification_email }
        params = { "access_key": self.api_key }

        # construct the tasks list, which contains objects with data(inputs, pre-annotations), priority and whether to submit
        tasks = []
        for task_data in task_data_records:
            tasks.append({
                "data": task_data,
                "priority": batch_priority, 
                "submit": submit
            })

        # call the 'create a batch of tasks' endpoint without the tasks list. It'll return a batch_id and a tasks_put_url(AWS S3) in which we'll upload the tasks to instead to avoid the 1000 tasks limit
        json_response = self._call_and_retry_http_method(url=url, json=json, params=params, headers=headers, method="POST") 
        
        # upload tasks directly to AWS S3 pre-signed url
        self._call_and_retry_http_method(url=json_response["tasks_put_url"], json=tasks, params=None, headers=headers, method="PUT")
        
        # call the 'create a batch of tasks from an uploaded file' endpoint to signal file was uploaded and start creating tasks from it
        batch_id = json_response["batch_id"]
        url = f"https://api.sama.com/v2/projects/{proj_id}/batches/{batch_id}/continue.json"
        return self._call_and_retry_http_method(url=url, headers=headers, params=params, method="POST")

    def cancel_batch_creation_job(self, proj_id: str, batch_id: str):
        """
        cancel batch creation job

        Args:
            proj_id (str): The project ID on SamaHub where the task exists
            batch_id (str): The IDs of the batch to cancel
        """
        url = f"https://api.sama.com/v2/projects/{proj_id}/batches/{batch_id}/cancel.json"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        params = {"access_key": self.api_key}

        return self._call_and_retry_http_method(url, params=params, headers=headers, method="POST")

    def reject_task(self, proj_id: str, task_id: str, reasons: List[str]) -> requests.Response:
        """
        Rejects a task to send it for rework

        Args:
            proj_id (str): The project ID on SamaHub where the task exists
            task_id (str): The ID of the task to reject
            reasons (List[str]): The list of reasons for rejecting the task
        """

        url = f"https://api.sama.com/v2/projects/{proj_id}/tasks/{task_id}/reject.json"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        json = {"reasons": reasons}
        params = {"access_key": self.api_key}

        return self._call_and_retry_http_method(url, json=json, params=params, headers=headers, method="PUT")
    
    def update_task_priorities(self, proj_id: str, task_ids: List[str], priority: int):
        """
        Updates priority of tasks

        Args:
            proj_id (str): The project ID on SamaHub where the task exists
            task_ids (List[str]): The IDs of the tasks to update priority
            priority (int): The priority
        """

        url = f"https://api.sama.com/v2/projects/{proj_id}/tasks/bulk_update.json"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        json = {
                "task_ids": task_ids,
                "priority": priority
        }
        params = {"access_key": self.api_key}

        return self._call_and_retry_http_method(url, json=json, params=params, headers=headers, method="POST")

    def delete_tasks(self, proj_id: str, task_ids: List[str]):
        """
        Delete tasks

        Args:
            proj_id (str): The project ID on SamaHub where the task exists
            task_ids (List[str]): The IDs of the tasks to delete
        """

        url = f"https://api.sama.com/v2/projects/{proj_id}/tasks/delete_tasks.json"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        json = {
                "task_ids": task_ids
        }
        params = {"access_key": self.api_key}

        return self._call_and_retry_http_method(url, json=json, params=params, headers=headers, method="POST")

    def get_task_status(self, proj_id, task_id, same_as_delivery=True):
        """
        Fetches task info for a single task
        https://docs.sama.com/reference/singletaskstatus

        Args:
            proj_id (str): The unique identifier of the project on SamaHub. 
                            Specifies the project under which the task resides.
            
            task_id (str): The unique identifier of the task within the specified 
                            project on SamaHub. Identifies the specific task for 
                            which the status is being requested.

            same_as_delivery (bool, optional): Flag to determine the format of the 
                                                task data to be returned. If True (default),
                                                task data is returned in the same format 
                                                as delivery.
    
        """

        url = f"https://api.sama.com/v2/projects/{proj_id}/tasks/{task_id}.json"
        headers = {"Accept": "application/json"}
        query_params = {
            "access_key": self.api_key,
            "same_as_delivery": same_as_delivery }

        return next(self._fetch_paginated_results(url, json=None, params=query_params, headers=headers, method="GET"))


    def get_multi_task_status(self, proj_id, batch_id=None, client_batch_id=None, client_batch_id_match_type=None, date_type=None, from_timestamp=None, to_timestamp=None, state:TaskStates = None, omit_answers=True):
        """     
        Fetches task info for multiple tasks based on the provided filters.
        Returns generator object that is iterable.
        https://docs.sama.com/reference/multitaskstatus

        Args:
            proj_id (str): The unique identifier of the project on SamaHub. Specifies 
                        the project under which the tasks reside.

            batch_id (str, optional): The identifier for a batch within the project. 
                                    If provided, filters tasks that belong to this batch.

            client_batch_id (str, optional): The client-specific identifier for a batch. 
                                            Useful for filtering tasks based on client-defined batches.

            client_batch_id_match_type (str, optional): Specifies how the client_batch_id 
                                                        should be matched. Common options might 
                                                        include "exact" or "contains".

            date_type (str, optional): Determines which date to use for the timestamp 
                                    filters. Examples might include "creation_date" or "completion_date".

            from_timestamp (str, optional): Filters tasks that have a date (specified by date_type) 
                                            after this timestamp.

            to_timestamp (str, optional): Filters tasks that have a date (specified by date_type) 
                                        before this timestamp.

            state (TaskStates, optional): An enum value that specifies the desired status of the 
                                        tasks to filter. For example, "delivered" or "acknowledged".

            omit_answers (bool, optional): Flag to determine if answers related to tasks should 
                                        be omitted from the response. Defaults to True.

        """

        url = f"https://api.sama.com/v2/projects/{proj_id}/tasks.json"
        headers = {"Accept": "application/json"}
        t_state = getattr(state, 'value', None)
        query_params = {
            "access_key": self.api_key,
            "batch_id": batch_id,
            "client_batch_id": client_batch_id,
            "client_batch_id_match_type": client_batch_id_match_type,
            "date_type":date_type,
            "from":from_timestamp,
            "to":to_timestamp,
            "state":t_state,
            "omit_answers":omit_answers
        } 
        page_size=100

        return self._fetch_paginated_results(url, json=None, params=query_params, headers=headers, page_size=page_size, method="GET")
  
    def get_delivered_tasks(self, proj_id, batch_id=None, client_batch_id=None, client_batch_id_match_type=None, from_timestamp=None, task_id=None):
        """
        Fetches all deliveries since a given timestamp(in the
        RFC3339 format) for the specified project or other optional filters.
        Returns generator object that is iterable.
        
        Args:
            proj_id (str): The unique identifier of the project on SamaHub. Specifies 
                        the project under which the deliveries reside.

            batch_id (str, optional): The identifier for a batch within the project. 
                                    If provided, filters deliveries that belong to this batch.

            client_batch_id (str, optional): The client-specific identifier for a batch. 
                                            Useful for filtering deliveries based on client-defined batches.

            client_batch_id_match_type (str, optional): Specifies how the client_batch_id 
                                                        should be matched. Common options might 
                                                        include "exact" or "contains".

            from_timestamp (str, optional): Filters deliveries that have a date 
                                            after this timestamp.

            task_id (str, optional): The unique identifier for a specific task. If provided, 
                                    fetches deliveries related to this specific task.
        """

        url = f"https://api.sama.com/v2/projects/{proj_id}/tasks/delivered.json"
        headers = {"Accept": "application/json"}
        query_params = {
            "access_key": self.api_key,
            "batch_id": batch_id,
            "client_batch_id": client_batch_id,
            "client_batch_id_match_type": client_batch_id_match_type,
            "from": from_timestamp,
            "task_id": task_id
        } 
        page_size=1000

        return self._fetch_paginated_results(url, json=None, params=query_params, headers=headers, page_size=page_size, method="GET")
    
    def get_delivered_tasks_since_last_call(self, proj_id, batch_id=None, client_batch_id=None, client_batch_id_match_type=None, consumer=None):
        """
        Fetches all deliveries since last call based on a consumer token.
        Returns generator object that is iterable.

        Args:
            proj_id (str): The unique identifier of the project on SamaHub. Specifies 
                        the project under which the deliveries reside.

            batch_id (str, optional): The identifier for a batch within the project. 
                                    If provided, filters deliveries that belong to this batch.

            client_batch_id (str, optional): The client-specific identifier for a batch. 
                                            Useful for filtering deliveries based on client-defined batches.

            client_batch_id_match_type (str, optional): Specifies how the client_batch_id 
                                                        should be matched. Common options might 
                                                        include "exact" or "contains".

            consumer (str, optional): Token that identifies the caller, so different consumers 
                                      can be in different places of the delivered tasks list.
        """

        url = f"https://api.sama.com/v2/projects/{proj_id}/tasks/delivered.json"
        query_params = {
            "access_key": self.api_key,
        }
        limit=1000
        payload = {
            "batch_id": batch_id,
            "client_batch_id": client_batch_id,
            "client_batch_id_match_type": client_batch_id_match_type,
            "consumer": consumer,
            "limit": limit
        }
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        

        return self._fetch_paginated_results(url, json=payload, params=query_params, headers=headers, page_size=limit, method="POST")


    def get_status_batch_creation_job(self, proj_id, batch_id, omit_failed_task_data=False):
        """
        Retrieves the status of a batch creation job in the SamaHub project.
        Returns generator object that is iterable.
        
        Args:
            proj_id (str): The unique identifier of the project on SamaHub. Specifies 
                        the project under which the batch resides.

            batch_id (str): The identifier for the batch within the project. This batch's 
                            creation status will be fetched.

            omit_failed_task_data (bool, optional): If set to True, the returned information 
                                                will not include data related to tasks that 
                                                failed during the batch creation. Defaults to False.
        """

        url = f"https://api.sama.com/v2/projects/{proj_id}/batches/{batch_id}.json"
        headers = {"Accept": "application/json"}
        query_params = {
            "access_key": self.api_key,
            "batch_id": batch_id,
            "omit_failed_task_data":omit_failed_task_data
        } 
        page_size=1000

        return self._fetch_paginated_results(url, json=None, params=query_params, headers=headers, page_size=page_size, method="GET")
  
    