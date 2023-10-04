from django.utils import timezone
from lesion_bank.models import PracticeImages, PracticeImageVoxels, TrueImageVoxels, GeneratedImages
from lesion_bank.forms import PracticeImageForm
from lesion_bank.array_functions import npToSql_uploads, niftiTo2d, reshapeTo3d
from django.shortcuts import render
from django.shortcuts import redirect
from lesion_bank.views import genericFunctions
from django.shortcuts import get_object_or_404
import numpy as np
import nibabel as nib
import os
import time
import json

# @login_required  # remove this line if you want to allow unauthenticated users to access the view
def practice_view(request):
    if request.method == 'POST':
        form = PracticeImageForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_image = form.save(commit=False)
            uploaded_image.upload_id = int(timezone.now().timestamp())
            uploaded_image.user = request.user if request.user.is_authenticated else None
            uploaded_image.save()
            # Call your function to populate UploadedImageVoxels for both files
            npToSql_uploads(niftiTo2d(uploaded_image.file_path.path), uploaded_image.upload_id, PracticeImageVoxels)
            npToSql_uploads(niftiTo2d(uploaded_image.true_file_path.path), uploaded_image.upload_id, TrueImageVoxels)
            # redirect or render a success message
            return redirect('practice_view_compare', upload_id=uploaded_image.upload_id)
    else:
        form = PracticeImageForm()
            
    return render(request, 'lesion_bank/practice.html', {'form': form})

def practice_view_compare(request, upload_id):
    # Fetch the PracticeImages record with the specified upload_id
    practice_image = PracticeImages.objects.get(upload_id=upload_id)
    
    # Get the file paths
    file_path = practice_image.file_path
    true_file_path = practice_image.true_file_path

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
    column_names, rows = genericFunctions.execute_query(query, params)
    result = rows[0]
    stats = dict(zip(column_names, result))

    
    return render(request, 'lesion_bank/practice_compare.html', {'stats': stats,
                                                                 'file_path': file_path,
                                                                 'true_file_path': true_file_path})


def practice_view_trace(request):
    if request.method == 'POST':
        logged_points = json.loads(request.POST.get('loggedPoints', '[]'))
        logged_points = np.array(logged_points)
        # 2 mm resolution:
        # affine = np.array([
        #     [-2., 0., 0., 90.],
        #     [0., 2., 0., -126.],
        #     [0., 0., 2., -72.],
        #     [0., 0., 0., 1.]
        # ])
        # shape=(91,109,91)
        # 1mm resolution:
        affine= np.array([
            [-1.,0.,0.,90.],
            [0.,1.,0.,-126.],
            [0.,0.,1.,-72.],
            [0.,0.,0.,1.]
        ])
        shape=(182,218,182)
        ni_img = nib.Nifti1Image(reshapeTo3d(logged_points, affine,shape), affine)
        # Specify the directory and filename for saving the image
        directory = 'media/output/'  # Replace with the desired directory
        file_id = str(int(time.time()))  # Get 10-digit UNIX timestamp
        filename = f"{file_id}_trace.nii.gz"
        filepath = os.path.join(directory, filename)
        nib.save(ni_img, filepath)

        # Remove the 'media/' part of the filepath
        filepath = filepath.replace('media/', '')

        # Create a GeneratedImages object
        image, created = GeneratedImages.objects.get_or_create(
            file_id=file_id,
            defaults={
                'file_path': filepath,
                'user': request.user if request.user.is_authenticated else None,
                'page_name': 'practice/trace'
            }
        )

        return redirect('trace_view', file_id=file_id)
    else:
        return render(request, 'lesion_bank/practice_trace.html')

def trace_view(request, file_id):
    image = get_object_or_404(GeneratedImages, file_id=file_id)
    return render(request, 'lesion_bank/trace_view.html', {'file_path': image.file_path})