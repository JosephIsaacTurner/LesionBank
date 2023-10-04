import nibabel as nib
import numpy as np
import os
from scipy import stats
import time

# Wrapper function to make t-array and p-array from a tracing file and GSP dataset directory."""
def create_arrays(tracing_file_path, directory_gsp_dataset):
    tracing_file = os.path.abspath(tracing_file_path)
    gsp_dataset_list = os.listdir(directory_gsp_dataset)
    
    lesion_image = nib.load(tracing_file).get_fdata()
    lesion_indices = np.nonzero(lesion_image)
    
    merged_z_array = np.zeros(lesion_image.shape[:3] + (len(gsp_dataset_list),))
    del lesion_image

    # Iterate over all functional data files in GSP1000
    for i, filename in enumerate(gsp_dataset_list):
        file_path = os.path.join(directory_gsp_dataset, filename)
        if os.path.isfile(file_path):
            functional_data = nib.load(file_path).get_fdata()
            # Create individual z_array from functional image and add to merged z_array
            merged_z_array[..., i] = get_z_array(functional_data, lesion_indices)
            del functional_data

    # Perform one-sample t-test on merged z-array to get t-array and p-array
    return stats.ttest_1samp(merged_z_array, 0, axis=-1)


# Calculate z-array for correlations between functional image voxels and the lesion timeseries.
def get_z_array(functional_data, lesion_indices):
    lesion_timeseries = np.mean(functional_data[lesion_indices], axis=0) # Timeseries of BOLD signal averaged across lesioned voxels
    lesion_timeseries_mean = lesion_timeseries.mean(axis=-1, keepdims=True)
    functional_mean = functional_data.mean(axis=-1, keepdims=True)
    
    covariance = ((functional_data - functional_mean) * (lesion_timeseries - lesion_timeseries_mean)).sum(axis=-1) / (functional_data.shape[-1] - 1)
    std_dev = functional_data.std(axis=-1) * lesion_timeseries.std(axis=-1)
    
    return np.arctanh(covariance / (std_dev + 1e-8))  # Apply arctanh to get z_values


# Create a .nii image from an array and save it.
def create_map(array, output_filename="output.nii.gz"):
    # Affine matrix for MNI space
    affine = np.array([
        [-2., 0., 0., 90.],
        [0., 2., 0., -126.],
        [0., 0., 2., -72.],
        [0., 0., 0., 1.]
    ])
    ni_img = nib.Nifti2Image(array, affine)
    nib.save(ni_img, os.path.abspath(output_filename))


# Measure start time
start_time = time.time()

# Define paths
tracing_file_path = "FuncConnData/exampleTrace.nii.gz"
directory_gsp_dataset = "FuncConnData/GSP1000Dataset"
t_network_map_output = "t_lesion_network_map.nii.gz"
p_network_map_output = "p_lesion_network_map.nii.gz"

# Generate T-map and P-map arrays
t_array, p_array = create_arrays(tracing_file_path, directory_gsp_dataset)

# Save the T-map and P-map as .nii files
create_map(t_array, t_network_map_output)
create_map(p_array, p_network_map_output)

# Calculate and print execution time
print(f"The script executed in {time.time() - start_time} seconds")
