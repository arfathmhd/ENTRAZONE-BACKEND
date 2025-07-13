from rest_framework import serializers
from dashboard.models import Lesson, Folder

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'lesson_name', 'image', 'description', 'is_free']

class FolderSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)  

    class Meta:
        model = Folder
        fields = ['id', 'title', 'name', 'lessons']

class FullLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'lesson_name', 'image', 'description']


class NestedFolderSerializer(serializers.ModelSerializer):
    sub_folders = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Folder
        fields = ['id', 'title', 'name', 'lessons', 'sub_folders']

    def get_sub_folders(self, obj):
        # Fetch subfolders that are not deleted
        sub_folders = Folder.objects.filter(parent_folder=obj, is_deleted=False).order_by('order')
        return NestedFolderSerializer(sub_folders, many=True).data
