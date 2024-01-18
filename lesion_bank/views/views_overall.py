from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm
from lesion_bank.models import Symptoms, LesionMetadata

class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

def index_view(request):
    return render(request, 'lesion_bank/index.html')

def index_new_view(request):
    # Pick a random symptom from the database
    random_symptom = Symptoms.objects.order_by('?').first()
    if not random_symptom:
        # Handle the case where no symptoms are found
        return render(request, 'lesion_bank/index_new.html', {'error': 'No symptoms found'})

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
        'symptom': random_symptom.symptom,
        'cases': lesion_metadata,
        'case_count': len(lesion_metadata),  # Or lesions.count()
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