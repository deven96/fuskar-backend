import os
from django.db import models
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils import timezone


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
    name = models.CharField(max_length=256, blank=False, null=False)
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
    stopped_at = models.DateTimeField(blank=True, null=True)
    students_present = models.ManyToManyField(Student, blank=True)

class Image(models.Model):
    """
    Image is owned by a single student
    """
    owner = models.ForeignKey(Student, on_delete=models.CASCADE)
    file = models.ImageField(blank=False, null=False, upload_to=get_image_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Image object : {}".format(self.id)

class TaskScheduler(models.Model):

    periodic_task = models.ForeignKey(PeriodicTask, on_delete=models.CASCADE)
    lecture = models.ForeignKey(Lecture, default=1, on_delete=models.CASCADE)


    @staticmethod
    def schedule_every(task_name, period, every, lecture, args=None, kwargs=None):
        """ schedules a task by name every "every" "period". So an example call would be:
            TaskScheduler.schedule_every('mycustomtask', 'seconds', 30, 1, [1,2,3])
            that would schedule your custom task to run every 30 seconds with the arguments 1,2 and 3 passed to the actual task. 
        """
        permissible_periods = ['days', 'hours', 'minutes', 'seconds']
        if period not in permissible_periods:
            raise Exception('Invalid period specified')
        # create the periodic task and the interval
        ptask_name = "%s_%s" % (task_name,  timezone.now()) # create some name for the period task
        interval_schedules = IntervalSchedule.objects.filter(period=period, every=every)
        lecture = Lecture.objects.get(id=lecture)
        if interval_schedules: # just check if interval schedules exist like that already and reuse em
            interval_schedule = interval_schedules[0]
        else: # create a brand new interval schedule
            interval_schedule = IntervalSchedule()
            interval_schedule.every = every # should check to make sure this is a positive int
            interval_schedule.period = period 
            interval_schedule.save()
        ptask = PeriodicTask(name=ptask_name, task=task_name, interval=interval_schedule)
        if args:
            ptask.args = args
        if kwargs:
            ptask.kwargs = kwargs
        ptask.save()
        return TaskScheduler.objects.create(periodic_task=ptask, lecture=lecture)

    def stop(self):
        """pauses the task"""
        ptask = self.periodic_task
        ptask.enabled = False
        ptask.save()
        self.save()
        print("Stopped TaskSchedule")

    def start(self):
        """starts the task"""
        ptask = self.periodic_task
        ptask.enabled = True
        ptask.save()
        self.save()

    def terminate(self):
        print("TaskSchedule terminate called")
        ptask = self.periodic_task
        ptask.enabled = False
        ptask.save()
        ptask.delete()
        self.delete()
        print("Deleted TaskSchedule")