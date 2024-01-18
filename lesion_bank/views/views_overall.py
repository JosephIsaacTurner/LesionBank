from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm
# from .models import Symptoms, LesionMetadata

class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

def index_view(request):
    return render(request, 'lesion_bank/index.html')

def index_new_view(request):
    # # Pick a random symptom from the database
    # random_symptom = Symptoms.objects.order_by('?').first()
    # # Get all lesions with that symptom
    # lesion_metadata = LesionMetadata.objects.filter(symptoms__symptom=random_symptom.symptom)
    # # Get the count of lesions with that symptom
    # case_count = lesion_metadata.count()
    # # Rename dict keys to match the template
    # # tracing_file_name -> lesion_mask
    # # network_file_name -> lesion_network_map
    # lesion_metadata = {k: v for k, v in lesion_metadata.items() if k in ['lesion_id', 'lesion_mask', 'lesion_network_map']}
    # lesion_metadata['lesion_mask'] = lesion_metadata.pop('tracing_file_name')
    # lesion_metadata['lesion_network_map'] = lesion_metadata.pop('network_file_name')
    # lesion_metadata['case_count'] = case_count
    # lesion_metadata['symptom'] = random_symptom.symptom
    # context = {
    #     'symptom': random_symptom.symptom,
    #     'cases': lesion_metadata,
    #     'case_count': case_count,
    # }
    return render(request, 'lesion_bank/index_new.html')

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