from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from dashboard.models import Exam, Subject, Course, Chapter, Lesson, Folder
from datetime import datetime, timedelta
from django.utils import timezone

@login_required(login_url='dashboard-login')
def folder_exam_add(request, folder_id):
    """
    Add a new exam to a folder
    """
    if request.user.user_type != 1 and request.user.user_type != 2:
        return redirect('/')
        
    folder = get_object_or_404(Folder, id=folder_id, is_deleted=False)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        duration_str = request.POST.get('duration')
        is_free = request.POST.get('is_free') == 'on'
        is_shuffle = request.POST.get('is_shuffle') == 'on'
        number_of_attempt = request.POST.get('number_of_attempt', 1)
        exam_type = request.POST.get('exam_type')
        exam_start_date = request.POST.get('start_date')
        exam_end_date = request.POST.get('end_date')
        
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
                exam_type=exam_type,
                start_date=exam_start_date if exam_type != Exam.EXAM_TYPE_CHOICES[0][0] else None,
                end_date=exam_end_date if exam_type != Exam.EXAM_TYPE_CHOICES[0][0] else None,
                folder=folder
            )
            exam.save()
            
            messages.success(request, "Exam added successfully.")
            return redirect('dashboard-folder', folder_id=folder_id)
        except ValueError as e:
            print(f"Error parsing duration: {e}")
            messages.error(request, "Invalid duration format. Please use HH:MM:SS format.")
            return redirect('dashboard-folder', folder_id=folder_id)
    
    return redirect('dashboard-folder', folder_id=folder_id)

@login_required(login_url='dashboard-login')
def folder_exam_update(request, exam_id):
    """
    Update an existing exam in a folder
    """
    if request.user.user_type != 1 and request.user.user_type != 2:
        return redirect('/')
        
    exam = get_object_or_404(Exam, id=exam_id, is_deleted=False)
    folder = exam.folder
    
    if not folder:
        messages.error(request, "This exam is not associated with any folder.")
        return redirect('dashboard-home')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        duration_str = request.POST.get('duration')
        is_free = request.POST.get('is_free') == 'on'
        is_shuffle = request.POST.get('is_shuffle') == 'on'
        number_of_attempt = request.POST.get('number_of_attempt', 1)
        exam_type = request.POST.get('exam_type')
        exam_start_date = request.POST.get('start_date')
        exam_end_date = request.POST.get('end_date')
        
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
            exam.start_date = exam_start_date if exam_type != Exam.EXAM_TYPE_CHOICES[0][0] else None
            exam.end_date = exam_end_date if exam_type != Exam.EXAM_TYPE_CHOICES[0][0] else None
            exam.save()
            
            messages.success(request, "Exam updated successfully.")
            return redirect('dashboard-folder', folder_id=folder.id)
        except ValueError as e:
            print(f"Error parsing duration: {e}")
            messages.error(request, "Invalid duration format. Please use HH:MM:SS format.")
            return redirect('dashboard-folder', folder_id=folder.id)
    
    # Get all lessons and exams for this folder
    lessons = Lesson.objects.filter(folder=folder, is_deleted=False).order_by('order')
    exams = Exam.objects.filter(folder=folder, is_deleted=False).order_by('-id')
    folders = Folder.objects.filter(is_deleted=False, parent_folder=folder.id).order_by('order')
    
    context = {
        'folder_id': folder.id,
        'current_folder': folder,
        'lessons': lessons,
        'exams': exams,
        'folders': folders,
    }
    return render(request, 'dashboard/content/folder/folder.html', context)

@login_required(login_url='dashboard-login')
def folder_exam_delete(request, exam_id):
    """
    Delete an exam from a folder
    """
    if request.user.user_type != 1 and request.user.user_type != 2:
        return redirect('/')
        
    exam = get_object_or_404(Exam, id=exam_id, is_deleted=False)
    folder = exam.folder
    
    if not folder:
        messages.error(request, "This exam is not associated with any folder.")
        return redirect('dashboard-home')
    
    if request.method == 'POST':
        # Mark the exam as deleted
        exam.is_deleted = True
        exam.save()
        
        messages.success(request, "Exam deleted successfully.")
        return redirect('dashboard-folder', folder_id=folder.id)
    
    return redirect('dashboard-folder', folder_id=folder.id)
