# app_name/serializers.py

from rest_framework import serializers
from dashboard.models import Course


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'course_name','image']
