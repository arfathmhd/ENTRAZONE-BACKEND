import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum, F, Q, Case, When, Value, FloatField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import FileResponse
from django.template.loader import get_template
from django.conf import settings

from dashboard.models import (
    Batch, Subscription, CustomUser, Exam, StudentProgress, 
    StudentProgressDetail, Question
)

@login_required(login_url='dashboard-login')
def batch_exam_progress(request, batch_id):
    """View to display exam progress report for all students in a specific batch"""
    if request.user.user_type not in [1, 3, 4]:  # Admin, Admission manager, or Mentor
        return render(request, "dashboard/home/index.html")
    
    batch = get_object_or_404(Batch, id=batch_id, is_deleted=False)
    
    # Get all subscriptions for this batch
    subscriptions = Subscription.objects.filter(
        batch=batch,
        is_deleted=False
    ).select_related('user')
    
    # Get all students from these subscriptions
    students = [subscription.user for subscription in subscriptions]
    student_ids = [student.id for student in students]
    
    # Get all exams attempted by students in this batch
    student_progress = StudentProgress.objects.filter(
        student_id__in=student_ids,
        is_deleted=False
    ).select_related('student', 'exam')
    
    # Get unique exams taken by students in this batch
    exams_taken = list(set([sp.exam for sp in student_progress if sp.exam]))
    
    # Get unique exam types from the exams taken
    exam_types = list(set([exam.exam_type for exam in exams_taken if exam and exam.exam_type]))
    
    # Apply filters
    selected_exam_id = request.GET.get('exam_id')
    selected_exam_type = request.GET.get('exam_type')
    
    filtered_progress = student_progress
    
    if selected_exam_id:
        filtered_progress = filtered_progress.filter(exam_id=selected_exam_id)
    
    if selected_exam_type:
        # Filter by exam type - need to filter the progress records where exam.exam_type matches
        filtered_progress = filtered_progress.filter(exam__exam_type=selected_exam_type)
        
    # Prepare data for the report
    student_exam_data = {}
    
    for student in students:
        student_exam_data[student.id] = {
            'student': student,
            'exams': [],
            'avg_score': 0,
            'exams_taken': 0,
            'exams_passed': 0,
            'exam_type_scores': {}  # To track scores by exam type
        }
    
    # Calculate statistics for each student
    for progress in filtered_progress:
        if progress.student_id in student_exam_data and progress.exam:
            # Calculate percentage score
            percentage = 0
            if progress.total_marks and float(progress.total_marks) > 0:
                percentage = (float(progress.marks_obtained) / float(progress.total_marks)) * 100
            
            exam_data = {
                'exam': progress.exam,
                'marks_obtained': progress.marks_obtained,
                'total_marks': progress.total_marks,
                'percentage': round(percentage, 2),
                'passed': progress.passed,
                'date': progress.created,
                'exam_type': progress.exam.exam_type
            }
            
            student_exam_data[progress.student_id]['exams'].append(exam_data)
            
            # Track scores by exam type
            exam_type = progress.exam.exam_type
            if exam_type:
                if exam_type not in student_exam_data[progress.student_id]['exam_type_scores']:
                    student_exam_data[progress.student_id]['exam_type_scores'][exam_type] = {
                        'scores': [],
                        'avg_score': 0,
                        'exams_taken': 0,
                        'exams_passed': 0
                    }
                
                student_exam_data[progress.student_id]['exam_type_scores'][exam_type]['scores'].append(percentage)
                student_exam_data[progress.student_id]['exam_type_scores'][exam_type]['exams_taken'] += 1
                if progress.passed:
                    student_exam_data[progress.student_id]['exam_type_scores'][exam_type]['exams_passed'] += 1
            
    # Calculate averages and counts
    for student_id, data in student_exam_data.items():
        if data['exams']:
            data['exams_taken'] = len(data['exams'])
            data['exams_passed'] = sum(1 for exam in data['exams'] if exam['passed'])
            data['avg_score'] = round(sum(exam['percentage'] for exam in data['exams']) / len(data['exams']), 2)
            
            # Calculate averages for each exam type
            for exam_type, type_data in data['exam_type_scores'].items():
                if type_data['scores']:
                    type_data['avg_score'] = round(sum(type_data['scores']) / len(type_data['scores']), 2)
    
    # Sort students by average score (descending)
    sorted_student_data = sorted(
        [data for data in student_exam_data.values() if data['exams_taken'] > 0],
        key=lambda x: x['avg_score'],
        reverse=True
    )
    
    # Find batch topper (student with highest average score)
    batch_topper = sorted_student_data[0] if sorted_student_data else None
    
    # Find toppers for each exam type
    exam_type_toppers = {}
    for exam_type in exam_types:
        if not exam_type:
            continue
            
        # Find students who have taken this exam type
        students_with_type = [
            data for data in student_exam_data.values() 
            if data['exam_type_scores'].get(exam_type) and 
            data['exam_type_scores'][exam_type]['exams_taken'] > 0
        ]
        
        # Sort by average score for this exam type
        if students_with_type:
            sorted_by_type = sorted(
                students_with_type,
                key=lambda x: x['exam_type_scores'][exam_type]['avg_score'],
                reverse=True
            )
            exam_type_toppers[exam_type] = sorted_by_type[0]
    
    # Pagination
    paginator = Paginator(sorted_student_data, 25)  # Show 25 students per page
    page_number = request.GET.get('page')
    students_paginated = paginator.get_page(page_number)
    
    # Export functionality
    export_format = request.GET.get('format')
    if export_format:
        return export_batch_exam_progress(request, batch, sorted_student_data, export_format)
    
    context = {
        "title": f"Exam Progress Report - {batch.batch_name}",
        "batch": batch,
        "students": students_paginated,
        "total_students": len(sorted_student_data),
        "exams": exams_taken,
        "exam_types": exam_types,
        "selected_exam_id": selected_exam_id,
        "selected_exam_type": selected_exam_type,
        "batch_topper": batch_topper,
        "exam_type_toppers": exam_type_toppers
    }
    
    return render(request, "dashboard/batch/batch_exam_progress.html", context)

