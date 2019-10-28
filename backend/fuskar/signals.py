import os
import pickle
import django.dispatch
from django.db import models
from django.conf import settings
from django.dispatch import receiver
from celery.task.control import revoke
from fuskar.models import Image, Lecture, Course, TaskScheduler
from fuskar.utils.camera import capture_from_camera
from fuskar.tasks import retrain_pkl, test_attendance, capture_pictures

attendance_task_id = None

end_attendance = django.dispatch.Signal()

@receiver(models.signals.post_delete, sender=Image)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `Image` object is deleted.
    """
    print("Image object signal-delete received, deleting hardcopy")
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)


@receiver(models.signals.post_save, sender=Image)
def retrain_embedding_on_image_save(sender, instance, **kwargs):
    """
    Retrains the scikit-learn embedding map
    When a new Image is created

    Calls the shared task retrain_pkl()
    """
    retrain_pkl.delay()


@receiver(models.signals.post_save, sender=Lecture)
def take_attendance_on_lecture_create(sender, instance, **kwargs):
    """
    Begins taking attendance
    Once a Lecture object is created
    """
    global attendance_task_id
    task = test_attendance.delay(instance.id)
    attendance_task_id = task.id


# TODO: find a way to shutdown the infinite loop of attendance taking upon
# receiving the end attendance signal
@receiver(end_attendance)
def cancel_attendance_on_lecture_end(sender, lecture_id, **kwargs):
    """
    Cancels the attendance procedure 
    """
    global attendance_task_id
    revoke(attendance_task_id, terminate=True)
