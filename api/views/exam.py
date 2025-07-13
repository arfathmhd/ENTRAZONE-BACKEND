from dashboard.views.imports import *   
from decimal import Decimal
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Max
from django.core.exceptions import ObjectDoesNotExist


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exam_list(request):
    user = request.user
    default_course = user.default_course
    
    if not default_course:
        return Response({
            "status": "error",
            "message": "No default course set for user",
            "data": []
        }, status=400)
    
    # Get all exams attempted by the user
    exam_attempts = StudentProgress.objects.filter(
        student=user,
        is_deleted=False
    ).values('exam').annotate(attempt_count=Count('exam'))
    
    # Create a dictionary for quick lookup of attempt counts
    attempt_counts = {item['exam']: item['attempt_count'] for item in exam_attempts}
    
    # Get all subjects in the default course
    subjects = Subject.objects.filter(
        course=default_course,
        is_deleted=False
    ).select_related('course').order_by('order')
    subject_ids = subjects.values_list('id', flat=True)
    
    # Get all chapters in these subjects
    chapters = Chapter.objects.filter(
        subject_id__in=subject_ids,
        is_deleted=False
    ).select_related('subject').order_by('order')
    chapter_ids = chapters.values_list('id', flat=True)
    
    # Get all folders in these chapters
    folders = Folder.objects.filter(
        chapter_id__in=chapter_ids,
        is_deleted=False
    ).select_related('chapter').order_by('order')
    
    # Build a dictionary of folders by parent_folder_id for quick lookup
    folder_dict = {}
    folder_by_parent = {}
    for folder in folders:
        folder_dict[folder.id] = folder
        if folder.parent_folder_id not in folder_by_parent:
            folder_by_parent[folder.parent_folder_id] = []
        folder_by_parent[folder.parent_folder_id].append(folder)
    
    # Get all folder ids (including nested ones)
    folder_ids = folders.values_list('id', flat=True)
    
    # Get all lessons in these chapters and folders
    lessons = Lesson.objects.filter(
        Q(chapter_id__in=chapter_ids) | Q(folder_id__in=folder_ids),
        is_deleted=False
    ).select_related('chapter', 'folder').order_by('order')
    lesson_ids = lessons.values_list('id', flat=True)
    
    # Get all exams related to the course structure, including those directly linked to the course
    exams = Exam.objects.filter(
        Q(course=default_course) |
        Q(subject_id__in=subject_ids) |
        Q(chapter_id__in=chapter_ids) |
        Q(folder_id__in=folder_ids) |
        Q(lesson_id__in=lesson_ids),
        is_deleted=False
    ).select_related('course', 'subject', 'chapter', 'folder', 'lesson')
    
    # Get question counts for all exams in a single query
    question_counts = Question.objects.filter(
        exam__in=exams,
        is_deleted=False
    ).values('exam').annotate(count=Count('id'))
    
    # Create a dictionary for quick lookup of question counts
    question_count_dict = {item['exam']: item['count'] for item in question_counts}
    
    # Organize exams by their location in the hierarchy
    exams_by_course = []
    exams_by_subject = {}
    exams_by_chapter = {}
    exams_by_folder = {}
    exams_by_lesson = {}
    
    for exam in exams:
        # Skip exams where user has exhausted attempts
        if attempt_counts.get(exam.id, 0) >= exam.number_of_attempt:
            continue
            
        exam_data = _prepare_exam_data(exam, attempt_counts.get(exam.id, 0), 
                                      question_count_dict.get(exam.id, 0), request)
        
        # Exams directly linked to course
        if exam.course_id == default_course.id and not exam.subject_id and not exam.chapter_id and not exam.folder_id and not exam.lesson_id:
            exams_by_course.append(exam_data)
        # Exams linked to subject
        elif exam.subject_id and not exam.chapter_id and not exam.folder_id and not exam.lesson_id:
            if exam.subject_id not in exams_by_subject:
                exams_by_subject[exam.subject_id] = []
            exams_by_subject[exam.subject_id].append(exam_data)
        # Exams linked to chapter    
        elif exam.chapter_id and not exam.folder_id and not exam.lesson_id:
            if exam.chapter_id not in exams_by_chapter:
                exams_by_chapter[exam.chapter_id] = []
            exams_by_chapter[exam.chapter_id].append(exam_data)
        # Exams linked to folder    
        elif exam.folder_id and not exam.lesson_id:
            if exam.folder_id not in exams_by_folder:
                exams_by_folder[exam.folder_id] = []
            exams_by_folder[exam.folder_id].append(exam_data)
        # Exams linked to lesson    
        elif exam.lesson_id:
            if exam.lesson_id not in exams_by_lesson:
                exams_by_lesson[exam.lesson_id] = []
            exams_by_lesson[exam.lesson_id].append(exam_data)
    
    # Group lessons by chapter_id and folder_id
    lessons_by_chapter = {}
    lessons_by_folder = {}
    
    for lesson in lessons:
        lesson_data = {
            "lesson_id": lesson.id,
            "lesson_name": lesson.lesson_name,
            "lesson_image": request.build_absolute_uri(lesson.image.url) if lesson.image else "",
            "exams": exams_by_lesson.get(lesson.id, [])
        }
        
        # Add lesson to chapter
        if lesson.chapter_id:
            if lesson.chapter_id not in lessons_by_chapter:
                lessons_by_chapter[lesson.chapter_id] = []
            lessons_by_chapter[lesson.chapter_id].append(lesson_data)
            
        # Add lesson to folder
        if lesson.folder_id:
            if lesson.folder_id not in lessons_by_folder:
                lessons_by_folder[lesson.folder_id] = []
            lessons_by_folder[lesson.folder_id].append(lesson_data)
    
    # Build the response structure
    structured_data = {
        "course": {
            "course_id": default_course.id,
            "course_name": default_course.course_name,
            "course_image": request.build_absolute_uri(default_course.image.url) if default_course.image else "",
            "exams": exams_by_course
        },
        "subjects": []
    }
    
    for subject in subjects:
        subject_data = {
            "subject_id": subject.id,
            "subject_name": subject.subject_name,
            "subject_image": request.build_absolute_uri(subject.image.url) if subject.image else "",
            "exams": exams_by_subject.get(subject.id, []),
            "chapters": []
        }
        
        # Add chapters for this subject
        for chapter in [c for c in chapters if c.subject_id == subject.id]:
            chapter_data = {
                "chapter_id": chapter.id,
                "chapter_name": chapter.chapter_name,
                "chapter_image": request.build_absolute_uri(chapter.image.url) if chapter.image else "",
                "exams": exams_by_chapter.get(chapter.id, []),
                "lessons": lessons_by_chapter.get(chapter.id, []),
                "folders": []
            }
            
            # Add top-level folders for this chapter
            top_folders = folder_by_parent.get(None, [])
            top_folders = [f for f in top_folders if f.chapter_id == chapter.id]
            
            for folder in top_folders:
                folder_data = _build_folder_structure(
                    folder, 
                    folder_by_parent, 
                    lessons_by_folder, 
                    exams_by_folder
                )
                chapter_data["folders"].append(folder_data)
            
            subject_data["chapters"].append(chapter_data)
        
        structured_data["subjects"].append(subject_data)
    
    return Response({
        "status": "success",
        "message": "Exam data fetched successfully",
        "data": structured_data
    }, status=200)


