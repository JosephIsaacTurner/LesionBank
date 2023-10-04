from django.http import HttpResponse, HttpRequest
import nibabel as nib
import numpy as np
from django.db import connection
import csv
import os

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
        with connection.cursor() as cursor:
            if params is None:
                cursor.execute(query)
            else:
                cursor.execute(query, params)
            rows = cursor.fetchall()
            if len(rows) == 0:
                return None
            np_array = np.array(rows)
            return np_array
    except Exception as e:
        print(f"An error occurred during query execution: {str(e)}")
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


def createMap(output, filename="output.nii.gz"):
    affine = np.array([
        [-2., 0., 0., 90.],
        [0., 2., 0., -126.],
        [0., 0., 2., -72.],
        [0., 0., 0., 1.]
    ])
    ni_img = nib.Nifti2Image(reshapeTo3d(output, affine), affine)
    # Specify the directory and filename for saving the image
    directory = 'django_project/static/generatedData/'  # Replace with the desired directory
    filepath = os.path.join(directory, filename)
    nib.save(ni_img, filepath)

def page(request):
    query = f"""    
        SELECT 
            * 
        FROM
            (SELECT 
                ROUND(AVG(t_stat)::numeric,2) AS avg,
                x,
                y,
                z 
            FROM networkscoordinates 
            inner join lesiontable
            on lesiontable.lesion_id = networkscoordinates.lesion_id
            where lesiontable.symptom = 'Amnesia'
            GROUP BY 
                x,
                y,
                z) AS innerquery
    """
    query = f"""
    select x,y,z, count(distinct lesion_id) from
        (select x, y, z, networkscoordinates.lesion_id from networkscoordinates
        left join lesiontable
        on lesiontable.lesion_id = networkscoordinates.lesion_id
        where t_stat > 7 or t_stat < -7
        and symptom = 'Amnesia') as inner1
        group by x, y, z
    """
    # query = f"""    
    #    select x, y,z,lesion_id from tracingscoordinates where lesion_id = 111
    # """
    query = """
        WITH id_list AS (
            SELECT distinct m.lesion_id 
            FROM metadata m
            LEFT JOIN metadata_symptoms ms ON m.lesion_id = ms.lesionmetadata_id
            LEFT JOIN symptoms s ON ms.symptoms_id = s.id 
            WHERE s.symptom = 'Amnesia'
        ),
        value_table as (
        select value,id_list.lesion_id,x,y,z from network_voxels 
        inner join id_list
        on id_list.lesion_id = network_voxels.lesion_id
        left join coordinates 
        on coordinates.voxel_id = network_voxels.voxel_id)
        select x,y,z, count(distinct lesion_id) from value_table where (value > 7 or value < -7)
        group by x,y,z
        order by count desc, x, y, z
    """
    filename = "testOutput.nii.gz"
    data = query_to_numpy(query)
    createMap(data, filename)
    html = f"""
    <!DOCTYPE html>
    <html xmlns="http://www.w3.org/1999/xhtml" lang="en">
        <head>
            <link rel='stylesheet' type='text/css' href='../static/css/papaya.css?version=0.8&build=979'/>
            <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
            <script type="text/javascript" src="https://cdn.jsdelivr.net/gh/rii-mango/Papaya@build-1449/release/current/minimal/papaya.js"></script>
            <title>Nifti Generator</title> 
            <script type="text/javascript">
                var params = [];
                params["images"] = ["../static/MRIData/GenericMNI.nii.gz", "../static/generatedData/{filename}"];
                params["worldSpace"] = true;
                params["expandable"] = true;
                params["combineParametric"] = true;
                params["showControls"] = false;
                params["smoothDisplay"] = false;
            </script>
        </head>
        <body>
            <div style="width: 50%; !important" class="papaya" data-params="params"></div>
        </body>
    </html>
    
    """
    return HttpResponse(html)



