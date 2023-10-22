from django.shortcuts import render, redirect
from lesion_bank.models import LesionMetadata, Symptoms, TraceVoxels, NetworkVoxels, Coordinates
from lesion_bank.forms import LesionMetadataForm
from lesion_bank.array_functions import npToSql, niftiTo2d, fillCoordinateTable, getNiftiFromCloud, niftiObjTo2d
from django.db import IntegrityError
from django.core.files.uploadedfile import InMemoryUploadedFile
import gzip
from django.contrib.auth.decorators import login_required
from django.conf import settings
from lesion_bank.forms import NewSymptomsForm, UpdateSymptomsForm
from django.forms import modelformset_factory
private_symptoms = settings.PRIVATE_SYMPTOMS


@login_required
def edit_metadata_list_view(request):
    metadata_list = LesionMetadata.objects.all()
    return render(request, 'lesion_bank/edit_metadata_list.html', {'title':'Dataset Admin', 'metadata_list': metadata_list, 'edit':True})

@login_required
def import_metadata_form(request):
    if request.method == 'POST':
        form = LesionMetadataForm(request.POST, request.FILES)
        
        if form.is_valid():
            instance = form.save()
            # Get filenames and lesion_id from the saved instance
            tracing_file_url = instance.tracing_file_name.name if instance.tracing_file_name else None
            network_file_url = instance.network_file_name.name if instance.network_file_name else None
            lesion_id = instance.lesion_id
            # Now you can use these variables in your function calls
            if tracing_file_url:
                try:
                    npToSql(niftiObjTo2d(getNiftiFromCloud(tracing_file_url)), lesion_id, TraceVoxels)
                except Exception as e:
                    # Add custom debugging information to the exception message
                    custom_message = f"An error occurred in import_data. Additional info: {tracing_file_url}, {network_file_url}"
                    raise Exception(custom_message) from e
            if network_file_url:
                try:
                    npToSql(niftiObjTo2d(getNiftiFromCloud(network_file_url)), lesion_id, NetworkVoxels)
                except IntegrityError:
                    fillCoordinateTable(niftiTo2d(network_file_url))
                    npToSql(niftiObjTo2d(getNiftiFromCloud(network_file_url)), lesion_id, NetworkVoxels)

            # Optionally, redirect to a success page
            return redirect('import_data')
    else:
        form = LesionMetadataForm()
    
    return render(request, 'lesion_bank/metadata_form_template.html', {'form': form})

@login_required
def edit_metadata_form_view(request, lesion_id):
    try:
        instance = LesionMetadata.objects.get(lesion_id=lesion_id)
    except LesionMetadata.DoesNotExist:
        return redirect('edit_metadata_list')  # or show an error message

    if request.method == 'POST':
        form = LesionMetadataForm(request.POST, request.FILES, instance=instance)

        if form.is_valid():
            # This will update the existing LesionMetadata instance
            instance = form.save()

            new_tracing_file = form.cleaned_data['tracing_file_name']
            new_network_file = form.cleaned_data['network_file_name']

            # Check if a new tracing file has been uploaded
            if isinstance(new_tracing_file, InMemoryUploadedFile) or str(instance.tracing_file_name) != str(new_tracing_file):
                TraceVoxels.objects.filter(lesion_id=lesion_id).delete()
                if new_tracing_file:
                    npToSql(niftiTo2d(instance.tracing_file_name.path), lesion_id, TraceVoxels)
            
            # Check if a new network file has been uploaded
            if isinstance(new_network_file, InMemoryUploadedFile) or str(instance.network_file_name) != str(new_network_file):
                NetworkVoxels.objects.filter(lesion_id=lesion_id).delete()
                if new_network_file:
                    try:
                        npToSql(niftiTo2d(instance.network_file_name.path), lesion_id, NetworkVoxels)
                    except IntegrityError:
                        fillCoordinateTable(niftiTo2d(instance.network_file_name.path))
                        npToSql(niftiTo2d(instance.network_file_name.path), lesion_id, NetworkVoxels)

        form = LesionMetadataForm(instance=instance)
    else:
        form = LesionMetadataForm(instance=instance)

    return render(request, 'lesion_bank/metadata_form_template.html', {'form': form})

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
