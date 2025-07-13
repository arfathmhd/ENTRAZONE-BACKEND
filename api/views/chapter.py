from dashboard.views.imports import *
from urllib.parse import urlparse, parse_qs
from django.conf import settings
from dashboard.models import Subject, Chapter, Folder, Lesson, Video, PDFNote, Exam, Question, VideoPause
from django.db.models import Count


@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def chapter_list(request):
    subject_id = request.data.get('subject_id')
    
    if not subject_id:
        return Response({"status": "error", "message": "Subject ID is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        subject = Subject.objects.get(id=subject_id, is_deleted=False)
        subject_name = subject.subject_name
    except Subject.DoesNotExist:
        return Response({
            "status": "success", 
              "type":"chapter",
            "subject_name": None, 
            "chapter_count": 0, 
            "data": []
        }, status=status.HTTP_200_OK)

    chapters = Chapter.objects.filter(is_deleted=False, subject_id=subject_id).order_by('order')
    exams = Exam.objects.filter(is_deleted=False, subject_id=subject_id)
    total_chapter_count = chapters.count()
    total_exam_count = exams.count()

    if chapters.exists():
        chapter_list_with_details = []

        for chapter in chapters:
            #find the count of folders in the chapter
            folder_count = Folder.objects.filter(is_deleted=False, chapter=chapter, parent_folder__isnull=True).count()

            # Add chapter with folders and lessons without folders
            chapter_lessons = Lesson.objects.filter(is_deleted=False, chapter=chapter, folder__isnull=True).order_by('order')
            chapter_list_with_details.append({
                "chapter_id": chapter.id if chapter.id else "",
                "chapter_name": chapter.chapter_name if chapter.chapter_name else "",
                "chapter_image": chapter.image.url if chapter.image else "",
                "description": chapter.description if chapter.description else "",
                "folders_count": folder_count,
                "lessons_count": chapter_lessons.count(),
                "is_free": chapter.is_free,
            })
        exam_list = []
        if exams.count() > 0:
            for exam in exams:
                # Get question count for this exam
                question_count = Question.objects.filter(exam=exam, is_deleted=False).count()
                attempt_count = StudentProgress.objects.filter(exam=exam, student=request.user, is_deleted=False).count()
                exam_list.append({
                    "exam_id": exam.id,
                    "title": exam.title,
                    "exam_type": exam.exam_type,
                    "exam_start_date": exam.start_date,
                    "exam_end_date": exam.end_date,
                    "question_count": question_count,
                    "duration": str(exam.duration) if exam.duration else None,
                    "is_free": exam.is_free,
                    "created": exam.created,
                    "number_of_attempt": exam.number_of_attempt,
                    "attempted_count": attempt_count
                })

        return Response({
            "status": "success",
            "type":"chapter",
            "subject_name": subject_name if subject_name else "",
            "chapter_count": total_chapter_count if total_chapter_count else 0,
            "exam_count": total_exam_count if total_exam_count else 0,
            "chapters": chapter_list_with_details,
            "exams": exam_list
        }, status=status.HTTP_200_OK)
    
    else:
        return Response({
            "status": "success",
            "message": "No chapters found for this subject",
            "subject_name": "",
            "chapter_count": 0,
            "chapters": []
        }, status=status.HTTP_200_OK)
    



@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated]) 
def tpstream_token(request):
    try:
        asset_id = request.data.get('asset_id')
        if not asset_id:
            return Response({
                "status": "error",
                "message": "Asset ID is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        
        url = f"{settings.TP_STREAM_URL}{settings.ORG_ID}/assets/{asset_id}/access_tokens/"

        headers = {
           "Authorization": f"Token {settings.API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "expires_after_first_usage": True
        }

        response = requests.post(url, json=payload, headers=headers)
      
        
        if response.status_code in [200, 201]:
            response_data = response.json()
            structured_data = {
                "playback_url": response_data.get("playback_url"),
                "expires_after_first_usage": response_data.get("expires_after_first_usage"),
                "token_code": response_data.get("code"),
                "status": response_data.get("status"),
                "valid_until": response_data.get("valid_until"),
                "annotations": response_data.get("annotations", [])
            }
            return Response({
                "status": "success",
                "data": structured_data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "error",
                "message": "TPStream API returned an error",
                "details": response.json()
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
