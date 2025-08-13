#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging

from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)


class PsqlPool:
    """Asynchronous postgres client wrapper with connection management and utility methods."""

    _MAX_CONN_RETRY = 3

    def __init__(
        self,
        user,
        password,
        host,
        database,
        port="5432",
        schema="public",
        min_pool_size: int = 1,
        max_pool_size: int = 10,
        command_timeout: int = 60,
    ):
        """
        Initializes the AsyncPSQL instance with connection parameters.

        Args:
            user (str): Database user.
            password (str): Database password.
            host (str): Database host.
            database (str): Database name.
            port (str, optional): Database port. Defaults to '5432'.
            schema (str, optional): Database schema. Defaults to 'public'.
            min_pool_size (int, optional): Minimum connection pool size. Defaults to 1.
            max_pool_size (int, optional): Maximum connection pool size. Defaults to 10.
            command_timeout (int, optional): Timeout for commands in seconds. Defaults to 60.
        """
        self._user = user
        self._password = password
        self._host = host
        self._port = port
        self._database = database
        self._schema = schema
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size
        self._command_timeout = command_timeout
        self._connection_pool = None

    @property
    async def connection_pool(self):
        """
        Returns the connection pool, connecting if necessary.

        Returns:
            asyncpg.Pool: The asyncpg connection pool.
        """
        await self.connect()
        return self._connection_pool

    async def __aenter__(self):
        """
        Async context manager enter method to establish the connection pool.

        Returns:
            AsyncPSQL: The AsyncPSQL instance.
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        """
        Async context manager exit method to close the connection pool.

        Args:
            exc_type (type): Exception type.
            exc_value (Exception): Exception value.
            exc_traceback (traceback): Exception traceback.
        """
        await self.close()

    async def _attempt_connection(self):
        """
        Attempts to create a connection pool with the specified settings.

        Returns:
            asyncpg.Pool: The newly created connection pool.
        """
        connection_pool = await asyncpg.create_pool(
            min_size=self._min_pool_size,
            max_size=self._max_pool_size,
            command_timeout=self._command_timeout,
            host=self._host,
            port=self._port,
            user=self._user,
            password=self._password,
            database=self._database,
            server_settings={"search_path": self._schema},
            # ssl='require',
        )
        return connection_pool

    async def connect(self, force: bool = False):
        """
        Establishes the connection pool, retrying if necessary.

        Args:
            force (bool, optional): Force reconnection even if connected. Defaults to False.

        Raises:
            ConnectionRefusedError: If connection cannot be established after retries.
        """
        if not force and self._connection_pool is not None:
            return

        counter = 0
        connected = False
        while counter < self._MAX_CONN_RETRY:
            try:
                self._connection_pool = await self._attempt_connection()
                connected = True
                break
            except Exception:
                counter += 1

        if not connected:
            raise ConnectionRefusedError

    def _connect_connection_pool(func):
        """
        Decorator to ensure the connection pool is established before function execution.
        """

        async def inner(self, *args, **kwargs):
            if not self._connection_pool:
                await self.connect()
            return await func(self, *args, **kwargs)

        return inner

    @_connect_connection_pool
    async def fetch(self, query: str, params: tuple = (), silent: bool = False):
        """
        Executes a fetch query and returns the results.

        Args:
            query (str): The SQL query to execute.
            params (tuple, optional): Parameters for the query. Defaults to ().
            silent (bool, optional): Suppress exceptions if True, returning failure dict. Defaults to False.

        Returns:
            list[Record]|dict: Query result records or failure dict if silent and error occurs.
        """
        async with self._connection_pool.acquire() as con:
            try:
                return await con.fetch(query, *params)
            except Exception as e:
                if silent:
                    return {"data": [], "status": "FAILED", "msg": "Cannot fetch data."}
                raise e

    @_connect_connection_pool
    async def execute(
        self,
        query: str,
        params: tuple = (),
        returning: Optional[str] = None,
        silent: bool = False,
    ):
        """
        Executes a SQL command, optionally returning specified columns.

        Args:
            query (str): The SQL query to execute.
            params (tuple, optional): Parameters for the query. Defaults to ().
            returning (str, optional): Column(s) to return after execution. Defaults to None.
            silent (bool, optional): Suppress exceptions if True, returning failure dict. Defaults to False.

        Returns:
            list[Record]|dict: Query result records or failure dict if silent and error occurs.
        """
        if returning is not None:
            query = f"{query} returning {returning}"
        async with self._connection_pool.acquire() as con:
            try:
                return await con.fetch(query, *params)
            except Exception as e:
                if silent:
                    return {
                        "data": [],
                        "status": "FAILED",
                        "msg": "Cannot execute query.",
                    }
                raise e

    async def close(self):
        """
        Closes the connection pool if it exists.
        """
        if self._connection_pool:
            try:
                await self._connection_pool.close()
            except Exception:
                ...


