from rest_framework import serializers
from dashboard.models import Chapter  

class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ['id', 'subject', 'chapter_name', 'image', 'description']