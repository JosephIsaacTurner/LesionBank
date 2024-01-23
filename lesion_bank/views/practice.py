from django.utils import timezone
from lesion_bank.models import PracticeImages, PracticeImageVoxels, TrueImageVoxels, GeneratedImages
from lesion_bank.forms import PracticeImageForm
from lesion_bank.array_functions import npToSql_uploads, niftiTo2d, reshapeTo3d, getNiftiFromCloud, niftiObjTo2d, npToSql, numpyToSql
from django.shortcuts import render, redirect
from lesion_bank.utils.sql_utils import SQLUtils
from django.shortcuts import get_object_or_404
import numpy as np
import nibabel as nib
import os
import time
import json

# @login_required  # remove this line if you want to allow unauthenticated users to access the view

def practice_view(request):
    info_messages = []
    error_message = None

    try:
        if request.method == 'POST':
            form = PracticeImageForm(request.POST, request.FILES)
            info_messages.append(f"Form received: {form.is_valid()}")

            if form.is_valid():
                uploaded_image = form.save(commit=False)
                uploaded_image.upload_id = int(timezone.now().timestamp())
                uploaded_image.user = request.user if request.user.is_authenticated else None

                info_messages.append(f"Upload ID: {uploaded_image.upload_id}")
                info_messages.append(f"User: {uploaded_image.user}")

                uploaded_image.save()
                info_messages.append("Image saved successfully.")

                # Add file related info
                info_messages.append(f"File name: {uploaded_image.file_name.name}")
                info_messages.append(f"True file name: {uploaded_image.true_file_name.name}")

                try:
                    file_path = uploaded_image.file_name.name
                    true_file_path = uploaded_image.true_file_name.name
                    info_messages.append(f"File path: {file_path}")
                    info_messages.append(f"True file path: {true_file_path}")
                    numpyToSql(niftiObjTo2d(getNiftiFromCloud(file_path)), 'upload_id', uploaded_image.upload_id, PracticeImageVoxels)
                    info_messages.append(f"File {file_path} processed successfully.")
                    numpyToSql(niftiObjTo2d(getNiftiFromCloud(true_file_path)), 'upload_id', uploaded_image.upload_id, TrueImageVoxels)
                    info_messages.append(f"File {true_file_path} processed successfully.")

                except Exception as e:
                    error_message = f"Error during file processing: {str(e)}"
                    return render(request, 'lesion_bank/debugging.html', {
                        'error_message': error_message,
                        'info_messages': info_messages
                    })

                return redirect('practice_view_compare', upload_id=uploaded_image.upload_id)
        else:
            form = PracticeImageForm()

        return render(request, 'lesion_bank/practice.html', {'form': form})

    except Exception as e:
        error_message = f"Error in view: {str(e)}"

    return render(request, 'lesion_bank/debugging.html', {
        'error_message': error_message,
        'info_messages': info_messages
    })

def practice_view_compare(request, upload_id):
    # Fetch the PracticeImages record with the specified upload_id
    practice_image = PracticeImages.objects.get(upload_id=upload_id)
    
    # Get the file paths
    file_path = practice_image.file_name.name
    true_file_path = practice_image.true_file_name.name

    query = """
    WITH 
        upload_id AS (
            SELECT %(upload_id)s AS id
        ),
        numerator_result AS (
            SELECT COUNT(*) AS numerator 
            FROM true_image_voxels 
            INNER JOIN practice_image_voxels
                ON practice_image_voxels.voxel_id = true_image_voxels.voxel_id 
                AND practice_image_voxels.upload_id = true_image_voxels.upload_id
            WHERE true_image_voxels.upload_id = (SELECT id FROM upload_id)
        ),
        denominator_result AS (
            SELECT COUNT(*) AS denominator 
            FROM true_image_voxels 
            FULL OUTER JOIN practice_image_voxels
                ON practice_image_voxels.voxel_id = true_image_voxels.voxel_id 
                AND practice_image_voxels.upload_id = true_image_voxels.upload_id
            WHERE true_image_voxels.upload_id = (SELECT id FROM upload_id) 
            OR practice_image_voxels.upload_id = (SELECT id FROM upload_id)
        ),
        true_voxel_counts AS (
            SELECT COUNT(*) AS true_voxel_count 
            FROM true_image_voxels 
            WHERE upload_id = (SELECT id FROM upload_id)
        ),
        practice_voxel_counts AS (
            SELECT COUNT(*) AS practice_voxel_count 
            FROM practice_image_voxels 
            WHERE upload_id = (SELECT id FROM upload_id)
        )
    SELECT 
        numerator, 
        true_voxel_count, 
        practice_voxel_count,
        denominator, 
        ROUND((numerator::decimal / denominator),5) AS jaccard_similarity_coefficient
    FROM 
        numerator_result, 
        denominator_result, 
        true_voxel_counts,
        practice_voxel_counts
    """
    params = {'upload_id':int(upload_id)}
    sql_util = SQLUtils()
    column_names, rows = sql_util.execute_query(query, params)
    result = rows[0]
    stats = dict(zip(column_names, result))

    
    return render(request, 'lesion_bank/practice_compare.html', {'stats': stats,
                                                                 'file_name': file_path,
                                                                 'true_file_name': true_file_path})

def trace_view(request, file_id):
    image = get_object_or_404(GeneratedImages, file_id=file_id)
    return render(request, 'lesion_bank/trace_view.html', {'file_path': image.file_path})