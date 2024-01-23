from django.shortcuts import render, redirect
from lesion_bank.utils.nifti_utils import NiftiHandler

def test_view(request):

    path = "sensitivity_maps/Alice_in_Wonderland_Syndrome_sensitivity_neg.nii.gz"
    nifti_handler = NiftiHandler()
    nifti_handler.populate_data_from_s3(path)
    df_xyz, df_voxel_id = nifti_handler.nd_array_to_pandas()
    # Now let's trim the dataframes to only the first 10 rows
    df_xyz = df_xyz.iloc[:10]
    df_voxel_id = df_voxel_id.iloc[:10]
    error_messages = []
    info_messages = []
    raw_html = []
    raw_html.append(f"df_xyz_html: {df_xyz.to_html(index=False)}")
    raw_html.append(f"df_voxel_id_html: {df_voxel_id.to_html(index=False)}")
    return render(request, 'lesion_bank/debugging.html', {
                        'error_message': error_messages,
                        'info_messages': info_messages,
                        'raw_html': raw_html,
                    })