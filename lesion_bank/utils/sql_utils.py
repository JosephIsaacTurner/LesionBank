from django.db import connection
connection = connection

class SQLUtils:

    def __init__(self, connection=connection):
        self.connection = connection

    def execute_query(self, statement, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(statement, params)
            rows = cursor.fetchall()
            column_names = [col[0] for col in cursor.description]  # get column names
        return column_names, rows