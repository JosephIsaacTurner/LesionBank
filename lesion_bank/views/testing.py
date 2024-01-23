from django.shortcuts import render, redirect
from lesion_bank.utils.nifti_utils import NiftiHandler

def test_view(request):

    path = "sensitivity_maps/Alice_in_Wonderland_Syndrome_sensitivity_neg.nii.gz"
    nifti_handler = NiftiHandler()
    nifti_handler.populate_data_from_s3(path)
    df_xyz, df_voxel_id = nifti_handler.nd_array_to_pandas()
    error_messages = []
    info_messages = []
    info_messages.append(f"df_xyz_html: {df_xyz.to_html()}")
    info_messages.append(f"df_voxel_id_html: {df_voxel_id.to_html()}")
    return render(request, 'lesion_bank/debugging.html', {
                        'error_message': error_message,
                        'info_messages': info_messages
                    })