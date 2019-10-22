from rest_framework import serializers
from fuskar.models import Image, Student, Course

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