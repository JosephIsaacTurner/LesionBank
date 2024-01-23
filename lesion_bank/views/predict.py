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

private_symptoms = settings.PRIVATE_SYMPTOMS

def predict(request):
    if request.method == 'POST':
        nifti_handler = NiftiHandler()

        # Get resolution and logged points from form data
        mask_resolution = request.POST.get('selectedMask', '2mm')  # Default to 2mm
        logged_points = json.loads(request.POST.get('loggedPoints', '[]'))
        logged_points_array = np.array(logged_points)

        # Generate file_id and base file path
        file_id = str(int(time.time()))  # UNIX timestamp
        base_file_path = f"mask_input/{file_id}"

        # Function to handle Nifti file creation and S3 upload
        def create_and_upload_nifti(resolution, subfolder=''):
            file_path = f"{base_file_path}/{subfolder}input_mask.nii.gz"
            nifti_handler.populate_from_2d_array(logged_points_array, resolution)
            nifti_handler.save_to_s3(file_path, resolution)
            return file_path

        # Create Nifti file and upload to S3
        file_path_2mm = create_and_upload_nifti('2mm', '2mm/')
        file_path_1mm = ''
        if mask_resolution == '1mm':
            file_path_1mm = create_and_upload_nifti('1mm', '1mm/')

        # Create or update database record
        image_id, created = GeneratedImages.objects.get_or_create(
            file_id=file_id,
            defaults={
                'mask_filepath': f"{base_file_path}/{mask_resolution}/input_mask.nii.gz",
                'file_path_2mm': file_path_2mm,
                'file_path_1mm': file_path_1mm,
                'lesion_network_filepath': f"network_maps_output/{file_id}/input_mask_Precom_T.nii.gz",
                'user': request.user if request.user.is_authenticated else None,
                'page_name': 'Predict'
            }
        )

        # Save logged points to database
        nifti_handler.df_voxel_id_to_sql("file", image_id, PredictionVoxels)

        # Asynchronous task call
        compute_network_map_async.delay(f"s3://lesionbucket/uploads/{file_path_2mm}",
                                        f"s3://lesionbucket/uploads/network_maps_output/{file_id}")

        # Redirect to results
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
    
    nifti_handler = NiftiHandler()
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
    prediction_results = nifti_handler.run_raw_sql(prediction_query)
    initial_coord_query = f"""
        select voxel_id from prediction_voxels where file_id = '{file_id}' limit 1
        """
    initial_coord = nifti_handler.run_raw_sql(initial_coord_query, single_value=True)
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
    similar_case_studies = nifti_handler.run_raw_sql(similar_case_studies_query)
    context = {}
    context['file_path'] = image.mask_filepath
    context['network_path'] = image.lesion_network_filepath
    context['prediction_results'] = prediction_results
    context['title'] = "Prediction Results"
    context['initial_coord'] = initial_coord
    context['similar_case_studies'] = similar_case_studies
    context['page_name'] = 'Predict'
    return render(request, 'lesion_bank/prediction_results.html', context)