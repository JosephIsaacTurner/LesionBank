import boto3
from dotenv import load_dotenv
import gzip
import nibabel as nib
import numpy as np
from io import BytesIO
import os
import psycopg2
import pandas as pd
from datetime import datetime
from scipy import stats
from scipy.ndimage import zoom
import seaborn as sns
import matplotlib.pyplot as plt
import statsmodels.api as sm
import statsmodels.stats.multitest as mt
from statsmodels.formula.api import ols
from statsmodels.stats.multicomp import pairwise_tukeyhsd

load_dotenv() 

class CustomStorage:

    session = boto3.session.Session()

    def save(self, name, content, bucket_name=None, max_length=None):
        # Retrieve bucket name from environment variables if not provided
        if bucket_name is None:
            bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')

        headers = {'ContentType': ''}
        s3 = self._get_s3_client()
        try:
            s3.upload_fileobj(content, bucket_name, name, ExtraArgs=headers)
        except Exception as e:
            print(f"Failed to upload: {e}")
            return None
        return name
    
    def get_file_from_cloud(self, cloud_filepath):
        extension = cloud_filepath.split('.')[-1]
        
        client = self._get_s3_client()
        try:
            file_object = client.get_object(Bucket=os.getenv('AWS_STORAGE_BUCKET_NAME'), Key=cloud_filepath)
            file_data = file_object['Body'].read()
        except Exception as e:
            print(f"Failed to fetch: {e}")
            return None

        if extension == 'gz':
            fh = nib.FileHolder(fileobj=gzip.GzipFile(fileobj=BytesIO(file_data)))
            return nib.Nifti1Image.from_file_map({'header': fh, 'image': fh})

        elif extension == 'npy':
            return np.load(BytesIO(file_data), allow_pickle=True)

        else:
            raise ValueError(f"Unsupported file type: {extension}")

    def _get_s3_client(self):
        return self.session.client('s3',
                                   region_name='nyc3',
                                   endpoint_url=os.getenv('AWS_S3_ENDPOINT_URL'),
                                   aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                                   aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))


    def compress_nii_image(self, nii_img):
        """Compresses an NIfTI image.

        Args:
        - nii_img: An instance that has a to_bytes method which converts the image to byte data.

        Returns:
        - A BytesIO object containing the compressed image data.
        """
        img_data = nii_img.to_bytes()
        img_data_gz = BytesIO()
        with gzip.GzipFile(fileobj=img_data_gz, mode='w') as f_out:
            f_out.write(img_data)
        img_data_gz.seek(0)
        return img_data_gz

    def list_s3_files(self, s3_path):
        """
        List NIfTI files in an S3 bucket directory.

        Parameters
        ----------
        s3_path : str
            Path in the format s3://bucket-name/prefix
        
        Returns
        -------
        roi_paths : list of str
            List of S3 paths to NIfTI image ROIs.
        """

        # Parse the s3_path to extract bucket name and prefix
        if not s3_path.startswith('s3://'):
            raise ValueError("Provided path is not a valid S3 path.")
        
        s3_components = s3_path[5:].split('/', 1)
        bucket_name = s3_components[0]
        prefix = s3_components[1] if len(s3_components) > 1 else ""

        # Use the S3 client from the class's method
        s3 = self._get_s3_client()
        
        roi_paths = []
        
        paginator = s3.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            for obj in page.get('Contents', []):
                if (obj['Key'].endswith('.nii') or obj['Key'].endswith('.nii.gz')):
                    roi_paths.append('s3://' + bucket_name + '/' + obj['Key'])
        
        return roi_paths

