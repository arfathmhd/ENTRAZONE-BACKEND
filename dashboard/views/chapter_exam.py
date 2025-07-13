from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from dashboard.models import Exam, Subject, Course, Chapter
from datetime import datetime, timedelta
from django.utils import timezone

@login_required(login_url='dashboard-login')
def chapter_exam_add(request, subject_id):
    """
    Add a new exam to a chapter
    """
    if request.user.user_type != 1 and request.user.user_type != 2:
        return redirect('/')
    
    subject = get_object_or_404(Subject, id=subject_id, is_deleted=False)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        duration_str = request.POST.get('duration')
        is_free = request.POST.get('is_free') == 'on'
        is_shuffle = request.POST.get('is_shuffle') == 'on'
        number_of_attempt = request.POST.get('number_of_attempt', 1)
        exam_type = request.POST.get('exam_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        
        try:
            # Parse duration string (HH:MM:SS)
            hours, minutes, seconds = map(int, duration_str.split(':'))
            duration = datetime.strptime(f"{hours}:{minutes}:{seconds}", "%H:%M:%S").time()
            
            # Create the exam
            exam = Exam(
                title=title,
                duration=duration,
                is_free=is_free,
                is_shuffle=is_shuffle,
                number_of_attempt=number_of_attempt,
                subject=subject,
                exam_type=exam_type,
                start_date=start_date if exam_type != Exam.EXAM_TYPE_CHOICES[0][0] else None,
                end_date=end_date if exam_type != Exam.EXAM_TYPE_CHOICES[0][0] else None,
            )
            exam.save()
            
            messages.success(request, "Exam added successfully.")
            return redirect('subject-chapters-list', subject_id=subject_id)
        except ValueError:
            messages.error(request, "Invalid duration format. Please use HH:MM:SS format.")
            return redirect('subject-chapters-list', subject_id=subject_id)
    
    context = {
        'subject_id': subject_id,
        'course': subject.course,

    }
    
    return render(request, 'dashboard/content/chapter/chapter.html', context)

@login_required(login_url='dashboard-login')
def chapter_exam_update(request, exam_id):
    """
    Update an existing exam
    """
    if request.user.user_type != 1 and request.user.user_type != 2:
        return redirect('/')
        
    exam = get_object_or_404(Exam, id=exam_id, is_deleted=False)
    chapter = exam.chapter
    
    if request.method == 'POST':
        title = request.POST.get('title')
        duration_str = request.POST.get('duration')
        is_free = request.POST.get('is_free') == 'on'
        is_shuffle = request.POST.get('is_shuffle') == 'on'
        number_of_attempt = request.POST.get('number_of_attempt', 1)
        exam_type = request.POST.get('exam_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        try:
            # Parse duration string (HH:MM:SS)
            hours, minutes, seconds = map(int, duration_str.split(':'))
            duration = datetime.strptime(f"{hours}:{minutes}:{seconds}", "%H:%M:%S").time()
            
            # Update the exam
            exam.title = title
            exam.duration = duration
            exam.is_free = is_free
            exam.is_shuffle = is_shuffle
            exam.number_of_attempt = number_of_attempt
            exam.exam_type = exam_type
            exam.start_date = start_date if exam_type != Exam.EXAM_TYPE_CHOICES[0][0] else None
            exam.end_date = end_date if exam_type != Exam.EXAM_TYPE_CHOICES[0][0] else None
            exam.save()
            
            messages.success(request, "Exam updated successfully.")
            return redirect('subject-chapters-list', subject_id=exam.subject.id)
        except ValueError:
            messages.error(request, "Invalid duration format. Please use HH:MM:SS format.")
            return redirect('subject-chapters-list', subject_id=exam.subject.id)
    
    # If not POST, redirect back to the chapter page
    return redirect('subject-chapters-list', subject_id=exam.subject.id)

@login_required(login_url='dashboard-login')
def chapter_exam_delete(request, exam_id):
    """
    Delete an exam (mark as deleted)
    """
    exam = get_object_or_404(Exam, id=exam_id)
    if request.user.user_type != 1 and request.user.user_type != 2:
        return redirect('/')
        
    if request.method == 'POST':
       
        exam.is_deleted = True
        exam.save()
        
        messages.success(request, "Exam deleted successfully.")
        return redirect('subject-chapters-list', subject_id=exam.subject.id)
    
    return redirect('subject-chapters-list', subject_id=exam.subject.id)
