
import logging
from typing import Any, Dict, List, Union

import requests
from retry import retry

import json

from sama.constants.tasks import TaskStates

class CustomHTTPException(Exception):
    MAX_TRIES = 5
    DELAY = 2
    BACKOFF = 2
    ERROR_CODES = [429, 502, 503, 504]

    @staticmethod
    def raise_for_error_code(response_code):
        if response_code in CustomHTTPException.ERROR_CODES:
            raise CustomHTTPException(f"HTTP Error: {response_code}")

class Client:
    """
    Provides methods to interact with Sama API endpoints
    """

    def __init__(
        self,
        api_key: str,
        requests_session_keep_alive: bool = False,
        requests_session_stream: bool = False,
        silent: bool = True,
        retry_attempts: int = 5,
        retry_delay: float = 2,
        retry_backoff: float = 2,
        logger: Union[logging.Logger, None] = None,
        log_level: int = logging.INFO,
    ) -> None:
        """
        Constructor to initialise the Sama API client

        Args:
            api_key (str): The API key to use for authentication
            requests_session_keep_alive (bool): Preference for corresponding requests.session setting. Defaults to False
            requests_session_stream (bool): Preference for corresponding requests.session setting. Defaults to False
            silent (bool): Whether to suppress all print/log statements. Defaults to False
            retry_attempts (int): The number of times to retry a request before giving up. Defaults to 5
            retry_delay (float): Time in seconds to wait before retrying a request. Defaults to 2
            retry_backoff (float): Factor by which to increase the retry delay after each attempt. Defaults to 2
            logger (Union[Logger, None]): The logger to use for logging.
                Defaults to None, meaning API interaction logs are printed to stdout
                (unless silent is True), and retry logs are not recorded.
            log_level (int): The log level to use for logging. Defaults to logging.INFO (20)

        Note: Setting `keep_alive` and `stream` for the requests session to False has
        historically worked best for avoiding the error "RemoteDisconnected: Remote end closed connection without response"
        """

        self.api_key = api_key
        self.silent = silent

        self.session = requests.session()
        self.session.keep_alive = requests_session_keep_alive
        self.session.stream = requests_session_stream

        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.retry_backoff = retry_backoff

        self.logger = logger
        self.log_level = log_level

    def __log_message(self, message: str, prefix: str = "Sama API: ") -> None:
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

    def create_task_batch(
        self,
        proj_id: str,
        task_data_records: List[Dict[str, Any]],
        batch_priority: int = 0,
        notification_email: Union[str, None] = None,
        submit: bool = False,
    ) -> requests.Response:
        """
        Creates a batch of tasks using the two async batch task creation API endpoints
        (the tasks file upload approach)

        Args:
            proj_id (str): The project ID on SamaHub where tasks are to be created
            task_data_records (List[Dict[str, Any]]): The list of task "data" dicts
                (inputs + preannotations)
            batch_priority (int): The priority of the batch. Defaults to 0
            notification_email (Union[str, None]): The email address where SamaHub
                should send notifications about the batch creation status. Defaults to None
            submit (bool): Whether to create the tasks in submitted state. Defaults to False
        """

        @retry(tries=self.retry_attempts, delay=self.retry_delay, backoff=self.retry_backoff, logger=self.logger)
        def run():
            credentials = {"access_key": self.api_key}

            self.__log_message("Sending batch initialisation request")
            init_url = f"https://api.sama.com/v2/projects/{proj_id}/batches.json"
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            if notification_email != None:
                payload = {"notification_email": notification_email}
                init_resp = self.session.request("POST", init_url, headers=headers, params=credentials, json=payload)
            else:
                init_resp = self.session.request("POST", init_url, headers=headers, params=credentials)
            self.__log_message(f"Batch initialisation response:\n{init_resp.text}")
            init_resp = init_resp.json()

            self.__log_message("Uploading tasks file")
            batch_id = init_resp["batch_id"]
            tasks_put_url = init_resp["tasks_put_url"]
            tasks = []
            for task_data in task_data_records:
                tasks.append({"data": task_data, "priority": batch_priority, "submit": submit})
            payload = tasks
            upload_resp = self.session.request("PUT", tasks_put_url, json=payload, headers=headers)
            self.__log_message(f"Tasks file upload response:\n{upload_resp.text}")

            self.__log_message(f"Sending file-driven batch creation request")
            cont_url = f"https://api.sama.com/v2/projects/{proj_id}/batches/{batch_id}/continue.json"
            headers = {"Accept": "application/json"}
            creation_resp = self.session.request("POST", cont_url, headers=headers, params=credentials)
            self.__log_message(f"Task creation response:\n{creation_resp.text}")

            return creation_resp

        return run()

    def cancel_batch_creation_job(self, proj_id: str, batch_id: str) -> requests.Response:
        """
        cancel batch creation job

        Args:
            proj_id (str): The project ID on SamaHub where the task exists
            batch_id (str): The IDs of the batch to cancel
        """

        @retry(tries=self.retry_attempts, delay=self.retry_delay, backoff=self.retry_backoff, logger=self.logger)
        def run():
            url = f"https://api.sama.com/v2/projects/{proj_id}/batches/{batch_id}/cancel.json"
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            credentials = {"access_key": self.api_key}

            self.__log_message(f"Sending cancel request for batch {batch_id}")
            resp = self.session.request("POST", url, headers=headers, params=credentials)
            self.__log_message(f"batch cancel response:\n{resp.text}")

            return resp

        return run()

    def reject_task(self, proj_id: str, task_id: str, reasons: List[str]) -> requests.Response:
        """
        Rejects a task to send it for rework

        Args:
            proj_id (str): The project ID on SamaHub where the task exists
            task_id (str): The ID of the task to reject
            reasons (List[str]): The list of reasons for rejecting the task
        """

        @retry(tries=self.retry_attempts, delay=self.retry_delay, backoff=self.retry_backoff, logger=self.logger)
        def run():
            url = f"https://api.sama.com/v2/projects/{proj_id}/tasks/{task_id}/reject.json"
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            credentials = {"access_key": self.api_key}
            payload = {"reasons": reasons}

            self.__log_message(f"Sending rejection request for task {task_id}")
            resp = self.session.request("PUT", url, json=payload, headers=headers, params=credentials)
            self.__log_message(f"Task rejection response:\n{resp.text}")

            return resp

        return run()
    
    def update_task_priority(self, proj_id: str, task_ids: List[str], priority: int) -> requests.Response:
        """
        Updates priority of tasks

        Args:
            proj_id (str): The project ID on SamaHub where the task exists
            task_ids (List[str]): The IDs of the tasks to update priority
            priority (int): The priority
        """

        @retry(tries=self.retry_attempts, delay=self.retry_delay, backoff=self.retry_backoff, logger=self.logger)
        def run():
            url = f"https://api.sama.com/v2/projects/{proj_id}/tasks/bulk_update.json"
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            credentials = {"access_key": self.api_key}
            payload = {
                "task_ids": task_ids,
                "priority": priority
            }

            self.__log_message(f"Sending priority update request for tasks {task_ids}")
            resp = self.session.request("POST", url, json=payload, headers=headers, params=credentials)
            self.__log_message(f"Tasks update priority response:\n{resp.text}")

            return resp

        return run()

    def delete_tasks(self, proj_id: str, task_ids: List[str]) -> requests.Response:
        """
        Delete tasks

        Args:
            proj_id (str): The project ID on SamaHub where the task exists
            task_ids (List[str]): The IDs of the tasks to delete
        """

        @retry(tries=self.retry_attempts, delay=self.retry_delay, backoff=self.retry_backoff, logger=self.logger)
        def run():
            url = f"https://api.sama.com/v2/projects/{proj_id}/tasks/delete_tasks.json"
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            credentials = {"access_key": self.api_key}
            payload = {
                "task_ids": task_ids
            }

            self.__log_message(f"Sending delete request for tasks {task_ids}")
            resp = self.session.request("POST", url, json=payload, headers=headers, params=credentials)
            self.__log_message(f"Tasks delete response:\n{resp.text}")

            return resp

        return run()

    def fetch_deliveries_since_timestamp(self, proj_id, timestamp, page_size=1000):
        """
        Fetches all deliveries since a given timestamp (in the
        RFC3339 format)
        """

        url = f"https://api.sama.com/v2/projects/{proj_id}/tasks/delivered.json"
        headers = {"Accept": "application/json"}
        query_params = {"from": timestamp, "page": 1, "page_size": page_size, "access_key": self.api_key}  # dynamic

        tasks = []
        while True:
            self.__log_message(f'Sending delivery request for page #{query_params["page"]}')
            resp = self.session.request("GET", url, headers=headers, params=query_params)
            self.__log_message(f"Delivery request response:\n{resp.text}")

            page_tasks = resp.json()["tasks"]
            tasks += page_tasks
            if page_size != len(page_tasks):
                break
            query_params["page"] += 1

        return tasks

    def fetch_deliveries_since_last_call(self, proj_id, consumer, page_size=1000):
        url = f"https://api.sama.com/v2/projects/{proj_id}/tasks/delivered.json"
        payload = {
            "limit": page_size,
            "consumer": consumer,
        }
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        cred = {"access_key": self.api_key}

        tasks = []
        i = 1
        while True:
            self.__log_message(f"Sending delivery request #{i}")
            response = self.session.request("POST", url, json=payload, headers=headers, params=cred)
            res_tasks = response.json()["tasks"]
            tasks += res_tasks
            self.__log_message(f"Delivery request response:\n{response.text}")
            if len(res_tasks) < page_size:
                break
            i += 1

        return tasks

    def get_task_status(self, proj_id, task_id, same_as_delivery=True):
        """
        Fetches info for a single task
        """

        url = f"https://api.sama.com/v2/projects/{proj_id}/tasks/{task_id}.json"
        headers = {"Accept": "application/json"}
        query_params = {
            "access_key": self.api_key,
            "same_as_delivery": same_as_delivery }

        resp = self.session.request("GET", url, headers=headers, params=query_params)
        self.__log_message(f"Get single tasks status request response:\n{resp.text}")

        return resp.json()["tasks"]

    @retry(CustomHTTPException, tries=CustomHTTPException.MAX_TRIES, delay=CustomHTTPException.DELAY, backoff=CustomHTTPException.BACKOFF)
    def get_multi_task_status(self, proj_id, batch_id=None, client_batch_id=None, client_batch_id_match_type=None, date_type=None, from_timestamp=None, to_timestamp=None, state:TaskStates = None, omit_answers=True, page_size=100):
        """
        Fetches info for multiple tasks
        """

        url = f"https://api.sama.com/v2/projects/{proj_id}/tasks.json"
        headers = {"Accept": "application/json"}
        query_params = {
            "access_key": self.api_key,
            "batch_id": batch_id,
            "client_batch_id": client_batch_id,
            "client_batch_id_match_type": client_batch_id_match_type,
            "date_type":date_type,
            "from":from_timestamp,
            "to":to_timestamp,
            "state":state.value,
            "omit_answers":omit_answers,
            "page": 1, 
            "page_size": page_size, }  # dynamic

        tasks = []
        while True:
            self.__log_message(f'Sending tasks request for page #{query_params["page"]}')
            resp = self.session.request("GET", url, headers=headers, params=query_params)
            self.__log_message(f"Get multi status request response:\n{resp.text}")

            CustomHTTPException.raise_for_error_code(resp.status_code)

            page_tasks = resp.json()["tasks"]
            tasks += page_tasks
            if page_size != len(page_tasks):
                break
            query_params["page"] += 1

        return tasks
    
    def get_status_batch_creation_job(self, proj_id, batch_id, omit_failed_task_data=False, page_size=1000):
        """
        Fetches batch creation job info
        """

        url = f"https://api.sama.com/v2/projects/{proj_id}/batches/{batch_id}.json"
        headers = {"Accept": "application/json"}
        query_params = {
            "access_key": self.api_key,
            "batch_id": batch_id,
            "omit_failed_task_data":omit_failed_task_data,
            "page": 1, 
            "page_size": page_size, }  # dynamic

        tasks = []
        while True:
            self.__log_message(f'Get batch creation job status for page #{query_params["page"]}')
            resp = self.session.request("GET", url, headers=headers, params=query_params)
            self.__log_message(f"Get batch creation job status response:\n{resp.text}")

            page_tasks = resp.json()["tasks"]
            tasks += page_tasks
            if page_size != len(page_tasks):
                break
            query_params["page"] += 1

        resp_json = resp.json()
        resp_json['tasks'] = tasks

        return resp_json
    