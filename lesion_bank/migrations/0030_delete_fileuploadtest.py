# Generated by Django 4.1.1 on 2023-06-30 00:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lesion_bank', '0029_rename_patient_gender_lesionmetadata_patient_sex_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='FileUploadTest',
        ),
    ]
