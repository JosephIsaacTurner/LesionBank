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