def _build_folder_structure(folder, folder_by_parent, lessons_by_folder, exams_by_folder):
    """Build folder structure recursively using pre-fetched data"""
    folder_data = {
        "folder_id": folder.id,
        "folder_name": folder.title,
        "exams": exams_by_folder.get(folder.id, []),
        "lessons": lessons_by_folder.get(folder.id, []),
        "sub_folders": []
    }
    
    # Add sub-folders recursively
    sub_folders = folder_by_parent.get(folder.id, [])
    for sub_folder in sub_folders:
        sub_folder_data = _build_folder_structure(
            sub_folder, 
            folder_by_parent, 
            lessons_by_folder, 
            exams_by_folder
        )
        folder_data["sub_folders"].append(sub_folder_data)
    
    return folder_data


def _prepare_exam_data(exam, attempt_count, question_count, request):
    """Prepare exam data for response"""
    # Format duration
    exam_duration = exam.duration
    if exam_duration:
        total_minutes = (exam_duration.hour * 60) + exam_duration.minute
        formatted_duration = f"{total_minutes} mins" if total_minutes > 0 else "0 min"
    else:
        formatted_duration = "0 min"
    
    # Prepare exam data
    return {
        "exam_id": exam.id,
        "exam_title": exam.title if exam.title else "",
        "duration": formatted_duration,
        "exam_is_free": exam.is_free,
        "total_questions": question_count,
        "number_of_attempt": exam.number_of_attempt,
        "attempted_count": attempt_count,
        "image": request.build_absolute_uri(exam.image.url) if exam.image else ""
    }




# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def course_exam_list(request):
#     course_id = request.data.get("course_id")
#     course = Course.objects.get(id=course_id, is_deleted=False)
#     subjects = Subject.objects.filter(course=course, is_deleted=False).values_list("id")
#     exams = Exam.objects.filter(subject__in=subjects, is_deleted=False)
#     question_count = Question.objects.filter(exam__in=exams, is_deleted=False).count()
#     data = []
#     for exam in exams:
#         subject = exam.subject
#         exam_data = {
#             "exam_id": exam.id,
#             "exam_title": exam.title,
#             "duration":exam.duration ,
#             "question_count": question_count,
#             "is_free": exam.is_free,
#             # "subject_name": subject.subject_name,
#             # "subject_id": subject.id
#         }
#         data.append(exam_data)

#     return Response({
#         "status": "success",
#         "message": "Subject exams fetched successfully",
#         "data": data
#     }, status=200)






import re
from django.db.models import Sum

def extract_latex(raw_string):
    # Match inline LaTeX (within \(...\))
    latex_pattern = re.compile(r'\\\((.*?)\\\)')  
    
    # Search for the LaTeX pattern in the string
    match = latex_pattern.search(raw_string)
    
    if match:
        # If LaTeX is found, format it with block math mode \[...\]
        latex_content = match.group(1)  # Extract the content inside \(...\)
        formatted_latex = r"""\[{}]""".format(latex_content)
        return formatted_latex  # Return the formatted LaTeX as a raw string
    return raw_string  # Return the original string if no LaTeX is found



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exam_question(request):
    exam_id = request.data.get('exam_id')
    
    try:
        exam = Exam.objects.get(id=exam_id, is_deleted=False)
        if exam is None:
            return Response({
                "status": "error",
                "message": "Exam not found",
            }, status=status.HTTP_404_NOT_FOUND)
        questions = Question.objects.filter(exam=exam, is_deleted=False)
        question_count = questions.count()
        check_number_of_attempt = StudentProgress.objects.filter(exam=exam, student=request.user).count()
        
        # Convert QuerySet to list for potential shuffling
        questions_list = list(questions)
        
        # If shuffle is enabled, randomize the questions order
        if exam.is_shuffle:
            import random
            random.shuffle(questions_list)
            
        response_questions = []
        for question in questions_list:
            cleaned_description = extract_latex(question.question_description)

            processed_options = []
            for option in question.options:
                if isinstance(option, dict):
                    if 'id' in option:
                        processed_option = option  
                    else:
                        processed_option = {key: value for key, value in option.items() if key != 'id'}  
                    processed_options.append(processed_option)
                else:
                    processed_options.append(option)

            response_questions.append({
                "question_id": question.id,
                "question_description": cleaned_description,
                "options": processed_options,
                "right_answers": question.right_answers,
                "mark": question.mark if question.mark else 0, 
                "negative_mark": question.negative_mark if question.negative_mark else 0,
                "explanation_description": question.explanation_description if question.explanation_description else "",
                "explanation_image": question.explanation_image.url if question.explanation_image else "",
            })

        response = {
            "status": "success",
            "message": "Questions retrieved successfully",
            "duration":exam.duration,
            "question_count":question_count,
            "number_of_attempt":exam.number_of_attempt,
            "attempted_count":check_number_of_attempt,
            "questions": response_questions,
        }

        return Response(response, status=status.HTTP_200_OK)

    except Exam.DoesNotExist:
        return Response({
            "status": "error",
            "message": "exam not found",
        }, status=status.HTTP_404_NOT_FOUND)
    








