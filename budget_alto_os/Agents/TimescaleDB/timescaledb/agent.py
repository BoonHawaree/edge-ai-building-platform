"""
Agent documentation goes here.
"""

__docformat__ = "reStructuredText"

import os
import json
import logging
import re
import sys
import datetime
from queue import Empty, Queue
from threading import Thread

import pendulum
import yaml
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

from volttron.platform.agent import utils
from volttron.platform.scheduling import periodic
from volttron.platform.vip.agent import RPC, Agent

import gevent


from altolib import AltoHealth

_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"

# Mapping between table name and topics to subscribe/insert to for each table
DEFAULT_SUBSCRIPTION_TOPICS = {
    "sensor_data": ["iaq", "powermeter"],
    "afdd_history": ["afdd_history"],
    "chiller_prediction": ["chiller_prediction"],
    "raw_data": ["datalogger", "calculated_data"],
    "weather_forecast": ["weather_forecast"],
    "agent_status": ["altoheartbeat"],
    "command_result": ["command_result"],
}


class TimescaleDBTableHandler(object):
    def __init__(self, controller, table_name):
        self.table_name = table_name
        self.controller = controller

        self.build_table()  # Create new table if table_name does not exist in TimescaleDB
        self.column_names = self.get_table_columns()
        # Queue of data entries which will be logged into Database
        self.data_queue = Queue()

        # Thread for handling data logging
        self.log_thread = Thread(
            target=self._flush_thread,
            name=f"timescaledb_flush_{self.table_name}",
            daemon=True,
        )
        self.log_thread.start()

        self.do_flush = False

    @staticmethod
    def is_valid_value(val):
        """
        Validate if a value is suitable for insertion into TimescaleDB.

        Args:
            val: The value to validate

        Returns:
            bool: True if the value is valid (numeric or convertible to numeric), False otherwise
        """
        if isinstance(val, (int, float)):
            return True
        if isinstance(val, bool):
            return True
        if isinstance(val, str):
            # Try to convert string to float if it represents a number
            try:
                float(val)
                return True
            except ValueError:
                return False
        return False

    @property
    def connection_string(self):
        return f"dbname={self.controller.db_name} user={self.controller.db_user} password={self.controller.db_password} host={self.controller.db_host} port={self.controller.db_port}"

    def build_table(self):
        """
        Create table if not exists by running the query.
        """
        try:
            cursor = None
            try:
                connection = psycopg2.connect(self.connection_string)
                _log.info(f"Connected to TimescaleDB database: {self.controller.db_name} at {self.controller.db_host}:{self.controller.db_port}")
                self.controller.custom_health.update_health(
                    status="GOOD", context="Connected to database successfully"
                )
            except Exception as e:
                _log.warning(
                    f"Could not connect to database: {self.connection_string}.\nErro: {e}.\nWaiting for 15 seconds before retrying."
                )
                self.controller.custom_health.update_health(
                    status="BAD", context=f"Could not connect to database: {e}"
                )
                gevent.sleep(15)
                connection = psycopg2.connect(self.connection_string)

            cursor = connection.cursor()
            table_sql = os.path.join(
                os.path.dirname(__file__),
                "sql/create_tables",
                self.table_name + ".sql",
            )
            with open(table_sql, "r") as f:
                # read all lines the sql file
                sql_content = f.read()
                # Replace placeholders with actual values
                sql_content = self.controller.replace_placeholders(sql_content)
                # Split and execute queries
                queries = sql_content.split(";")
                for query in queries:
                    if query.strip():
                        try:
                            cursor.execute(query + ";")
                            connection.commit()
                        except Exception as e:
                            _log.error(f"Error executing query: {e}")
                            self.controller.custom_health.update_health(
                                status="BAD",
                                context=f"Error executing query: {e}",
                            )
                            continue
            self.controller.custom_health.update_health(
                status="GOOD", context="Table created successfully"
            )
        except Exception as e:
            _log.critical(f"Table creation failed: {e}")
            self.controller.custom_health.update_health(
                status="BAD", context=f"Table creation failed: {e}"
            )
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def log_data(self, data: dict):
        """
        Log data into self.data_queue
        """
        # Keys that shouldn't be included into the data sample (e.g. timestamp, device_id, etc.)
        COMMON_KEYS = [
            "timestamp",
            "unix_timestamp",
            "week",
            "month",
            "year",
            "device_id",
            "subdevice_idx",
            "site_id",
            "type",
            "model",
            "device_name",
            "subdevice_name",
        ]

        # If timestamp exists in data. Make sure that the data type is float (timestamp in milliseconds) so TimescaleDB will
        # correctly parse it
        if "timestamp" in data.keys():
            if "datetime" in data.keys():
                data["timestamp"] = data["datetime"]
                del data["datetime"]
        if "location" in data.keys():
            data["site_id"] = data["location"]
            del data["location"]

        # Case 1: Old convention from DeviceAgent
        if (
            ("datapoint" in self.column_names)
            and ("value" in self.column_names)
            and ("datapoint" not in data)
            and ("value" not in data)
        ):
            sample_template = {
                col: data[col]
                for col in list(set(self.column_names) - set(["datapoint", "value"]))
            }

            additional_points = list(
                set(data.keys()) - set(self.column_names) - set(COMMON_KEYS)
            )
            for k in additional_points:
                sample = sample_template.copy()
                sample["datapoint"] = k
                sample["value"] = data[k]
                # Only add valid data points
                if self.is_valid_value(sample["value"]):
                    self.data_queue.put_nowait(sample)
                else:
                    _log.debug(f"Skipping invalid value for datapoint {k}: {data[k]}")
        # Case 2: Agent health
        elif self.table_name == "agent_status":
            self.data_queue.put_nowait(
                {
                    "timestamp": data["timestamp"],
                    "site_id": data["site_id"],
                    "agent_id": data["agent_id"],
                    "status": data["status"],
                    "context": data["context"],
                }
            )
        else:
            sample_template = {col: data[col] for col in list(set(self.column_names))}
            sample = sample_template.copy()
            try:
                # check if timestamp is seconds or milliseconds
                if sample["timestamp"] < 10000000000:
                    sample["timestamp"] = pendulum.from_timestamp(
                        sample["timestamp"], tz="UTC"
                    )
                else:
                    sample["timestamp"] = pendulum.from_timestamp(
                        sample["timestamp"] / 1000, tz="UTC"
                    )
            except Exception as e:
                # _log.debug(f"Error parsing timestamp: {e}")
                pass

            # if any of the values in data is list of dictionaries, convert it 'JSONB'
            for k, v in sample.items():
                if isinstance(v, list) or isinstance(v, dict):
                    sample[k] = json.dumps(v)
                elif k == "value" and not self.is_valid_value(v):
                    _log.debug(f"Skipping invalid value: {v}")
                    return
            self.data_queue.put_nowait(sample)

    def flush_data(self):
        """Change the flag to flush data into TimescaleDB in the next loop in self._flush_thread"""
        self.do_flush = True

    def query_data(self, query_string: str):
        """
        Query data from TimescaleDB with specified query string.
        """
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(query_string)
                    columns = [desc[0] for desc in cursor.description]
                    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    self.controller.custom_health.update_health(
                        status="GOOD",
                        context=f"Data queried successfully: {query_string}",
                    )
                    return data
                except Exception as e:
                    _log.debug(f"Data could not be queried: {e}")
                    self.controller.custom_health.update_health(
                        status="BAD", context=f"Data could not be queried: {e}"
                    )

    def execute(self, sql_string: str):
        """
        Execute given SQL string. Return nothing
        """
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(sql_string)
                    conn.commit()
                    self.controller.custom_health.update_health(
                        status="GOOD",
                        context=f"Command executed successfully: {sql_string}",
                    )
                except Exception as e:
                    _log.debug(f"Error `{e}` when executing command {sql_string}")
                    self.controller.custom_health.update_health(
                        status="BAD",
                        context=f"Error `{e}` when executing command {sql_string}",
                    )

    def executemany(self, sql_string: str, data: list):
        """
        Execute given SQL string with multiple data. Return nothing
        """
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.executemany(sql_string, data)
                    conn.commit()
                    self.controller.custom_health.update_health(
                        status="GOOD",
                        context=f"Executed command {sql_string} with {len(data)} rows",
                    )
                except Exception as e:
                    _log.debug(f"Error `{e}` when executing command {sql_string}")
                    self.controller.custom_health.update_health(
                        status="BAD",
                        context=f"Error `{e}` when executing command {sql_string}",
                    )

    def _flush_thread(self):
        """
        A thread for handling data logging into TimescaleDB. The INSERT command will be executed every time self.do_flush
        is changed to True by the periodically-called function self.flush_data
        """
        time_to_die = False
        # Gather the queued data
        lod = []
        while True:
            while True:
                try:
                    data = self.data_queue.get(timeout=1)
                    self.data_queue.task_done()
                    if data == "Die":
                        time_to_die = True
                        break

                    # Preporcess lod to convert boolean values to float
                    if "value" in data.keys() and isinstance(data["value"], bool):
                        data["value"] = float(data["value"])

                    lod.append([data.get(col, None) for col in self.column_names])

                    if len(lod) >= 1000:
                        break

                except Empty:
                    break
                except Exception as e:
                    _log.debug(f"Queue exception: {e}")
                    break

            if self.do_flush and lod:
                query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
                    sql.Identifier(self.table_name),
                    sql.SQL(", ").join(map(sql.Identifier, self.column_names)),
                )
                max_retries = 3
                base_delay = 1  # seconds

                for retry_count in range(max_retries):
                    try:
                        with psycopg2.connect(self.connection_string) as conn:
                            with conn.cursor() as cursor:
                                execute_values(cursor, query, lod)
                                conn.commit()
                                _log.info(
                                    f"Inserted {len(lod)} rows into {self.table_name}."
                                )
                                self.controller.custom_health.update_health(
                                    status="GOOD",
                                    context=f"Inserted {len(lod)} rows into {self.table_name}.",
                                )
                                break

                    except (
                        psycopg2.OperationalError,
                        psycopg2.InterfaceError,
                        psycopg2.DatabaseError,
                    ) as e:
                        # Handle connection-related errors with retry
                        # exponential backoff
                        delay = base_delay * (2**retry_count)
                        _log.warning(
                            f"Database connection error (attempt {retry_count + 1}/{max_retries}): {e}"
                        )
                        _log.warning(f"Retrying in {delay} seconds...")

                        # Ensure connection is closed before retry
                        if "conn" in locals():
                            try:
                                conn.close()
                            except Exception:
                                pass

                        gevent.sleep(delay)

                        if retry_count == max_retries - 1:
                            _log.critical(
                                f"Failed to insert data after {max_retries} attempts: {e}"
                            )
                            self.controller.custom_health.update_health(
                                status="BAD",
                                context=f"Failed to insert data after {max_retries} attempts: {e}",
                            )

                    except Exception as e:
                        # Handle other errors (like syntax errors) without retry
                        _log.critical(f"Data could not be saved due to error: {e}")
                        self.controller.custom_health.update_health(
                            status="BAD", context=f"Data could not be saved: {e}"
                        )
                        break

                    finally:
                        self.do_flush = False
                        lod = []
            if time_to_die:
                break

    def get_table_columns(self):
        """
        Get the columns of the table.
        """
        connection = psycopg2.connect(self.connection_string)
        cursor = connection.cursor()
        query = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{self.table_name}';"
        cursor.execute(query)
        columns = [row[0] for row in cursor.fetchall()]
        return columns


