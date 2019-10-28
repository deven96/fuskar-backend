import face_recognition
from django.utils import timezone
from django.shortcuts import render
from django.http import StreamingHttpResponse
from django.http import HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators import gzip
from rest_framework import viewsets, status
from fuskar.models import Student, Image, Course, Lecture
from fuskar.utils.camera import video_stream
from fuskar.signals import end_attendance, capture
from fuskar.serializers import (
                        StudentSerializer, 
                        ImageSerializer, 
                        CourseSerializer, 
                        StudentCourseSerializer, 
                        LectureSerializer, 
                        CourseLectureSerializer
)
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

class ImageViewSet(viewsets.ModelViewSet):
    """
    Viewset for handling image queries 
    """
    serializer_class = ImageSerializer
    queryset = Image.objects.all()

    def create(self, request, *args, **kwargs):
        """
        Override the default create function to check if the image has None
        or multiple faces
        """
        data = request.data.copy()
        image = data['file']
        print(image)
        face = face_recognition.load_image_file(image)
        face_bounding_boxes = face_recognition.face_locations(face)
        if len(face_bounding_boxes) == 1 :
            return super().create(request)
        else:
            return Response(
                {'detail': "Image contains none or multiple faces"},
                status=status.HTTP_406_NOT_ACCEPTABLE)

class CourseViewSet(viewsets.ModelViewSet):
    """
   Viewset for handling course queries 
    """
    serializer_class = CourseSerializer
    queryset = Course.objects.all()
    lecture_serializer = CourseLectureSerializer

    @action(detail=True, methods=['get'])
    def lectures(self, request, pk=None):
        """
        Returns all lectures for a particular course
        """
        course = Course.objects.get(id=pk)
        # get all lectures for that course
        queryset = course.lecture_set
        serializer = self.lecture_serializer(queryset.all(), many=True)
        return Response(serializer.data)

class StudentViewSet(viewsets.ModelViewSet):
    """
    Viewset for handling student queries

    /student/student-id/images/ is used to add/remove an image for a student only
    """
    serializer_class = StudentSerializer
    queryset = Student.objects.all()
    image_serializer = ImageSerializer
    course_serializer = StudentCourseSerializer

    @action(detail=True, methods=['get', 'post'])
    # pylint: disable=invalid-name
    def images(self, request, pk=None):
        """ Checks a specific student's images 
        
        :param pk: student id
        :type pk: int
        """
        if request.method == "GET":
            queryset = Image.objects.filter(owner=pk)
            serializer = self.image_serializer(queryset, many=True)
            return Response(serializer.data)
        elif request.method == "POST":
            try:
                file = request.data['file']
            except KeyError:
                return Response(
                {'detail': "No image data posted"},
                status=status.HTTP_406_NOT_ACCEPTABLE)
            owner = Student.objects.get(id=pk)
            image = Image.objects.create(owner=owner, file=file)
            serializer = self.image_serializer(image)
            return Response(serializer.data)
            
    @action(detail=True, methods=['get', 'post'])
    # pylint: disable=invalid-name
    def courses(self, request, pk=None):
        """ Checks a specific student's courses 
        
        :param pk: student id
        :type pk: int
        """
        student = Student.objects.get(id=pk)
        queryset = student.course_set
        if request.method == "GET":
            serializer = self.course_serializer(queryset.all(), many=True)
            return Response(serializer.data)
        elif request.method == "POST":
            try:
                course_no = int(request.data['course'])
                course = Course.objects.get(id=course_no)
                if course not in queryset.all():
                    queryset.add(course)
                    serializer = self.course_serializer(course)
                    return Response(serializer.data)
                else:
                    detail = 'Student already takes this course'
            except KeyError:
                detail = "No course_no attached"
            except ObjectDoesNotExist:
                detail = "Course Number does not exist"
                return Response(
                    {"detail": detail},
                    status=status.HTTP_406_NOT_ACCEPTABLE
                )
    

class LectureViewSet(viewsets.ModelViewSet):
    """
   Viewset for handling course queries 
    """
    serializer_class = LectureSerializer
    queryset = Lecture.objects.all()


    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """
        Ends an existing lecture
        """
        now = timezone.now()
        try:
            lecture_object = Lecture.objects.get(id=pk)
        except ObjectDoesNotExist:
            return Response(
                {'detail': "lecture {} does not exist".format(pk)},
                status=status.HTTP_406_NOT_ACCEPTABLE)
        course_name = lecture_object.course.name
        if lecture_object.stopped_at:
            return Response(
                {'detail': "lecture [{}]-lecture-obj-{} has already ended". format(
                    course_name, pk
                )},
                status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            # save time of stoppage as now
            end_attendance.send(sender=self.__class__, lecture_id=pk)
            lecture_object.stopped_at = now
            lecture_object.save()
            # send signal to end attendance taking
            serializer = self.get_serializer(lecture_object)
            return Response(serializer.data)


@gzip.gzip_page
@api_view(['get'])
def get_stream(request):
    return StreamingHttpResponse(video_stream(), content_type="multipart/x-mixed-replace;boundary=frame")