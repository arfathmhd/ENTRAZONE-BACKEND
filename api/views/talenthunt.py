from dashboard.views.imports import *
from django.db.models import F, Value, CharField, BooleanField
from django.db.models.functions import Coalesce, Cast
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status



@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def talenthunt_list(request):
    course = request.user.default_course
    if not course:
        response = {
            "status": "success",
            "message": "User doesn't have any course",
            "data": []  
        }
        return Response(response, status=status.HTTP_200_OK)

    talent_hunts = TalentHunt.objects.filter(is_deleted=False).annotate(
        talent_hunt_id=F('id'),
        talenthunt_title=Coalesce(F('title'), Value(''), output_field=CharField()),
        talenthunt_image=Coalesce(Cast(F('image'), CharField()), Value(''), output_field=CharField()),
        talenthunt_is_free=Coalesce(F('is_free'), Value(False), output_field=BooleanField())
    ).values('talent_hunt_id', 'talenthunt_title', 'talenthunt_image', 'talenthunt_is_free')

    response_data = list(talent_hunts)

    return Response({
        "status": "success",
        "message": "Talent-Hunt retrieved successfully",
        "data": response_data
    }, status=status.HTTP_200_OK)



@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def talenthunt_subject_list(request):
    talent_hunt_id = request.data.get('talent_hunt_id') 
    user = request.user

    if not talent_hunt_id:
        return Response({"status": "error", "message": "talent_hunt_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    talent_hunt = get_object_or_404(TalentHunt, id=talent_hunt_id)

    talent_hunt_subjects = TalentHuntSubject.objects.filter(talentHunt=talent_hunt, is_deleted=False).select_related('subject')

    response_data = []
    for th_subject in talent_hunt_subjects:
        level_ids = Level.objects.filter(
            talenthuntsubject=th_subject, 
            is_deleted=False
        ).values_list('id', flat=True)

        # Get distinct level IDs from StudentProgress for this user
        attended_level_ids = StudentProgress.objects.filter(
            student=user,
            level__talenthuntsubject=th_subject,
            is_deleted=False
        ).values_list('level_id', flat=True).distinct()

        # Check if user has attended all levels
        is_completed = set(attended_level_ids) == set(level_ids) if level_ids else False


        subject_data = {
            "talent_subject_id": th_subject.id,
            "title": th_subject.title if th_subject.title else "",
            "subject_name": th_subject.subject.subject_name if th_subject.subject else "",
            "is_free": th_subject.is_free,
            "is_completed": is_completed,
        }
        response_data.append(subject_data)

    return Response({
            "status": "success",
            "message": "Talent-Hunt-Subject retrieved successfully",
            "talent_hunt": talent_hunt.title if talent_hunt.title else "",
            "talent_hunt_image": talent_hunt.image.url if talent_hunt.image else "",
            "data": response_data
    }, status=status.HTTP_200_OK)




@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def talenthunt_levels(request):
    user = request.user
    subject_id = request.data.get('talent_subject_id')

    try:
        levels = Level.objects.filter(talenthuntsubject_id=subject_id, is_deleted=False)

        response_levels = []
        unlock_next_level = True  

        for level in levels:
            attended_questions = Question.objects.filter(level=level, is_deleted=False)
            total_questions = attended_questions.count()

            correct_answers_count = 0
            has_attempted = False  

            if attended_questions.exists():
                student_progress = StudentProgress.objects.filter(
                    student=user, 
                    level=level,  
                    is_deleted=False
                ).last()
                if student_progress:
                    correct_answers_count = StudentProgressDetail.objects.filter(
                        student_progress=student_progress, 
                        question__level=level, 
                        is_correct=True, 
                        is_deleted=False
                    ).count()

                    has_attempted = StudentProgressDetail.objects.filter(
                        student_progress=student_progress,
                        is_deleted=False
                    ).exists()

            if total_questions > 0:
                correct_answers_percentage = (correct_answers_count / total_questions) * 100
                correct_answers_percentage = round(correct_answers_percentage, 2)  
            else:
                correct_answers_percentage = 0.0

            if unlock_next_level or has_attempted:
                is_unlocked = True
            else:
                is_unlocked = False

            unlock_next_level = has_attempted

            response_levels.append({
                "level_id": level.id,
                "level_title": level.title if level.title else "",
                "level_number": level.number if level.number else "",
                "is_free": level.is_free ,
                "time": level.duration if level.duration else "",
                "level_percentage": correct_answers_percentage, 
                "total_questions": total_questions ,
                "is_unlocked": is_unlocked,  
                "is_submitted": has_attempted,
            })

        response = {
            "status": "success",
            "message": "Levels retrieved successfully",
            "levels": response_levels,
        }

        return Response(response, status=status.HTTP_200_OK)

    except TalentHuntSubject.DoesNotExist:
        return Response({
            "status": "error",
            "message": "Talent-Hunt-Subject not found",
        }, status=status.HTTP_404_NOT_FOUND)






import re

def extract_latex(raw_string):
    # Match inline LaTeX (within \( ... \))
    latex_pattern = re.compile(r'\\\((.*?)\\\)')  
    
    # Search for the LaTeX pattern in the string
    match = latex_pattern.search(raw_string)
    
    if match:
        # If LaTeX is found, format it with block math mode \[ ... \]
        latex_content = match.group(1)  # Extract the content inside \( ... \)
        
        # Ensure any HTML tags are removed (e.g., <p>, <div>, etc.)
        latex_content = re.sub(r'<.*?>', '', latex_content)
        
        # Format with double backslashes and block math mode \[ ... \]
        formatted_latex = r"\[" + latex_content + r"\]"
        
        return formatted_latex  # Return the formatted LaTeX as a raw string
    
    return raw_string  # Return the original string if no LaTeX is found






@api_view(['GET'])
@permission_classes([IsAuthenticated])
def talenthunt_question(request):
    level_id = request.data.get('level_id')

    if not level_id:
        return Response({
            "status": "error",
            "message": "Level ID is required",
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        questions = Question.objects.filter(level_id=level_id, is_deleted=False)

        response_questions = []
        for question in questions:
            # cleaned_description = extract_latex(question.question_description)

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
                "question_description": question.question_description,
                "options": processed_options,
                "right_answers": question.right_answers,
                "mark": question.mark,
                "negative_mark": question.negative_mark,
                 "explanation_description": question.explanation_description if question.explanation_description else "",
                "explanation_image": question.explanation_image.url if question.explanation_image else "",
            })

        response = {
            "status": "success",
            "message": "Questions retrieved successfully",
            "questions": response_questions,
        }

        return Response(response, status=status.HTTP_200_OK)

    except Level.DoesNotExist:
        return Response({
            "status": "error",
            "message": "Level not found",
        }, status=status.HTTP_404_NOT_FOUND)
    


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def talenthunt_answer_submission(request):
    questions = request.data.get('questions', [])
    level_id = request.data.get('level_id')
    student = request.user  

    if not questions or level_id is None:
        return Response({"status": "error", "message": "Questions data and level_id are required."}, status=status.HTTP_400_BAD_REQUEST)

    question_ids = [q.get('question_id') for q in questions]
    duplicate_question_ids = [q_id for q_id in question_ids if question_ids.count(q_id) > 1]
    
    if duplicate_question_ids:
        return Response({
            "status": "error",
            "message": f"Duplicate question IDs found: {set(duplicate_question_ids)}. Each question must be unique."
        }, status=status.HTTP_400_BAD_REQUEST)

    total_time = timedelta()  
    total_marks = 0
    level_object = Level.objects.get(id=level_id)

    level_total_marks = 0
    for question in Question.objects.filter(level=level_object, is_deleted=False):
        if question.mark:
            level_total_marks += question.mark
        level_total_marks += 0

    student_progress = StudentProgress.objects.create(
        student=student,
        level=level_object,
        marks_obtained=total_marks, 
        total_marks=level_total_marks,  
        passed=False,  
    )

    for question in questions:
        question_id = question.get('question_id')
        selected_answer = question.get('selected_answer')
        time_taken = question.get('time_taken')

        if question_id is None or selected_answer is None or time_taken is None:
            return Response({"status": "error", "message": f"Missing data for question {question_id}"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            time_parts = time_taken.split(":")
            if len(time_parts) != 2:
                return Response({"status": "error", "message": "Invalid time format. Use MM:SS."}, status=status.HTTP_400_BAD_REQUEST)

            minutes, seconds = int(time_parts[0]), int(time_parts[1])
            time_delta = timedelta(minutes=minutes, seconds=seconds)
            total_time += time_delta
        except ValueError:
            return Response({"status": "error", "message": "Invalid time format."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            question_obj = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return Response({"status": "error", "message": f"Question with ID {question_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        correct_answer_data = question_obj.right_answers
        correct_answer_id = None

        if isinstance(correct_answer_data, list) and correct_answer_data:
            correct_answer_id = correct_answer_data[0].get('id')

        if correct_answer_id is None:
            return Response({"status": "error", "message": f"No valid correct answer found for question {question_id}"}, status=status.HTTP_404_NOT_FOUND)

        is_correct = selected_answer == correct_answer_id
        
        answered = selected_answer != 0  

        marks = question_obj.mark or 0
        if is_correct and answered:  
            marks = question_obj.mark or 0  

        student_progress_detail = StudentProgressDetail(
            student_progress=student_progress,  
            question=question_obj,
            selected_option=selected_answer,
            is_correct=is_correct,
            answered=answered,  
            marks_obtained=marks,
            negative_marks=None,  
        )
        student_progress_detail.save() 

        if answered:
            total_marks += marks
 

    # Calculate passing criteria - need at least 50% of total marks to pass
    passing_threshold = student_progress.total_marks * 0.5
    
    # Update student_progress with final marks
    student_progress.marks_obtained = total_marks

    # Set passed to True only if all questions are answered and score meets threshold
    student_progress.passed = total_marks >= passing_threshold
    student_progress.save()

    question_count = Question.objects.filter(level=level_object, is_deleted=False).count()
    correct_answer = StudentProgressDetail.objects.filter(student_progress=student_progress, is_correct=True, is_deleted=False).count()
    wrong_answer = StudentProgressDetail.objects.filter(student_progress=student_progress, selected_option__gt=0,is_correct=False, is_deleted=False).count()
   
    unanswered = StudentProgressDetail.objects.filter(
    student_progress=student_progress, 
    is_correct=False,
    # selected_option=0,
    answered=False,
    is_deleted=False
    ).count()
    if question_count > 0:
        level_percentage = (correct_answer / question_count) * 100
        level_percentage = round(level_percentage, 2)  
    else:
        level_percentage = 0.0

    return Response({
        "status": "success",
        "message": "Answers submitted successfully",
        "level_percentage": level_percentage,
        "level_id":level_id,
        "question": question_count,
        "correct_answers": correct_answer,
        "wrong_answer": wrong_answer,
        "unanswered":unanswered,
        "time_taken": str(total_time), 
        "score": total_marks,
        "total_marks": level_total_marks,
    }, status=status.HTTP_200_OK)






@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_result(request):
    level_id = request.data.get('level_id') 
    exam_id = request.data.get('exam_id')
    status_id = request.data.get('status_code', 0)
    student = request.user  

    # Fetch level or exam questions
    if level_id:
        try:
            level = Level.objects.get(id=level_id)
        except Level.DoesNotExist:
            return Response({"status": "error", "message": "Level not found."}, status=status.HTTP_404_NOT_FOUND)
        questions = Question.objects.filter(level=level, is_deleted=False)
    elif exam_id:
        try:
            exam = Exam.objects.get(id=exam_id)
        except Exam.DoesNotExist:
            return Response({"status": "error", "message": "Exam not found."}, status=status.HTTP_404_NOT_FOUND)
        questions = Question.objects.filter(exam=exam, is_deleted=False)
    else:
        return Response({"status": "error", "message": "Level ID or Exam ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    student_progress = StudentProgress.objects.filter(
        student=student,
        level=level if level_id else None,
        exam=exam if exam_id else None,
        is_deleted=False
    ).last()
    print("Student Progress:", student_progress.id)

    if not student_progress:
        return Response({"status": "error", "message": "No progress found for the specified level or exam."}, status=status.HTTP_404_NOT_FOUND)

    # Retrieve StudentProgressDetail based on the status code
    if status_id == 0:
        progress_details = StudentProgressDetail.objects.filter(student_progress=student_progress, is_deleted=False).order_by('-created')
    elif status_id == 1:
        progress_details = StudentProgressDetail.objects.filter(student_progress=student_progress, is_correct=True, is_deleted=False).order_by('-created')
    elif status_id == 2:
        progress_details = StudentProgressDetail.objects.filter(student_progress=student_progress, is_correct=False, is_deleted=False).order_by('-created')
    elif status_id == 3:
        progress_details = StudentProgressDetail.objects.filter(student_progress=student_progress, is_correct=False,answered=False, is_deleted=False).order_by('-created')
    else:
        return Response({"status": "error", "message": "Invalid status code."}, status=status.HTTP_400_BAD_REQUEST)

    # Construct response data based on progress_details
    questions_data = []
    for detail in progress_details:
        question = detail.question
        right_answers_ids = {answer["id"] for answer in question.right_answers}
        selected_options_ids = detail.selected_option if isinstance(detail.selected_option, (list, tuple)) else [detail.selected_option]

        options_data = [
            {
                "id": option["id"],
                "text": option["text"],
                "is_correct": option["id"] in right_answers_ids,
                "clicked": option["id"] in selected_options_ids
            }
            for option in question.options
        ]

        questions_data.append({
            "question_id": question.id,
            "question_description": question.question_description,
            "attended": bool(selected_options_ids),
            "options": options_data,
            "is_correct": detail.is_correct,
            "marks_obtained": detail.marks_obtained,
            "negative_marks": detail.negative_marks,
        })

    response_data = {
        "status": "success",
        "questions": questions_data
    }
    # if level_id:
    #     response_data["level_id"] = level_id
    # elif exam_id:
    #     response_data["exam_id"] = exam_id

    return Response(response_data, status=status.HTTP_200_OK)