def export_batch_exam_progress(request, batch, student_data, export_format):
    """Export batch exam progress report in CSV or PDF format"""
    filename = f"batch_{batch.id}_exam_progress_{timezone.now().strftime('%Y%m%d%H%M%S')}"
    
    if export_format == 'excel':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Student ID', 'Name', 'Email', 'Exams Taken', 'Exams Passed', 'Average Score (%)'])
        
        for data in student_data:
            writer.writerow([
                data['student'].id,
                data['student'].name or 'N/A',
                data['student'].email or 'N/A',
                data['exams_taken'],
                data['exams_passed'],
                data['avg_score']
            ])
        
        return response
    
    # For future PDF export implementation
    return HttpResponse("PDF export not implemented yet", content_type='text/plain')


@login_required(login_url='dashboard-login')
def student_exam_detail(request, batch_id, student_id):
    """View to display detailed exam performance for a specific student in a batch"""
    if request.user.user_type not in [1, 3, 4]:  # Admin, Admission manager, or Mentor
        return render(request, "dashboard/home/index.html")
    
    batch = get_object_or_404(Batch, id=batch_id, is_deleted=False)
    student = get_object_or_404(CustomUser, id=student_id, is_deleted=False)
    
    # Verify student is in this batch
    subscription_exists = Subscription.objects.filter(
        batch=batch,
        user=student,
        is_deleted=False
    ).exists()
    
    if not subscription_exists:
        return redirect('dashboard-batch-students', batch_id=batch_id)
    
    # Get all exam progress for this student
    progress_records = StudentProgress.objects.filter(
        student=student,
        is_deleted=False
    ).select_related('exam').order_by('-created')
    
    # Get detailed statistics
    exam_details = []
    
    for progress in progress_records:
        if not progress.exam:
            continue
            
        # Get question-level details
        question_details = StudentProgressDetail.objects.filter(
            student_progress=progress,
            is_deleted=False
        ).select_related('question')
        
        # Calculate statistics
        total_questions = question_details.count()
        correct_answers = question_details.filter(is_correct=True).count()
        incorrect_answers = total_questions - correct_answers
        
        # Calculate percentage score
        percentage = 0
        if progress.total_marks and float(progress.total_marks) > 0:
            percentage = (float(progress.marks_obtained) / float(progress.total_marks)) * 100
        
        exam_details.append({
            'progress': progress,
            'exam': progress.exam,
            'marks_obtained': progress.marks_obtained,
            'total_marks': progress.total_marks,
            'percentage': round(percentage, 2),
            'passed': progress.passed,
            'date': progress.created,
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'incorrect_answers': incorrect_answers,
            'question_details': question_details
        })
    
    context = {
        "title": f"Exam Performance - {student.name}",
        "batch": batch,
        "student": student,
        "exam_details": exam_details,
    }
    
    return render(request, "dashboard/batch/student_exam_detail.html", context)
