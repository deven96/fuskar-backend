from rest_framework import serializers
from fuskar.models import Image, Student, Course, Lecture
import face_recognition


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = "__all__"


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = "__all__"

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = "__all__"

class StudentCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        exclude = ['registered_students', ]

class CourseLectureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lecture
        exclude = ['course', ]

class LectureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lecture
        fields = "__all__"