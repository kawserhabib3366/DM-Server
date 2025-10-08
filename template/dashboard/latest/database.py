
import mysql.connector
from mysql.connector import Error
import json

class MySQLConnection:
    def __init__(self, host=\'localhost\', database=\'campaign_db\', user=\'root\', password=\'\'):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.connection = None

    def get_connection(self):
        if self.connection is None or not self.connection.is_connected():
            try:
                self.connection = mysql.connector.connect(
                    host=self.host,
                    database=self.database,
                    user=self.user,
                    password=self.password
                )
                if self.connection.is_connected():
                    print("Successfully connected to MySQL database")
                return self.connection
            except Error as e:
                print(f"Error connecting to MySQL database: {e}")
                return None
        return self.connection

    def close_connection(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL connection closed")

    def execute_query(self, query, params=None, fetch_one=False):
        conn = self.get_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, params)
                if query.strip().upper().startswith((\'INSERT\', \'UPDATE\', \'DELETE\')):
                    conn.commit()
                    return cursor.rowcount
                else:
                    if fetch_one:
                        return cursor.fetchone()
                    return cursor.fetchall()
            except Error as e:
                print(f"Error executing query: {e}")
                conn.rollback()
                return None
            finally:
                cursor.close()
        return None

    def get_client_groups(self):
        query = "SELECT id, name FROM client_groups"
        return self.execute_query(query)

    def get_clients_by_group(self, group_id):
        query = "SELECT id, first_name, last_name, email, phone FROM clients WHERE group_id = %s"
        return self.execute_query(query, (group_id,))

# Initialize the MySQL connection (assuming default credentials for now)
mysql_conn = MySQLConnection()


