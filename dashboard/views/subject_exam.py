from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from dashboard.models import Exam, Subject, Course
from datetime import datetime, timedelta
from django.utils import timezone

@login_required(login_url='dashboard-login')
def subject_exam_add(request, course_id=None):
    if request.user.user_type != 1 and request.user.user_type != 2:
        return redirect('/')
    
    course = None
    if course_id:
        try:
            course = get_object_or_404(Course, id=course_id, is_deleted=False)
        except (ValueError, Course.DoesNotExist):
            messages.error(request, "Invalid course ID.")
            return redirect('dashboard-course')
        
    if request.method == 'POST':
        form_course_id = request.POST.get('course_id')
        
        if not course_id and form_course_id:
            try:
                course_id = int(form_course_id)
                course = get_object_or_404(Course, id=course_id, is_deleted=False)
            except (ValueError, Course.DoesNotExist):
                messages.error(request, "Invalid course ID.")
                return redirect('dashboard-course')

        try:
            title = request.POST.get('title')
            duration_str = request.POST.get('duration')
            exam_type = request.POST.get('exam_type')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            is_free = request.POST.get('is_free') == 'on'
            is_shuffle = request.POST.get('is_shuffle') == 'on'
            number_of_attempt = request.POST.get('number_of_attempt', 1)
            
            # Parse duration string (HH:MM:SS)
            try:
                hours, minutes, seconds = map(int, duration_str.split(':'))
                duration = datetime.strptime(f"{hours}:{minutes}:{seconds}", "%H:%M:%S").time()
                
                # Create the exam with all fields
                exam = Exam(
                    title=title,
                    duration=duration,
                    exam_type=exam_type,
                    is_free=is_free,
                    is_shuffle=is_shuffle,
                    number_of_attempt=number_of_attempt
                )
                
                # Only set dates if they are provided and exam type is not daily
                if exam_type != 'daily' and start_date and end_date:
                    exam.start_date = start_date
                    exam.end_date = end_date
                
                # If course is available, set it for the exam
                if course:
                    exam.course = course
                
                exam.save()
                
                messages.success(request, "Exam added successfully.")
                if course_id:
                    return redirect('dashboard-course-subjects-list', pk=course_id)
                return redirect('dashboard-course')
                
            except ValueError as e:
                messages.error(request, f"Error processing exam data: {str(e)}")
                if course_id:
                    return redirect('dashboard-course-subjects-list', pk=course_id)
                return redirect('dashboard-course')
                
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            if course_id:
                return redirect('dashboard-course-subjects-list', pk=course_id)
            return redirect('dashboard-course')
    
    # If not POST, redirect to appropriate page
    if course_id:
        return redirect('dashboard-course-subjects-list', pk=course_id)
    return redirect('dashboard-course')


@login_required(login_url='dashboard-login')
def subject_exam_update(request, exam_id):
    """
    Update an existing exam
    """
    if request.user.user_type != 1 and request.user.user_type != 2:
        return redirect('/')
        
    exam = get_object_or_404(Exam, id=exam_id, is_deleted=False)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        duration_str = request.POST.get('duration')
        exam_type = request.POST.get('exam_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        is_free = request.POST.get('is_free') == 'on'
        is_shuffle = request.POST.get('is_shuffle') == 'on'
        number_of_attempt = request.POST.get('number_of_attempt', 1)
        
        try:
            # Parse duration string (HH:MM:SS)
            hours, minutes, seconds = map(int, duration_str.split(':'))
            duration = datetime.strptime(f"{hours}:{minutes}:{seconds}", "%H:%M:%S").time()
            
            # Update the exam
            exam.title = title
            exam.duration = duration
            exam.exam_type = exam_type
            exam.start_date = start_date if exam_type != Exam.EXAM_TYPE_CHOICES[0][0] else None
            exam.end_date = end_date if exam_type != Exam.EXAM_TYPE_CHOICES[0][0] else None
            exam.is_free = is_free
            exam.is_shuffle = is_shuffle
            exam.number_of_attempt = number_of_attempt
            exam.save()
            
            messages.success(request, "Exam updated successfully.")
            return redirect('dashboard-course-subjects-list', pk=exam.course.id)
        except ValueError:
            messages.error(request, "Invalid duration format. Please use HH:MM:SS format.")
            return redirect('dashboard-course-subjects-list', pk=exam.course.id)
    
    # If not POST, redirect back to the course subjects list
    return redirect('dashboard-course-subjects-list', pk=exam.course.id)

@login_required(login_url='dashboard-login')
def subject_exam_delete(request, exam_id):
    """
    Delete an exam (mark as deleted)
    """
    if request.user.user_type != 1 and request.user.user_type != 2:
        return redirect('/')
        
    if request.method == 'POST':
        exam = get_object_or_404(Exam, id=exam_id)
        course_id = exam.course.id
        exam.is_deleted = True
        exam.save()
        
        messages.success(request, "Exam deleted successfully.")
        return redirect('dashboard-course-subjects-list', pk=course_id)
    
    return redirect('dashboard-course-subjects-list', pk=course_id)
