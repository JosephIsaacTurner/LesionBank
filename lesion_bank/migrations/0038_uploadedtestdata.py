# Generated by Django 4.1.1 on 2023-07-04 20:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lesion_bank', '0037_remove_atlasvoxels_key_atlasvoxels_value'),
    ]

    operations = [
        migrations.CreateModel(
            name='UploadedTestData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('upload_key', models.IntegerField()),
                ('value', models.FloatField(null=True)),
                ('voxel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lesion_bank.coordinates')),
            ],
            options={
                'db_table': 'uploaded_test_voxels',
            },
        ),
    ]
