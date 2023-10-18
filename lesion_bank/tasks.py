from celery import shared_task
from lesion_bank.network_maps_pipeline import compute_network_map


@shared_task
def compute_network_map_async(s3_input, s3_output):
    # Your long-running function here
    compute_network_map(s3_input, s3_output)
