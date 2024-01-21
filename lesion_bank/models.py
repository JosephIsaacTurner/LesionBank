from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
import os
import uuid
from django.utils.deconstruct import deconstructible
from django.core.files.base import ContentFile

@deconstructible
class PathAndRename(object):

    def __init__(self, sub_path):
        self.path = sub_path

    def __call__(self, instance, filename):
        ext = filename.split('.')[-1]  # get file extension
        middle = filename.split('.')[-2]  # get .nii part
        first_parts = filename.rsplit('.', 2)[0]  # get the parts of the filename before .nii

        # create new filename
        filename = '{}_{}.{}.{}'.format(first_parts, uuid.uuid4().hex[:6], middle, ext)

        return os.path.join(self.path, filename)

class Coordinates(models.Model):
    voxel_id = models.CharField(max_length=15, primary_key=True)
    x = models.IntegerField(null=True)
    y = models.IntegerField(null=True)
    z = models.FloatField(null=True)

    class Meta:
        db_table = 'coordinates'

    def __str__(self):
        return str(self.voxel_id)

class Symptoms(models.Model):
    symptom = models.CharField(max_length=100, blank=True)  # Here, blank=True makes this field optional
    description = models.TextField(blank=True)  # And here as well
    sensitivity_pos_path = models.FileField(upload_to='sensitivity_maps',blank=True, null=True)
    sensitivity_neg_path = models.FileField(upload_to='sensitivity_maps',blank=True, null=True)
    sensitivity_parametric_path = models.FileField(upload_to='sensitivity_maps',blank=True, null=True)

    class Meta:
        db_table = 'symptoms'

    def __str__(self):
        return str(self.symptom)

class LesionMetadata(models.Model):
    lesion_id = models.AutoField(primary_key=True)
    author = models.CharField(max_length=100, blank=True, null=True)
    publication_year = models.IntegerField(blank=True, null=True)
    doi = models.CharField(max_length=100, blank=True, null=True)
    cause_of_lesion = models.CharField(max_length=100, blank=True, null=True)
    patient_age = models.IntegerField(blank=True, null=True)
    patient_sex = models.CharField(max_length=2, blank=True, null=True)
    original_image_1 = models.ImageField(upload_to='uploads/original_images', blank=True, null=True)
    original_image_2 = models.ImageField(upload_to='uploads/original_images', blank=True, null=True)
    original_image_3 = models.ImageField(upload_to='uploads/original_images', blank=True, null=True)
    original_image_4 = models.ImageField(upload_to='uploads/original_images', blank=True, null=True)
    tracing_file_name = models.FileField(upload_to='uploads/lesion_files', blank=True, null=True)
    network_file_name = models.FileField(upload_to='uploads/lesion_files', blank=True, null=True)
    symptoms = models.ManyToManyField(Symptoms)
    created_on = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'metadata'

    def __str__(self):
        return str(self.lesion_id)
   
class VoxelData(models.Model):
    lesion = models.ForeignKey('LesionMetadata', on_delete=models.CASCADE, null=True)
    voxel = models.ForeignKey('Coordinates', on_delete=models.CASCADE)
    value = models.FloatField(null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.lesion)

class TraceVoxels(VoxelData):
    class Meta:
        db_table = 'trace_voxels'

class NetworkVoxels(VoxelData):
    class Meta:
        db_table = 'network_voxels'

class UploadedImages(models.Model):
    upload = models.IntegerField(unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    file_path = models.FileField(upload_to='uploads/upload_data')
    file_size = models.IntegerField()

    class Meta:
        db_table = "uploaded_images"

    def save(self, *args, **kwargs):
        self.file_size = self.file_path.size
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.file_path)

class UploadedImageVoxels(models.Model):
    upload_id = models.ForeignKey(UploadedImages, on_delete=models.CASCADE, db_column='upload')
    voxel = models.ForeignKey('Coordinates', on_delete=models.CASCADE)
    value = models.FloatField(null=True)

    class Meta:
        db_table = "uploaded_image_voxels"

    def __str__(self):
        return str(self.upload_id)

