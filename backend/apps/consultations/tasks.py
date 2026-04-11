from common.tasking import shared_task

from .models import Consultation
from .services.workflow import process_consultation


@shared_task
def process_consultation_task(consultation_id: int):
    consultation = Consultation.objects.get(pk=consultation_id)
    process_consultation(consultation)
    return consultation_id
