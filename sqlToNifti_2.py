import nibabel as nib
import numpy as np
import psycopg2
import csv
import os
import boto3
from io import BytesIO
import gzip
from decouple import config
# Define connection parameters from .env
params = {
    "host": config('DB_HOST'),
    "database": config('DB_NAME'),
    "user": config('DB_USER'),
    "password": config('DB_PASSWORD')
}

conn = psycopg2.connect(**params)
access_key = config('AWS_ACCESS_KEY_ID')
secret_key = config('AWS_SECRET_ACCESS_KEY')
SESSION = boto3.session.Session()
CLIENT = SESSION.client('s3',
                        region_name='nyc3',
                        endpoint_url='https://nyc3.digitaloceanspaces.com',
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key)

def compress_nii_image(nii_img):
    img_data = nii_img.to_bytes()
    img_data_gz = BytesIO()
    with gzip.GzipFile(fileobj=img_data_gz, mode='w') as f_out:
        f_out.write(img_data)
    img_data_gz.seek(0)
    return img_data_gz

def upload_to_s3(content, path, client=CLIENT):
    headers = {'ContentType': ''}
    try:
        client.upload_fileobj(content, "lesionbucket", f"{path}", ExtraArgs=headers)
    except Exception as e:
        print(f"Failed to upload {path} to S3. Error: {e}")
        return None
    return path

def save_to_cloud(nii_img, path):
    compressed_img = compress_nii_image(nii_img)
    return upload_to_s3(compressed_img, path)

def run_raw_sql(query, single_value=False):
    with conn.cursor() as cursor:
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
    
def csv_to_numpy(csv_file):
    try:
        with open(csv_file, 'r') as file:
            csv_data = csv.reader(file)
            data_list = list(csv_data)
        np_array = np.array(data_list)
        return np_array
    except Exception as e:
        print(f"An error occurred while converting CSV to NumPy array: {str(e)}")
        return None

def query_to_numpy(query, params=None):
    print("starting query")
    try:
        with conn.cursor() as cursor:  # this ensures you're using a new cursor for each call
            if params is None:
                cursor.execute(query)
            else:
                cursor.execute(query, params)
            rows = cursor.fetchall()
            if len(rows) == 0:
                print(f"no results for:{query}")
                return None
            np_array = np.array(rows)
            print("query successfully executed.")
            return np_array
    except Exception as e:
        print(f"An error occurred during query execution: {str(e)}")
        raise e  # This will show you the full error stack trace.        
        return None

def reshapeTo3d(np_array, affine=np.array([
        [-2., 0., 0., 90.],
        [0., 2., 0., -126.],
        [0., 0., 2., -72.],
        [0., 0., 0., 1.]
    ])):
    # It expects the values to be the first element, then x, y, z.
    oldCoords = np_array[:, :3].astype(float)  # Extract the first three values as coordinates
    inverseMatrix = np.linalg.inv(affine)
    # Create the final transformed array
    mni_shape = (91, 109, 91)
    mni_array = np.zeros(mni_shape, dtype=float)
    oldCoords = np.hstack((oldCoords, np.ones((len(np_array), 1))))
    newCoords = np.dot(oldCoords, inverseMatrix.T)
    newCoords = newCoords[:, :3]  # Extract only the transformed coordinates
    # Convert the transformed coordinates to integers and assign values in mni_array
    newCoords = newCoords.astype(int)
    mni_array[newCoords[:, 0], newCoords[:, 1], newCoords[:, 2]] = np_array[:, 3]
    return mni_array

def createMap(data, filename="output.nii.gz"):
    affine = np.array([
        [-2., 0., 0., 90.],
        [0., 2., 0., -126.],
        [0., 0., 2., -72.],
        [0., 0., 0., 1.]
    ])
    nii_img = nib.Nifti1Image(reshapeTo3d(data, affine), affine)
    # Specify the directory and filename for saving the image
    # directory = '/home/django/django_project/staticfiles/generatedData'  # Replace with the desired directory
    # filepath = os.path.join(directory, filename)
    save_to_cloud(nii_img, filename)
    # nib.save(nii_img, filepath)