class PracticeImages(models.Model):
    upload_id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    file_path = models.FileField(upload_to=PathAndRename('practice_masks'))
    true_file_path = models.FileField(upload_to=PathAndRename('practice_masks'))
    file_size = models.IntegerField()

    class Meta:
        db_table = "practice_images"

    def save(self, *args, **kwargs):
        self.file_size = self.file_path.size
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.file_path)

class PracticeImageVoxels(models.Model):
    upload = models.ForeignKey(PracticeImages, on_delete=models.CASCADE, db_column='upload_id', null=True)
    voxel = models.ForeignKey('Coordinates', on_delete=models.CASCADE)
    value = models.FloatField(null=True)

    class Meta:
        db_table = "practice_image_voxels"

    def __str__(self):
        return str(self.upload_id)

class TrueImageVoxels(models.Model):
    upload = models.ForeignKey(PracticeImages, on_delete=models.CASCADE, db_column='upload_id', null=True)
    voxel = models.ForeignKey('Coordinates', on_delete=models.CASCADE)
    value = models.FloatField(null=True)

    class Meta:
        db_table = "true_image_voxels"

    def __str__(self):
        return str(self.upload_id)

class AtlasMetadata(models.Model):
    atlas_id = models.AutoField(primary_key=True)
    atlas_name = models.CharField(max_length=100, blank=True, null=True)
    atlas_file_name = models.FileField(upload_to='uploads/atlas_files', blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'atlas_metadata'

    def __str__(self):
        return str(self.atlas_id)

class AtlasKey(models.Model):
    atlas = models.ForeignKey('AtlasMetadata', on_delete=models.CASCADE, null=True)
    key_id = models.FloatField(null=True)
    value = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'atlas_key'

    def __str__(self):
        return str(self.atlas)

class AtlasVoxels(models.Model):
    atlas = models.ForeignKey('AtlasMetadata', on_delete=models.CASCADE, null=True)
    voxel = models.ForeignKey('Coordinates', on_delete=models.CASCADE)
    value = models.FloatField(null=True)

    class Meta:
        db_table = 'atlas_voxels'

    def __str__(self):
        return str(self.atlas)

class GeneratedImages(models.Model):
    file_id = models.CharField(max_length=10, db_column='file_id', primary_key=True)
    mask_filepath = models.FileField(upload_to='mask_input/', default='mask_input/default')
    lesion_network_filepath = models.FileField(upload_to='network_maps_output/', default='network_maps_output/default')
    file_path_1mm = models.FileField(upload_to='output/', default='output/not_generated')
    file_path_2mm = models.FileField(upload_to='output/', default='output/not_generated')
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)
    page_name = models.CharField(max_length=200)

    class Meta:
        db_table = 'generated_images'

    def __str__(self):
        return str(self.file_id)

    def save(self, *args, **kwargs):
        if not self.file_path_1mm:
            self.file_path_1mm.save('not_generated', ContentFile(''), save=False)
        if not self.file_path_2mm:
            self.file_path_2mm.save('not_generated', ContentFile(''), save=False)
        super().save(*args, **kwargs)
    
class PredictionVoxels(models.Model):
    file = models.ForeignKey('GeneratedImages', on_delete=models.CASCADE, null=True)
    voxel_id = models.CharField(max_length=20)  # Update this line
    value = models.FloatField(null=True)

    class Meta:
        db_table = 'prediction_voxels'

    def __str__(self):
        return str(self.file)
    
class SensitivityVoxels(models.Model):
    voxel_id = models.CharField(max_length=255, primary_key=True)
    symptom_id = models.IntegerField()
    positive_overlap_count = models.IntegerField()
    negative_overlap_count = models.IntegerField()
    overlap_difference = models.IntegerField()
    total_count = models.IntegerField()
    percent_overlap = models.FloatField()

    class Meta:
        db_table = 'sensitivity_voxels'       # specify the name of the table in the database
        managed = False                       # ensure Django doesn't manage the table (create/alter)
        constraints = [
            models.UniqueConstraint(fields=['voxel_id', 'symptom_id'], name='unique_voxel_symptom')
        ]

    def __str__(self):
        return f"Voxel: {self.voxel_id}, Symptom: {self.symptom_id}"