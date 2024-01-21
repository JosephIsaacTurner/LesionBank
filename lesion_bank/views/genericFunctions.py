from django.db import connection

def execute_query(statement, params=None):
    with connection.cursor() as cursor:
        cursor.execute(statement, params)
        rows = cursor.fetchall()
        column_names = [col[0] for col in cursor.description]  # get column names
    return column_names, rows