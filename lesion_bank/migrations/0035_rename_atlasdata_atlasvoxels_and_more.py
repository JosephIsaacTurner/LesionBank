# Generated by Django 4.1.1 on 2023-06-30 15:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lesion_bank', '0034_rename_atlas_id_atlaskey_atlas'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='AtlasData',
            new_name='AtlasVoxels',
        ),
        migrations.RenameField(
            model_name='atlasvoxels',
            old_name='atlas_id',
            new_name='atlas',
        ),
    ]