class SQLUtils:
    def __init__(self):
        pass
        self.connection = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT")
        )

    def execute_query(self, statement, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(statement, params)
            rows = cursor.fetchall()
            column_names = [col[0] for col in cursor.description]  # get column names
        return column_names, rows
    
    def run_raw_sql(self, query, single_value=False):
        with self.connection.cursor() as cursor:
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

class NiftiHandler():

    def __init__(self, data=None):
        self.one_mm_affine = np.array([
                [-1.,0.,0.,90.],
                [0.,1.,0.,-126.],
                [0.,0.,1.,-72.],
                [0.,0.,0.,1.]
            ])
        self.two_mm_affine = np.array([
                [-2., 0., 0., 90.],
                [0., 2., 0., -126.],
                [0., 0., 2., -72.],
                [0., 0., 0., 1.]
            ])
        self.data = None # 3d array in voxel space
        self.affine = None # 4x4 affine matrix
        self.shape = None # 3-tuple of integers, indicating resolution
        self.resolution = None # '1mm' or '2mm'
        self.twod_data = None # Should be a 2D array with 4 columns: x, y, z, value (world space)
        self.df_xyz = None # A dataframe with columns 'x', 'y', 'z', and 'value' (world space)
        self.df_voxel_id = None # A dataframe with columns 'Voxel ID' and 'value' (world space)
        self.id = None # String id of the object in the database, or the object we will insert into the database.
        self.type = None # Either 'mask' or 'continuous'
        self.mask_applied = False
        self.is_quantile_normalized = False
        self.storage = CustomStorage()
        super().__init__()
        if data is not None:
            if type(data) == str:
                try:
                    self.populate_data_from_s3(data)
                except Exception as e:
                    print(f"An error occurred: {e}")
                    try:
                        self.populate_data_from_db(id=data, model=GeneratedImages)
                    except Exception as e:
                        print(f"An error occurred: {e}")
                        try:
                            self.populate_data_from_local(data)
                        except Exception as e:
                            raise ValueError(f"Could not populate data from s3, db, or local storage using {data}.")
            elif type(data) == nib.nifti1.Nifti1Image:
                self.populate_data_from_nifti(data)
            elif type(data) == np.ndarray:
                self.populate_data_from_2d_array(data)
            else:
                raise ValueError("Data must be a string, NIfTI object, or numpy array.")

    def populate_data_from_nifti(self, nifti_obj, type=None):
        self.data = nifti_obj.get_fdata() # 3d array in voxel space
        self.affine = nifti_obj.affine # 4x4 affine matrix
        self.shape = nifti_obj.shape # 3-tuple of integers, indicating resolution
        if self.shape == (182,218,182):
            self.resolution = '1mm'
        elif self.shape == (91,109,91):
            self.resolution = '2mm'
        else:
            self.resolution == "unknown" # This should never happen

        if self.type is None:
            if np.all(np.logical_or(np.isclose(self.data, 0), np.isclose(self.data, 1))):
                self.type = 'mask'
            else:
                self.type = 'continuous'

    def populate_data_from_s3(self, s3_path):
        nifti_obj = self.get_nifti_from_s3(s3_path)
        self.populate_data_from_nifti(nifti_obj)
    
    def populate_data_from_local(self, local_path):
        nifti_obj = nib.load(local_path)
        self.populate_data_from_nifti(nifti_obj)

    def populate_data_from_db(self, id_name='lesion_id', id=None, model=None):
        if id is None or model is None:
            raise ValueError("ID and model must be provided.")

        query = f"""
        SELECT
            voxel_id, value
        FROM {model._meta.db_table}
        WHERE {id_name} = %s
        """
        params = (id,)
        result = self.run_raw_sql(query, params)

        # Make a df_voxel_id dataframe (A dataframe with columns 'x', 'y', 'z', and 'value' (world space))
        self.df_voxel_id = pd.DataFrame(result, columns=['voxel_id', 'value'])

        # Make a df_xyz dataframe (A dataframe with columns 'Voxel ID' and 'value' (world space))
        voxel_id = self.df_voxel_id['voxel_id'].str.split('_', expand=True).astype(int)
        self.df_xyz = pd.concat([voxel_id, self.df_voxel_id['value']], axis=1)
        self.df_xyz.columns = ['x', 'y', 'z', 'value']

        # Make a 2D array with 4 columns: x, y, z, value (world space)
        self.twod_data = self.df_xyz.to_numpy()

        # Convert result to a 2D array with columns: x, y, z, value
        data = np.array([[*map(int, voxel_id.split('_')), value] for voxel_id, value in result])

        # Create a 3D array in voxel space and make it a NIfTI object
        nii_img = nib.Nifti1Image(self.reshape_to_3d(data), self.two_mm_affine)

        # Further processing with the NIfTI object
        self.populate_data_from_nifti(nii_img)
        
        return nii_img
    
    def populate_data_from_2d_array(self, data, resolution='2mm'):
        """Populates the NiftiHandler object from a 2D array with 4 columns: x, y, z, value"""
        nd_array = self.reshape_to_3d(data, resolution)
        nifti_obj = self.to_nifti_obj(nd_array, resolution)
        self.populate_data_from_nifti(nifti_obj)

    def reshape_to_3d(self, nd_array, resolution='2mm'):
        """Reshapes a 2d array with 4 columns: x, y, z, value to a 3d array in voxel space"""
        worldspace_coords = nd_array[:, :3].astype(float)  # Extract the first three values as coordinates

        if resolution == '2mm':
            affine_matrix = self.two_mm_affine
            three_d_array_shape = (91, 109, 91)
        elif resolution == '1mm':
            affine_matrix = self.one_mm_affine
            three_d_array_shape = (182, 218, 182)
        else:
            raise ValueError("Unsupported resolution. Expected '1mm' or '2mm'.")

        three_d_array = np.zeros(three_d_array_shape, dtype=float)
        worldspace_coords = np.hstack((worldspace_coords, np.ones((len(nd_array), 1))))
        inverseMatrix = np.linalg.inv(affine_matrix)
        voxel_coords = np.dot(worldspace_coords, inverseMatrix.T)
        voxel_coords = voxel_coords[:, :3]  # Extract only the transformed coordinates
        voxel_coords = np.clip(voxel_coords, a_min=0, a_max=np.array(three_d_array_shape) - 1).astype(int)  # Clip to prevent out-of-bounds indexing
        three_d_array[voxel_coords[:, 0], voxel_coords[:, 1], voxel_coords[:, 2]] = nd_array[:, 3]

        return three_d_array

    def get_nifti_from_s3(self, s3_path):
        """Gets a NIfTI object from a file path in s3 storage, relative to the bucket root"""
        return self.storage.get_file_from_cloud(s3_path)
    
    def save_to_s3(self, filename, resolution='2mm', file_content=None):
        """Saves a NIfTI object to s3 storage, relative to the bucket root"""
        if file_content is None:
            file_content = self.data
            file_content = self.to_nifti_obj(file_content, resolution)
        file_content = self.storage.compress_nii_image(file_content)
        self.storage.save(filename, file_content)
        return filename

    def reshape_to_2d(self, ndarray=None):
        """Reshapes a 3d array to a 2d array with 4 columns: x, y, z, value"""
        if ndarray is None:
            ndarray = self.data # 3d array in voxel space
        non_zero_indices = np.nonzero(ndarray)
        values = np.round(ndarray[non_zero_indices], 3)  # Round the values to 3 decimals
        coords = np.array(non_zero_indices).T
        forward_matrix = self.two_mm_affine[:3, :3]
        forward_translation = self.two_mm_affine[:3, 3]
        transformed_coords = np.dot(coords, forward_matrix.T) + forward_translation
        self.twod_data = np.column_stack((transformed_coords, values)) # Swap the order of the columns
        return self.twod_data
    
    def drop_zero_values(self, ndarray=None):
        """Drops zero values from a 2d array with 4 columns: x, y, z, value"""
        if ndarray is None:
            ndarray = self.twod_data
        mask = ~np.logical_or(ndarray[:, 3] == 0, np.isnan(ndarray[:, 3]))  # create a mask that is False where the first column is 0 or NaN
        self.twod_data = ndarray[mask]
        return self.twod_data
    
    def nd_array_to_pandas(self, nd_array=None):
        """Converts a 2D array with 4 columns: x, y, z, value into two pandas DataFrames.
        The first DataFrame will have columns 'x', 'y', 'z', and 'value'.
        The second DataFrame will have a two columns: 'Voxel ID' and 'value'."""
        if nd_array is None:
            if self.twod_data is None:
                self.reshape_to_2d()
                self.drop_zero_values()
            nd_array = self.twod_data

        if nd_array.shape[1] != 4:
            raise ValueError("Array must have exactly 4 columns")

        # Include 'value' column in df_xyz
        df_xyz = pd.DataFrame(nd_array, columns=['x', 'y', 'z', 'value'])

        # Create voxel_id and include 'value' column in df_voxel_id
        voxel_id = ['{}_{}_{}'.format(*map(int, row[:3])) for row in nd_array]
        df_voxel_id = pd.DataFrame({'voxel_id': voxel_id, 'value': nd_array[:, 3]})

        self.df_xyz = df_xyz
        self.df_voxel_id = df_voxel_id
        return df_xyz, df_voxel_id
    
    # def df_voxel_id_to_sql(self, id_name="upload_id", id_value=None, model=GeneratedImages, df=None):
    #     # Here's my own implementation, do you think it will work?
    #     if df is None:
    #         if self.df_voxel_id is None:
    #             self.resample()
    #             self.reshape_to_2d()
    #             self.drop_zero_values()
    #             self.nd_array_to_pandas()
    #         df = self.df_voxel_id

    #     if id_value is None:
    #         if self.id is None:
    #             id_value = str(int(datetime.now().timestamp()))
    #             self.id = id_value
    #         else:
    #             id_value = self.id

    #     df[id_name] = id_value

    #     data_to_insert = df.to_dict('records')

    #     # Insert to SQL
    #     batch_size = 1000
    #     for i in range(0, len(data_to_insert), batch_size):
    #         batch = data_to_insert[i:i+batch_size]
    #         with transaction.atomic():
    #             # Create model objects within the atomic transaction and insert immediately
    #             model.objects.bulk_create(
    #                 [model(**{id_name: row[id_name], 'voxel_id': row['voxel_id'], 'value': row['value']}) for row in batch],
    #                 ignore_conflicts=True
    #             )

    #             print(f"{i} of {len(data_to_insert)} records inserted...")
    #         print(f"all {len(data_to_insert)} records successfully inserted.")

    def resample(self, target_resolution="2mm", nd_array=None):
        """Resamples a 3D mask array to the specified resolution.
        The nd_array is a 3D array in voxel space. This function supports resampling
        from 1mm to 2mm and from 2mm to 1mm resolutions. It ensures that all non-zero
        values in the resampled array are set to 1.

        Args:
            target_resolution (str): The target resolution, either '1mm' or '2mm'.
            nd_array (numpy.ndarray, optional): The array to resample. If None, uses the instance's data.

        Returns:
            numpy.ndarray: The resampled array.
        """
        if target_resolution not in ['1mm', '2mm']:
            raise ValueError("Target resolution must be '1mm' or '2mm'.")

        if nd_array is None:
            nd_array = self.data

        if self.resolution == target_resolution:
            print(f"This array is already in {target_resolution} resolution.")
            return nd_array

        valid_transitions = [('1mm', '2mm'), ('2mm', '1mm')]
        if (self.resolution, target_resolution) not in valid_transitions:
            raise ValueError(f"Cannot resample from {self.resolution} to {target_resolution}.")

        # Determine resampling factor based on the desired transition
        if target_resolution == '2mm':
            resample_factor = np.diag(self.one_mm_affine)[:3] / np.diag(self.two_mm_affine)[:3]
        else:  # Resampling from 2mm to 1mm
            resample_factor = np.diag(self.two_mm_affine)[:3] / np.diag(self.one_mm_affine)[:3]

        # Ensure resample_factor is an array of floats
        resample_factor = np.array(resample_factor, dtype=float)

        # Resample the array
        resampled_nd_array = zoom(nd_array, resample_factor, order=1)  # order=1 for linear interpolation

        # Post-process to ensure binary values (0 or 1)
        resampled_nd_array[resampled_nd_array != 0] = 1

        # Update instance attributes
        self.data = resampled_nd_array
        self.resolution = target_resolution
        self.shape = resampled_nd_array.shape

        return resampled_nd_array
    
    def apply_anatomical_mask(self, mask_filepath="MNI152_T1_2mm_brain_mask.nii.gz", nd_array=None):
        """Applies an anatomical mask to a 3D array in voxel space"""
        if nd_array is None:
            nd_array = self.data
        
        mask = nib.load(mask_filepath).get_fdata()
        if nd_array.shape != mask.shape:
            print("Array and mask must have the same shape.")
            self.resample()
        # Apply the mask such that all values outside the mask are set to NaN
        nd_array[mask == 0] = np.nan
        # Apply the mask such that all values inside the mask are left as they are, OR set to 0 if they are NaN or inf
        nd_array[mask == 1] = np.nan_to_num(nd_array[mask == 1], nan=0, posinf=0, neginf=0)
        self.mask_applied = True
        self.data = nd_array
        return self

    def normalize_to_quantile(self, nd_array=None):
        """Converts an n-dimensional array to quantile scores, excluding infs and nans."""
        if nd_array is None:
            if self.mask_applied == False:
                self.apply_anatomical_mask()
            nd_array = self.data
        
        original_shape = nd_array.shape
        
        # Mask to identify finite (non-inf, non-nan) elements
        finite_mask = np.isfinite(nd_array) # Should be exactly the same as the anatomical mask applied

        # Flatten the array and apply the mask to exclude infs and nans
        data_flat = nd_array[finite_mask].flatten()

        # Rank the data and calculate quantile scores
        data_ranked = stats.rankdata(data_flat)
        data_quantile_scores = data_ranked / len(data_ranked)

        # Create an output array filled with NaNs (or another fill value) to hold the quantile scores
        # This ensures the shape is maintained and non-finite values are excluded
        output_array = np.full_like(nd_array, np.nan, dtype=np.float64)

        # Place quantile scores back into the original shape, excluding infs and nans
        output_array[finite_mask] = data_quantile_scores.reshape(nd_array[finite_mask].shape)

        final_shape = output_array.shape

        if final_shape != original_shape:
            raise ValueError(f"Shape mismatch. Expected {original_shape}, got {final_shape}.")

        # Update the class attribute if needed
        self.is_quantile_normalized = True
        self.data = output_array

        return self

    def to_nifti_obj(self, data=None, resolution='2mm'):
        """Converts a 3D array in voxel space to a NIfTI object"""
        if data is None:
            data = self.data
        if resolution == '2mm':
            return nib.Nifti1Image(data, self.two_mm_affine)
        elif resolution == '1mm':
            return nib.Nifti1Image(data, self.one_mm_affine)

    def nifti_file_to_sql_wrapper(self, s3_path):
        """Wrapper function to convert a NIfTI file to SQL"""
        self.populate_data_from_s3(s3_path)
        self.reshape_to_2d()
        self.drop_zero_values()
        self.nd_array_to_pandas()
        self.df_voxel_id_to_sql()
    
    def sql_to_nifti_file_wrapper(self, id_name='lesion_id', id=None, model=None, filename=None):
        """Wrapper function to convert a SQL object to a NIfTI file"""
        if model is None or filename is None or id is None:
            raise ValueError("Model, filename, and id must be provided.")
        self.populate_data_from_db(id_name, id, model)
        self.save_to_s3(filename)
        return filename
    
class ImageComparison:
    """A class for comparing two NIfTI images. Can compute Pearson correlation and Dice coefficient."""
    def __init__(self):
        pass

    def correlate_images(self, image1, image2):
        """Computes the Pearson correlation between two NIfTI images."""
        # Check if both images are instances of NiftiHandler
        if not isinstance(image1, NiftiHandler) or not isinstance(image2, NiftiHandler):
            raise TypeError("Both images must be instances of NiftiHandler.")
        # Check if resolutions match, if not, resample
        if image1.resolution != image2.resolution:
            image1.resample()
            image2.resample()
        # Ensure shapes are the same
        if image1.data.shape != image2.data.shape:
            raise ValueError("The images must have the same shape.")
        # Check if types match (mask or continuous)
        if image1.type != image2.type:
            raise ValueError("Both images must be of the same type (mask or continuous).")
        # Ensure both images are quantile normalized
        if not image1.is_quantile_normalized:
            image1.normalize_to_quantile()
        if not image2.is_quantile_normalized:
            image2.normalize_to_quantile()
        # Flatten the 3D arrays to 1D to compute correlation
        flattened_data1 = image1.data.flatten()
        flattened_data2 = image2.data.flatten()

        # Ensure no infs or NaNs
        flattened_data1 = flattened_data1[np.isfinite(flattened_data1)]
        flattened_data2 = flattened_data2[np.isfinite(flattened_data2)]

        # Check if after removing infs and NaNs, the arrays are non-empty and of the same length
        if flattened_data1.size == 0 or flattened_data2.size == 0:
            raise ValueError("One or both of the images result in empty arrays after removing infs and NaNs.")
        if flattened_data1.size != flattened_data2.size:
            raise ValueError("The images must have the same number of finite values.")

        # Compute Pearson correlation
        correlation, _ = stats.pearsonr(flattened_data1, flattened_data2)
        
        return correlation

    def dice_coefficient(self, image1, image2):
        """
        Computes the Dice coefficient between two NIfTI images.

        Parameters:
        image1 (NiftiHandler): The first NIfTI image.
        image2 (NiftiHandler): The second NIfTI image.

        Returns:
        float: The Dice coefficient between the two images.
        """
        try:
            # Check if both images are instances of NiftiHandler
            if not isinstance(image1, NiftiHandler) or not isinstance(image2, NiftiHandler):
                raise TypeError("Both images must be instances of NiftiHandler.")
            # Check if resolutions match, if not, resample
            if image1.resolution != image2.resolution:
                image1.resample()
                image2.resample()
            # Ensure shapes are the same
            if image1.data.shape != image2.data.shape:
                raise ValueError("The images must have the same shape.")
            # Check if types match (mask or continuous)
            if image1.type != 'mask' or image1.type != image2.type:
                raise ValueError("Both images must be of the type mask")
            
            intersection = np.logical_and(image1.data, image2.data)
            dice_coefficient = 2 * np.sum(intersection) / (np.sum(image1.data) + np.sum(image2.data))
            return dice_coefficient
        
        except Exception as e:
            print(f"An error occurred: {e}")

    def correlate_with_symptoms(self, image, data_to_compare):
        if type(data_to_compare) == list:
            df = pd.DataFrame(data_to_compare)
        elif type(data_to_compare) == pd.DataFrame:
            df = data_to_compare
        else:
            raise ValueError("Data must be a list of dictionaries or a pandas DataFrame.")
        
        original_image = NiftiHandler(image)
        original_image.normalize_to_quantile()

        # Initialize an empty DataFrame to store correlations, with NaNs
        df['images'] = df['path'].apply(lambda x: NiftiHandler(x))

        df['correlation'] = df['images'].apply(lambda x: self.correlate_images(original_image, x))
        df['z_value'] = df['correlation'].apply(lambda x: np.arctanh(x))
        
        # Perform ANOVA
        anova_results = ols('z_value ~ C(symptom)', data=df).fit()
        anova_table = sm.stats.anova_lm(anova_results, typ=2)

        # Check if the overall model is significant
        if anova_table['PR(>F)'].iloc[0] < 0.05:
            # If significant, perform Tukey's HSD test
            tukey_results = pairwise_tukeyhsd(df['z_value'], df['symptom'])

        else:
            print("No significant differences found among symptom correlations.")
            summary_df = df.groupby('symptom')['correlation'].mean()
            summary_df = summary_df.sort_values(ascending=False)
            return summary_df

        # Calculate mean correlation for each symptom
        mean_corr = df.groupby('symptom')['correlation'].mean()

        # Convert Tukey's test results to a DataFrame
        tukey_df = pd.DataFrame(data=tukey_results._results_table.data[1:], columns=tukey_results._results_table.data[0])

        rows = []

        # Process each symptom
        for symptom in df['symptom'].unique():
            # Filter Tukey's results for the current symptom
            symptom_pairs = tukey_df[(tukey_df['group1'] == symptom) | (tukey_df['group2'] == symptom)]

            # Calculate mean p-value across all comparisons for this symptom
            mean_p_value = symptom_pairs['p-adj'].mean()

            # Identify symptoms with significant differences
            significant_symptoms = symptom_pairs[symptom_pairs['reject'] == True]
            significant_symptoms_list = significant_symptoms['group1'].tolist() + significant_symptoms['group2'].tolist()
            significant_symptoms_list = list(set(significant_symptoms_list) - {symptom})

            # Calculate proportion of significant comparisons
            prop_significant = len(significant_symptoms) / len(symptom_pairs) * 100

            symptom_data = {
                "symptom": symptom,
                "mean_correlation(r)": mean_corr[symptom],
                "mean_p_value_of_symptom_comparisons": mean_p_value,
                "symptoms_with_significant_differences": significant_symptoms_list,
                "percentage_of_comparisons_that_are_significant": prop_significant
            }

            # Add the dictionary to the list
            rows.append(symptom_data)

        
        # Create the summary DataFrame from the list of rows
        summary_df = pd.DataFrame(rows)

        # Sort the DataFrame by mean correlation
        summary_df = summary_df.sort_values(by="mean_correlation(r)", ascending=False)

        # Display the summary DataFrame
        # print(summary_df)
     
        return summary_df

class GroupAnalysis:

    def __init__(self, data):
        if type(data) != list:
            raise TypeError("Data must be a list of dictionaries.")
        self.df = pd.DataFrame(data)
        # For testing, let's randomly select five rows from the dataframe
        # self.df = self.df.sample(20)
        # # Reset index
        # self.df.reset_index(drop=True, inplace=True)
    def get_nifti_from_s3(self, s3_path):
        """Gets a NIfTI object from a file path in s3 storage, relative to the bucket root"""
        return self.storage.get_file_from_cloud(s3_path)
    
    def save_to_s3(self, filename, resolution='2mm', file_content=None):
        """Saves a NIfTI object to s3 storage, relative to the bucket root"""
        if file_content is None:
            file_content = self.data
            file_content = self.to_nifti_obj(file_content, resolution)
        file_content = self.storage.compress_nii_image(file_content)
        self.storage.save(filename, file_content)
        return filename

    def sensitivity_analysis(self):
        pass

    def specificity_analysis(self):
        pass

    def cross_correlation_analysis(self):
        df = self.df.copy()
        df['image'] = df['path'].apply(lambda x: NiftiHandler(x))

        # Initialize an empty DataFrame to store correlations, with NaNs
        paths = df['path']
        correlation_df = pd.DataFrame(index=paths, columns=paths)

        # Fill the diagonal with 1s (self-correlation)
        np.fill_diagonal(correlation_df.values, 1.0)

        # Get upper triangle indices
        upper_tri_indices = np.triu_indices(len(df), k=1)

        for i, j in zip(*upper_tri_indices):
            image_i, image_j = df.iloc[i]['images'], df.iloc[j]['images']
            correlation = ImageComparison().correlate_images(image_i, image_j)

            # Set correlation in both upper and lower triangles
            path_i, path_j = paths[i], paths[j]
            correlation_df.at[path_i, path_j] = correlation
            correlation_df.at[path_j, path_i] = correlation  # Symmetric

        symptom_correlation_df = correlation_df.copy()
        df['symptom1'] = df['symptom']
        df['symptom2'] = df['symptom']
        symptom_correlation_df.index = df['symptom1']
        symptom_correlation_df.columns = df['symptom2']
        symptom_correlation_df = symptom_correlation_df.stack().reset_index()
        symptom_correlation_df['correlation'] = symptom_correlation_df[0]
        symptom_correlation_df.drop(columns=[0], inplace=True)
        symptom_correlation_df = symptom_correlation_df[symptom_correlation_df['correlation'] != 1]
        symptom_correlation_grouped_by_symptom = symptom_correlation_df.groupby(['symptom1', 'symptom2']).mean().reset_index()
        return symptom_correlation_df, symptom_correlation_grouped_by_symptom
    

query = """
WITH symptom_count_table AS (
    SELECT * FROM (
        SELECT symptom, COUNT(symptom) 
        FROM (
            SELECT symptom 
            FROM symptoms
            LEFT JOIN metadata_symptoms 
            ON symptoms.id = metadata_symptoms.symptoms_id
            LEFT JOIN metadata
            ON metadata.lesion_id = metadata_symptoms.lesionmetadata_id
        ) AS a
        GROUP BY symptom
    ) AS b 
    WHERE count > 10
),
randomized AS (
    SELECT 
        symptom, 
        network_file_name AS path,
        ROW_NUMBER() OVER (PARTITION BY symptom ORDER BY RANDOM()) as rn
    FROM metadata
    LEFT JOIN metadata_symptoms 
    ON metadata_symptoms.lesionmetadata_id = metadata.lesion_id
    LEFT JOIN symptoms
    ON symptoms.id = metadata_symptoms.symptoms_id
    WHERE network_file_name IS NOT NULL
    AND network_file_name NOT IN ('', ' ')
    AND symptom IN (SELECT symptom FROM symptom_count_table)
)
SELECT symptom, path 
FROM randomized
"""

data_dict = SQLUtils().run_raw_sql(query)
original_image_map = "network_maps_output/1706047815/input_mask_Precom_T.nii.gz"
comparer = ImageComparison()
df_corr = comparer.correlate_with_symptoms(original_image_map, data_dict)
print(df_corr)
# Turn datframe to csv
df_corr.to_csv('correlation.csv', index=False)