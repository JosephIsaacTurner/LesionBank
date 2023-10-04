import nibabel as nib
import numpy as np
import psycopg2
import csv
import os
import boto3
from io import BytesIO
import gzip
from scipy import stats
import math 
from decouple import config

# Define connection parameters
params = {
    "host": config('DB_HOST'),
    "database": config('DB_NAME'),
    "user": config('DB_USER'),
    "password": config('DB_PASSWORD')
}
print("hello world.")
conn = psycopg2.connect(**params)
access_key = config('AWS_ACCESS_KEY_ID')
secret_key = config('AWS_SECRET_ACCESS_KEY')
SESSION = boto3.session.Session()
CLIENT = SESSION.client('s3',
                        region_name='nyc3',
                        endpoint_url='https://nyc3.digitaloceanspaces.com',
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key)

def getNiftiFromCloud(cloud_filepath, client=CLIENT):
    image_object = client.get_object(Bucket='lesionbucket', Key=cloud_filepath)
    image_data = image_object['Body'].read()
    fh = nib.FileHolder(fileobj=gzip.GzipFile(fileobj=BytesIO(image_data)))
    img = nib.Nifti1Image.from_file_map({'header': fh, 'image': fh})
    return img

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
    save_to_cloud(nii_img, filename)

def query_to_any_map_type(query, filepath):
    data = query_to_numpy(query)
    createMap(data, filepath)
    return filepath

def normalizeNiftiVolume(data):
    data_flat = data.flatten()
    data_ranked = stats.rankdata(data_flat)
    data_quantile_scores = data_ranked / len(data_ranked)
    data_quantile_scores = data_quantile_scores.reshape(data.shape)
    return data_quantile_scores

def calculate_pearson_details(array1, array2):
    if array1.shape != array2.shape:
        raise ValueError("The input arrays must have the same shape")
    count_obs = np.size(array1)
    mean1 = np.mean(array1)
    mean2 = np.mean(array2)
    std_dev1 = np.std(array1)
    std_dev2 = np.std(array2)
    product_moments = (((array1 - mean1) * (array2 - mean2)) / (std_dev1 * std_dev2))/count_obs
    r, p_value = stats.pearsonr(array1.flatten(), array2.flatten())
    return r, p_value, product_moments

def pearson_alternative(array1, array2):
    if array1.shape != array2.shape:
        raise ValueError("The input arrays must have the same shape")
    n = len(array1)
    x_mean = np.mean(array1)
    y_mean = np.mean(array2)
    x_diff = array1 - x_mean 
    y_diff = array2 - y_mean 
    cov = np.sum(x_diff * y_diff) / n
    x_std = math.sqrt(np.sum(x_diff**2) / n)
    y_std = math.sqrt(np.sum(y_diff**2) / n)
    r = cov / ( x_std * y_std )
    num_contribution = x_diff * y_diff / ( n * x_std * y_std )
    
    return num_contribution

def calculate_r_contrib(array1, array2):
    if array1.shape != array2.shape:
        raise ValueError("The input arrays must have the same shape")
    count_obs = np.size(array1)
    x_mean = np.mean(array1)
    y_mean = np.mean(array2)
    x_std_dev = np.std(array1)
    y_std_dev = np.std(array2)
    x_variance = np.var(array1)
    y_variance = np.var(array2)
    covar = np.cov(array1.flatten(), array2.flatten())[0, 1]
    r_contrib = (-covar / (x_std_dev * y_std_dev)) * (
        ((np.sqrt((x_variance + ((np.power(array1 - x_mean, 2) - x_variance) / count_obs))) / x_std_dev) - 1)
        +
        ((np.sqrt((y_variance + ((np.power(array2 - y_mean, 2) - y_variance) / count_obs))) / y_std_dev) - 1)
    ) + ((array1 - x_mean) * (array2 - y_mean)) / (x_std_dev * y_std_dev * count_obs)
    
    return r_contrib

def r_contrib_final(x_array, y_array):
    if x_array.shape != y_array.shape:
        raise ValueError("The input arrays must have the same shape")
    count_obs = np.size(x_array)
    x_mean = np.mean(x_array)
    y_mean = np.mean(y_array)
    x_std_dev = np.std(x_array)
    y_std_dev = np.std(y_array)
    x_var = x_std_dev ** 2
    y_var = y_std_dev ** 2

    x_diff = x_array - x_mean 
    y_diff = y_array - y_mean 
    cov = np.sum(x_diff * y_diff) / count_obs
    r = cov / ( x_std_dev * y_std_dev )

    def getGrowth( z ):
        n = len(z)
        z_mean = np.mean(z)
        z_diff = z - z_mean
        z_std = math.sqrt(np.sum(z_diff**2) / n)
        z_var = z_std**2

        return (z_var + (z_diff**2 - z_var)/n)**.5 / z_std - 1

    x_growth = getGrowth( x_array )
    y_growth = getGrowth( y_array )
    den_contribution = - r * ( x_growth + y_growth )

    full_contribution = (den_contribution) + pearson_alternative(x_array, y_array)
    return full_contribution


if __name__== '__main__':
    nifti1 = getNiftiFromCloud("uploads/sensitivity_maps/Hypersomnia_sensitivity_parametric.nii.gz")
    nifti2 = getNiftiFromCloud("uploads/sensitivity_maps/Insomnia_sensitivity_parametric.nii.gz")
    data1 = np.asanyarray(nifti1.dataobj)
    data2 = np.asanyarray(nifti2.dataobj)
    data1Normal = normalizeNiftiVolume(data1)
    data2Normal = normalizeNiftiVolume(data2)
    r, p, product_array = calculate_pearson_details(data1Normal, data2Normal)
    affine=np.array([
        [-2., 0., 0., 90.],
        [0., 2., 0., -126.],
        [0., 0., 2., -72.],
        [0., 0., 0., 1.]
    ])
    nii_img = nib.Nifti1Image(product_array, affine)
    save_to_cloud(nii_img, "correlation_map.nii.gz")
    print(r)

