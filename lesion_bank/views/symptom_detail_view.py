from django.shortcuts import render, get_object_or_404
from lesion_bank.models import LesionMetadata, Symptoms
from django.http import HttpResponse
import json
from django.db import connection
from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse
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

def symptom_detail_view(request, symptom):
    if not request.user.is_authenticated and symptom in private_symptoms:
        return redirect(reverse('symptoms'))
    query = """
        SELECT * FROM (
            SELECT symptom, COUNT(metadata.lesion_id) AS "count" 
            FROM symptoms
            LEFT JOIN metadata_symptoms ON metadata_symptoms.symptoms_id = symptoms.id
            LEFT JOIN metadata ON metadata.lesion_id = metadata_symptoms.lesionmetadata_id
            GROUP BY symptom
        ) AS a 
        WHERE a."count" > 5
    """

    if not request.user.is_authenticated:
        query += f""" AND symptom NOT IN ({', '.join(map(lambda x: f"'{x}'", private_symptoms))})"""

    query += " ORDER BY symptom"

    symptom_list = ""
    symptom_list = run_raw_sql(query)
    symptom_object = get_object_or_404(Symptoms, symptom=symptom)
    if symptom_object:
        case_results = LesionMetadata.objects.filter(symptoms__symptom=symptom) 
        count = case_results.count()
        case_list = list(case_results.values('author','publication_year', 'doi', 'lesion_id', 'tracing_file_name', 'network_file_name', 'patient_age', 'patient_sex', 'cause_of_lesion'))
        context = {
            'symptom_list':symptom_list,
            'symptom':symptom_object.symptom,
            'description':symptom_object.description,
            'count':count,
            'case_list':case_list,
            'sensitivity_pos_path':symptom_object.sensitivity_pos_path,
            'sensitivity_neg_path':symptom_object.sensitivity_neg_path,
            'min_threshold':int(.50*count),
            'max_threshold':count,
            'title':symptom
        }
        return render(request, 'lesion_bank/symptom_view.html', context)
        # return HttpResponse(f"{symptom_object.description} Number of cases: {case_results.count()}, {json.dumps(case_list)}")
    else:
        return HttpResponse("No such symptom found")
