from app.tasks.celery_app import celery_app


@celery_app.task(name='file_translate.process')
def process_file_translate(task_id: str) -> str:
    return task_id
