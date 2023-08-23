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
        requests_session_keep_alive: bool = False,
        requests_session_stream: bool = False,
        silent: bool = True,
        retry_attempts: int = 5,
        retry_delay: float = 2,
        retry_backoff: float = 2,
        logger: Union[logging.Logger, None] = None,
        log_level: int = logging.INFO,
    ) -> None:
        
        self.sama_client = samaClient(api_key, requests_session_keep_alive, requests_session_stream, silent, retry_attempts, retry_delay, retry_backoff, logger, log_level)

    def create_task_batch_from_table(
        self,
        proj_id: str,
        spark_dataframe
    ) -> requests.Response:
        
        data = spark_dataframe.toPandas().to_dict(orient='records')

        prefix = "output_"

        # Iterate over the list of dictionaries
        for dict_item in data:
            for key, value in dict_item.items():
                if key.startswith(prefix):
                    dict_item[key] = json.loads(dict_item[key])

        return self.sama_client.create_task_batch(proj_id, data)

    def fetch_deliveries_since_timestamp_to_table(
        self,
        proj_id, 
        timestamp,
        page_size=1000):
        
        data = self.sama_client.fetch_deliveries_since_timestamp(proj_id,timestamp,page_size)

        for data_item in data:
            data_item['answers'] = json.dumps(data_item['answers'])

        # Convert JSON string to RDD
        json_rdd = spark.sparkContext.parallelize(data)
        # Convert RDD to DataFrame
        return spark.read.json(json_rdd)