@api_view(['POST'])
@permission_classes([IsAuthenticated])
def exam_answer_submission(request):

    questions = request.data.get('questions', [])
    exam_id = request.data.get('exam_id')
    total_time_taken = request.data.get('total_time_taken')
    student = request.user  

    if not questions or exam_id is None:
        return Response({"status": "error", "message": "Questions data and exam_id are required."}, status=status.HTTP_400_BAD_REQUEST)

    question_ids = [q.get('question_id') for q in questions]
    duplicate_question_ids = [q_id for q_id in question_ids if question_ids.count(q_id) > 1]
    
    if duplicate_question_ids:
        return Response({
            "status": "error",
            "message": f"Duplicate question IDs found: {set(duplicate_question_ids)}. Each question must be unique."
        }, status=status.HTTP_400_BAD_REQUEST)

    # if StudentProgress.objects.filter(student=student, exam_id=exam_id).exists():
    #     return Response({
    #         "status": "error",
    #         "message": "You have already submitted this exam. You cannot submit again."
    #     }, status=status.HTTP_400_BAD_REQUEST)

    total_time = timedelta()  
    total_marks = 0
    try:
        exam_object = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        return Response({
            "status": "error",
            "message": "Exam not found.",
        }, status=status.HTTP_404_NOT_FOUND)
    check_number_of_attempt = StudentProgress.objects.filter(exam=exam_object, student=student).count()
    if check_number_of_attempt >= exam_object.number_of_attempt:
        return Response({
            "status": "error",
            "message": "Attempt limit exceeded."
        }, status=status.HTTP_400_BAD_REQUEST)

    level_total_marks = 0
    for question in Question.objects.filter(exam=exam_object, is_deleted=False):
        question_mark = question.mark if question.mark is not None else 0  # Ensure default is 0 if mark is None
        level_total_marks += question_mark

    # Create the initial StudentProgress instance
    student_progress = StudentProgress.objects.create(
        student=student,
        exam=exam_object,
        marks_obtained=0,  # start with 0 marks
        total_marks=level_total_marks,  
        passed=False,  
    )

    for question in questions:
        question_id = question.get('question_id')
        selected_answer = question.get('selected_answer')
        # time_taken = question.get('time_taken')

        if question_id is None or selected_answer is None:
            return Response({"status": "error", "message": f"Missing data for question {question_id}"}, status=status.HTTP_400_BAD_REQUEST)

        # try:
        #     time_parts = total_time_taken.split(":")
        #     if len(time_parts) != 2:
        #         return Response({"status": "error", "message": "Invalid time format. Use MM:SS."}, status=status.HTTP_400_BAD_REQUEST)

        #     minutes, seconds = int(time_parts[0]), int(time_parts[1])
        #     time_delta = timedelta(minutes=minutes, seconds=seconds)
        #     total_time += time_delta
        # except ValueError:
        #     return Response({"status": "error", "message": "Invalid time format."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            question_obj = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return Response({"status": "error", "message": f"Question with ID {question_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        # Return error if selected_answer is not provided
        if selected_answer is None:
            return Response({"status": "error", "message": "Selected answer is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Handle database right_answers
        correct_answer_data = question_obj.right_answers if question_obj.right_answers else []
        has_correct_answer = isinstance(correct_answer_data, list) and correct_answer_data
        
        # If question has no correct answer in DB, treat as unanswered
        if not has_correct_answer:
            is_correct = False
            answered = False  # Mark as unanswered if question has no correct answer
            correct_answer_id = 0
        else:
            correct_answer_id = correct_answer_data[0].get('id', 0)
            is_correct = selected_answer == correct_answer_id
            answered = selected_answer != 0  # If answer is non-zero, question is answered

        marks = 0
        negative_marks = 0
        
        if answered:  # Question was answered
            if is_correct:  # Correct answer
                marks = question_obj.mark if question_obj.mark is not None else 0
            else:  # Wrong answer - apply negative marking
                if question_obj.negative_mark is not None and question_obj.negative_mark > 0:
                    negative_marks = question_obj.negative_mark
                    # Subtract negative marks from total
                    marks = -negative_marks

        student_progress_detail = StudentProgressDetail(
            student_progress=student_progress,  
            question=question_obj,
            selected_option=selected_answer,
            is_correct=is_correct,
            answered=answered,  
            marks_obtained=marks if is_correct else 0,
            negative_marks=negative_marks if not is_correct and answered else 0,  
        )
        student_progress_detail.save() 

        if answered:  # Update total marks for both correct and incorrect answers
            total_marks += marks


    # Update the total marks and pass/fail status
    student_progress.marks_obtained = total_marks
    student_progress.passed = total_marks >= student_progress.total_marks * 0.5 
    student_progress.save()  # Only save the updated marks and pass/fail status

    question_count = Question.objects.filter(exam=exam_object, is_deleted=False).count()
    correct_answer = StudentProgressDetail.objects.filter(student_progress=student_progress, is_correct=True, is_deleted=False).count()
    wrong_answer = StudentProgressDetail.objects.filter(student_progress=student_progress, selected_option__gt=0, is_correct=False, is_deleted=False).count()
   
    unanswered = StudentProgressDetail.objects.filter(
    student_progress=student_progress, 
    is_correct=False,
    answered=False,  # Answered is False
    is_deleted=False
    ).count()
    
    # Calculate total negative marks
    total_negative_marks = StudentProgressDetail.objects.filter(
        student_progress=student_progress,
        is_correct=False,
        answered=True,
        is_deleted=False
    ).aggregate(Sum('negative_marks'))['negative_marks__sum'] or 0

    if question_count > 0:
        level_percentage = (correct_answer / question_count) * 100
        level_percentage = round(level_percentage, 2)  
    else:
        level_percentage = 0.0

    correct_percentage = (correct_answer / question_count) * 100 if question_count > 0 else 0.0
    wrong_percentage = (wrong_answer / question_count) * 100 if question_count > 0 else 0.0
    unanswered_percentage = (unanswered / question_count) * 100 if question_count > 0 else 0.0

    return Response({
        "status": "success",
        "message": "Answers submitted successfully",
        "donut": {
            "correct_percentage": correct_percentage,   
            "wrong_percentage": wrong_percentage,   
            "unanswered_percentage": unanswered_percentage,
        },
        "question": question_count,
        "correct_answers": correct_answer,
        "wrong_answer": wrong_answer,
        "unanswered": unanswered,
        "time_taken": total_time_taken, 
        "score": total_marks,
        "total_marks": level_total_marks,
        "negative_marks": total_negative_marks,
        "net_score": total_marks,  # This is already the net score after negative marking
    }, status=status.HTTP_200_OK)







@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_exam_results(request):
    student_id = request.user.id  

    try:
        student = CustomUser.objects.get(id=student_id)
    except CustomUser.DoesNotExist:
        return Response({"status": "error", "message": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        # Get the latest progress for each exam in a single query
        latest_progress_ids = (
            StudentProgress.objects.filter(student=student, is_deleted=False)
            .values('exam')
            .annotate(latest_id=Max('id'))
            .values_list('latest_id', flat=True)
        )
        
        # Fetch all progress records with related exam data in a single query
        progress_records = (
            StudentProgress.objects.filter(id__in=latest_progress_ids)
            .select_related(
                'exam', 'exam__course', 'exam__subject', 
                'exam__chapter', 'exam__lesson', 'exam__folder'
            )
            .order_by('-created')
        )
        
        # Get all exam IDs
        exam_ids = [p.exam_id for p in progress_records if p.exam_id is not None]
        
        # Fetch question counts for all exams in a single query
        question_counts = dict(
            Question.objects.filter(exam_id__in=exam_ids, is_deleted=False)
            .values('exam')
            .annotate(count=Count('id'))
            .values_list('exam', 'count')
        )
        
        # Get all progress IDs
        progress_ids = [p.id for p in progress_records]
        
        # Fetch all progress details in a single query and organize by progress_id
        progress_details = (
            StudentProgressDetail.objects.filter(
                student_progress_id__in=progress_ids,
                is_deleted=False
            )
            .values('student_progress', 'answered', 'is_correct')
        )
        
        # Organize progress details by progress_id for quick access
        details_by_progress = {}
        for detail in progress_details:
            progress_id = detail['student_progress']
            if progress_id not in details_by_progress:
                details_by_progress[progress_id] = {
                    'attended': 0,
                    'correct': 0,
                    'wrong': 0,
                    'unanswered': 0
                }
            
            if detail['answered']:
                details_by_progress[progress_id]['attended'] += 1
                if detail['is_correct']:
                    details_by_progress[progress_id]['correct'] += 1
                else:
                    details_by_progress[progress_id]['wrong'] += 1
            else:
                details_by_progress[progress_id]['unanswered'] += 1
        
        # Dictionary to organize results by course
        course_results = {}
        
        # Process each progress record
        for progress in progress_records:
            if progress.exam is None:
                continue
                
            # Get question count and details
            question_count = question_counts.get(progress.exam_id, 0)
            details = details_by_progress.get(progress.id, {
                'attended': 0,
                'correct': 0,
                'wrong': 0,
                'unanswered': 0
            })
            
            formatted_created = progress.created.strftime("%a, %d %b, %I:%M %p")
            
            # Safely get related fields
            def safe_get(obj, attr_path, default=None):
                try:
                    for attr in attr_path.split('.'):
                        if obj is None:
                            return default
                        obj = getattr(obj, attr)
                    return obj
                except (AttributeError, TypeError):
                    return default
            
            # Get course information
            course_id = safe_get(progress.exam, 'course.id')
            course_name = safe_get(progress.exam, 'course.course_name', "Uncategorized")
            
            # Build result data
            result_data = {
                "exam_id": progress.exam.id,
                "exam_title": progress.exam.title,
                "subject": safe_get(progress.exam, 'subject.subject_name', ""),
                "subject_id": safe_get(progress.exam, 'subject.id'),
                "chapter": safe_get(progress.exam, 'chapter.chapter_name', ""),
                "chapter_id": safe_get(progress.exam, 'chapter.id'),
                "lesson": safe_get(progress.exam, 'lesson.lesson_name', ""),
                "lesson_id": safe_get(progress.exam, 'lesson.id'),
                "folder": safe_get(progress.exam, 'folder.title', ""),
                "folder_id": safe_get(progress.exam, 'folder.id'),
                "total_marks": int(progress.total_marks),
                "marks_obtained": int(progress.marks_obtained),
                "total_questions": question_count,
                "attended_questions": details['attended'],
                "correct_answers": details['correct'],
                "wrong_answers": details['wrong'],
                "unanswered_questions": details['unanswered'],
                "passed": progress.passed,
                "created": formatted_created,
            }
            
            # Initialize course in dictionary if not exists
            if course_id not in course_results:
                course_results[course_id] = {
                    "course_id": course_id,
                    "course_name": course_name,
                    "exams": []
                }
            
            # Add result to the course
            course_results[course_id]["exams"].append(result_data)
        
        # Convert dictionary to list for response
        response_data = list(course_results.values())
        
        # Calculate overall statistics in a single pass
        total_exams = 0
        total_questions = 0
        total_correct = 0
        total_wrong = 0
        total_unanswered = 0
        total_marks_possible = 0
        total_marks_obtained = 0
        total_passed = 0
        course_stats = {}
        
        # Process all exams in a single loop
        for course in response_data:
            course_id = course['course_id']
            course_stats[course_id] = {
                'total_questions': 0,
                'correct_answers': 0,
                'exam_count': len(course['exams'])
            }
            
            for exam in course['exams']:
                total_exams += 1
                total_questions += exam['total_questions']
                total_correct += exam['correct_answers']
                total_wrong += exam['wrong_answers']
                total_unanswered += exam['unanswered_questions']
                total_marks_possible += exam['total_marks']
                total_marks_obtained += exam['marks_obtained']
                total_passed += 1 if exam['passed'] else 0
                
                # Track course-level stats
                course_stats[course_id]['total_questions'] += exam['total_questions']
                course_stats[course_id]['correct_answers'] += exam['correct_answers']
        
        # Calculate percentages safely
        def safe_percentage(numerator, denominator, default=0):
            return (numerator / denominator * 100) if denominator > 0 else default
        
        percentage_correct = safe_percentage(total_correct, total_questions)
        percentage_wrong = safe_percentage(total_wrong, total_questions)
        percentage_unanswered = safe_percentage(total_unanswered, total_questions)
        percentage_score = safe_percentage(total_marks_obtained, total_marks_possible)
        percentage_passed = safe_percentage(total_passed, total_exams)
        
        # Prepare chart data
        overall_pie_chart_data = [
            {"label": "Correct", "value": total_correct, "percentage": round(percentage_correct, 1), "color": "#28a745"},
            {"label": "Wrong", "value": total_wrong, "percentage": round(percentage_wrong, 1), "color": "#dc3545"},
            {"label": "Unanswered", "value": total_unanswered, "percentage": round(percentage_unanswered, 1), "color": "#6c757d"}
        ]
        
        # Performance metrics
        overall_performance_metrics = {
            "accuracy": round(percentage_correct, 1),
            "completion_rate": round(safe_percentage(total_correct + total_wrong, total_questions), 1),
            "score_percentage": round(percentage_score, 1),
            "pass_rate": round(percentage_passed, 1)
        }
        
        # Course performance data
        course_performance = [
            {
                "course_id": course['course_id'],
                "course_name": course['course_name'],
                "accuracy": round(safe_percentage(course_stats[course['course_id']]['correct_answers'], 
                                                course_stats[course['course_id']]['total_questions']), 1),
                "exam_count": course_stats[course['course_id']]['exam_count']
            }
            for course in response_data if course['exams']
        ]
        
        # Overall chart data
        overall_chart_data = {
            "pie": overall_pie_chart_data,
            "performance": overall_performance_metrics,
            "course_comparison": course_performance,
            "total_exams": total_exams,
            "total_questions": total_questions,
            "total_correct": total_correct,
            "total_wrong": total_wrong,
            "total_unanswered": total_unanswered,
            "score_percentage": round(percentage_score, 1),
            "pass_rate": round(percentage_passed, 1)
        }

        return Response({
            "status": "success", 
            "data": response_data,
            "chart_data": overall_chart_data
        }, status=status.HTTP_200_OK)

    except ObjectDoesNotExist as e:
        return Response(
            {"status": "error", "message": f"Object not found: {str(e)}"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    except AttributeError as e:
        return Response(
            {"status": "error", "message": f"Attribute error: {str(e)}. It seems an expected attribute is missing or incorrect."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        return Response(
            {"status": "error", "message": f"An unexpected error occurred: {str(e)}. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )





@api_view(["POST"])
@permission_classes([IsAuthenticated])
def report(request):
    student = request.user
    content = request.data.get('content')
    question_id = request.data.get('question_id')

    if not content:
        return Response({"status": "error", "message": "Content is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not question_id:
        return Response({"status": "error", "message": "Question ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        question = Question.objects.get(id=question_id, is_deleted=False)
    except Question.DoesNotExist:
        return Response({"status": "error", "message": "Question not found."}, status=status.HTTP_404_NOT_FOUND)

    Report.objects.create(student=student, content=content, question=question)

    return Response({"status": "success", "message": "Report submitted successfully."}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def exam_report_chart(request):
    """
    API to generate exam report charts for a student.
    Returns 6 charts:
    - 5 charts for each exam type (Daily, Weekly, Monthly, Model, Live)
    - 1 consolidated chart with all exams ordered by date
    
    Charts show exam performance with marks obtained and total marks.
    """
    student = request.user
 
    # Get all student progress records for exams with a single optimized query
    student_progress = (StudentProgress.objects
        .filter(student=student, exam__isnull=False, is_deleted=False)
        .select_related('exam')
        .order_by('created'))
    
    if not student_progress.exists():
        return Response({
            "status": "error",
            "message": "No exam data found for this student."
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Initialize data structures
    exam_type_data = {
        'Daily': [],
        'Weekly': [],
        'Monthly': [],
        'Model': [],
        'Live': [],
    }
    consolidated_data = []
    
    # Process exam data in a single pass
    for progress in student_progress:
        exam = progress.exam
        if not exam or not exam.exam_type:
            continue
            
        # Calculate marks safely
        marks_obtained = float(progress.marks_obtained) if progress.marks_obtained else 0.0
        total_marks = float(progress.total_marks) if progress.total_marks else 1.0
        percentage = round((marks_obtained / total_marks) * 100, 2) if total_marks > 0 else 0.0
        # Create simplified exam data structure
        exam_data = {
            'exam_name': progress.exam.title or f"Exam #{progress.exam.id}",
            'exam_type': progress.exam.exam_type,
            'marks_obtained': marks_obtained,
            'total_marks': total_marks,
            'percentage': percentage,
            'date': progress.created,
            'passed': progress.passed
        }
        
        # Add to appropriate collections
        exam_type = exam.exam_type
        if exam_type in exam_type_data:
            exam_type_data[exam_type].append(exam_data)
        
        # Add to consolidated data with date for sorting
        consolidated_data.append({
            **exam_data,
            'exam_type': exam_type
        })
    
    # Sort consolidated data by date
    consolidated_data.sort(key=lambda x: x['date'])
    
     # Calculate performance metrics
    total_exams = len(consolidated_data)
    average_score = round(sum(exam['percentage'] for exam in consolidated_data) / total_exams, 2) if total_exams > 0 else 0
    exams_passed = sum(1 for exam in consolidated_data if exam['passed'])
    pass_rate = round((exams_passed / total_exams) * 100, 2) if total_exams > 0 else 0
    
    # Get performance trend (improving, declining, stable)
    trend = "stable"
    if total_exams >= 3:
        recent_scores = [exam['percentage'] for exam in consolidated_data[-3:]]
        if recent_scores[2] > recent_scores[0]:
            trend = "improving"
        elif recent_scores[2] < recent_scores[0]:
            trend = "declining"
    
    # Prepare response data
    response_data = {
        # Format each exam type data as a list of exam objects
        **{exam_type: exams for exam_type, exams in exam_type_data.items()},
        
        # Add consolidated data
        'Consolidated': consolidated_data,
         "performance_metrics": {
                    "total_exams": total_exams,
                    "average_score": average_score,
                    "exams_passed": exams_passed,
                    "pass_rate": pass_rate,
                    "performance_trend": trend
                }
    }
    
    return Response({
        "status": "success",
        "message": "Exam report generated successfully",
        "data": response_data
    }, status=status.HTTP_200_OK)
