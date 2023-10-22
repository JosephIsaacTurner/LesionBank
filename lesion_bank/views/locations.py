from django.shortcuts import render, get_object_or_404, redirect
from lesion_bank.models import LesionMetadata, Symptoms
from django.http import HttpResponse
import json
from django.db import connection
from django.conf import settings
private_symptoms = settings.PRIVATE_SYMPTOMS


def run_raw_sql(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        # Fetch the column names from the cursor description
        column_names = [col[0] for col in cursor.description]
        return [
            dict(zip(column_names, row))
            for row in cursor.fetchall()
        ]

def locations_landing(request):
    context = {}
    context['title'] = "Locations"
    return render(request, 'lesion_bank/locations_landing.html', context)

def locations_view(request, voxel_id):
    coords = voxel_id.split('_')
    are_any_odd = any(int(float(x)) % 2 for x in coords)
    if are_any_odd:
        coords = [str(int(float(x) + 1) if int(float(x)) % 2 else int(float(x))) for x in coords]
        even_voxel_id = '_'.join(coords)
        return redirect('locations', voxel_id=even_voxel_id)
    context = {}
    context['x'] = coords[0]
    context['y'] = coords[1]
    context['z'] = coords[2]
    sensitivity_query = f"""
    SELECT 
        voxel_id, 
        percent_overlap, 
        symptom, 
        sensitivity_pos_path, 
        sensitivity_neg_path,
        sensitivity_parametric_path,
        CONCAT(ABS(percent_overlap)::TEXT, 
            CASE 
                WHEN percent_overlap < 0 THEN '% (t<-7)'
                ELSE '% (t>+7)'
            END
        ) AS percent_correlated
    FROM 
        sensitivity_voxels 
    LEFT JOIN 
        symptoms 
    ON 
        sensitivity_voxels.symptom_id = symptoms.id
    WHERE 
        voxel_id = '{voxel_id}'"""
    if not request.user.is_authenticated:
        sensitivity_query += f""" AND symptom NOT IN ({', '.join(map(lambda x: f"'{x}'", private_symptoms))})"""
    sensitivity_query += """
     ORDER BY 
        percent_overlap DESC;
    """
    symptom_results = run_raw_sql(sensitivity_query)
    trace_query = f"""
    select metadata.lesion_id, author, patient_age, patient_sex, publication_year, doi, cause_of_lesion, tracing_file_name, network_file_name, symptom from metadata
    left join trace_voxels
    on metadata.lesion_id = trace_voxels.lesion_id
    left join metadata_symptoms
    on metadata_symptoms.lesionmetadata_id = metadata.lesion_id
    left join symptoms
    on metadata_symptoms.symptoms_id = symptoms.id
    where trace_voxels.voxel_id = '{voxel_id}'
    """
    if not request.user.is_authenticated:
        trace_query += f""" AND symptom NOT IN ({', '.join(map(lambda x: f"'{x}'", private_symptoms))})"""
    trace_results = run_raw_sql(trace_query)
    network_query = f"""
    select metadata.lesion_id,value, author, patient_age, patient_sex, publication_year, doi, cause_of_lesion, tracing_file_name, network_file_name, symptom from metadata
    left join network_voxels
    on metadata.lesion_id = network_voxels.lesion_id
    left join metadata_symptoms
    on metadata_symptoms.lesionmetadata_id = metadata.lesion_id
    left join symptoms
    on metadata_symptoms.symptoms_id = symptoms.id
    where network_voxels.voxel_id = '{voxel_id}'"""
    if not request.user.is_authenticated:
        network_query += f""" AND symptom NOT IN ({', '.join(map(lambda x: f"'{x}'", private_symptoms))})"""
    network_query += """
     order by value desc
    limit 5
    """
    network_results = run_raw_sql(network_query)
    context['symptom_results'] = symptom_results
    context['trace_results'] = trace_results
    context['network_results'] = network_results
    context['coord'] = voxel_id
    context['title'] = voxel_id.replace('_',', ')
    return render(request, 'lesion_bank/locations_view.html', context)