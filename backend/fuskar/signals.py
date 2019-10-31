import os
import pickle
import threading
import django.dispatch
from django.db import models
from django.conf import settings
from django.dispatch import receiver
from fuskar.models import Image, Lecture, Course
from fuskar.tasks import retrain_pkl, test_attendance

attendance_task = None

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
    # retrain pkl to remove image from svm map and serial encodings
    retrain_pkl()

@receiver(models.signals.post_save, sender=Image)
def retrain_embedding_on_image_save(sender, instance, **kwargs):
    """
    Retrains the scikit-learn embedding map
    When a new Image is created

    Calls the shared task retrain_pkl()
    """
    retrain_pkl()


@receiver(models.signals.post_save, sender=Lecture)
def take_attendance_on_lecture_create(sender, instance, **kwargs):
    """
    Begins taking attendance
    Once a Lecture object is created
    """
    # task = threading.Thread(target=test_attendance, args=[instance.id])
    # task.daemon = True
    # task.start()
    test_attendance(instance.id)

