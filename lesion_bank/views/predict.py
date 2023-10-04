from lesion_bank.array_functions import npToSql_uploads, niftiTo2d, reshapeTo3d, numpyToSql
from lesion_bank.models import GeneratedImages, PredictionVoxels
from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
import numpy as np
import nibabel as nib
import os
import time
import json
from django.http import HttpResponse
from django.core.files.storage import default_storage
import boto3
from django.conf import settings
from tempfile import NamedTemporaryFile
from django.db import connection
import gzip
from io import BytesIO
from django.conf import settings

private_symptoms = settings.PRIVATE_SYMPTOMS

if settings.USE_S3:
    SESSION = boto3.session.Session()
    CLIENT = SESSION.client('s3',
                            region_name='nyc3',
                            endpoint_url='https://nyc3.digitaloceanspaces.com',
                            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
    
    def upload_to_s3(content, path, client=CLIENT):
        headers = {'ContentType': ''}
        try:
            client.upload_fileobj(content, "lesionbucket", f"{path}", ExtraArgs=headers)
        except Exception as e:
            print(f"Failed to upload {path} to S3. Error: {e}")
            return None
        return path

def compress_nii_image(nii_img):
    img_data = nii_img.to_bytes()
    img_data_gz = BytesIO()
    with gzip.GzipFile(fileobj=img_data_gz, mode='w') as f_out:
        f_out.write(img_data)
    img_data_gz.seek(0)
    return img_data_gz

def save_local(nii_img, path):
    nib.save(nii_img, path)
    return path

def save_to_cloud(nii_img, path):
    if settings.USE_S3:
        compressed_img = compress_nii_image(nii_img)
        return upload_to_s3(compressed_img, path)
    else:
        save_local(nii_img, path)
        return None

def run_raw_sql(query, single_value=False):
    with connection.cursor() as cursor:
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


def predict(request):
    if request.method == 'POST':
        logged_points = json.loads(request.POST.get('loggedPoints', '[]'))
        logged_points = np.array(logged_points)
        # 2mm resolution: 
        # First, make the .nifti file in 1mm resolution
        # 1mm resolution:
        affine= np.array([
            [-1.,0.,0.,90.],
            [0.,1.,0.,-126.],
            [0.,0.,1.,-72.],
            [0.,0.,0.,1.]
        ])
        shape=(182,218,182)
        # 2 mm resolution
        # affine = np.array([
        #     [-2., 0., 0., 90.],
        #     [0., 2., 0., -126.],
        #     [0., 0., 2., -72.],
        #     [0., 0., 0., 1.]
        # ])
        # shape=(91,109,91)
        nii_img = nib.Nifti1Image(reshapeTo3d(logged_points, affine,shape), affine)
        file_id = str(int(time.time()))  # Get 10-digit UNIX timestamp
        filename = f"{file_id}_trace.nii.gz"
        filepath = os.path.join("prediction_traces/",filename)
        if settings.USE_S3:
            save_to_cloud(nii_img, os.path.join("uploads/",filepath))
        else:
            save_local(nii_img, os.path.join("uploads/", filepath))
       # Create a GeneratedImages object
        image, created = GeneratedImages.objects.get_or_create(
            file_id=file_id,
            defaults={
                'file_path': filepath,
                'user': request.user if request.user.is_authenticated else None,
                'page_name': 'predict'
            }
        )

        # Next, convert the original world space voxel data to 2mm resolution:
        # Find the odd values in the first 3 columns: they will have modulo 2 equals to 1.
        odd_indices = logged_points[:, :3] % 2 == 1
        logged_points[:, :3][odd_indices] += 1
        numpyToSql(logged_points, "file", image, PredictionVoxels)  # pass image instance instead of file_id

        # return HttpResponse("success running numpyToSql")
        return redirect('prediction_results', file_id=file_id)
    else:
        context = {}
        context["title"] = "Predict"
        context["initial_coord"] = "0_-18_6"
        return render(request, 'lesion_bank/predict_trace.html', context)

def prediction_results(request, file_id):
    image = get_object_or_404(GeneratedImages, file_id=file_id)
    prediction_query = f"""
        WITH join_table AS (
            SELECT prediction_voxels.voxel_id, symptom, percent_overlap, sensitivity_parametric_path
            FROM prediction_voxels 
            INNER JOIN sensitivity_voxels
            ON prediction_voxels.voxel_id = sensitivity_voxels.voxel_id
            LEFT JOIN symptoms
            ON sensitivity_voxels.symptom_id = symptoms.id
            WHERE prediction_voxels.file_id = {'file_id'}
        )
        SELECT
            AVG(percent_overlap),
            CASE
                WHEN AVG(percent_overlap) < 0 THEN 
                    CONCAT(ROUND(CAST(ABS(AVG(percent_overlap)) AS numeric), 2), '% (t<-7)')
                ELSE
                    CONCAT(ROUND(CAST(AVG(percent_overlap) AS numeric), 2), '% (t>+7)')
            END AS average_overlap, 
            symptom, 
            sensitivity_parametric_path 
        FROM join_table
        """

    if not request.user.is_authenticated:
        prediction_query += f""" WHERE symptom NOT IN ({', '.join(map(lambda x: f"'{x}'", private_symptoms))})"""
    prediction_query += " GROUP BY symptom, sensitivity_parametric_path ORDER BY AVG(percent_overlap) DESC"
    prediction_results = run_raw_sql(prediction_query)
    initial_coord_query = f"""
        select voxel_id from prediction_voxels where file_id = '{file_id}' limit 1
        """
    initial_coord = run_raw_sql(initial_coord_query, single_value=True)
    similar_case_studies_query = f"""
    select * from (
        select round(avg(cast(network_voxels.value as numeric)),2) as value, network_voxels.lesion_id, symptom
        , metadata.tracing_file_name, metadata.network_file_name, metadata.author, metadata.publication_year, metadata.doi
        , metadata.patient_age, metadata.patient_sex, metadata.cause_of_lesion from prediction_voxels
        inner join network_voxels
        on prediction_voxels.voxel_id = network_voxels.voxel_id
        inner join metadata 
        on metadata.lesion_id = network_voxels.lesion_id
        inner join metadata_symptoms 
        on metadata_symptoms.lesionmetadata_id = metadata.lesion_id 
        inner join symptoms 
        on metadata_symptoms.symptoms_id = symptoms.id
        where prediction_voxels.file_id = '{file_id}'
        group by network_voxels.lesion_id, symptom, tracing_file_Name, network_file_Name, author, publication_year, doi, patient_age, patient_sex, cause_of_lesion
    ) as filter_table
    where value > 50"""
    if not request.user.is_authenticated:
        similar_case_studies_query += f""" AND symptom NOT IN ({', '.join(map(lambda x: f"'{x}'", private_symptoms))})"""
    similar_case_studies_query += """ order by value desc """
    similar_case_studies = run_raw_sql(similar_case_studies_query)
    context = {}
    context['file_path'] = image.file_path
    context['prediction_results'] = prediction_results
    context['title'] = "Prediction Results"
    context['initial_coord'] = initial_coord
    context['similar_case_studies'] = similar_case_studies
    return render(request, 'lesion_bank/prediction_results.html', context)