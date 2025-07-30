from dashboard.views.imports import *   
from decimal import Decimal
from datetime import datetime, timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Max
from django.core.exceptions import ObjectDoesNotExist
from api.serializers.lesson import NestedFolderSerializer, LessonSerializer, FolderSerializer
from dashboard.models import Folder, Lesson, Video, PDFNote, Exam, Question, VideoPause

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def folder_detail(request):
    folder_id = request.GET.get("folder_id")
    # Get query parameters for sorting and filtering
    sort_option = request.query_params.get('sort')
    start_date = request.query_params.get('start_date', None)
    end_date = request.query_params.get('end_date', None)
    
    # Process date parameters
    if start_date and start_date.lower() != 'null':
        start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y-%m-%d")
    else:
        start_date = None

    if end_date and end_date.lower() != 'null':
        end_date = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        end_date = None
    
    try:
        folder = Folder.objects.get(id=folder_id, is_deleted=False)
    except Folder.DoesNotExist:
        return Response({"error": "Folder not found"}, status=status.HTTP_404_NOT_FOUND)
    
    # Get subfolders
    subfolders = Folder.objects.filter(parent_folder_id=folder_id, is_deleted=False).order_by('order')
    
    # Get lessons with filtering and sorting
    lessons = Lesson.objects.filter(folder=folder_id, is_deleted=False)
    
    # Apply date filtering if provided
    if start_date and end_date:
        lessons = lessons.filter(created__range=[start_date, end_date])
    
    # Apply sorting
    if sort_option == 'name_ascending':
        lessons = lessons.order_by('lesson_name')
    elif sort_option == 'name_descending':
        lessons = lessons.order_by('-lesson_name')
    else:
        lessons = lessons.order_by('-order')  # Default sorting
    
    # Get exams related to this folder
    exams = Exam.objects.filter(folder=folder_id, is_deleted=False)
    
    # Serialize the folder details with more comprehensive information
    folder_data = {
        'id': folder.id,
        'title': folder.title,
        'name': folder.name,
        'created': folder.created,
    }
    
    # Create a list to store enhanced lesson data
    enhanced_lessons = []
    
    # Process each lesson to include videos and PDF notes
    for lesson in lessons:
        # Start with the basic lesson data from serializer
        lesson_data = LessonSerializer(lesson).data
        
        # Add videos if available
        try:
            videos_data = []
            videos = lesson.videos.filter(is_deleted=False)
            for video in videos:
                video_url = video.url.split('=')[-1] if 'www.youtube.com' in video.url else video.url
                # Get video progress for current user if available
                video_progress = VideoPause.objects.filter(user=request.user, video=video, is_deleted=False).first()
                
                video_info = {
                    'id': video.id,
                    'title': video.title,
                    'type': 'video',
                    'url': video_url,
                    "m3u8": video.m3u8 if video.m3u8 else "",
                    "tp_stream": video.tp_stream if video.tp_stream else "",
                    'is_downloadable': video.is_downloadable,
                    'is_free': video.is_free,
                    'minutes_watched': video_progress.minutes_watched if video_progress else "00:00:00",
                    'total_duration': video_progress.total_duration if video_progress else "00:00:00"
                }
                videos_data.append(video_info)
            lesson_data['videos'] = videos_data
        except Exception as e:
            lesson_data['videos'] = []
        
        # Add PDF notes if available
        try:
            pdf_notes_data = []
            if hasattr(lesson, 'pdf_notes'):
                pdf_notes = lesson.pdf_notes.filter(is_deleted=False)
                for pdf_note in pdf_notes:
                    pdf_note_info = {
                        'id': pdf_note.id,
                        'title': pdf_note.title,
                        'type': 'pdf',
                        'file': pdf_note.file.url if pdf_note.file else None,
                        'is_downloadable': pdf_note.is_downloadable,
                        'is_free': pdf_note.is_free
                    }
                    pdf_notes_data.append(pdf_note_info)
            lesson_data['pdf_notes'] = pdf_notes_data
        except Exception as e:
            lesson_data['pdf_notes'] = []
        
        # Add the enhanced lesson to our list
        enhanced_lessons.append(lesson_data)
    
    # Add the enhanced lessons to folder data
    folder_data['lessons'] = enhanced_lessons
    
    # Serialize subfolders
    subfolder_serializer = FolderSerializer(subfolders, many=True)
    exam_attempted = StudentProgress.objects.filter(student=request.user,is_deleted=False).prefetch_related('exam')
    # Process exams
    exams_data = []
    for exam in exams:
        # Get question count for this exam
        question_count = Question.objects.filter(exam=exam, is_deleted=False).count()
        
        exam_info = {
            'id': exam.id,
            'title': exam.title,
            'exam_type': exam.exam_type,
            'exam_start_date': exam.start_date,
            'exam_end_date': exam.end_date,
            'duration': str(exam.duration) if exam.duration else None,
            'is_free': exam.is_free,
            'created': exam.created,
            'question_count': question_count,
            'number_of_attempt': exam.number_of_attempt,
            'attempted_count': exam_attempted.filter(exam=exam).count()
        }
        exams_data.append(exam_info)
    
    # Create comprehensive response structure
    response_data = {
        'folder': folder_data,
        'subfolders': subfolder_serializer.data,
        'lesson_count': lessons.count(),
        'subfolder_count': subfolders.count(),
        'exams': exams_data,
        'exam_count': exams.count(),
        'current_sort': sort_option,
    }
    
    return Response({
        'status': 'success',
        'data': response_data
    })
