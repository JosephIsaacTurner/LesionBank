from lesion_bank.models import GeneratedImages, PracticeImageVoxels, TrueImageVoxels, TraceVoxels, NetworkVoxels, AtlasVoxels, PredictionVoxels, SensitivityVoxels
from django.conf import settings
from django.db import transaction, connection
import pandas as pd
import nibabel as nib
import numpy as np
from datetime import datetime
from io import BytesIO
from scipy import stats
from scipy.ndimage import zoom
from .sql_utils import SQLUtils
from django_project.custom_storage import CustomStorage

class NiftiHandler(SQLUtils):

    def __init__(self):
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
        self.is_quantile_normalized = False
        self.storage = CustomStorage()
        super().__init__()

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
    
    def populate_from_2d_array(self, data, resolution='2mm'):
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
    
    def df_voxel_id_to_sql(self, id_name="upload_id", id_value=None, model=GeneratedImages, df=None):
        # Here's my own implementation, do you think it will work?
        if df is None:
            if self.df_voxel_id is None:
                self.resample()
                self.reshape_to_2d()
                self.drop_zero_values()
                self.nd_array_to_pandas()
            df = self.df_voxel_id

        if id_value is None:
            if self.id is None:
                id_value = str(int(datetime.now().timestamp()))
                self.id = id_value
            else:
                id_value = self.id

        df[id_name] = id_value

        data_to_insert = df.to_dict('records')

        # Insert to SQL
        batch_size = 1000
        for i in range(0, len(data_to_insert), batch_size):
            batch = data_to_insert[i:i+batch_size]
            with transaction.atomic():
                # Create model objects within the atomic transaction and insert immediately
                model.objects.bulk_create(
                    [model(**{id_name: row[id_name], 'voxel_id': row['voxel_id'], 'value': row['value']}) for row in batch],
                    ignore_conflicts=True
                )

                print(f"{i} of {len(data_to_insert)} records inserted...")
            print(f"all {len(data_to_insert)} records successfully inserted.")

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
    
    def normalize_to_quantile(self, nd_array=None):
        """Converts an n-dimensional array to quantile scores."""
        if nd_array is None:
            nd_array = self.data
        data_flat = nd_array.flatten()
        data_ranked = stats.rankdata(data_flat)
        data_quantile_scores = data_ranked / len(data_ranked)
        data_quantile_scores = data_quantile_scores.reshape(nd_array.shape)
        self.is_quantile_normalized = True
        self.data = data_quantile_scores
        return data_quantile_scores

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
        flattened_data1 = image1.data.ravel()
        flattened_data2 = image2.data.ravel()
        
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

class GroupAnalysis:

    def __init__(self, filepath_list):
        self.filepath_list = filepath_list

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
        pass