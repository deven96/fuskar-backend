import os
from django.db import models
from django.dispatch import receiver

def get_image_path(instance, filename):
    """
    Saves every image to the owner subfolder
    """
    return os.path.join('images', str(instance.owner.id), filename)

class Student(models.Model):
    """
    Student Model
    """
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    full_name = models.CharField(max_length=256, blank=False, null=False)
    email = models.EmailField(unique=True)
    matric_no = models.CharField(max_length=15, unique=True, blank=False, null=False)

class Course(models.Model):
    """
    Course belongs to a department and has a list of registered_students
    """
    DEPT_CHOICES = (
        ('CPE', 'Computer Engineering'),
        ('CME', 'Telecommunication Engineering'),
    )
    department = models.CharField(max_length=15, choices=DEPT_CHOICES)
    code = models.CharField(max_length=3, blank=False, null=False)
    description = models.CharField(max_length=512, blank=True, null=True)
    registered_students = models.ManyToManyField(Student, blank=True)

    class Meta:
        unique_together = [['department', 'code']]

class Lecture(models.Model):
    """
    Every lecture belongs to a course and contains a list of students in attendance
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    stopped_at = models.DateTimeField()
    students_present = models.ManyToManyField(Student)

class Image(models.Model):
    """
    Image is owned by a single student
    """
    owner = models.ForeignKey(Student, on_delete=models.CASCADE)
    file = models.ImageField(blank=False, null=False, upload_to=get_image_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.id

@receiver(models.signals.post_delete, sender=Image)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `Image` object is deleted.
    """
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)