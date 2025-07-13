from rest_framework import serializers
from dashboard.models import VideoRating, CustomUser, Video


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'name']


class VideoRatingSerializer(serializers.ModelSerializer):
    student_details = serializers.SerializerMethodField()
    video_details = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoRating
        fields = ['id', 'video', 'rating', 'comment', 'created_at', 'student_details', 'video_details']
    
    def get_student_details(self, obj):
        return {
            'id': obj.student.id,
            'username': obj.student.username,
            'name': obj.student.name or obj.student.username
        }
    
    def get_video_details(self, obj):
        return {
            'id': obj.video.id,
            'title': obj.video.title
        }