def sensitivity_map(symptom, pos_threshold, neg_threshold):
    pos_query = f"""
        WITH id_list AS (
            SELECT distinct m.lesion_id 
            FROM metadata m
            LEFT JOIN metadata_symptoms ms ON m.lesion_id = ms.lesionmetadata_id
            LEFT JOIN symptoms s ON ms.symptoms_id = s.id 
            WHERE s.symptom = '{symptom}'
        ),
        value_table as (
        select value,id_list.lesion_id,x,y,z from network_voxels 
        inner join id_list
        on id_list.lesion_id = network_voxels.lesion_id
        left join coordinates 
        on coordinates.voxel_id = network_voxels.voxel_id)
        select x,y,z, count(distinct lesion_id) from value_table where (value > {pos_threshold})
        group by x,y,z
        order by count desc, x, y, z
    """
    neg_query = f"""
        WITH id_list AS (
            SELECT distinct m.lesion_id 
            FROM metadata m
            LEFT JOIN metadata_symptoms ms ON m.lesion_id = ms.lesionmetadata_id
            LEFT JOIN symptoms s ON ms.symptoms_id = s.id 
            WHERE s.symptom = '{symptom}'
        ),
        value_table as (
        select value,id_list.lesion_id,x,y,z from network_voxels 
        inner join id_list
        on id_list.lesion_id = network_voxels.lesion_id
        left join coordinates 
        on coordinates.voxel_id = network_voxels.voxel_id)
        select x,y,z, count(distinct lesion_id) from value_table where (value < {neg_threshold})
        group by x,y,z
        order by count desc, x, y, z
    """
    pos_filename = f"{symptom.replace(' ', '_')}_sensitivity_pos_alt.nii.gz"
    neg_filename = f"{symptom.replace(' ', '_')}_sensitivity_neg_alt.nii.gz"
    pos_data = query_to_numpy(pos_query)
    createMap(pos_data, pos_filename)
    neg_data = query_to_numpy(neg_query)
    createMap(neg_data, neg_filename)

    update_sensitivity_table_query = f"""
    insert into sensitivity_voxels
        select * from       
        (with pos as (
        select * from  (
        WITH id_list AS (
            SELECT DISTINCT m.lesion_id 
            FROM metadata m
            LEFT JOIN metadata_symptoms ms ON m.lesion_id = ms.lesionmetadata_id
            LEFT JOIN symptoms s ON ms.symptoms_id = s.id 
            WHERE s.symptom = '{symptom}'
        ),
        value_table AS (
            SELECT value, id_list.lesion_id, network_voxels.voxel_id 
            FROM network_voxels 
            INNER JOIN id_list ON id_list.lesion_id = network_voxels.lesion_id
        ),
        count_table as (
        SELECT voxel_id, COUNT(DISTINCT lesion_id)
        FROM value_table 
        WHERE value > {pos_threshold}
        GROUP BY voxel_id)
        select * from _
        count_table
        left join 
        (
        select count(*) as total from id_list) as a
        on 1 = 1
        ORDER BY COUNT DESC, voxel_id) as b),
        neg as (
        select * from  (
        WITH id_list AS (
            SELECT DISTINCT m.lesion_id 
            FROM metadata m
            LEFT JOIN metadata_symptoms ms ON m.lesion_id = ms.lesionmetadata_id
            LEFT JOIN symptoms s ON ms.symptoms_id = s.id 
            WHERE s.symptom = '{symptom}'
        ),
        value_table AS (
            SELECT value, id_list.lesion_id, network_voxels.voxel_id 
            FROM network_voxels 
            INNER JOIN id_list ON id_list.lesion_id = network_voxels.lesion_id
        ),
        count_table as (
        SELECT voxel_id, COUNT(DISTINCT lesion_id)
        FROM value_table 
        WHERE value < {neg_threshold}
        GROUP BY voxel_id)
        select * from 
        count_table
        left join 
        (
        select count(*) as total from id_list) as a
        on 1 = 1
        ORDER BY COUNT DESC, voxel_id) as b)
        select coalesce(pos.voxel_id, neg.voxel_id) as voxel_id, symptoms.id as symptom_id, coalesce(pos.count,0) as positive_overlap_count, coalesce(neg.count,0) as negative_overlap_count, coalesce(pos.count,0) - coalesce(neg.count,0) as overlap_difference, pos.total, ((coalesce(pos.count,0) - coalesce(neg.count,0)) * 100 ) / pos.total as percent_overlap from pos
        full join 
        neg
        on neg.voxel_id = pos.voxel_id
        join 
        (select * from symptoms
        where symptom = '{symptom}') as symptoms
        on 1 = 1
        order by overlap_difference desc) as final
    """
    return pos_filename, neg_filename

