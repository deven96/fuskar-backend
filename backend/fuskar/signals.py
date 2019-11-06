import os
import pickle
import threading
import django.dispatch
from django.db import models, transaction
from django.conf import settings
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from backend.consumers import LectureConsumer
from fuskar.serializers import LectureSerializer
from fuskar.models import Image, Lecture, Course
from fuskar.tasks import retrain_pkl, test_attendance, remove_image_objects


@receiver(models.signals.post_delete, sender=Image)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `Image` object is deleted.
    """
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)
            print(f"Deleting hardcopy image at {instance.file.path}")
    remove_image_objects(instance)

@receiver(models.signals.post_save, sender=Image)
def retrain_embedding_on_image_save(sender, instance, **kwargs):
    """
    Retrains the scikit-learn embedding map
    When a new Image is created

    Calls the shared task retrain_pkl()
    """
    retrain_pkl()


@receiver(models.signals.post_save, sender=Lecture)
def take_attendance_and_emotions_on_lecture_create(sender, instance, **kwargs):
    """
    Begins taking attendance and emotions
    Once a Lecture object is created
    """
    test_attendance(instance.id)


@receiver(models.signals.m2m_changed, sender=Lecture.students_present.through)
@receiver(models.signals.m2m_changed, sender=Lecture.emotions.through)
@receiver(models.signals.post_save, sender=Lecture)
def trigger_ws_serialization(sender, instance, **kwargs):
    """
    Triggers sending of a lecture object to a websocket
    Also closes ws connection if lecture is stopped
    """
    serializer = LectureSerializer(instance)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'lectures_update_group_{instance.id}',
        {
            'type': 'trigger',
            'message': serializer.data,
        }
    )