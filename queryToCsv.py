import csv
import psycopg2
from decouple import config

def export_query_to_csv(query, conn, csv_file_path='output.csv', batch_size=1000):
    try:
        with conn.cursor() as cur:  # Removed name='server_side_cursor' to use a regular cursor
            cur.itersize = batch_size
            cur.execute(query)
            conn.commit()  # Committing the transaction immediately after executing the query

            print(cur.statusmessage)
            
            # Attempt to fetch a row before checking the description
            cur.fetchone()  
            print(cur.description)

            if cur.description is None:
                print("The query did not return a result set.")
                return

            column_names = [desc[0] for desc in cur.description]

            with open(csv_file_path, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(column_names)
                
                for row in cur:
                    if row is None:
                        print("No more rows to fetch.")
                        break
                    csv_writer.writerow(row)
                
        print(f"Query results have been exported to {csv_file_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage:

# Define connection parameters from .env
params = {
    "host": config('DB_HOST'),
    "database": config('DB_NAME'),
    "user": config('DB_USER'),
    "password": config('DB_PASSWORD')
}

conn = psycopg2.connect(**params)
query = """
WITH 
x_arr AS (
    SELECT voxel_id, ROUND(CAST(percent_overlap AS NUMERIC), 5) as x_obs
    FROM sensitivity_voxels
    LEFT JOIN 
    symptoms ON sensitivity_voxels.symptom_id = symptoms.id
    WHERE symptom = 'REM Sleep Disorder'
),
y_arr AS (
    SELECT voxel_id, ROUND(CAST(percent_overlap AS NUMERIC), 5) as y_obs
    FROM sensitivity_voxels
    LEFT JOIN 
    symptoms ON sensitivity_voxels.symptom_id = symptoms.id
    WHERE symptom = 'Hypersomnia'
),
x_y_join AS (
    SELECT 
        COALESCE(x_arr.voxel_id, y_arr.voxel_id) AS voxel_id, 
        COALESCE(x_obs, 0) AS x_obs, 
        COALESCE(y_obs, 0) AS y_obs
    FROM x_arr
    FULL JOIN y_arr 
    ON x_arr.voxel_id = y_arr.voxel_id
),
x_y_stats AS (
    SELECT 
        ROUND(AVG(x_obs)::NUMERIC, 5) AS x_mean, 
        ROUND(STDDEV(x_obs)::NUMERIC, 5) AS x_std_dev,
        ROUND(AVG(y_obs)::NUMERIC, 5) AS y_mean, 
        ROUND(STDDEV(y_obs)::NUMERIC, 5) AS y_std_dev
    FROM x_y_join
),
basic_stats_table AS (
    SELECT 
        voxel_id, 
        x_obs,  
        y_obs, 
        x_mean, 
        x_std_dev, 
        y_mean, 
        y_std_dev 
    FROM x_y_join
    LEFT JOIN x_y_stats
    ON 1=1
),
aggregate_stats_table AS (
    SELECT
        ROUND(covar::NUMERIC, 5) AS covar, 
        ROUND((covar/(x_std_dev * y_std_dev))::NUMERIC, 5) AS r_original 
    FROM
        (SELECT COVAR_SAMP(x_obs, y_obs) AS covar FROM basic_stats_table) AS a
    LEFT JOIN basic_stats_table AS b
    ON 1 = 1
    limit 1
)
select * from aggregate_stats_table
LEFT JOIN basic_stats_table
ON 1 = 1
"""
# query = """
# select * from metadata LIMIT 50"""

export_query_to_csv(query, conn, "full_cleaned_data.csv")

# Don't forget to close the connection
conn.close()
