from sama import Client as samaClient

import pandas as pd
import logging
from typing import Any, Dict, List, Union

import requests
import json

from databricks.sdk.runtime import *

class Client:

    def __init__(
        self,
        api_key: str,
        silent: bool = True,
        logger: Union[logging.Logger, None] = None,
        log_level: int = logging.INFO,
    ) -> None:
        
        self.sama_client = samaClient(api_key, silent, logger, log_level)

    def create_task_batch_from_table(
        self,
        proj_id: str,
        spark_dataframe,
        batch_priority: int = 0,
        notification_email: Union[str, None] = None,
        submit: bool = False,
    ):
        """
        Creates a batch of tasks using data from a DataFrame

        Args:
            proj_id (str): The project ID on SamaHub where tasks are to be created
            spark_dataframe (DataFrame): The list of task "data" dicts
                (inputs + preannotations)
            batch_priority (int): The priority of the batch. Defaults to 0. Negative numbers indicate higher priority
            notification_email (Union[str, None]): The email address where SamaHub
                should send notifications about the batch creation status. Defaults to None
            submit (bool): Whether to create the tasks in submitted state. Defaults to False
        """

        data = spark_dataframe.toPandas().to_dict(orient='records')

        prefix = "output_"

        # Iterate over the list of dictionaries
        for dict_item in data:
            for key, value in dict_item.items():
                if key.startswith(prefix):
                    dict_item[key] = json.loads(dict_item[key])

        return self.sama_client.create_task_batch(proj_id, data)

    def fetch_deliveries_since_timestamp_to_table(self, proj_id, batch_id=None, client_batch_id=None, client_batch_id_match_type=None, from_timestamp=None, task_id=None):
        """
        Fetches all deliveries since a given timestamp(in the
        RFC3339 format) for the specified project and optional filters.
        Returns deliveries in a DataFrame
        
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


        data = self.sama_client.fetch_deliveries_since_timestamp(proj_id, batch_id=batch_id, client_batch_id=client_batch_id, client_batch_id_match_type=client_batch_id_match_type, from_timestamp=from_timestamp, task_id=task_id)

        for data_item in data:
            data_item['answers'] = json.dumps(data_item['answers'])

        # Convert JSON string to RDD
        json_rdd = spark.sparkContext.parallelize(data)
        # Convert RDD to DataFrame
        return spark.read.json(json_rdd)