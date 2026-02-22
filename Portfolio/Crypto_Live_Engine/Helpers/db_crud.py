import mysql.connector
from mysql.connector import Error

class MySQLDatabase:
    def __init__(self):
        self.config = {
            'host': "31.97.46.196",
            'user': "misho",
            'password': "Mi#len4eto1234",
            'database': "trades"
        }

    def _connect(self):
        try:
            connection = mysql.connector.connect(**self.config)
            return connection
        except Error as e:
            print(f"❌ MySQL Connection Error: {e}")
            return None

    def execute_query(self, query, params=None):
        connection = self._connect()
        if not connection:
            return None

        cursor = connection.cursor()
        try:
            cursor.execute(query, params)
            connection.commit()
            return cursor.lastrowid
        except Error as e:
            print(f"❌ Query Error: {e}")
            connection.rollback()
            return None
        finally:
            cursor.close()
            connection.close()

    def fetch_one(self, query, params=None):
        connection = self._connect()
        if not connection:
            return None

        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor.fetchone()
        except Error as e:
            print(f"❌ Query Error: {e}")
            return None
        finally:
            cursor.close()
            connection.close()

    def fetch_all(self, query, params=None):
        connection = self._connect()
        if not connection:
            return None

        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except Error as e:
            print(f"❌ Query Error: {e}")
            return None
        finally:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    connection = MySQLDatabase()
    connection._connect()