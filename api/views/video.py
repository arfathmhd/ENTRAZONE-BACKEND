from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from dashboard.models import Video, VideoPause, VideoRating

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def video_pause_resume(request):
    user = request.user
    video_id = request.data.get("video_id")
    minutes_watched = request.data.get("minutes_watched")
    total_duration = request.data.get("total_duration")
    if not video_id or not minutes_watched or not total_duration:
        return Response({
            "status": "error",
            "message": "All fields are required"
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        video = Video.objects.get(id=video_id)
        if not video:
            return Response({
                "status": "error",
                "message": "Video not found"
            }, status=status.HTTP_404_NOT_FOUND)
        progress, created = VideoPause.objects.get_or_create(user=user, video=video)

        # Update the minutes watched
        progress.minutes_watched = minutes_watched
        progress.total_duration = total_duration
        progress.save()

        return Response({
            "status": "success",
            "message": "Video progress updated successfully",
            "minutes_watched": progress.minutes_watched,
            "total_duration": progress.total_duration,
        }, status=status.HTTP_200_OK)

    except Video.DoesNotExist:
        return Response({
            "status": "error",
            "message": "Video not found"
        }, status=status.HTTP_404_NOT_FOUND)


class VideoRatingView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Add or update a rating for a video"""
        user = request.user
        video_id = request.data.get("video_id")
        rating = request.data.get("rating")
        comment = request.data.get("comment", "")
        
        # Validate required fields
        if not video_id or not rating:
            return Response({
                "status": "error",
                "message": "Video ID and rating are required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate rating value
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                return Response({
                    "status": "error",
                    "message": "Rating must be between 1 and 5"
                }, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({
                "status": "error",
                "message": "Rating must be a valid integer"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Check if video exists
            video = Video.objects.get(id=video_id)
            
            # Create or update the rating
            video_rating, created = VideoRating.objects.update_or_create(
                student=user,
                video=video,
                defaults={
                    'rating': rating,
                    'comment': comment
                }
            )
            
            return Response({
                "status": "success",
                "message": "Video rated successfully",
                "data": {
                    "rating": video_rating.rating,
                    "comment": video_rating.comment,
                    "video_title": video.title
                }
            }, status=status.HTTP_200_OK)
            
        except Video.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Video not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """Get ratings for a video"""
        from api.serializers.video import VideoRatingSerializer
        
        video_id = request.query_params.get("video_id")
        
        if not video_id:
            return Response({
                "status": "error",
                "message": "Video ID is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Check if video exists
            video = Video.objects.get(id=video_id)
            
            # Get all ratings for the video (limit to 10 most recent)
            ratings = VideoRating.objects.filter(video=video).order_by('-created_at')
            
            serializer = VideoRatingSerializer(ratings, many=True)
            
            return Response({
                "status": "success",
                "data": {
                    "video_title": video.title,
                    "video_id": video.id,
                    "ratings": serializer.data
                }
            }, status=status.HTTP_200_OK)
            
        except Video.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Video not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