def any_map_type(query, filepath):
    data = query_to_numpy(query)
    createMap(data, filepath)
    return filepath

    
if __name__== '__main__':
    print("starting")
    symptom1 = "Alice in Wonderland Syndrome"
    symptom2 = "Neglect Syndrome"
    query = f"""
    WITH 
    {symptom1.replace(' ','_')} AS (
        SELECT voxel_id, percent_overlap as percent_overlap_{symptom1.replace(' ','_')}
        FROM sensitivity_voxels
        left join 
        symptoms on sensitivity_voxels.symptom_id = symptoms.id
        WHERE symptom = '{symptom1}'
    ),
    {symptom2.replace(' ','_')} AS (
        SELECT voxel_id, percent_overlap as percent_overlap_{symptom2.replace(' ','_')}
        FROM sensitivity_voxels
        left join 
        symptoms on sensitivity_voxels.symptom_id = symptoms.id
        WHERE symptom = '{symptom2}'
    ),
    {symptom1.replace(' ','_')}Stats AS (
        SELECT 
            AVG(percent_overlap) as mean_{symptom1.replace(' ','_')}, 
            STDDEV(percent_overlap) as {symptom1.replace(' ','_')}_std_dev
        FROM sensitivity_voxels
        left join 
        symptoms on sensitivity_voxels.symptom_id = symptoms.id
        WHERE symptom = '{symptom1}'
    ),
    {symptom2.replace(' ','_')}Stats AS (
        SELECT 
            AVG(percent_overlap) as mean_{symptom2.replace(' ','_')}, 
            STDDEV(percent_overlap) as {symptom2.replace(' ','_')}_std_dev
        FROM sensitivity_voxels
        left join 
        symptoms on sensitivity_voxels.symptom_id = symptoms.id
        WHERE symptom = '{symptom2}'
    ),
    CorrNumerator AS (
        SELECT 
            i.voxel_id,
            ((i.percent_overlap_{symptom1.replace(' ','_')} - {symptom1[:3].replace(' ','_')}_stats.mean_{symptom1.replace(' ','_')}) * (h.percent_overlap_{symptom2.replace(' ','_')} - {symptom2[:3].replace(' ','_')}_stats.mean_{symptom2.replace(' ','_')})) as pearson_numerator_element
        FROM {symptom1.replace(' ','_')} i
        JOIN {symptom2.replace(' ','_')} h ON i.voxel_id = h.voxel_id
        CROSS JOIN {symptom1.replace(' ','_')}Stats {symptom1[:3].replace(' ','_')}_stats
        CROSS JOIN {symptom2.replace(' ','_')}Stats {symptom2[:3].replace(' ','_')}_stats
    ),
    CorrDenominator AS (
        SELECT 
            SUM(POWER(i.percent_overlap_{symptom1.replace(' ','_')} - {symptom1[:3].replace(' ','_')}_stats.mean_{symptom1.replace(' ','_')}, 2)) as {symptom1.replace(' ','_')}_denominator, 
            SUM(POWER(h.percent_overlap_{symptom2.replace(' ','_')} - {symptom2[:3].replace(' ','_')}_stats.mean_{symptom2.replace(' ','_')}, 2)) as {symptom2.replace(' ','_')}_denominator
        FROM {symptom1.replace(' ','_')} i
        JOIN {symptom2.replace(' ','_')} h ON i.voxel_id = h.voxel_id
        CROSS JOIN {symptom1.replace(' ','_')}Stats {symptom1[:3].replace(' ','_')}_stats
        CROSS JOIN {symptom2.replace(' ','_')}Stats {symptom2[:3].replace(' ','_')}_stats
    ),
    contrib_table as (
    SELECT 
        cn.voxel_id,
        (cn.pearson_numerator_element / SQRT(cd.{symptom1.replace(' ','_')}_denominator * cd.{symptom2.replace(' ','_')}_denominator)) as pearson_coefficient_contribution
    FROM CorrNumerator cn
    CROSS JOIN CorrDenominator cd)
    --select sum(pearson_coefficient_contribution)
    select 
    SPLIT_PART(voxel_id, '_', 1) AS x,
        SPLIT_PART(voxel_id, '_', 2) AS y,
        SPLIT_PART(voxel_id, '_', 3) AS z,
        round(cast(pearson_coefficient_contribution as numeric) * count, 3) as contribution from contrib_table
    left join (select count(*) as count from contrib_table) as count
    on 1=1
    order by pearson_coefficient_contribution asc
    """
    query = f"""
WITH 
x_arr AS (
    SELECT voxel_id, percent_overlap as x_obs
    FROM sensitivity_voxels
    LEFT JOIN 
    symptoms ON sensitivity_voxels.symptom_id = symptoms.id
    WHERE symptom = '{symptom1}'
    AND percent_overlap>0
),
y_arr AS (
    SELECT voxel_id, percent_overlap as y_obs
    FROM sensitivity_voxels
    LEFT JOIN 
    symptoms ON sensitivity_voxels.symptom_id = symptoms.id
    WHERE symptom = '{symptom2}'
    AND percent_overlap>0
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
       	x_var,
       	y_var,
        (covar/(x_std_dev * y_std_dev))::NUMERIC AS r_original
        , total_count
    FROM
        (SELECT COVAR_POP(x_obs, y_obs) AS covar FROM basic_stats_table) AS a
    LEFT JOIN basic_stats_table AS b
    ON 1 = 1
    left join 
    (select count(*) as total_count from x_y_join) as count_table
    on 1 = 1
    left join 
    (select variance(x_obs) as x_var from x_y_join) as c
    on 1 = 1
    left join 
    (select variance(y_obs) as y_var from x_y_join) as d
    on 1 = 1
    limit 1
), full_stats as (
select * from aggregate_stats_table
LEFT JOIN basic_stats_table
ON 1 = 1),
estimator_array as (
select 
voxel_id,
((x_obs-x_mean)*(y_obs-y_mean))/(x_std_dev * y_std_dev * total_count ) as numerator
, r_original
,
(
    sqrt(
        x_var + (
            (POWER((x_obs - x_mean),2) - x_var)/total_count
            )
        )
    ) 
    / x_std_dev
- 1 as x_growth_est,
(
    sqrt(
        y_var + (
            (POWER((y_obs - y_mean),2) - y_var)/total_count
            )
        )
    ) 
    / y_std_dev
- 1 as y_growth_est
from full_stats),
r_contrib_table as (
select 
voxel_id,
r_original,
 SPLIT_PART(voxel_id, '_', 1) AS x,
        SPLIT_PART(voxel_id, '_', 2) AS y,
        SPLIT_PART(voxel_id, '_', 3) AS z,
numerator - r_original * (x_growth_est+y_growth_est) as r_contrib
from estimator_array)
--select sum(numerator), r_original from estimator_array
--group by r_original
select 
x, y, z, r_contrib/r_original * 100 as r_contrib_percentage
--sum(r_contrib/r_original)
--sum(r_contrib), r_original
from r_contrib_table
--group by r_original

    """
    filepath = f"symptom_comparison_pos_{symptom1}_{symptom2}.nii.gz".replace(' ','_')
    print(query)
    results = any_map_type(query, filepath)
    print(results)



