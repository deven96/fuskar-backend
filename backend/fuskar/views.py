import face_recognition
from django.utils import timezone
from django.shortcuts import render
from django.http import StreamingHttpResponse
from django.http import HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators import gzip
from rest_framework import viewsets, status
from fuskar.models import Student, Image, Course, Lecture, Capturing, Emotion
from fuskar.utils.camera import video_stream
from fuskar.utils.helpers import get_hash
from fuskar.serializers import (
                        StudentSerializer, 
                        ImageSerializer, 
                        CourseSerializer, 
                        StudentCourseSerializer, 
                        LectureSerializer, 
                        CourseLectureSerializer,
                        CourseEmotionSerializer,
                        EmotionSerializer,
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
        try:
            image = data['file']
        except:
            return Response(
                {'detail': "No image sent"},
                status=status.HTTP_406_NOT_ACCEPTABLE)
        face = face_recognition.load_image_file(image)
        face_bounding_boxes = face_recognition.face_locations(face, model='cnn')
        if len(face_bounding_boxes) == 1 :
            print("Image accepted as image contained only one face, checking uniqueness")
            # check image uniqueness
            image = request.data.copy()['file']
            hashval = get_hash(image)
            request._full_data['hashval'] = hashval
            return super(ImageViewSet, self).create(request, *args, **kwargs)
        else:
            return Response(
                {'detail': "Image contains no recognizable face or multiple faces"},
                status=status.HTTP_406_NOT_ACCEPTABLE)

class EmotionViewSet(viewsets.ModelViewSet):
    """
    Viewset for handling emotion queries 
    """
    serializer_class = EmotionSerializer
    queryset = Emotion.objects.all()

class CourseViewSet(viewsets.ModelViewSet):
    """
   Viewset for handling course queries 
    """
    serializer_class = CourseSerializer
    queryset = Course.objects.all()
    lecture_serializer = CourseLectureSerializer
    emotion_serializer = CourseEmotionSerializer


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
    
    @action(detail=True, methods=['get'])
    def emotions(self, request, pk=None):
        """
        Returns all emotions for a particular course
        """
        course = Course.objects.get(id=pk)
        # get all lectures for that course
        queryset = course.lecture_set
        serializer = self.emotion_serializer(queryset.all(), many=True)
        return Response(serializer.data)

class StudentViewSet(viewsets.ModelViewSet):
    """
    Viewset for handling student queries
    """
    serializer_class = StudentSerializer
    queryset = Student.objects.all()
    image_serializer = ImageSerializer
    course_serializer = StudentCourseSerializer

    @action(detail=True, methods=['get', 'post'])
    # pylint: disable=invalid-name
    def images(self, request, pk=None):
        """ Checks a specific student's images 
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
   Viewset for handling lecture queries 
    """
    serializer_class = LectureSerializer
    queryset = Lecture.objects.all()
    emotion_serializer = EmotionSerializer


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
                {'detail': f"lecture [{course_name}]-{pk} has already ended"},
                status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            # save time of stoppage as now
            lecture_object.lock = True
            lecture_object.stopped_at = now
            lecture_object.save()
            # send signal to end attendance taking
            serializer = self.get_serializer(lecture_object)
            return Response(serializer.data)


@gzip.gzip_page
@api_view(['get', 'post'])
def get_stream(request):
    """
    Stream the video coming from connected camera
    """
    Capturing.objects.create()
    response = StreamingHttpResponse(video_stream(), content_type="multipart/x-mixed-replace;boundary=frame")
    if request.method == "GET":
        return response
    elif request.method == "POST":
        capturing = Capturing.objects.last()
        capturing.stop = True
        capturing.save()
        response.close()
        return Response(
                    {"detail": "Stopped video stream"},
                    status=status.HTTP_202_ACCEPTED
                )