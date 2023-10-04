from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm

class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

def index_view(request):
    return render(request, 'lesion_bank/index.html')

# def locations_view(request):
#     from . import locations
#     return locations.page(request)
# def symptoms_view_old(request):
#     from . import symptoms
#     return symptoms.page(request)

def api_docs(request):
    return render(request, 'lesion_bank/api_docs.html',{'title': "API Docs"})

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
    
def charts_view(request):
    from . import charts
    return charts.page(request)
