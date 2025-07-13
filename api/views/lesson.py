"""API views for lesson-related operations."""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from dashboard.models import Chapter, StudentProgress
from api.services.lesson_service import LessonService

# Setup logger
logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lesson_list(request):
    """
    Retrieve a hierarchical list of lessons, folders, and exams for a chapter.
    
    This endpoint returns a complete structure of educational content including:
    - Top-level folders with their lessons and subfolders
    - Direct lessons (not in any folder)
    - Chapter-level exams
    
    Each content item includes its metadata and attempt status for the current user.
    
    Args:
        request: HTTP request object containing chapter_id in query params
        
    Returns:
        Response with success/error status and data payload
    """
    # Get chapter_id from query params for GET request
    chapter_id = request.query_params.get('chapter_id') or request.data.get('chapter_id')

    if not chapter_id:
        return Response(
            {"status": "error", "message": "Chapter ID is required"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Use the service layer to get all chapter content
        response_data = LessonService.get_chapter_content(chapter_id, request.user)
        
        if response_data is None:
            return Response(
                {"status": "error", "message": "Chapter not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        return Response(
            {"status": "success", "data": response_data}, 
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error in lesson_list view: {str(e)}")
        return Response(
            {"status": "error", "message": "An error occurred while fetching lessons"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
