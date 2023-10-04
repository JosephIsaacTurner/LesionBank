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
    file_path = forms.FileField(label='', widget=forms.FileInput(attrs={'class': 'form-control'}))
    true_file_path = forms.FileField(label='', widget=forms.FileInput(attrs={'class': 'form-control'}))

    class Meta:
        model = PracticeImages
        fields = ['file_path', 'true_file_path']

    def clean_file_path(self):
        file_path = self.cleaned_data.get('file_path')
        if not str(file_path).endswith('.gz'):
            raise forms.ValidationError('Uploaded file is not a .gz file.')
        return file_path

    def clean_true_file_path(self):
        true_file_path = self.cleaned_data.get('true_file_path')
        if not str(true_file_path).endswith('.gz'):
            raise forms.ValidationError('Uploaded file is not a .gz file.')
        return true_file_path

class MedicalQuestionnaireForm(forms.Form):
    # 1. Primary Complaint/Reason for Visit
    primary_complaint = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'What brings you in today?'}),
        label='Primary Complaint/Reason for Visit'
    )
    
    # 2. Duration and Onset
    symptom_duration = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'When did you first notice these symptoms?'}),
        label='Duration and Onset of Symptoms'
    )
    symptom_progression = forms.ChoiceField(
        choices=[
            ('better', 'Getting Better'),
            ('worse', 'Getting Worse'),
            ('same', 'Staying the Same')
        ],
        widget=forms.RadioSelect,
        label='How have the symptoms progressed?'
    )
    
    # 3. Pain Assessment (if applicable)
    pain_level = forms.ChoiceField(
        choices=[(i, str(i)) for i in range(11)],
        widget=forms.RadioSelect,
        label='On a scale of 0-10, how would you rate your pain?'
    )
    
    # 4. Past Medical History
    known_conditions = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'E.g., diabetes, hypertension'}),
        label='Known Medical Conditions',
        required=False
    )

    # 5. Medications and Allergies
    current_medications = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'List all medications including over-the-counter ones.'}),
        label='Current Medications',
        required=False
    )
    known_allergies = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'List all known allergies.'}),
        label='Known Allergies',
        required=False
    )
    
    # 6. Family History
    family_medical_history = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'List any significant conditions or early deaths in your immediate family.'}),
        label='Family Medical History',
        required=False
    )

    # 7. Social History
    tobacco_use = forms.ChoiceField(
        choices=[
            ('yes', 'Yes'),
            ('no', 'No')
        ],
        widget=forms.RadioSelect,
        label='Do you use tobacco?'
    )
    alcohol_use = forms.ChoiceField(
        choices=[
            ('yes', 'Yes'),
            ('no', 'No'),
            ('occasionally', 'Occasionally')
        ],
        widget=forms.RadioSelect,
        label='Do you consume alcohol?'
    )
    drug_use = forms.ChoiceField(
        choices=[
            ('yes', 'Yes'),
            ('no', 'No'),
            ('occasionally', 'Occasionally')
        ],
        widget=forms.RadioSelect,
        label='Do you use recreational drugs?'
    )

    # 8. Systems Review
    other_symptoms = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'List any other symptoms you may be experiencing.'}),
        label='Other Symptoms/Systems Review',
        required=False
    )

    # 9. Menstrual and Obstetric History (for those assigned female at birth)
    last_menstrual_period = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Date of Last Menstrual Period',
        required=False
    )
    periods_regular = forms.ChoiceField(
        choices=[
            ('yes', 'Yes'),
            ('no', 'No')
        ],
        widget=forms.RadioSelect,
        label='Are your periods regular?',
        required=False
    )
    previous_pregnancies = forms.IntegerField(
        widget=forms.NumberInput,
        label='Number of Previous Pregnancies',
        required=False
    )

    # 10. Previous Surgeries or Hospitalizations
    previous_surgeries = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'List any previous surgeries or hospitalizations.'}),
        label='Previous Surgeries or Hospitalizations',
        required=False
    )

    # 11. Immunizations
    immunizations_up_to_date = forms.ChoiceField(
        choices=[
            ('yes', 'Yes'),
            ('no', 'No')
        ],
        widget=forms.RadioSelect,
        label='Are your immunizations up-to-date?'
    )

    # 12. Diet and Activity
    diet_description = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Describe your usual diet.'}),
        label='Diet Description',
        required=False
    )
    physical_activity_level = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Describe your typical physical activity level.'}),
        label='Physical Activity Level',
        required=False
    )

    # 13. Mental Health
    feeling_down = forms.ChoiceField(
        choices=[
            ('often', 'Often'),
            ('sometimes', 'Sometimes'),
            ('never', 'Never')
        ],
        widget=forms.RadioSelect,
        label='In the past month, have you often been bothered by feeling down, depressed, or hopeless?'
    )
    little_interest = forms.ChoiceField(
        choices=[
            ('often', 'Often'),
            ('sometimes', 'Sometimes'),
            ('never', 'Never')
        ],
        widget=forms.RadioSelect,
        label='In the past month, have you had little interest or pleasure in doing things?'
    )

    # 14. Sleep:
    sleep_patterns = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Describe your sleep patterns.'}),
        label='Sleep Patterns',
        required=False
    )
    feel_rested = forms.ChoiceField(
        choices=[
            ('yes', 'Yes'),
            ('no', 'No')
        ],
        widget=forms.RadioSelect,
        label='Do you feel rested upon waking?'
    )
    
    # 15. Travel and Exposure History:
    recent_travel = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'List any countries/places you visited in the last six months.'}),
        label='Recent Travel History',
        required=False
    )
    exposure_to_sick_individuals = forms.ChoiceField(
        choices=[
            ('yes', 'Yes'),
            ('no', 'No')
        ],
        widget=forms.RadioSelect,
        label='Have you been in close contact with anyone who has been sick?'
    )
