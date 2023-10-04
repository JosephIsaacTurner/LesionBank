# Generated by Django 4.1.1 on 2023-06-26 23:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lesion_bank', '0020_remove_voxelsnetworks_lesion_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LesionMetadata',
            fields=[
                ('lesion_id', models.CharField(max_length=30, primary_key=True, serialize=False)),
                ('author', models.CharField(blank=True, max_length=100, null=True)),
                ('publication_year', models.IntegerField(blank=True, null=True)),
                ('doi', models.CharField(blank=True, max_length=100, null=True)),
                ('cause_of_lesion', models.CharField(blank=True, max_length=100, null=True)),
                ('original_image_1', models.CharField(blank=True, max_length=100, null=True)),
                ('original_image_2', models.CharField(blank=True, max_length=100, null=True)),
                ('original_image_3', models.CharField(blank=True, max_length=100, null=True)),
                ('original_image_4', models.CharField(blank=True, max_length=100, null=True)),
                ('tracing_file_name', models.CharField(blank=True, max_length=100, null=True)),
                ('network_file_name', models.CharField(blank=True, max_length=100, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Symptoms',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symptom', models.CharField(max_length=100)),
                ('description', models.TextField(default='This will later be populated with a description of the symptom (Under development)')),
            ],
        ),
        migrations.CreateModel(
            name='VoxelsUploaded',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=100, null=True)),
                ('lesion', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='lesion_bank.lesionmetadata')),
                ('voxel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lesion_bank.coordinates')),
            ],
        ),
        migrations.CreateModel(
            name='VoxelsTracings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=100, null=True)),
                ('lesion', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='lesion_bank.lesionmetadata')),
                ('voxel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lesion_bank.coordinates')),
            ],
        ),
        migrations.CreateModel(
            name='VoxelsNetworks',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=100, null=True)),
                ('lesion', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='lesion_bank.lesionmetadata')),
                ('voxel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lesion_bank.coordinates')),
            ],
        ),
        migrations.AddField(
            model_name='lesionmetadata',
            name='symptoms',
            field=models.ManyToManyField(to='lesion_bank.symptoms'),
        ),
    ]
