# Generated by Django 4.1.1 on 2023-06-26 23:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lesion_bank', '0018_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='symptoms',
            name='description',
            field=models.TextField(default='This will later be populated with a description of the symptom (Under development)'),
        ),
        migrations.AlterField(
            model_name='lesionmetadata',
            name='lesion_id',
            field=models.CharField(max_length=30, primary_key=True, serialize=False),
        ),
    ]
