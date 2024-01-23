from django.db import connection

class SQLUtils:

    def __init__(self):
        self.connection = connection

    def execute_query(self, statement, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(statement, params)
            rows = cursor.fetchall()
            column_names = [col[0] for col in cursor.description]  # get column names
        return column_names, rows
    
    def run_raw_sql(self, query, single_value=False):
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            if single_value:
                # If we expect a single value, fetch and return that directly
                return cursor.fetchone()[0]
            # Fetch the column names from the cursor description
            column_names = [col[0] for col in cursor.description]
            return [
                dict(zip(column_names, row))
                for row in cursor.fetchall()
            ]