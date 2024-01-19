from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm
from lesion_bank.models import Symptoms, LesionMetadata
from django.db.models import Count


class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

def index_view(request):
    return render(request, 'lesion_bank/index.html')

def index_new_view(request):
    # Pick a random symptom from the database where sensitivity_parametric_path is not null and count of lesions is > 10
    symptoms_with_lesion_count = Symptoms.objects.annotate(
            lesion_count=Count('lesionmetadata')
        ).filter(
            sensitivity_parametric_path__isnull=False,
            lesion_count__gt=10
        )
    # Pick a random symptom from the filtered queryset
    random_symptom = symptoms_with_lesion_count.order_by('?').first()


    if not random_symptom:
        # Handle the case where no symptoms are found
        return render(request, 'lesion_bank/index.html', {'error': 'No symptoms found'})

    # Get all lesions with that symptom
    lesions = LesionMetadata.objects.filter(symptoms__symptom=random_symptom.symptom)

    # Transform the lesions into a list of dictionaries
    lesion_metadata = []
    for lesion in lesions:
        lesion_dict = {
            'lesion_id': lesion.lesion_id,
            'lesion_mask': getattr(lesion, 'tracing_file_name', None),
            'lesion_network_map': getattr(lesion, 'network_file_name', None),
            'doi': lesion.doi,
            'author': lesion.author,
            'publication_year': lesion.publication_year,
            'lesion_id': lesion.lesion_id,
        }
        lesion_metadata.append(lesion_dict)

    context = {
        'title': 'LesionBank',
        'page_name': 'Home',
        'symptom': random_symptom.symptom,
        'case_studies': lesion_metadata,
        'case_count': len(lesion_metadata),
        'sensitivity_map': random_symptom.sensitivity_parametric_path,
    }

    # Now render it with the context
    return render(request, 'lesion_bank/index_new.html', context)

def faq(request):
    return render(request, 'lesion_bank/faq.html',{'title':'FAQ'})

def api_view(request):
    from . import api
    from django.shortcuts import render
    if request.method == 'GET':
        # Call the API logic from api.py
        response = api.my_api_view(request)
        return response
    else:
        return render(request, 'error.html', {'message': 'Invalid request method.'})