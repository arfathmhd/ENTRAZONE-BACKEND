from dashboard.views.imports import *
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404

@login_required(login_url='dashboard-login')
def get_courses_subject_chapters(request):
    """API to get courses, subjects, chapters, and folders for the copy/move functionality"""
    course_id = request.GET.get('course_id')
    subject_id = request.GET.get('subject_id')
    chapter_id = request.GET.get('chapter_id')
    folder_id = request.GET.get('folder_id')
    
    data = {}
    
    # Get all courses
    if not course_id and not subject_id and not chapter_id and not folder_id:
        courses = Course.objects.filter(is_deleted=False)
        data['courses'] = [{'id': course.id, 'course_name': course.course_name} for course in courses]
        return JsonResponse(data)
    
    # Get subjects for a course
    if course_id and not subject_id and not chapter_id and not folder_id:
        subjects = Subject.objects.filter(course_id=course_id, is_deleted=False)
        data['subjects'] = [{'id': subject.id, 'subject_name': subject.subject_name} for subject in subjects]
        return JsonResponse(data)
    
    # Get chapters for a subject
    if course_id and subject_id and not chapter_id and not folder_id:
        chapters = Chapter.objects.filter(subject_id=subject_id, is_deleted=False)
        data['chapters'] = [{'id': chapter.id, 'chapter_name': chapter.chapter_name} for chapter in chapters]
        return JsonResponse(data)
    
    # Get folders for a chapter
    if chapter_id and not folder_id:
        folders = Folder.objects.filter(chapter_id=chapter_id, parent=None, is_deleted=False)
        data['has_folders'] = folders.exists()
        if data['has_folders']:
            data['folders'] = [{
                'id': folder.id, 
                'title': folder.title,
                'has_subfolders': Folder.objects.filter(parent=folder, is_deleted=False).exists()
            } for folder in folders]
        return JsonResponse(data)
    
    # Get subfolders for a folder
    if folder_id:
        folder = get_object_or_404(Folder, id=folder_id)
        subfolders = Folder.objects.filter(parent=folder, is_deleted=False)
        data['folders'] = [{
            'id': folder.id,
            'title': folder.title,
            'subfolders': [{
                'id': subfolder.id,
                'title': subfolder.title
            } for subfolder in subfolders]
        }]
        return JsonResponse(data)
    
    return JsonResponse(data)

