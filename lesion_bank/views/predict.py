from lesion_bank.array_functions import reshapeTo3d, numpyToSql
from lesion_bank.models import GeneratedImages, PredictionVoxels
from django.shortcuts import render, redirect, get_object_or_404
import numpy as np
import nibabel as nib
import os
import time
import json
from django.conf import settings
from django.db import connection
from django.utils.module_loading import import_string
from django.conf import settings
from lesion_bank.tasks import compute_network_map_async
import requests
from lesion_bank.utils.nifti_utils import NiftiHandler

CustomStorage = import_string(settings.DEFAULT_FILE_STORAGE)

private_symptoms = settings.PRIVATE_SYMPTOMS
storage = CustomStorage()

def save_to_cloud(nii_img, path, bucketName=settings.AWS_STORAGE_BUCKET_NAME):
    # The save method from CustomStorage is used to handle both the compression and the uploading process
    compressed_img = storage.compress_nii_image(nii_img)
    return storage.save(name=path, content=compressed_img, bucket_name=bucketName)

def save_local(nii_img, path):
    # This function remains unchanged as it is specific to local saving and not present in CustomStorage
    nib.save(nii_img, path)
    return path

def save_image(nii_img, path, bucketName=settings.AWS_STORAGE_BUCKET_NAME):
    if settings.USE_S3:
        return save_to_cloud(nii_img, path, bucketName)
    else:
        return save_local(nii_img, path)

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
        nifti_handler = NiftiHandler()
        # Find resolution of mask from form data (can be either 1mm or 2mm)
        mask_resolution = request.POST.get('selectedMask', '2mm') # Default to 2mm if not specified

        # Get the logged points from the form data (these are the voxels that the user selected in the mask)        
        logged_points = json.loads(request.POST.get('loggedPoints', '[]'))
        logged_points = np.array(logged_points)

        # Generate file_id and filename from UNIX timestamp
        file_id = str(int(time.time()))  # Get 10-digit UNIX timestamp
        full_file_path = f"mask_input/{file_id}/{mask_resolution}/input_mask.nii.gz"

        if mask_resolution == '1mm':
            file_path_1mm = full_file_path
            # First, make the .nifti file in 1mm resolution
            affine= np.array([
                [-1.,0.,0.,90.],
                [0.,1.,0.,-126.],
                [0.,0.,1.,-72.],
                [0.,0.,0.,1.]
            ])
            shape=(182,218,182) # 1mm resolution shape
            nii_img = nib.Nifti1Image(reshapeTo3d(logged_points, affine,shape), affine)
            # filepath_1mm = os.path.join("prediction_traces/",filename) # Standardize filepath
            save_image(nii_img, full_file_path)

            # Even though the selected mask is 1mm, we still need to save the 2mm version for lesion network mapping
            affine = np.array([
                [-2., 0., 0., 90.],
                [0., 2., 0., -126.],
                [0., 0., 2., -72.],
                [0., 0., 0., 1.]
            ])
            shape=(91,109,91) # 2mm resolution shape
            nii_img = nib.Nifti1Image(reshapeTo3d(logged_points, affine,shape), affine)
            filename_2mm = f"2mm/input_mask.nii.gz" # Create filename in separate folder for each resolution
            full_2mm_file_path = os.path.join(f"mask_input/{file_id}/", filename_2mm) # Include file_id as parent directory for mask
            save_image(nii_img, full_2mm_file_path)
        
        # If mask resolution is 2mm:
        if mask_resolution == '2mm':
            file_path_1mm = ''
            # First, make the .nifti file in 2mm resolution
            affine = np.array([
                [-2., 0., 0., 90.],
                [0., 2., 0., -126.],
                [0., 0., 2., -72.],
                [0., 0., 0., 1.]
            ])
            shape=(91,109,91)
            nifti_handler.populate_from_2d_array(logged_points)
            nii_img = nib.Nifti1Image(reshapeTo3d(logged_points, affine,shape), affine)
            save_image(nii_img, full_file_path)
        
        image, created = GeneratedImages.objects.get_or_create(
            file_id=file_id,
            defaults={
                'mask_filepath': f"mask_input/{file_id}/{mask_resolution}/input_mask.nii.gz",
                'file_path_2mm': f"mask_input/{file_id}/2mm/input_mask.nii.gz",
                'file_path_1mm': file_path_1mm,
                'lesion_network_filepath': f"network_maps_output/{file_id}/input_mask_Precom_T.nii.gz",
                'user': request.user if request.user.is_authenticated else None,
                'page_name': 'Predict'
            }
        )

        # Next, convert the original world space voxel data to 2mm resolution:
        # Find the odd values in the first 3 columns: they will have modulo 2 equals to 1.
        odd_indices = logged_points[:, :3] % 2 == 1
        logged_points[:, :3][odd_indices] += 1
        numpyToSql(logged_points, "file", image, PredictionVoxels)  # pass image instance instead of file_id

        compute_network_map_async.delay(f"s3://lesionbucket/uploads/mask_input/{file_id}/2mm", f"s3://lesionbucket/uploads/network_maps_output/{file_id}")
        
        return redirect('prediction_results', file_id=file_id)
    else:
        context = {}
        context["title"] = "Predict"
        context["page_name"] = "Predict"
        context["initial_coord"] = "0_-18_6"
        return render(request, 'lesion_bank/predict_trace.html', context)

def prediction_results(request, file_id):
    image = get_object_or_404(GeneratedImages, file_id=file_id)
    url_to_check = f'https://lesionbucket.nyc3.digitaloceanspaces.com/uploads/network_maps_output/{file_id}/input_mask_Precom_T.nii.gz'
    # Check if the file exists
    response = requests.head(url_to_check)

    # if the response status is 404 (Not Found), then return the loading page
    if response.status_code == 404:
        return render(request, 'lesion_bank/loading.html', {'file_id': file_id, 'url_to_check': url_to_check})
    
    prediction_query = f"""
        WITH join_table AS (
            SELECT prediction_voxels.voxel_id, symptom, percent_overlap, sensitivity_parametric_path
            FROM prediction_voxels 
            INNER JOIN sensitivity_voxels
            ON prediction_voxels.voxel_id = sensitivity_voxels.voxel_id
            LEFT JOIN symptoms
            ON sensitivity_voxels.symptom_id = symptoms.id
            WHERE prediction_voxels.file_id = '{file_id}'
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
    context['file_path'] = image.mask_filepath
    context['network_path'] = image.lesion_network_filepath #f"https://lesionbucket.nyc3.digitaloceanspaces.com/uploads/network_maps_output/{file_id}/{file_id}_2mm_trace_Precom_T.nii.gz"
    context['prediction_results'] = prediction_results
    context['title'] = "Prediction Results"
    context['initial_coord'] = initial_coord
    context['similar_case_studies'] = similar_case_studies
    context['page_name'] = 'Predict'
    return render(request, 'lesion_bank/prediction_results.html', context)