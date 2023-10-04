import nibabel as nib
import numpy as np
import os
import django
from datetime import datetime
# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

# Configure the Django environment
django.setup()

from lesion_bank.models import UploadedVoxels, Coordinates, LesionMetadata, Symptoms
from django.db import transaction
from django.db.models import Max

def fillMetadataTable(model=LesionMetadata, symptoms=[], author="", publication_year=None, doi="", cause_of_lesion="", original_image_1="", original_image_2="", original_image_3="", original_image_4="", tracing_file_name="", network_file_name=""):
    latest_id = model.objects.aggregate(Max('lesion_id'))['lesion_id__max']  # Find the latest lesion_id
    new_id = latest_id + 1 if latest_id is not None else 0  # If the table is empty, start at 0
    new_record = model.objects.create(lesion_id=int(new_id), author=author, publication_year=publication_year,
                                      doi=doi, cause_of_lesion=cause_of_lesion, original_image_1=original_image_1,
                                      original_image_2=original_image_2, original_image_3=original_image_3,
                                      original_image_4=original_image_4, tracing_file_name=tracing_file_name,
                                      network_file_name=network_file_name)

    for symptom_name in symptoms:
        symptom_obj, created = Symptoms.objects.get_or_create(symptom=symptom_name)
        new_record.symptoms.add(symptom_obj)

    return new_id



# def fillMetadataTable(model=LesionMetadata, author="", publication_year="", doi="", cause_of_lesion="", original_image_1="", original_image_2="",original_image_3="",original_image_4="",tracing_file_name="",network_file_name="", symptoms=[]):
#     latest_id = model.objects.aggregate(Max('lesion_id'))['lesion_id__max']  # Find the latest lesion_id
#     new_id = latest_id + 1 if latest_id is not None else 0  # If the table is empty, start at 0
#     new_record = model.objects.create(lesion_id=int(new_id))  # Create a new record with the new_id

#     # Return the new_id or the created object if needed
#     return new_id


def fillCoordinateTable(np_array, model=Coordinates):
    if np_array.shape[1] == 4:
        # Create voxel_id from x, y, z coordinates
        voxel_id = np.array(['{}_{}_{}'.format(a, b, c) for a, b, c in zip(np_array[:, 0].astype(int), np_array[:, 1].astype(int), np_array[:, 2].astype(int))])
        # Replace first column with voxel_id and drop the last column
        new_array = np.column_stack((voxel_id, np_array[:, :-1].astype(int)))
        del np_array
        # Perform batch inserts
        batch_size = 1000
        for i in range(0, len(new_array), batch_size):
            batch = new_array[i:i+batch_size]
            with transaction.atomic():
                # Create model objects within the atomic transaction and insert immediately
                model.objects.bulk_create(
                    [model(voxel_id=row[0], x=row[1], y=row[2], z=row[3]) for row in batch],
                    ignore_conflicts=True
                )
                print(f"{i} of {len(new_array)} records inserted...")
    else:
        print("Error with the shape of the array.")
        return np_array  # If the input array doesn't have 4 columns, return it as is

def npToSql(np_array,lesion_id=None, model=VoxelsUploaded):
    if np_array.shape[1] == 4:
        # create the voxel_id by concatenating 'x', 'y', and 'z' and converting to string
        voxel_id = np.array(['{}_{}_{}'.format(a, b, c) for a, b, c in zip(np_array[:, 0].astype(int), np_array[:, 1].astype(int), np_array[:, 2].astype(int))])

        if lesion_id is None:
            lesion_id = str(int(datetime.now().timestamp()))  # Convert current timestamp to Unix time
            # upload_id = "0"

        # Create a new array with 3 columns: upload_id, voxel_id, and value
        new_array = np.column_stack((np.full(np_array.shape[0], lesion_id, dtype=object), voxel_id, np_array[:, -1]))
        # Inser to sql
        batch_size = 1000
        for i in range(0, len(new_array), batch_size):
            batch = new_array[i:i+batch_size]
            with transaction.atomic():
                # Create model objects within the atomic transaction and insert immediately
                model.objects.bulk_create(
                    [model(value=row[-1],lesion_id=row[0], voxel_id=row[1]) for row in batch],
                    ignore_conflicts=True
                )
                print(f"{i} of {len(new_array)} records inserted...")
    else:
        print("Error with the shape of the array.")
        return np_array  # If the input array doesn't have 4 columns, return it as is

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

def reshapeTo2d(mni_array, affine=np.array([
        [-2., 0., 0., 90.],
        [0., 2., 0., -126.],
        [0., 0., 2., -72.],
        [0., 0., 0., 1.]
    ])):
    non_zero_indices = np.nonzero(mni_array)
    values = np.round(mni_array[non_zero_indices], 3)  # Round the values to 3 decimals
    coords = np.array(non_zero_indices).T
    forward_matrix = affine[:3, :3]
    forward_translation = affine[:3, 3]
    transformed_coords = np.dot(coords, forward_matrix.T) + forward_translation
    return np.column_stack((transformed_coords, values))  # Swap the order of columns

def drop_zero_values(array):
    mask = ~np.logical_or(array[:, 3] == 0, np.isnan(array[:, 3]))  # create a mask that is False where the first column is 0 or NaN
    return array[mask]  # use the mask to select rows

def niftiTo2d(directory,filename):
    file = os.path.join(directory, filename)
    image = nib.load(file)
    affine = image.affine
    # print(affine)
    data = image.get_fdata()
    return drop_zero_values(reshapeTo2d(data, affine))
    npToSql(drop_zero_values(reshapeTo2d(data, affine)))
   

directory = "django_project/static/MRIData/GZippedEverything"
filename = "NeglectLesionTracing_Saj_2018_Case05.nii.gz"
# filename = "REMSleepBehaviorLesionNetwork_Zambelis_Case01.nii.gz"
# filename = "HypersomniaLesionNetwork_Luigetti_2011_Case01.nii.gz"
# directory = "Data/LesionNetworks/AmnesiaLesionNetworks"
# filename = "AmnesiaLesionNetwork_Chen2008_Case01.nii"

lesion_id = fillMetadataTable(LesionMetadata, ["Neglect", "MadeUpSymptom"])
npToSql(niftiTo2d(directory,filename), lesion_id) 

print("executed succesfully")