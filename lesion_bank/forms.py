# forms.py

from django import forms
from .models import Symptoms
from django.core.exceptions import ValidationError
from .models import LesionMetadata, Symptoms, UploadedImages, PracticeImages

def validate_file_extension_nifti(value):
    if not value.name.endswith('.gz'):
        raise ValidationError(u'Invalid file type. Only .nii.gz files are supported.')

class LesionMetadataForm(forms.ModelForm):
    tracing_file_name = forms.FileField(validators=[validate_file_extension_nifti])
    network_file_name = forms.FileField(validators=[validate_file_extension_nifti], required=False)
    
    class Meta:
        model = LesionMetadata
        fields = ['author', 'publication_year', 'doi', 'cause_of_lesion', 'patient_age', 'patient_sex', 'original_image_1', 
                  'original_image_2', 'original_image_3', 'original_image_4', 'tracing_file_name', 'network_file_name', 'symptoms']
        widgets = {
            'symptoms': forms.CheckboxSelectMultiple
        }

class NewSymptomsForm(forms.ModelForm):
    class Meta:
        model = Symptoms
        fields = '__all__'

    def clean_symptom(self):
        symptom = self.cleaned_data['symptom']
        if Symptoms.objects.filter(symptom=symptom).exists():
            raise forms.ValidationError("This symptom already exists.")
        return symptom


class UpdateSymptomsForm(forms.ModelForm):
    class Meta:
        model = Symptoms
        fields = ['description', 'sensitivity_pos_path', 'sensitivity_neg_path']  # Include file fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].label = f"Description for {self.instance.symptom}"
        self.fields['sensitivity_pos_path'].label = f"Sensitivity Positive Path for {self.instance.symptom}"
        self.fields['sensitivity_neg_path'].label = f"Sensitivity Negative Path for {self.instance.symptom}"

class UploadImageForm(forms.ModelForm):
    file_path = forms.FileField(label='', widget=forms.FileInput(attrs={'class': 'form-control'}))

    class Meta:
        model = UploadedImages
        fields = ['file_path']
    
    def clean_file_path(self):
        file_path = self.cleaned_data.get('file_path')
        if not str(file_path).endswith('.gz'):
            raise forms.ValidationError('Uploaded file is not a .gz file.')
        return file_path
    
class PracticeImageForm(forms.ModelForm):
    file_name = forms.FileField(label='', widget=forms.FileInput(attrs={'class': 'form-control'}))
    true_file_name = forms.FileField(label='', widget=forms.FileInput(attrs={'class': 'form-control'}))

    class Meta:
        model = PracticeImages
        fields = ['file_name', 'true_file_name']

    def clean_file_path(self):
        file_path = self.cleaned_data.get('file_name')
        if not str(file_path).endswith('.gz'):
            raise forms.ValidationError('Uploaded file is not a .gz file.')
        return file_path

    def clean_true_file_path(self):
        true_file_path = self.cleaned_data.get('true_file_name')
        if not str(true_file_path).endswith('.gz'):
            raise forms.ValidationError('Uploaded file is not a .gz file.')
        return true_file_path