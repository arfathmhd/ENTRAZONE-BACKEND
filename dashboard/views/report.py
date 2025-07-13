from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from dashboard.views.imports import *
@login_required
def all_progression_details(request, student_id):

    all_progressions = StudentProgress.objects.filter(student__id=student_id, is_deleted=False).select_related('level').last()

    print(all_progressions,"{{{{}}}}")
    progress_data = []
    for progress in all_progressions:
        details = progress.details.filter(is_deleted=False)
        progress_data.append({
            'level': progress.level,
            'correct_answers': details.filter(is_correct=True),
            'wrong_answers': details.filter(is_correct=False, answered=True),
            'unanswered_questions': details.filter(answered=False),
            'total_questions': details.count(),
        })

    context = {
        'student': all_progressions.first().student,
        'progress_data': progress_data,
    }

    return render(request, 'dashboard/student/student-details.html', context)
