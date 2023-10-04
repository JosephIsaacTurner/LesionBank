from .models import Coordinates
from django.db import transaction
import os
import nibabel as nib
import numpy as np
from datetime import datetime
import boto3
from io import BytesIO
import gzip

def getNiftiFromCloud(cloud_filepath):
    from django.conf import settings
    session = boto3.session.Session()
    client = session.client('s3',
                            region_name='nyc3',
                            endpoint_url =settings.AWS_S3_ENDPOINT_URL,
                            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
    image_object = client.get_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=cloud_filepath)
    image_data = image_object['Body'].read()
    fh = nib.FileHolder(fileobj=gzip.GzipFile(fileobj=BytesIO(image_data)))
    img = nib.Nifti1Image.from_file_map({'header': fh, 'image': fh})
    return img

def numpyToSql(np_array, id_name, id_value=None, model=None):
    if np_array.shape[1] == 4:
        # create the voxel_id by concatenating 'x', 'y', and 'z' and converting to string
        voxel_id = np.array(['{}_{}_{}'.format(a, b, c) for a, b, c in zip(np_array[:, 0].astype(int), np_array[:, 1].astype(int), np_array[:, 2].astype(int))])

        if id_value is None:
            id_value = str(int(datetime.now().timestamp()))  # Convert current timestamp to Unix time

        # Create a new array with 3 columns: id_name, voxel_id, and value
        new_array = np.column_stack((np.full(np_array.shape[0], id_value, dtype=object), voxel_id, np_array[:, -1]))
        
        # Insert to sql
        batch_size = 1000
        for i in range(0, len(new_array), batch_size):
            batch = new_array[i:i+batch_size]
            with transaction.atomic():
                # Create model objects within the atomic transaction and insert immediately
                model.objects.bulk_create(
                    [model(**{id_name: row[0], 'voxel_id': row[1], 'value': row[-1]}) for row in batch],
                    ignore_conflicts=True
                )

                print(f"{i} of {len(new_array)} records inserted...")
            print (f"all {len(new_array)} records successfully inserted.")
    else:
        print("Error with the shape of the array.")
        return np_array  # If

def npToSql_uploads(np_array,upload_id=None, model=None):
    if np_array.shape[1] == 4:
        # create the voxel_id by concatenating 'x', 'y', and 'z' and converting to string
        voxel_id = np.array(['{}_{}_{}'.format(a, b, c) for a, b, c in zip(np_array[:, 0].astype(int), np_array[:, 1].astype(int), np_array[:, 2].astype(int))])

        if upload_id is None:
            upload_id = str(int(datetime.now().timestamp()))  # Convert current timestamp to Unix time
            # upload_id = "0"

        # Create a new array with 3 columns: upload_id, voxel_id, and value
        new_array = np.column_stack((np.full(np_array.shape[0], upload_id, dtype=object), voxel_id, np_array[:, -1]))
        # Inser to sql
        batch_size = 1000
        for i in range(0, len(new_array), batch_size):
            batch = new_array[i:i+batch_size]
            with transaction.atomic():
                # Create model objects within the atomic transaction and insert immediately
                model.objects.bulk_create(
                    [model(value=row[-1],upload_id=row[0], voxel_id=row[1]) for row in batch],
                    ignore_conflicts=True
                )
                print(f"{i} of {len(new_array)} records inserted...")
            print (f"all {len(new_array)} records successfully inserted.")
    else:
        print("Error with the shape of the array.")
        return np_array  # If the input array doesn't have 4 columns, return it as is


def npToSql(np_array,lesion_id=None, model=None):
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
            print (f"all {len(new_array)} records successfully inserted.")
    else:
        print("Error with the shape of the array.")
        return np_array  # If the input array doesn't have 4 columns, return it as is

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

def niftiTo2d(filename):
    file = os.path.abspath(filename)
    image = nib.load(file)
    affine = image.affine
    # print(affine)
    data = image.get_fdata()
    return drop_zero_values(reshapeTo2d(data, affine))   
def niftiObjTo2d(niftiObj):
    image = niftiObj
    affine = image.affine
    # print(affine)
    data = image.get_fdata()
    return drop_zero_values(reshapeTo2d(data, affine))   

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
    
def reshapeTo3d(np_array, affine=np.array([
        [-2., 0., 0., 90.],
        [0., 2., 0., -126.],
        [0., 0., 2., -72.],
        [0., 0., 0., 1.]
    ]),
    shape=(91,109,91)):
    # It expects the values to be the first element, then x, y, z.
    oldCoords = np_array[:, :3].astype(float)  # Extract the first three values as coordinates
    inverseMatrix = np.linalg.inv(affine)
    # Create the final transformed array
    # mni_shape = (91, 109, 91)
    mni_array = np.zeros(shape, dtype=float)
    oldCoords = np.hstack((oldCoords, np.ones((len(np_array), 1))))
    newCoords = np.dot(oldCoords, inverseMatrix.T)
    newCoords = newCoords[:, :3]  # Extract only the transformed coordinates
    # Convert the transformed coordinates to integers and assign values in mni_array
    newCoords = newCoords.astype(int)
    mni_array[newCoords[:, 0], newCoords[:, 1], newCoords[:, 2]] = np_array[:, 3]
    return mni_array