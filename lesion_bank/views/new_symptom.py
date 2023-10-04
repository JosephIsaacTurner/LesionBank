from django.shortcuts import render, redirect
from lesion_bank.models import Symptoms
from lesion_bank.forms import NewSymptomsForm, UpdateSymptomsForm
from django.forms import modelformset_factory
from django.contrib.auth.decorators import login_required

@login_required
def symptoms_form_view(request):
    SymptomsFormSet = modelformset_factory(Symptoms, form=UpdateSymptomsForm, extra=0)

    if request.method == 'POST':
        form = NewSymptomsForm(request.POST or None)
        formset = SymptomsFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            if form.cleaned_data.get('symptom'):
                form.save()
            formset.save()

            # Optionally, redirect to a success page
            return redirect('new_symptom')
    else:
        form = NewSymptomsForm()
        formset = SymptomsFormSet(queryset=Symptoms.objects.all())
    
    return render(request, 'lesion_bank/form_template.html', {'form': form, 'formset': formset})