def timescaledb(config_path, **kwargs):
    """
    Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.
    :type config_path: str
    :returns: Timescaledb
    :rtype: Timescaledb
    """
    config = utils.load_config(config_path)
    agent_config = config.get("volttron_agents", dict()).get("timescaledb", dict())

    if not agent_config:
        _log.info("Using Agent defaults for starting configuration.")

    db_host = agent_config.get("db_host", "localhost")
    db_port = agent_config.get("db_port", 5432)
    db_name = agent_config.get("db_name", "postgres")
    db_user = agent_config.get("db_user", "postgres")
    db_password = agent_config.get("db_password", "Magicalmint@636")

    return Timescaledb(
        db_host,
        db_port,
        db_name,
        db_user,
        db_password,
        config,
        **kwargs,
    )


class Timescaledb(Agent):
    """
    Document agent constructor here.
    """

    def __init__(
        self,
        db_host,
        db_port,
        db_name,
        db_user,
        db_password,
        default_config,
        **kwargs,
    ):
        super(Timescaledb, self).__init__(**kwargs)
        _log.debug("vip_identity: " + self.core.identity)

        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password

        self.tables = dict()

        self.default_config = default_config

        # Set a default configuration to ensure that self.configure is called immediately to setup
        # the agent.
        self.vip.config.set_default("config", self.default_config)
        # Hook self.configure up to changes to the configuration file "config".
        self.vip.config.subscribe(
            self.configure, actions=["NEW", "UPDATE"], pattern="config"
        )

    def configure(self, config_name, action, contents):
        """
        Called after the Agent has connected to the message bus. If a configuration exists at startup
        this will be called before onstart.

        Is called every time the configuration in the store changes.
        """

        if isinstance(contents, dict):
            config = contents
        else:
            try:
                config = yaml.safe_load(contents)
            except yaml.YAMLError as e:
                _log.error("Error parsing YAML:", e)
                self.custom_health.update_health(
                    status="BAD", context=f"Error parsing YAML: {e}"
                )
                return None

        _log.debug("Configuring Agent")

        try:
            self.site_id = config.get("site_id", "staging")
            self.custom_health = AltoHealth(
                core=self.core,
                pubsub=self.vip.pubsub,
                heartbeat_period=60,
                verbose=True,
                site_id=self.site_id,
            )
            self.timezone = config.get("timezone", "Asia/Bangkok")
            self.business_hours = config.get("site_metadata", dict()).get(
                "business_hours", dict()
            )
            if self.business_hours:
                self.business_hours_start = self.business_hours.get(
                    "start_time", "06:00"
                )
                self.business_hours_end = self.business_hours.get("end_time", "18:00")
            agent_config = config.get("volttron_agents", dict()).get(
                "timescaledb", dict()
            )
            self.db_host = agent_config.get("db_host", "localhost")
            self.db_port = agent_config.get("db_port", 5432)
            self.db_name = agent_config.get("db_name", "postgres")
            self.db_user = agent_config.get("db_user", "postgres")
            self.db_password = agent_config.get("db_password", "Magicalmint@636")
            self.retention_interval = agent_config.get("retention_interval", "1 year")
        except ValueError as e:
            _log.error("ERROR PROCESSING CONFIGURATION: {}".format(e))
            self.custom_health.update_health(
                status="BAD", context=f"Error processing configuration: {e}"
            )
            return

        self.tables = dict()
        self._register_tables()
        self._setup_continuous_aggregations()

        self.subscribed_topics = []
        self._create_subscriptions(list(DEFAULT_SUBSCRIPTION_TOPICS.values()))

        # Set up period for flushing and writing data into database
        self.core.schedule(periodic(5), self._flush_data)

    def _flush_data(self):
        """
        Periodically flush all data already logged into data queue and write into TimescaleDB
        """
        for table in self.tables.values():
            table.flush_data()

    def _register_tables(self):
        """
        Register tables from config files
        """
        for table_name in DEFAULT_SUBSCRIPTION_TOPICS.keys():
            self.tables[table_name] = TimescaleDBTableHandler(self, table_name)

    def replace_placeholders(self, sql_content: str):
        """
        Replace placeholders in the SQL content with actual values
        """
        _log.info("Replacing placeholders...")
        sql_content = sql_content.replace("timezone_placeholder", self.timezone)
        _log.info(f"Replaced timezone placeholder with {self.timezone}")
        sql_content = sql_content.replace(
            "retention_interval_placeholder", self.retention_interval
        )
        _log.info(
            f"Replaced retention interval placeholder with {self.retention_interval}"
        )
        if self.business_hours and all(
            value is not None for value in self.business_hours.values()
        ):
            _log.info(f"Business hours specified in config: {self.business_hours}")
            business_hours_start = pendulum.parse(self.business_hours_start)
            business_hours_end = pendulum.parse(self.business_hours_end)
            operation_hours = (
                business_hours_start.diff(business_hours_end).in_minutes() / 60
            )
            business_hours_start_str = (
                f"{business_hours_start.hour:02d}:{business_hours_start.minute:02d}:00"
            )
            business_hours_end_str = (
                f"{business_hours_end.hour:02d}:{business_hours_end.minute:02d}:00"
            )
            sql_content = sql_content.replace(
                "business_hours_start", business_hours_start_str
            )
            sql_content = sql_content.replace(
                "business_hours_end", business_hours_end_str
            )
            sql_content = sql_content.replace(
                "operation_hours", f"{operation_hours:.2f}"
            )

            # Create initial start time using proper Pendulum methods
            initial_start = pendulum.now(tz=self.timezone).subtract(days=1)
            initial_start = initial_start.set(
                hour=business_hours_end.hour, minute=5, second=0
            )
            sql_content = sql_content.replace(
                "initial_start_placeholder", initial_start.to_iso8601_string()
            )
        else:
            _log.info(
                "No business hours specified in config, using whole day as business hours"
            )
            # whole day is business hours
            sql_content = sql_content.replace("business_hours_start", "00:00:00")
            sql_content = sql_content.replace("business_hours_end", "23:59:59")
            sql_content = sql_content.replace("operation_hours", "24")

            # Create initial start time using proper Pendulum methods
            initial_start = pendulum.now(tz=self.timezone).subtract(days=1)
            initial_start = initial_start.set(hour=0, minute=5, second=0)
            sql_content = sql_content.replace(
                "initial_start_placeholder", initial_start.to_iso8601_string()
            )
        return sql_content

    def _setup_continuous_aggregations(self):
        """
        Setup continuous aggregations from .sql files (for calculated data).
        """
        connection_string = f"dbname={self.db_name} user={self.db_user} password={self.db_password} host={self.db_host} port={self.db_port}"
        cursor = None
        try:
            connection = psycopg2.connect(connection_string)
            _log.info(f"Connected to TimescaleDB database: {self.db_name} at {self.db_host}:{self.db_port}")
        except Exception as e:
            _log.warning(
                f"Could not connect to database: {connection_string}.\nErro: {e}.\nWaiting for 15 seconds before retrying."
            )
            gevent.sleep(15)
            connection = psycopg2.connect(connection_string)
        cursor = connection.cursor()

        try:
            sqls_dir = os.path.join(
                os.path.dirname(__file__), "sql/continuous_aggregations"
            )
            for table_sql in os.listdir(sqls_dir):
                # Read the SQL file
                with open(os.path.join(sqls_dir, table_sql), "r") as sql_file:
                    _log.info(
                        f"Setting up continuous aggregations for {os.path.join(sqls_dir, table_sql)}"
                    )
                    sql_content = sql_file.read()
                    # Replace placeholders with actual values
                    sql_content = self.replace_placeholders(sql_content)
                    # Split and execute queries
                    queries = sql_content.split(";")
                    for query in queries:
                        if query.strip():  # Ensure the query is not empty
                            try:
                                cursor.execute(query + ";")
                                connection.commit()
                            except Exception as e:
                                _log.error(f"Error executing query in {table_sql}: {e}")
                                self.custom_health.update_health(
                                    status="BAD",
                                    context=f"Error executing query in {table_sql}: {e}",
                                )
                                continue
                self.custom_health.update_health(
                    status="GOOD",
                    context=f"Successfully setup continuous aggregations for {table_sql}",
                )
        except Exception as e:
            _log.error(f"Error during continuous aggregations setup: {e}")
            self.custom_health.update_health(
                status="BAD", context=f"Error during continuous aggregations setup: {e}"
            )
        finally:
            # Close the cursor and connection
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def _create_subscriptions(self, topics: list):
        """
        Unsubscribe from all pub/sub topics and create a subscription to a topic in the configuration which triggers
        the _handle_publish callback

        Args:
            topics (list[list[str]]): List of lists topics to subscribe to

        """
        self.vip.pubsub.unsubscribe("pubsub", None, None)

        for topic_list in topics:
            for t in topic_list:
                self.subscribed_topics.append(t)
                self.vip.pubsub.subscribe(
                    peer="pubsub", prefix=t, callback=self._handle_message_data
                )


    def _handle_message_data(self, peer, sender, bus, topic, headers, message):
        """
        Callback for all pubsub messages. Routes all IAQ and powermeter data to sensor_data table
        using BRICK point_id.
        """
        import datetime

        topic_parts = topic.split("/")
        if not topic_parts:
            return

        # Determine type and id from topic
        data_type = topic_parts[0]  # "iaq" or "powermeter"
        device_num = topic_parts[1] if len(topic_parts) > 1 else None

        # Map to point_ids
        if data_type == "iaq" and device_num is not None:
            # Expect message to have co2, temperature, humidity
            for point_type in ["co2", "temperature", "humidity"]:
                if point_type in message:
                    point_id = f"iaq_{int(device_num):03d}_{'humid' if point_type == 'humidity' else point_type}"
                    data_row = {
                        "timestamp": message.get("timestamp", datetime.datetime.utcnow().isoformat()),
                        "point_id": point_id,
                        "value": message[point_type],
                        "quality": "good"
                    }
                    self.tables["sensor_data"].log_data(data_row)
        elif data_type == "powermeter" and device_num is not None:
            if "power" in message:
                point_id = f"pm_{int(device_num):03d}_power"
                data_row = {
                    "timestamp": message.get("timestamp", datetime.datetime.utcnow().isoformat()),
                    "point_id": point_id,
                    "value": message["power"],
                    "quality": "good"
                }
                self.tables["sensor_data"].log_data(data_row)
        else:
            # Not a topic we care about
            return
        
    # def _handle_message_data(self, peer, sender, bus, topic, headers, message):
    #     """
    #     Callback triggered by the subscription setup using the topic from the agent's config file
    #     """
    #     schema = topic.split("/")[0]

    #     if isinstance(message, str):
    #         message = json.loads(message)

    #     if schema in self.subscribed_topics:
    #         for table_name, table_topics in DEFAULT_SUBSCRIPTION_TOPICS.items():
    #             if schema in table_topics:
    #                 t = self.tables.get(table_name, None)
    #                 if t is None:
    #                     _log.debug(
    #                         f"Table {table_name} hasn't been initialized for data logging"
    #                     )
    #                     self.custom_health.update_health(
    #                         status="WARNING",
    #                         context=f"Table {table_name} hasn't been initialized for data logging",
    #                     )
    #                     continue
    #                 else:
    #                     t.log_data(message)

    @RPC.export
    def get_data_from_timescaledb(self, table_name: str, filters: dict):
        """
        RPC Method for querying data from TimescaleDB

        Args:
            table_name (str): Name of the table to query data from
            filters (dict): Dictionary of filters to apply to the query with the following format:

            filters = {                             |   ex.     filters = {
                <column_name_1>: {                  |               unix_timestamp: {
                    <operator_1>: <value_1>,        |                   ">": 100000,
                    <operator_2>: <value_2>,        |                   "<": 200000
                    ...                             |               },
                },                                  |               device_id: {
                <column_name_2>: ...                |                   "=": "device_1"
            }                                       |               }
                                                    |           }

        Supported operators: "=", "!=", ">", "<", ">=", "<=", "IN", "NOT IN", "LIKE", "NOT LIKE"

        Returns:
            data (list): List of dictionaries containing the data queried from TimescaleDB

            data = [{'timestamp': 1675245600000,
                    'site_id': 'chiller_plant/iot_devices',
                    'device_id': 'CSQ_plant',
                    'subdevice_idx': 0,
                    'type': 'calculated_power',
                    'aggregation_type': 'avg_1h',
                    'datapoint': 'power',
                    'value': '1289.8812590049934'}, ....]

        """
        connection_string = f"dbname={self.db_name} user={self.db_user} password={self.db_password} host={self.db_host} port={self.db_port}"
        
        query = sql.SQL("SELECT * FROM {} WHERE ").format(sql.Identifier(table_name))
        conditions = []

        for col_name, f in filters.items():
            for oper, value in f.items():
                if value is None:
                    _log.debug(
                        f"Invalid value for column [{col_name}] -- value = {value}"
                    )
                    continue

                if oper in [">", "<", ">=", "<=", "=", "!=", "LIKE", "NOT LIKE"]:
                    conditions.append(
                        sql.SQL("{} {} {}").format(
                            sql.Identifier(col_name), sql.SQL(oper), sql.Literal(value)
                        )
                    )
                elif oper.upper() in ["IN", "NOT IN"] and isinstance(value, list):
                    conditions.append(
                        sql.SQL("{} {} {}").format(
                            sql.Identifier(col_name),
                            sql.SQL(oper.upper()),
                            sql.SQL("({})").format(
                                sql.SQL(", ").join(map(sql.Literal, value))
                            ),
                        )
                    )
                else:
                    _log.warning(
                        f"Invalid filter specified for querying data from TimescaleDB -- {col_name}: {f}"
                    )

        query += sql.SQL(" AND ").join(conditions)

        try:
            with psycopg2.connect(connection_string) as conn:
                with conn.cursor() as cursor:
                    _log.debug(f"[RPC] Querying data from TimescaleDB: {query.as_string(conn)}")
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    raw_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    
                    # Convert datetime objects to ISO strings for JSON serialization
                    data = []
                    for row in raw_data:
                        converted_row = {}
                        for key, value in row.items():
                            if isinstance(value, (pendulum.DateTime, pendulum.Date)) or hasattr(value, 'isoformat'):
                                # Convert datetime objects to ISO string
                                converted_row[key] = value.isoformat() if hasattr(value, 'isoformat') else str(value)
                            else:
                                converted_row[key] = value
                        data.append(converted_row)
                    
                    _log.debug(f"[RPC] Finished querying data from TimescaleDB from table: {table_name}. Returned {len(data)} rows")
                    self.custom_health.update_health(
                        status="GOOD",
                        context=f"[RPC] Data queried successfully from {table_name}",
                    )
                    return data
        except Exception as e:
            _log.error(f"Error querying data from TimescaleDB table {table_name}: {e}")
            self.custom_health.update_health(
                status="BAD", context=f"[RPC] Error querying data from {table_name}: {e}"
            )
            return None

    @RPC.export
    def drop_data_from_timescaledb(self, table_name: str, filters: dict):
        """
        RPC Method for deleting data from TimescaleDB in the specified table

        Args:
            table_name (str): Name of the table to query data from
            filters (dict): Dictionary of filters to apply to the query with the following format:

            filters = {                             |   ex.     filters = {
                <column_name_1>: {                  |               unix_timestamp: {
                    <operator_1>: <value_1>,        |                   ">": 100000,
                    <operator_2>: <value_2>,        |                   "<": 200000
                    ...                             |               },
                },                                  |               device_id: {
                <column_name_2>: ...                |                   "=": "device_1"
            }                                       |               }
                                                    |           }

        Supported operators: "=", "!=", ">", "<", ">=", "<=", "IN", "NOT IN", "LIKE", "NOT LIKE"

        """
        connection_string = f"dbname={self.db_name} user={self.db_user} password={self.db_password} host={self.db_host} port={self.db_port}"
        
        query = sql.SQL("DELETE FROM {} WHERE ").format(sql.Identifier(table_name))
        conditions = []

        for col_name, f in filters.items():
            for oper, value in f.items():
                if value is None:
                    _log.debug(
                        f"Invalid value for column [{col_name}] -- value = {value}"
                    )
                    continue

                if oper in [">", "<", ">=", "<=", "=", "!=", "LIKE", "NOT LIKE"]:
                    conditions.append(
                        sql.SQL("{} {} {}").format(
                            sql.Identifier(col_name), sql.SQL(oper), sql.Literal(value)
                        )
                    )
                elif oper.upper() in ["IN", "NOT IN"] and isinstance(value, list):
                    conditions.append(
                        sql.SQL("{} {} {}").format(
                            sql.Identifier(col_name),
                            sql.SQL(oper.upper()),
                            sql.SQL("({})").format(
                                sql.SQL(", ").join(map(sql.Literal, value))
                            ),
                        )
                    )
                else:
                    _log.warning(
                        f"Invalid filter specified for deleting data from TimescaleDB -- {col_name}: {f}"
                    )

        query += sql.SQL(" AND ").join(conditions)

        try:
            with psycopg2.connect(connection_string) as conn:
                with conn.cursor() as cursor:
                    _log.debug(f"[RPC] Deleting data from TimescaleDB: {query.as_string(conn)}")
                    cursor.execute(query)
                    conn.commit()
                    _log.debug(f"Successfully deleted data from TimescaleDB table {table_name}")
                    self.custom_health.update_health(
                        status="GOOD",
                        context=f"[RPC] Data deleted successfully from {table_name}",
                    )
        except Exception as e:
            _log.error(f"Error deleting data from TimescaleDB table {table_name}: {e}")
            self.custom_health.update_health(
                status="BAD", context=f"[RPC] Error deleting data from {table_name}: {e}"
            )

    @RPC.export
    def insert_data_to_timescaledb(self, table_name: str, data: list):
        """
        RPC Method for inserting data into TimescaleDB in the specified table

        Args:
            table_name (str): Name of the table to insert data into
            data (list): List of dictionaries containing the data to insert into the table

            ex. data = [{'timestamp': 1675245600000,
                         'site_id': 'chiller_plant/iot_devices',
                         'device_id': 'CSQ_plant',
                         'subdevice_idx': 0,
                         'type': 'calculated_power',
                         'aggregation_type': 'avg_1h',
                         'datapoint': 'power',
                         'value': '1289.8812590049934'}, ....]

        """
        _log.debug(f"[RPC] Inserting data to TimescaleDB: {data}")
        connection_string = f"dbname={self.db_name} user={self.db_user} password={self.db_password} host={self.db_host} port={self.db_port}"

        try:
            with psycopg2.connect(connection_string) as conn:
                with conn.cursor() as cursor:
                    # Get table column names dynamically
                    cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position;")
                    table_column_names = [row[0] for row in cursor.fetchall()]
                    
                    if not table_column_names:
                        _log.error(f"Table {table_name} not found or has no columns")
                        return "Error"

                    # Prepare the data for insertion
                    values = [[row.get(col, None) for col in table_column_names] for row in data]

                    query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
                        sql.Identifier(table_name),
                        sql.SQL(", ").join(map(sql.Identifier, table_column_names)),
                    )

                    _log.debug(f"[RPC] Inserting data to TimescaleDB: {query.as_string(conn)}")
                    execute_values(cursor, query, values)
                    conn.commit()
                    _log.debug(f"Successfully inserted data to TimescaleDB table {table_name}")
                    self.custom_health.update_health(
                        status="GOOD",
                        context=f"[RPC] Data inserted successfully to {table_name}",
                    )
                    return "Success"
        except Exception as e:
            _log.error(f"Error inserting data to TimescaleDB table {table_name}: {e}")
            self.custom_health.update_health(
                status="BAD", context=f"[RPC] Error inserting data to {table_name}: {e}"
            )
            return "Error"

    @RPC.export("query_data_from_timescaledb")
    def query_data_from_timescaledb(
        self,
        query: str,
    ):
        connection_string = f"dbname={self.db_name} user={self.db_user} password={self.db_password} host={self.db_host} port={self.db_port}"
        try:
            with psycopg2.connect(connection_string) as conn:
                _log.info(f"Connected to TimescaleDB database: {self.db_name} at {self.db_host}:{self.db_port}")
                self.custom_health.update_health(
                    status="GOOD",
                    context="[RPC] Connected to TimescaleDB"
                )
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    raw_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    
                    # Convert datetime objects to ISO strings for JSON serialization
                    data = []
                    for row in raw_data:
                        converted_row = {}
                        for key, value in row.items():
                            if isinstance(value, (pendulum.DateTime, pendulum.Date)) or hasattr(value, 'isoformat'):
                                # Convert datetime objects to ISO string
                                converted_row[key] = value.isoformat() if hasattr(value, 'isoformat') else str(value)
                            else:
                                converted_row[key] = value
                        data.append(converted_row)
                    
                    return data
        except Exception as e:
            _log.error(f"Error querying data from TimescaleDB: {e}")
            self.custom_health.update_health(
                status="BAD", context=f"[RPC] Error querying data from TimescaleDB: {e}"
            )
            return None


def main():
    """Main method called to start the agent."""
    utils.vip_main(timescaledb, version=__version__)


if __name__ == "__main__":
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