@login_required(login_url='dashboard-login')
@require_POST
def copy_exam_view(request, exam_id):
    """View to handle copying an exam to any level of the hierarchy"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)
    
    # Get the exam to copy
    try:
        exam = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Exam not found'}, status=404)
    
    # Check permissions
    if not request.user.has_perm('dashboard.add_exam'):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    # Get target information
    target_course_id = request.POST.get('target_course_id')
    target_subject_id = request.POST.get('target_subject_id')
    target_chapter_id = request.POST.get('target_chapter_id')
    target_folder_id = request.POST.get('target_folder_id')
    
    if not target_course_id:
        return JsonResponse({'status': 'error', 'message': 'Target course is required'}, status=400)
    
    # Initialize target objects
    target_course = None
    target_subject = None
    target_chapter = None
    target_folder = None
    
    # Get target course (required)
    try:
        target_course = Course.objects.get(id=target_course_id)
    except Course.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Target course not found'}, status=404)
    
    # Get target subject (optional)
    if target_subject_id:
        try:
            target_subject = Subject.objects.get(id=target_subject_id)
            if target_subject.course != target_course:
                return JsonResponse({'status': 'error', 'message': 'Subject does not belong to the selected course'}, status=400)
        except Subject.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Target subject not found'}, status=404)
    
    # Get target chapter (optional)
    if target_chapter_id:
        try:
            target_chapter = Chapter.objects.get(id=target_chapter_id)
            if target_subject and target_chapter.subject != target_subject:
                return JsonResponse({'status': 'error', 'message': 'Chapter does not belong to the selected subject'}, status=400)
        except Chapter.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Target chapter not found'}, status=404)
    
    # Get target folder (optional)
    if target_folder_id:
        try:
            target_folder = Folder.objects.get(id=target_folder_id)
            if target_chapter and target_folder.chapter != target_chapter:
                return JsonResponse({'status': 'error', 'message': 'Folder does not belong to the selected chapter'}, status=400)
        except Folder.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Target folder not found'}, status=404)
    
    # Create a new exam as a copy
    new_exam = Exam.objects.create(
        title=f"Copy of {exam.title}",
        image=exam.image,
        number_of_attempt=exam.number_of_attempt,
        duration=exam.duration,
        exam_type=exam.exam_type,
        course=target_course,
        subject=target_subject,
        chapter=target_chapter,
        folder=target_folder,
        lesson=exam.lesson,
        current_affair=exam.current_affair,
    )
    
    # Copy all questions associated with the exam using bulk create for better performance
    questions = Question.objects.filter(exam=exam)
    new_questions = []
    
    for question in questions:
        # Create a new Question instance but don't save it yet
        new_question = Question(
            exam=new_exam,
            question_description=question.question_description,
            question_type=question.question_type,
            mark=question.mark,
            negative_mark=question.negative_mark,
            hint=question.hint,
            options=question.options,
            right_answers=question.right_answers,
            explanation_description=question.explanation_description,
            explanation_image=question.explanation_image,
            chapter=question.chapter,
            level=question.level,
            is_completed=question.is_completed
        )
        new_questions.append(new_question)
    
    # Bulk create all questions in a single database query
    if new_questions:
        Question.objects.bulk_create(new_questions)
    
    return JsonResponse({'status': 'success', 'message': 'Exam copied successfully', 'exam_id': new_exam.id})

@login_required(login_url='dashboard-login')
@require_POST
def move_exam_view(request, exam_id):
    """View to handle moving an exam to any level of the hierarchy"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)
    
    # Get the exam to move
    try:
        exam = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Exam not found'}, status=404)
    
    # Check permissions
    if not (request.user.user_type == 1 or request.user.user_type == 2):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    # Get target information
    target_course_id = request.POST.get('target_course_id')
    target_subject_id = request.POST.get('target_subject_id')
    target_chapter_id = request.POST.get('target_chapter_id')
    target_folder_id = request.POST.get('target_folder_id')
    
    if not target_course_id:
        return JsonResponse({'status': 'error', 'message': 'Target course is required'}, status=400)
    
    # Initialize target objects
    target_course = None
    target_subject = None
    target_chapter = None
    target_folder = None
    
    # Get target course (required)
    try:
        target_course = Course.objects.get(id=target_course_id)
    except Course.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Target course not found'}, status=404)
    
    # Get target subject (optional)
    if target_subject_id:
        try:
            target_subject = Subject.objects.get(id=target_subject_id)
            if target_subject.course != target_course:
                return JsonResponse({'status': 'error', 'message': 'Subject does not belong to the selected course'}, status=400)
        except Subject.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Target subject not found'}, status=404)
    
    # Get target chapter (optional)
    if target_chapter_id:
        try:
            target_chapter = Chapter.objects.get(id=target_chapter_id)
            if target_subject and target_chapter.subject != target_subject:
                return JsonResponse({'status': 'error', 'message': 'Chapter does not belong to the selected subject'}, status=400)
        except Chapter.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Target chapter not found'}, status=404)
    
    # Get target folder (optional)
    if target_folder_id:
        try:
            target_folder = Folder.objects.get(id=target_folder_id)
            if target_chapter and target_folder.chapter != target_chapter:
                return JsonResponse({'status': 'error', 'message': 'Folder does not belong to the selected chapter'}, status=400)
        except Folder.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Target folder not found'}, status=404)
    
    # Update the exam with new location
    exam.course = target_course
    exam.subject = target_subject
    exam.chapter = target_chapter
    exam.folder = target_folder
    exam.save()
    
    return JsonResponse({'status': 'success', 'message': 'Exam moved successfully', 'exam_id': exam.id})
