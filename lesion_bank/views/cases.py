from django.shortcuts import render, get_object_or_404
from lesion_bank.models import LesionMetadata, Symptoms
from django.http import HttpResponse
from django.conf import settings
private_symptoms = settings.PRIVATE_SYMPTOMS

def view_metadata_list_view(request):
    if request.user.is_authenticated:
        # If the user is logged in, show all records
        metadata_list = LesionMetadata.objects.all()
    else:
        # If the user is not logged in, exclude records with specified symptoms
        excluded_symptoms = Symptoms.objects.filter(symptom__in=private_symptoms)
        metadata_list = LesionMetadata.objects.exclude(symptoms__in=excluded_symptoms)
        
    return render(request, 'lesion_bank/edit_metadata_list.html', {'page_name':'Case Studies','title':'Lesion Bank Dataset List', 'metadata_list': metadata_list, 'edit':False})

def single_case_view(request, case_id):
    instance = get_object_or_404(LesionMetadata, lesion_id=case_id)

    if instance:
        # Extracting the tracing_file_name from the instance
        tracing_file_path = instance.tracing_file_name
        network_file_path = instance.network_file_name
        author = instance.author
        publication_year = instance.publication_year
        doi = instance.doi
        patient_age = instance.patient_age
        patient_sex = instance.patient_sex
        original_image_1 = instance.original_image_1
        cause = instance.cause_of_lesion
        symptoms_list = [symptom.symptom for symptom in instance.symptoms.all()]  # assuming Symptoms model has a 'name' field


        # Passing the tracing_file_path to the template
        return render(request, 'lesion_bank/case_view.html', {'trace_file_path': tracing_file_path, 
                                                              'network_file_path': network_file_path,
                                                              'author': author,
                                                              'doi': doi,
                                                              'publication_year': publication_year,
                                                              'patient_age': patient_age,
                                                              'patient_sex':patient_sex,
                                                              'original_image_1':original_image_1,
                                                              'symptoms':symptoms_list,
                                                              'case_id':case_id,
                                                              'cause':cause,
                                                              'page_name':'Case Studies',
                                                              'title':'Case Reports'})
    else:
        # This else statement might actually never execute due to the behavior of get_object_or_404
        return HttpResponse('No such case exists.')