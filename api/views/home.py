from dashboard.views.imports import *
from urllib.parse import urlparse, parse_qs

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from dashboard.models import (
    Subscription, 
    Batch, 
    Course, 
    Banner, 
    Notification, 
    StudentNotification, 
    BatchMentor
)
from api.services.home_service import HomeService
import logging

# Configure logger
logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])  
def home(request):
    """
    API endpoint to retrieve home page data for authenticated users.
    
    Returns:
        Response: JSON response containing user's courses, notifications, and banners.
    """
    try:
        user = request.user
        response_data = HomeService.get_home_data(user)
        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in home view: {str(e)}", exc_info=True)
        return Response(
            {
                "status": "error",
                "message": "An error occurred while retrieving home data."
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def update_default_course(request):
    user = request.user
    course_id = request.data.get('course_id')

    try:
        course = Course.objects.get(id=course_id, is_deleted=False)
        user.default_course = course
        user.save()

        return Response({
            "status": "success",
            "message": "Default course updated successfully",
            "course_id": course.id,
            "course_name": course.course_name
        }, status=status.HTTP_200_OK)

    except Course.DoesNotExist:
        return Response({
            "status": "error", 
            "message": "Course not found"
        }, status=status.HTTP_404_NOT_FOUND)
    



@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def search_courses(request):
    search_query = request.GET.get('search', '') 
    if not search_query:
        return Response({
            "status": "error",
            "message": "Search query is required."
        }, status=status.HTTP_400_BAD_REQUEST)

    courses = Course.objects.filter(
        Q(course_name__icontains=search_query),
        is_deleted=False
    ).values(
        'id', 'course_name', 'description', 'image', 'duration', 'number_of_lessons'
    )

    return Response({
        "status": "success",
        "message": "Courses retrieved successfully",
        "data": list(courses)
    }, status=status.HTTP_200_OK)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def currentaffairs(request):
    try:
        currentaffairs = CurrentAffairs.objects.filter(is_deleted=False).order_by('-created')
        

        data = []
        for affair in currentaffairs:
            video_data = {}
            pdf_data = {}

            try:
                video = Video.objects.filter(currentaffair=affair, is_deleted=False).first()
                if video:
                    video_data = {
                        'video_id': video.id,
                        'video_title': video.title if video.title else "",
                        'url': parse_qs(urlparse(video.url).query).get('v', [''])[0] if "youtube.com" in video.url else video.url,
                        'm3u8': video.m3u8 if video.m3u8 else "",
                        'tp_stream': video.tp_stream if video.tp_stream else "",
                    }
            except Exception as e:
                video_data = {}  

            try:
                pdf_note = PDFNote.objects.filter(currentaffair=affair, is_deleted=False).first()
                if pdf_note:
                    pdf_data = {
                        'pdf_id': pdf_note.id,
                        'pdf_title': pdf_note.title if pdf_note.title else "",
                        'file': pdf_note.file.url if pdf_note.file else "",
                    }
            except Exception as e:
                pdf_data = {} 
            
            current_affairs_exams = Exam.objects.filter(current_affair=affair, is_deleted=False)
            
            exam_data = []
            for exam in current_affairs_exams:
                exam_data.append({
                    'exam_id': exam.id,
                    'exam_title': exam.title,
                    'exam_type': exam.exam_type,
                    'exam_start_date': exam.start_date,
                    'exam_end_date': exam.end_date,
                    'duration': str(exam.duration) if exam.duration else None,
                    'is_free': exam.is_free,
                    'created': exam.created,
                })

            data.append({
                'current_affair': { 
                    'id': affair.id,
                    'title': affair.title,
                    'image': affair.image.url if affair.image else "",
                    'created': affair.created.strftime('%d-%m-%Y') if affair.created else "",
                    **video_data, 
                    **pdf_data, 
                    'exams': exam_data,
                    }
            })

        return Response({
            "status": "success",
            "message": "Data retrieved successfully",
            "data": data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status": "error",
            "message": "An error occurred while retrieving data",
            "data": [{
                'current_affair': {
                    'id': None,
                    'title': "",
                    'image': "",
                    'created': "",
                    'exams': [],
                    'video_id': None,
                    'video_title': "",
                    'url': "",
                    'm3u8': "",
                    'pdf_id': None,
                    'pdf_title': "",
                    'file': "",
                }
            }]
        }, status=status.HTTP_400_BAD_REQUEST)
