from dashboard.views.imports  import *
from api.serializers.subject import SubjectSerializer




@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def subject_list(request):
    course_id = request.data.get('course_id')
    
    if not course_id:
        return Response({"status": "error", "message": "Course ID is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        course = Course.objects.get(id=course_id, is_deleted=False)
        course_name = course.course_name
    except Course.DoesNotExist:
        return Response({"status": "error", "message": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

    subjects = Subject.objects.filter(is_deleted=False, course_id=course_id).order_by('order')
    exams= Exam.objects.filter(is_deleted=False, course_id=course_id)
    
    subject_count = subjects.count()  
    
    if subject_count > 0:
        subject_list = []

        for subject in subjects:
            subject_list.append({
                "subject_id": subject.id,
                "subject_name": subject.subject_name
            })
    if exams.count() > 0:
        exam_list = []
        for exam in exams:
            exam_list.append({
                "exam_id": exam.id,
                "exam_name": exam.title,
                "exam_type": exam.exam_type,
                "exam_start_date": exam.start_date,
                "exam_end_date": exam.end_date,
                "duration": str(exam.duration) if exam.duration else None,
                "is_free": exam.is_free,
                "created": exam.created,
            })

        return Response({
            "status": "success",
            "course_name": course_name,  
            "subject_count": subject_count,
            "exam_count": exams.count(),   
            "subjects": subject_list,
            "exams": exam_list  
        }, status=status.HTTP_200_OK)
    
    else:
        return Response({"status": "error", "message": "No subjects found for this course"}, status=status.HTTP_404_NOT_FOUND)