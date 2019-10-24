from django.shortcuts import render
from django.http import StreamingHttpResponse
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import viewsets
from fuskar.models import Student, Image, Course
from fuskar.utils.camera import video_stream
from fuskar.serializers import StudentSerializer, ImageSerializer, CourseSerializer, StudentCourseSerializer
from rest_framework.decorators import action
from rest_framework.response import Response

class ImageViewSet(viewsets.ModelViewSet):
    """
    Viewset for handling image queries 
    """
    serializer_class = ImageSerializer
    queryset = Image.objects.all()

class CourseViewSet(viewsets.ModelViewSet):
    """
   Viewset for handling course queries 
    """
    serializer_class = CourseSerializer
    queryset = Course.objects.all()

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
                response = Response()
                response.status_code =  400
                response['detail'] = "No Image attached"
                return response
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
            response = Response()
            response.status_code =  400
            try:
                course_no = int(request.data['course'])
                course = Course.objects.get(id=course_no)
                if course not in queryset.all():
                    queryset.add(course)
                    serializer = self.course_serializer(course)
                    return Response(serializer.data)
                else:
                    return Response({'detail': 'Student already takes this course'})
            except KeyError:
                response['detail'] = "No course_no attached"
                return response
            except ObjectDoesNotExist:
                response['detail'] = "Course Number does not exist"
                return response
