# Generated by Django 4.1.1 on 2023-06-27 00:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lesion_bank', '0025_lesionmetadata_symptoms_voxelsuploaded_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesionmetadata',
            name='patient_age',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='lesionmetadata',
            name='patient_gender',
            field=models.CharField(blank=True, max_length=2, null=True),
        ),
    ]
