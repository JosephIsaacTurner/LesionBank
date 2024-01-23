from django.shortcuts import render, redirect
from lesion_bank.utils.nifti_utils import NiftiHandler

def test_view(request):
    return render(request, 'lesion_bank/debugging.html', {})