from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from dashboard.models import Exam, Subject, Course, Chapter, Lesson, Folder
from datetime import datetime, timedelta
from django.utils import timezone

@login_required(login_url='dashboard-login')
def lesson_exam_add(request, chapter_id):
    """
    Add a new exam to a lesson
    """
    if request.user.user_type != 1 and request.user.user_type != 2:
        return redirect('/')
    
    chapter = get_object_or_404(Chapter, id=chapter_id, is_deleted=False)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        duration_str = request.POST.get('duration')
        is_free = request.POST.get('is_free') == 'on'
        is_shuffle = request.POST.get('is_shuffle') == 'on'
        number_of_attempt = request.POST.get('number_of_attempt', 1)
        exam_type = request.POST.get('exam_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        print(Exam.EXAM_TYPE_CHOICES[0][0])
        
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
                chapter=chapter,
                exam_type=exam_type,
                start_date=start_date if exam_type != Exam.EXAM_TYPE_CHOICES[0][0] else None,
                end_date=end_date if exam_type != Exam.EXAM_TYPE_CHOICES[0][0] else None,
            )
            exam.save()
            
            messages.success(request, "Exam added successfully.")
            return redirect('dashboard-chapters-lesson-list', chapter_id=chapter.id)
        except ValueError:
            messages.error(request, "Invalid duration format. Please use HH:MM:SS format.")
            return redirect('dashboard-chapters-lesson-list', chapter_id=chapter.id)
    
    context = {
        'obj_chapter': chapter,
        'subject': chapter.subject,
        # 'pk':chapter.subject.course.id
    }
    
    return render(request, 'dashboard/content/lesson/lesson.html', context)

@login_required(login_url='dashboard-login')
def lesson_exam_update(request, exam_id):
    """
    Update an existing exam
    """
    print(f"User type: {request.user.user_type}")
    
    # Check user permissions
    if request.user.user_type != 1 and request.user.user_type != 2:
        print("User does not have permission, redirecting to home")
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
            print(f"Redirecting to dashboard-chapters-lesson-list with chapter_id={chapter.id}")
            return redirect('dashboard-chapters-lesson-list', chapter_id=chapter.id)
        except ValueError as e:
            print(f"Error parsing duration: {e}")
            messages.error(request, "Invalid duration format. Please use HH:MM:SS format.")
            return redirect('dashboard-chapters-lesson-list', chapter_id=chapter.id)
    
    # If not POST, show the edit form instead of redirecting
    print("GET request, rendering lesson.html with exam context")
    # Get all lessons for this chapter
    lessons = Lesson.objects.filter(chapter=chapter, is_deleted=False).order_by('order')
    exams = Exam.objects.filter(chapter=chapter, is_deleted=False).order_by('-id')
    folders = Folder.objects.filter(is_deleted=False, chapter=chapter.id, parent_folder=None).order_by('order')
    
    context = {
        'obj_chapter': chapter,
        'lessons': lessons,
        'exams': exams,
        'folders': folders,
    }
    return render(request, 'dashboard/content/lesson/lesson.html', context)

@login_required(login_url='dashboard-login')
def lesson_exam_delete(request, exam_id):
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
        return redirect('dashboard-chapters-lesson-list', chapter_id=exam.chapter.id)
    
    return redirect('dashboard-chapters-lesson-list', chapter_id=exam.chapter.id)
