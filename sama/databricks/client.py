from sama import Client as samaClient
from sama.constants.tasks import TaskStates

import pandas as pd
import logging
from typing import Any, Dict, List, Union
from typing import Optional

import requests
import json

#from databricks.sdk.runtime import *
from pyspark.sql import SparkSession
from pyspark.sql import DataFrame

class Client(samaClient):

    def create_task_batch_from_table(
        self,
        spark_dataframe: DataFrame,
        project_id: str,
        batch_priority: int = 0,
        notification_email: Union[str, None] = None,
        submit: bool = False,
    ):
        """
        Creates a batch of tasks using data from a DataFrame.
        Each DataFrame column will be used as an input to the task creation, e.g. url='https://wiki.com/img.jpg', client_batch_id='batch1'
        Prepend 'output_' to column to specify pre-annotations
        Return JSON - batch_id if successful

        Args:
            spark_dataframe (DataFrame): The list of task "data"
                (inputs + preannotations)
            project_id (str): The project ID on SamaHub where tasks are to be created
            batch_priority (int): The priority of the batch. Defaults to 0. Negative numbers indicate higher priority
            notification_email (Union[str, None]): The email address where SamaHub
                should send notifications about the batch creation status. Defaults to None
            submit (bool): Whether to create the tasks in submitted state. Defaults to False
        """

        data = spark_dataframe.toPandas().to_dict(orient='records')

        prefix = "output_"

        # Convert pre-annotations(columns with output_) that are represented as JSON strings to a dictionary.
        for dict_item in data:
            for key, value in list(dict_item.items()):  # Use list() to avoid runtime modification issues
                if key.startswith(prefix) and value is not None and isinstance(value, str):  # Ensure value is not None and is a string
                    dict_item[key] = json.loads(value)

        return super().create_task_batch(project_id, task_data_records=data, batch_priority=batch_priority, notification_email=notification_email, submit=submit)

    def transform_nested_answers_json(data_gen):
        for data in data_gen:
            if 'answers' in data:
                data['answers'] = json.dumps(data['answers'])

            yield data

    def get_delivered_tasks_to_table(self, spark: SparkSession, project_id, batch_id: Optional[str]=None, client_batch_id: Optional[str]=None, client_batch_id_match_type: Optional[str]=None, from_timestamp: Optional[str]=None, task_id: Optional[str]=None) -> DataFrame:
        """
        Fetches all deliveries since a given timestamp(in the
        RFC3339 format) for the specified project and optional filters.
        Returns deliveries in a DataFrame
        
        Args:
            spark (SparkSession) : A spark session

            project_id (str): The unique identifier of the project on SamaHub. Specifies 
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


        data_gen = super().get_delivered_tasks(project_id=project_id, batch_id=batch_id, client_batch_id=client_batch_id,client_batch_id_match_type=client_batch_id_match_type, from_timestamp=from_timestamp, task_id=task_id)

        spark = SparkSession.builder.appName('sama-databricks-connector').getOrCreate()
        
        return spark.read.json(spark.sparkContext.parallelize(Client.transform_nested_answers_json(data_gen)))
    
    def get_delivered_tasks_since_last_call_to_table(self, spark: SparkSession, project_id, batch_id: Optional[str]=None, client_batch_id: Optional[str]=None, client_batch_id_match_type: Optional[str]=None, consumer: Optional[str]=None) -> DataFrame:
        """
        Fetches all deliveries since last call based on a consumer token.
        Returns deliveries in a DataFrame

        Args:
            spark (SparkSession) : A spark session

            project_id (str): The unique identifier of the project on SamaHub. Specifies 
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

        data_gen = super().get_delivered_tasks_since_last_call(project_id=project_id,batch_id=batch_id, client_batch_id=client_batch_id,client_batch_id_match_type=client_batch_id_match_type, consumer=consumer)
        
        spark = SparkSession.builder.appName('sama-databricks-connector').getOrCreate()
        
        return spark.read.json(spark.sparkContext.parallelize(Client.transform_nested_answers_json(data_gen)))
    

    def get_task_status_to_table(self, spark: SparkSession, project_id, task_id, same_as_delivery=True) -> DataFrame:
        """
        Fetches task info for a single task
        https://docs.sama.com/reference/singletaskstatus

        Args:
            spark (SparkSession) : A spark session

            project_id (str): The unique identifier of the project on SamaHub. 
                            Specifies the project under which the task resides.
            
            task_id (str): The unique identifier of the task within the specified 
                            project on SamaHub. Identifies the specific task for 
                            which the status is being requested.

            same_as_delivery (bool, optional): Flag to determine the format of the 
                                                task data to be returned. If True (default),
                                                task data is returned in the same format 
                                                as delivery.
    
        """
        
        data_gen = super().get_task_status(project_id=project_id, task_id=task_id, same_as_delivery=same_as_delivery)
        
        spark = SparkSession.builder.appName('sama-databricks-connector').getOrCreate()
        
        return spark.read.json(spark.sparkContext.parallelize(Client.transform_nested_answers_json(data_gen)))

    def get_multi_task_status_to_table(self, spark: SparkSession, project_id, batch_id: Optional[str]=None, client_batch_id: Optional[str]=None, client_batch_id_match_type: Optional[str]=None, date_type: Optional[str]=None, from_timestamp: Optional[str]=None, to_timestamp: Optional[str]=None, state: Optional[TaskStates] = None, omit_answers=True) -> DataFrame:
        """     
        Fetches task info for multiple tasks based on the provided filters.
        Returns DataFrame of results
        https://docs.sama.com/reference/multitaskstatus

        Args:
            spark (SparkSession) : A spark session

            project_id (str): The unique identifier of the project on SamaHub. Specifies 
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
       
        data_gen =  super().get_multi_task_status(project_id=project_id, batch_id=batch_id, client_batch_id=client_batch_id,client_batch_id_match_type=client_batch_id_match_type, from_timestamp=from_timestamp, state=state, omit_answers=omit_answers)
 
        spark = SparkSession.builder.appName('sama-databricks-connector').getOrCreate()
        
        return spark.read.json(spark.sparkContext.parallelize(Client.transform_nested_answers_json(data_gen)))

