# database.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
import mysql.connector
from mysql.connector.connection import MySQLConnection


class Database(ABC):
    @abstractmethod
    def open_connection(self) -> MySQLConnection:
        ...

    @abstractmethod
    def close_connection(self, conn: MySQLConnection) -> None:
        ...

    @abstractmethod
    def run_query(
        self,
        conn: MySQLConnection,
        query: str,
        params: Optional[Tuple[Any, ...]] = None
    ) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def execute_update(
        self,
        conn: MySQLConnection,
        query: str,
        params: Optional[Tuple[Any, ...]] = None
    ) -> int:
        ...


class MySqlConnection(Database):
    def __init__(self):
        self.username = "root"
        self.password = "1436"
        self.database = "stockgenius"
        self.host = "localhost"
        self.port = 3306

    def open_connection(self) -> MySQLConnection:
        try:
            conn = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                database=self.database
            )
            if conn.is_connected():
                print("successful connection to the database")
            else:
                print("Not connection")

            print(self.database)
            return conn

        except mysql.connector.Error as e:
            print("DB error:", e)
            raise  # better than returning None

    def close_connection(self, conn: MySQLConnection) -> None:
        try:
            if conn and conn.is_connected():
                conn.close()
        except mysql.connector.Error as e:
            print("Close error:", e)

    def run_query(
        self,
        conn: MySQLConnection,
        query: str,
        params: Optional[Tuple[Any, ...]] = None
    ) -> List[Dict[str, Any]]:
        try:
            cursor = conn.cursor(dictionary=True)  # return rows as dict
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except mysql.connector.Error as e:
            print("Query error:", e)
            return []

    def execute_update(
        self,
        conn: MySQLConnection,
        query: str,
        params: Optional[Tuple[Any, ...]] = None
    ) -> int:
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected
        except mysql.connector.Error as e:
            print("Update error:", e)
            conn.rollback()
            return -1