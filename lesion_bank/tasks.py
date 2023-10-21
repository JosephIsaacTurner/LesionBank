from celery import shared_task
from lesion_bank.network_mapping import compute_network_map


@shared_task
def compute_network_map_async(s3_input, s3_output):
    compute_network_map(s3_input, s3_output)
