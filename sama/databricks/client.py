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
        spark_dataframe
    ):
        
        data = spark_dataframe.toPandas().to_dict(orient='records')

        prefix = "output_"

        # Iterate over the list of dictionaries
        for dict_item in data:
            for key, value in dict_item.items():
                if key.startswith(prefix):
                    dict_item[key] = json.loads(dict_item[key])

        return self.sama_client.create_task_batch(proj_id, data)

    def fetch_deliveries_since_timestamp_to_table(self, proj_id, batch_id=None, client_batch_id=None, client_batch_id_match_type=None, from_timestamp=None, task_id=None, page_size=1000):
        
        data = self.sama_client.fetch_deliveries_since_timestamp(proj_id, batch_id=batch_id, client_batch_id=client_batch_id, client_batch_id_match_type=client_batch_id_match_type, from_timestamp=from_timestamp, task_id=task_id, page_size=page_size)

        for data_item in data:
            data_item['answers'] = json.dumps(data_item['answers'])

        # Convert JSON string to RDD
        json_rdd = spark.sparkContext.parallelize(data)
        # Convert RDD to DataFrame
        return spark.read.json(json_rdd)