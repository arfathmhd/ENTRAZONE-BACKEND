from dashboard.views.imports import *
from api.serializers.course  import CourseSerializer
from dashboard.models import Course, Subject, Chapter, Folder, Lesson, Batch, Exam, Question
from django.db.models import Count


@api_view(["GET"])
@permission_classes([IsAuthenticated]) 
def course_list(request):

    courses = Course.objects.filter(is_deleted=False)

    serializer = CourseSerializer(courses, many=True)

    response = {
        "status": "success",
        "message": "Courses retrieved successfully",
        "courses": serializer.data,  
    }
    
    return Response(response, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated]) 
def course_select(request):
    user = request.user
    course_id = request.GET.get("course_id")  
    print(course_id)
    course = Course.objects.filter(id=course_id).first()
    if not course:
        return Response({"status": "error", "message": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

    customuser = CustomUser.objects.filter(id=user.id, is_deleted=False).first()
    if not customuser:
        return Response({"status": "error", "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    customuser.default_course = course 
    customuser.save()

    return Response({"status": "success", "message": "Course selected successfully"}, status=status.HTTP_200_OK)




@api_view(['GET'])
@permission_classes([IsAuthenticated])  
def subscribed_course(request):
    user = request.user
    
    subscriptions = Subscription.objects.filter(user=user, is_deleted=False)
    # if not subscriptions:
    #     return Response({"status": "error", "message": "No course subscribed"}, status=status.HTTP_400_BAD_REQUEST)
    
    subscribed_batches = []
    subscribed_course_ids = set() 
    
    for subscription in subscriptions:
        for batch in subscription.batch.all(): 
            course = batch.course
            subscribed_course_ids.add(course.id) 
            subscribed_batches.append({
                'course_id': course.id,
                'course_name': course.course_name,
                 'course_image': request.build_absolute_uri(course.image.url) if course.image else "",
                'is_free': True
            })

    if not subscribed_batches and user.default_course:
        subscribed_batches.append({
            'course_id': user.default_course.id,
            'course_name': user.default_course.course_name,
            'course_image': request.build_absolute_uri(user.default_course.image.url) if user.default_course.image else "",
            'is_default': True,
            'is_free': True
        })
        subscribed_course_ids.add(user.default_course.id)

    
    if not subscribed_batches and user.default_course:
        return Response({"status": "error", "message": "No course subscribed and No default course"}, status=status.HTTP_400_BAD_REQUEST)
    # if not subscribed_batches:
        subscribed_batches = [] 

    unsubscribed_courses = Course.objects.filter(is_deleted=False).exclude(id__in=subscribed_course_ids)
    
    unsubscribed_courses_list = []
    for course in unsubscribed_courses:
        unsubscribed_courses_list.append({
            'course_id': course.id,
            'course_name': course.course_name,
             'course_image': request.build_absolute_uri(course.image.url) if course.image else "",
        })

    response = {
        "status": "success",
        "message": "Courses retrieved successfully",
        "subscribed_courses": subscribed_batches,  
        "unsubscribed_courses": unsubscribed_courses_list 
    }

    return Response(response, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def course_subjects(request):
    course_id = request.data.get('course_id')
    
    try:
        if course_id:
            try:
                course = Course.objects.get(id=course_id, is_deleted=False) 
            except Course.DoesNotExist:
                if request.user.default_course:
                    course = request.user.default_course
                else:
                    return Response({
                        "status": "error",
                        "message": "Course not found"
                    }, status=status.HTTP_404_NOT_FOUND)
        elif request.user.default_course:
            course = request.user.default_course
        else:
            return Response({
                "status": "error", 
                "message": "No course specified and no default course found"
            }, status=status.HTTP_404_NOT_FOUND)

        subjects = Subject.objects.filter(course=course, is_deleted=False).order_by('order')
        subject_count = subjects.count()
        subject_data = []
        
        # Get exams for this course directly
        course_exams = Exam.objects.filter(course=course, is_deleted=False)
        course_exam_count = course_exams.count()
        exam_attempted = StudentProgress.objects.filter(student=request.user,is_deleted=False).prefetch_related('exam')
        # Prepare course exam data
        course_exam_data = []
        for exam in course_exams:
            # Get question count for this exam
            question_count = Question.objects.filter(exam=exam, is_deleted=False).count()
            
            exam_info = {
                'exam_id': exam.id,
                'title': exam.title,
                'exam_type': exam.exam_type if exam.exam_type else "",
                'exam_start_date': exam.start_date if exam.start_date else "",
                'exam_end_date': exam.end_date if exam.end_date else "",
                'duration': str(exam.duration) if exam.duration else None,
                'is_free': exam.is_free,
                'created': exam.created,
                'question_count': question_count,
                'number_of_attempt': exam.number_of_attempt,
                'attempted_count': exam_attempted.filter(exam=exam).count()
            }
            course_exam_data.append(exam_info)
        
        for subject in subjects:
            chapters = Chapter.objects.filter(subject=subject, is_deleted=False).order_by('order')
            chapter_count = chapters.count()
            
            # Get exams for this subject
            subject_exams = Exam.objects.filter(subject=subject, is_deleted=False)
            exam_count = subject_exams.count()
            
            # Prepare exam data
            exam_data = []
            for exam in subject_exams:
                # Get question count for this exam
                question_count = Question.objects.filter(exam=exam, is_deleted=False).count()
                
                exam_info = {
                    'exam_id': exam.id,
                    'title': exam.title,
                    'exam_type': exam.exam_type if exam.exam_type else "",
                    'exam_start_date': exam.start_date if exam.start_date else "",
                    'exam_end_date': exam.end_date if exam.end_date else "",
                    'duration': str(exam.duration) if exam.duration else None,
                    'is_free': exam.is_free,
                    'created': exam.created,
                    'question_count': question_count,
                    'number_of_attempt': exam.number_of_attempt,
                    'attempted_count': exam_attempted.filter(exam=exam).count()
                }
                exam_data.append(exam_info)
           
            subject_data.append({
                'subject_id': subject.id,
                'subject_name': subject.subject_name,
                'subject_description': subject.description,
                'subject_image': request.build_absolute_uri(subject.image.url) if subject.image else None,
                'is_free': subject.is_free,
                # 'chapters': chapter_data,
                'chapter_count': chapter_count,
                # 'exam_count': exam_count,
                # 'exams': exam_data
            })

        response = {
            "status": "success",
            "message": "Course details retrieved successfully",
            "course_name": course.course_name,
            # "course_description": course.description,
            "subject_count": subject_count,
            # "course_image": request.build_absolute_uri(course.image.url) if course.image else None,
            "subjects": subject_data,
            "exam_count": course_exam_count,
            "exams": course_exam_data
        }

        return Response(response, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
