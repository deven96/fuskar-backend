from rest_framework import serializers
from fuskar.models import Image, Student, Course, Lecture, Emotion


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = '__all__'

class EmotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Emotion
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
        exclude = ['course', 'lock']

class CourseEmotionSerializer(serializers.ModelSerializer):
    emotions = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='emotion'
    )
    class Meta:
        model = Lecture
        fields = ['emotions', ]

class LectureSerializer(serializers.ModelSerializer):
    emotions = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='emotion'
    )
    class Meta:
        model = Lecture
        exclude = ['lock', ]