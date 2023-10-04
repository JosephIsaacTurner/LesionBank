import nibabel as nib
import numpy as np
import psycopg2
import csv
import os
import boto3
from io import BytesIO
import gzip
from django.conf import settings
from decouple import config
# Define connection parameters
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
session = boto3.session.Session()
client = session.client('s3',
                        region_name='nyc3',
                        endpoint_url='https://nyc3.digitaloceanspaces.com',
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key)

def save_to_cloud(nii_img, path):
    def save(content, path):
        headers = {'ContentType': ''}
        client.upload_fileobj(content, "lesionbucket", f"uploads/sensitivity_maps/{path}", ExtraArgs=headers)
        return path
    img_data = nii_img.to_bytes()
    img_data_gz = BytesIO()
    with gzip.GzipFile(fileobj=img_data_gz, mode='w') as f_out:
        f_out.write(img_data)
    img_data_gz.seek(0)
    return save(img_data_gz, path)

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
    # symptom = 'Hypersomnia'
    # pos_threshold = 15
    # neg_threshold = -7
    # results = sensitivity_map(symptom, pos_threshold, neg_threshold)
    symptom = "REM Sleep Disorder"
    query = f"""
    SELECT 
        SPLIT_PART(voxel_id, '_', 1)::INT AS x,
        SPLIT_PART(voxel_id, '_', 2)::INT AS y,
        SPLIT_PART(voxel_id, '_', 3)::INT AS z,
        percent_overlap
    FROM 
        sensitivity_voxels 
    left join symptoms 
    on symptoms.id = sensitivity_voxels.symptom_id
    where symptoms.symptom = '{symptom}'
    ORDER BY 
        percent_overlap DESC;
    """
    filepath = f"{symptom}_sensitivity_parametric.nii.gz".replace(' ','_')
    results = any_map_type(query, filepath)
    print(results)



