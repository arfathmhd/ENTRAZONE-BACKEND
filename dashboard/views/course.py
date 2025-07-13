from django.shortcuts import redirect, render , get_object_or_404
from dashboard.models import *
from dashboard.forms.content.course import AddForm
from dashboard.forms.content.subject import SubjectForm
from dashboard.forms.content.chapter import ChapterForm
from dashboard.forms.content.lesson import LessonForm as LessonFormContent
from dashboard.forms.content.question import QuestionForm
from django.contrib import auth, messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from dashboard.views.imports  import *
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError


@login_required(login_url='dashboard-login')
def manager(request):
    if request.user.user_type == 1 or request.user.user_type == 2:
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        sort_option = request.GET.get('sort', 'name_ascending')

        if start_date and start_date.lower() != 'null':
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                start_date = None
        else:
            start_date = None

        if end_date and end_date.lower() != 'null':
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date() + timedelta(days=1)
            except ValueError:
                end_date = None
        else:
            end_date = None

        level_filter = Course.objects.filter(is_deleted=False)

        if start_date and end_date:
            level_filter = level_filter.filter(created__range=[start_date, end_date])

        if sort_option == 'name_ascending':
            level_filter = level_filter.order_by('course_name')
        elif sort_option == 'name_descending':
            level_filter = level_filter.order_by('-course_name')

        paginator = Paginator(level_filter, 25)
        page_number = request.GET.get('page')
        levels_paginated = paginator.get_page(page_number)

        context = {
            'courses': levels_paginated,
            'start_date': start_date,
            'end_date': end_date,
            'current_sort': sort_option,
        }

        return render(request, 'dashboard/content/course/course.html', context)
    else:
        return redirect('/')



@login_required(login_url='dashboard-login')
def add(request):
    if request.user.user_type == 1 or request.user.user_type == 2:
        if request.method == "POST":
            form = AddForm(request.POST, request.FILES)
            if form.is_valid():
                course = form.save(commit=False)

              
                course.save()

               
                messages.success(request, "Course and Batch information added successfully!")
                return redirect('dashboard-course')
            else:
                context = {
                    "title": "Add Course | Dashboard",
                    "form": form,
                }
                return render(request, "dashboard/content/course/add-course.html", context)
        else:
            form = AddForm()  
            context = {
                "title": "Add Course | Agua Dashboard",
                "form": form,
            }
            return render(request, "dashboard/content/course/add-course.html", context)
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def update(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 2:  
        course = Course.objects.get(id=pk, is_deleted=False)
        if not course:
            messages.error(request, 'Course not found')
            return redirect('dashboard-course')


        if request.method == 'POST':
            form = AddForm(request.POST, request.FILES, instance=course)
            if form.is_valid():
                course = form.save(commit=False)
            
                
                course.save()

            
                messages.success(request, "Course updated successfully!")
                return redirect('dashboard-course')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            
            form = AddForm(instance=course)
        
        context = {
            "title": "Update Course | Agua Dashboard",
            "form": form,
            "course_id": course.id,
        }
        return render(request, "dashboard/content/course/update-course.html", context)

    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def delete(request, pk):
		course = Course.objects.get(id = pk, is_deleted=False)
		course.is_deleted = True
		course.save()
		messages.success(request, 'Brand Deleted')
		return redirect('dashboard-course')

from django.utils.dateparse import parse_datetime
@login_required(login_url='dashboard-login')
def course_subjects_list(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 2:
        course = get_object_or_404(Course, id=pk, is_deleted=False)
        
        search_query = request.GET.get('search', '')
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        sort_option = request.GET.get('sort', 'name_ascending')  

        subjects = Subject.objects.filter(is_deleted=False, course=course).order_by('order')
        exams = Exam.objects.filter(is_deleted=False, course=course)

        if search_query:
            subjects = subjects.filter(subject_name__icontains=search_query)

        if start_date == 'null':
            start_date = None  
        else:
            try:
                start_date = parse_datetime(start_date)  
                if start_date is None:  
                    raise ValueError
            except (ValueError, TypeError):
                start_date = None

        if end_date == 'null':
            end_date = None  
        else:
            try:
                end_date = parse_datetime(end_date)  
                if end_date is None: 
                    raise ValueError
                end_date += timedelta(days=1)  
            except (ValueError, TypeError):
                end_date = None

        if start_date and end_date:
            subjects = subjects.filter(created__range=[start_date, end_date])

        if sort_option == 'name_ascending':
            subjects = subjects.order_by('subject_name')
        elif sort_option == 'name_descending':
            subjects = subjects.order_by('-subject_name')
        else:
            subjects = subjects.order_by('order')  

        paginator = Paginator(subjects, 25) 
        page_number = request.GET.get('page')
        paginated_subjects = paginator.get_page(page_number)

        context = {
            'course': course,
            'subjects': paginated_subjects,
            'exams': exams,
            'search_query': search_query,
            'start_date': start_date,
            'end_date': end_date,
            'current_sort': sort_option,
        }

        return render(request, 'dashboard/content/subject/subject.html', context)
    else:
        return redirect('/')



@login_required(login_url='dashboard-login')
def course_detail_subject(request, course_id):
        draw = int(request.GET.get("draw", 1))
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 10))  
        search_value = request.GET.get("search[value]", "")
        order_column = int(request.GET.get("order[0][column]", 0))
        order_dir = request.GET.get("order[0][dir]", "desc")
        
        course = Course.objects.filter(id=course_id, is_deleted=False).first()
        # if not course

        order_columns = {
            0: 'id',
            1: 'subject_name',
            2: 'description',
            3: 'created',
        }
        
        order_field = order_columns.get(order_column, 'id')
        if order_dir == 'desc':
            order_field = '-' + order_field
        
        subjects = Subject.objects.filter(is_deleted=False,course=course).order_by('order')
        
        if search_value:
            subjects = subjects.filter(subject_name__icontains=search_value)
        
        total_records = subjects.count()

        subjects = subjects.order_by(order_field)
        paginator = Paginator(subjects, length)
        page_number = (start // length) + 1
        page_obj = paginator.get_page(page_number)

        data = []
        for subject in page_obj:
            data.append({
                "id": subject.id,
                "image": subject.image.url if subject.image else None,
                "subject_name": subject.subject_name,
                "description": subject.description,
                "created": timezone.localtime(subject.created).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        response = {
            "draw": draw,
            "course": course.id,
            "recordsTotal": total_records,
            "recordsFiltered": total_records,
            "data": data,
        }

        return JsonResponse(response)

from dashboard.forms.content.subject import SubjectForm
@login_required(login_url='dashboard-login')
def course_subject_add(request, course_id):
    if request.user.user_type == 1 or request.user.user_type == 2:
        try:
            
            course = Course.objects.get(id=course_id, is_deleted=False)
            print("Course:", course)
        except Course.DoesNotExist:
            messages.error(request, "Course not found.")
            return redirect('dashboard-course')

        if request.method == 'POST':
            form = SubjectForm(request.POST, request.FILES) 
            if form.is_valid():
                subject = form.save(commit=False)
                subject.course = course  
                subject.save()
                messages.success(request, "Subject added successfully!")
                return redirect('dashboard-course-subjects-list', pk=course_id)
        else:
            form = SubjectForm()

        context = {
            "form": form,
            "course": course,
            "course_id":course_id
        }
        return render(request, "dashboard/content/subject/add-subject.html",context)
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def course_subject_update(request, course_id, subject_id):
    if request.user.user_type == 1 or request.user.user_type == 2:  
        try:
            course = Course.objects.get(id=course_id, is_deleted=False)
        except Course.DoesNotExist:
            messages.error(request, "Course not found.")
            return redirect('dashboard-course')

        if request.method == 'POST':
            if subject_id:
                subject = get_object_or_404(Subject, id=subject_id, course=course)
                form = SubjectForm(request.POST, request.FILES, instance=subject)
            else:
                form = SubjectForm(request.POST, request.FILES)
            if form.is_valid():
                subject = form.save(commit=False)
                subject.course = course
                subject.save()
                messages.success(request, "Subject updated successfully!")
                return redirect('dashboard-course-subjects-list', pk=course_id)
        else:
            if subject_id:
                subject = get_object_or_404(Subject, id=subject_id, course=course)
                form = SubjectForm(instance=subject)
            else:
                form = SubjectForm()

        context = {
            "title": "Update Subject ",
            "form": form,
            "course": course,
        }
        return render(request, "dashboard/content/subject/add-subject-update.html", context)
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def course_subject_delete(request, pk):
    try:
        subject = Subject.objects.get(id=pk, is_deleted=False)
        subject.is_deleted = True
        subject.save()  
        messages.success(request, 'Subject Deleted')
    except Subject.DoesNotExist:
        messages.error(request, 'Subject not found or already deleted.')

    return redirect('dashboard-course')





@login_required(login_url='dashboard-login')
def course_subject_chapters_list(request, subject_id):
    if request.user.user_type == 1 or request.user.user_type == 2:
        subject = get_object_or_404(Subject, id=subject_id, is_deleted=False)

        chapters = Chapter.objects.filter(subject=subject, is_deleted=False)
        exams = Exam.objects.filter(subject=subject, is_deleted=False)

        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        sort_option = request.GET.get('sort', 'name_ascending')  

        

        if start_date and start_date.lower() != 'null':
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date() + timedelta(days=1) 
                chapters = chapters.filter(created__gte=start_date)
            except ValueError:
                start_date = None

        if end_date and end_date.lower() != 'null':
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date() + timedelta(days=1) 

                chapters = chapters.filter(created__lte=end_date)
            except ValueError:
                end_date = None

        if sort_option == 'name_ascending':
            chapters = chapters.order_by('chapter_name')  
        elif sort_option == 'name_descending':
            chapters = chapters.order_by('-chapter_name')
        else:
            chapters = chapters.order_by('order')

        context = {
            "subject_id": subject_id,
            "chapters": chapters,  
            "subject_name": subject.subject_name,
            "course": subject.course, 
            "start_date": start_date,
            "end_date": end_date,
            "current_sort": sort_option,
            "exams": exams,
        }

        return render(request, 'dashboard/content/chapter/chapter.html', context)
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def subject_detail_chapter(request, pk):
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 10))  
    search_value = request.GET.get("search[value]", "")
    order_column = int(request.GET.get("order[0][column]", 0))
    order_dir = request.GET.get("order[0][dir]", "desc")
    
    subject = get_object_or_404(Subject, id=pk)

    order_columns = {
        0: 'id',
        1: 'subject_name',
        2: 'description',
        3: 'created',
    }
    
    order_field = order_columns.get(order_column, 'id')
    if order_dir == 'desc':
        order_field = '-' + order_field
    else:
        order_field = "order"
    
    chapter = Chapter.objects.filter(subject=subject, is_deleted=False)
    exams = Exam.objects.filter(subject=subject, is_deleted=False)
    
    if search_value:
        chapter = chapter.filter(chapter_name__icontains=search_value)
    
    total_records = chapter.count()

    chapter = chapter.order_by(order_field)
    paginator = Paginator(chapter, length)
    page_number = (start // length) + 1
    page_obj = paginator.get_page(page_number)

    data = []
    for chapter in page_obj:
        data.append({
            "id": chapter.id,
            "image": chapter.image.url if chapter.image else None,
            "chapter_name": chapter.chapter_name,
            "description": chapter.description,
             "created": timezone.localtime(chapter.created).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    response = {
        "draw": draw,
        "subject": subject.id,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data,
        "exams": exams,
    }

    return JsonResponse(response)


# from dashboard.forms.content subject.py
from dashboard.forms.content.chapter import ChapterForm
@login_required(login_url='dashboard-login')
def subject_chapter_add(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 2:
        try:
            subject = Subject.objects.get(id=pk, is_deleted=False)
        except Subject.DoesNotExist:
            messages.error(request, "Subject not found.")
            return redirect('dashboard-course')
        

        if request.method == 'POST':
            form = ChapterForm(request.POST, request.FILES, initial={'subject': subject})
            if form.is_valid():
                chapter = form.save(commit=False)
                chapter.subject = subject
                chapter.save()
                messages.success(request, "chapter added successfully!")
                return redirect('subject-chapters-list', subject_id=pk)
            else:
                messages.error(request, "chapter not added successfully!")
        else:
            form = ChapterForm(initial={'subject': subject})

        context = {
            "form": form,
            "subject": subject,
        }
        return render(request, "dashboard/content/chapter/add-chapter.html",context)
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def subject_chapter_update(request, chapter_id, subject_id):
    if request.user.user_type == 1 or request.user.user_type == 2:
        subject = get_object_or_404(Subject, id=subject_id, is_deleted=False)
        chapter = get_object_or_404(Chapter, id=chapter_id, subject=subject)

        if request.method == 'POST':
            form = ChapterForm(request.POST, request.FILES, instance=chapter)
            if form.is_valid():
                chapter = form.save(commit=False)
                chapter.subject = subject
                chapter.save()
                messages.success(request, "Chapter updated successfully!")
                
                return redirect('subject-chapters-list', subject_id=subject_id)
        else:
            form = ChapterForm(instance=chapter)

        context = {
            "title": "Update Chapter",
            "form": form,
            "subject": subject,
        }
        return render(request, "dashboard/content/chapter/update-chapter.html", context)

    else:
        return redirect('/')





@login_required(login_url='dashboard-login')
def subject_chapter_delete(request,chapter_id, subject_id):
    try:
        subject = Chapter.objects.get(id=chapter_id, is_deleted=False)
        subject.is_deleted = True
        subject.save()  
        messages.success(request, 'Chapter Deleted')
    except Subject.DoesNotExist:
        messages.error(request, 'Chapter not found or already deleted.')

    return redirect('subject-chapters-list', subject_id=subject_id)


def chapter_exam_list(request, chapter_id):
    if request.user.user_type == 1 or request.user.user_type == 2:
        chapter = get_object_or_404(Chapter, id=chapter_id)
        exams = Exam.objects.filter(chapter=chapter, is_deleted=False).order_by('-id')

        search_query = request.GET.get('search', '')
        if search_query:
            exams = exams.filter(exam_name__icontains=search_query)

        context = {
            "title": "Exam List",
            "exams": exams,
            "chapter": chapter,
        }
        return render(request, "dashboard/content/chapterexam/exam-list.html", context)
    else:
        return redirect('/')



@login_required(login_url='dashboard-login')
def chapter_lesson_list(request, chapter_id):
    if request.user.user_type == 1 or request.user.user_type == 2:
        chapter = get_object_or_404(Chapter, id=chapter_id)
        lessons = Lesson.objects.filter(chapter=chapter, is_deleted=False).order_by('order')
        exams = Exam.objects.filter(chapter=chapter, is_deleted=False).order_by('-id')

        search_query = request.GET.get('search', '')
        if search_query:
            lessons = lessons.filter(lesson_name__icontains=search_query)

        # Handle date range filtering
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')

        if start_date:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                lessons = lessons.filter(created__gte=start_date)
            except ValueError:
                start_date = None

        if end_date:
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date() + timedelta(days=1)
                lessons = lessons.filter(created__lt=end_date)
            except ValueError:
                end_date = None

        # Pagination
        paginator = Paginator(lessons, 25) 
        page_number = request.GET.get('page')
        paginated_lessons = paginator.get_page(page_number)
        folders = Folder.objects.filter(is_deleted=False,chapter=chapter_id,parent_folder=None).order_by('order')
        context = {
            "title": "Lessons",
            "chapter": chapter_id,
            "obj_chapter": chapter,
            "lessons": paginated_lessons,
            "search_query": search_query,
            "start_date": start_date,
            "end_date": end_date,
            "folders": folders,
            "exams": exams,
        }
        return render(request, 'dashboard/content/lesson/lesson.html', context)
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def chapter_detail_lesson(request, pk):
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 25))
    search_value = request.GET.get("search[value]", "")
    order_column = int(request.GET.get("order[0][column]", 0))
    order_dir = request.GET.get("order[0][dir]", "desc")
    
    chapter = get_object_or_404(Chapter, id=pk)

    order_columns = {
        0: 'id',
        1: 'subject_name',
        2: 'description',
        3: 'created',
    }
    
    order_field = order_columns.get(order_column, 'id')
    if order_dir == 'desc':
        order_field = '-' + order_field
    else:
        order_field = "order"
    
    lessons = Lesson.objects.filter(chapter=chapter, is_deleted=False)
    
    if search_value:
        lessons = lessons.filter(lesson_name__icontains=search_value)
    
    total_records = lessons.count()

    lessons = lessons.order_by(order_field)
    paginator = Paginator(lessons, length)
    page_number = (start // length) + 1
    page_obj = paginator.get_page(page_number)

    data = []
    for lesson in page_obj:
        videos = Video.objects.filter(lesson=lesson, is_deleted=False)
        pdfs = PDFNote.objects.filter(lesson=lesson, is_deleted=False)
        
        video_data = []
        for video in videos:
            video_data.append({
                "video_url": video.url if video.url else "N/A",
                "video_title": video.title if video.title else "N/A",
                "video_is_free": video.is_free
            })

        pdf_data = []
        for pdf in pdfs:
            pdf_data.append({
                "pdf_title": pdf.title if pdf.title else "N/A",
                "pdf_is_free": pdf.is_free,
                "pdf_file": pdf.file.url if pdf.file else "N/A"
            })

        data.append({
            "id": lesson.id,
            "image": lesson.image.url if lesson.image else None,
            "chapter_name": chapter.chapter_name,
            "videos": video_data,
            "pdfs": pdf_data,
            "description": lesson.description,
              "created": timezone.localtime(lesson.created).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    response = {
        "draw": draw,
        "chapter": chapter.id,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data,
    }

    return JsonResponse(response)



@login_required(login_url='dashboard-login')
def chapter_lesson_add(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 2:
        try:
            chapter = Chapter.objects.get(id=pk, is_deleted=False)
        except Chapter.DoesNotExist:
            messages.error(request, "Chapter not found.")
            return redirect('dashboard-course')
        
        if request.method == 'POST':
            form = LessonFormContent(request.POST, request.FILES)
        
            if form.is_valid():
                lesson = form.save(commit=False)  
                
                # The chapter is now set by the form, but we can ensure it here too
                lesson.chapter = chapter

                lesson.visible_in_days = form.cleaned_data.get('visible_in_days', 0) or 0

                lesson.save()  

                # Check which content type was selected (video or PDF)
                video_url = form.cleaned_data.get('video_url', "")
                m3u8_url = form.cleaned_data.get('m3u8', "")
                tp_stream = form.cleaned_data.get('tp_stream', "")
                pdf_file = form.cleaned_data.get('pdf_file')
                pdf_title = form.cleaned_data.get('pdf_title')
                
                # Create video if video content was provided
                if video_url or m3u8_url or tp_stream:
                    Video.objects.create(
                        lesson=lesson,
                        title=form.cleaned_data.get('video_title'),
                        url=video_url,
                        m3u8=m3u8_url,
                        tp_stream=tp_stream,
                        is_downloadable=form.cleaned_data.get('video_is_downloadable', False),
                        is_free=form.cleaned_data.get('video_is_free', False),
                        m3u8_is_downloadable=form.cleaned_data.get('m3u8_is_downloadable'),
                        m3u8_is_free=form.cleaned_data.get('m3u8_is_free'),
                    )
                # Create PDF note if PDF content was provided
                elif pdf_file:
                    PDFNote.objects.create(
                        lesson=lesson,
                        title=pdf_title,
                        file=pdf_file,
                        is_downloadable=form.cleaned_data.get('pdf_is_downloadable', False),
                        is_free=form.cleaned_data.get('pdf_is_free', False),
                    )

                messages.success(request, "Lesson added successfully!")
                return redirect('dashboard-chapters-lesson-list', chapter_id=chapter.id)
            else:
                print("Form errors:", form.errors)
                for error in form.non_field_errors():
                    messages.error(request, error)

        else:
            # Initialize the form with the chapter pre-selected
            form = LessonFormContent(initial={'chapter': chapter.id})

        context = {
            "form": form,
            "chapter": chapter,  
        }
        return render(request, "dashboard/content/lesson/add-lesson.html", context)

    else:
        return redirect('/')



@login_required(login_url='dashboard-login')
def chapter_lesson_update(request, chapter_id, lesson_id):
    if request.user.user_type not in [1, 2]:  
        return redirect('/')

    chapter = get_object_or_404(Chapter, id=chapter_id, is_deleted=False)
    lesson = get_object_or_404(Lesson, id=lesson_id, chapter=chapter, is_deleted=False)
    pdf_note = PDFNote.objects.filter(lesson=lesson).first()

    if request.method == 'POST':
        form = LessonFormContent(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.chapter = chapter
            lesson.save()

            # Extract video and PDF data
            video_data = {
                'title': form.cleaned_data.get('video_title'),
                'url': form.cleaned_data.get('video_url'),
                'is_downloadable': form.cleaned_data.get('video_is_downloadable', False),
                'is_free': form.cleaned_data.get('video_is_free', False),
                'tp_stream': form.cleaned_data.get('tp_stream'),
                'm3u8': form.cleaned_data.get('m3u8'),
                'm3u8_is_free': form.cleaned_data.get('m3u8_is_free', False),
                'm3u8_is_downloadable': form.cleaned_data.get('m3u8_is_downloadable', False),
            }
            
            pdf_file = form.cleaned_data.get('pdf_file')
            pdf_data = {
                'title': form.cleaned_data.get('pdf_title'),
                'file': pdf_file if pdf_file else None,  # Only update file if a new one is provided
                'is_downloadable': form.cleaned_data.get('pdf_is_downloadable', False),
                'is_free': form.cleaned_data.get('pdf_is_free', False),
            }
            
            has_video = bool(video_data['title'] or video_data['url'] or video_data['m3u8'] or video_data['tp_stream'])
            has_pdf = bool(pdf_file or pdf_data['title'])
            
            # Update or create video if video content was selected
            if has_video:
                Video.objects.update_or_create(
                    lesson=lesson,
                    defaults=video_data
                )
            # Update or create PDF if PDF content was selected
            elif has_pdf:
                
                # Only update the file field if a new file is provided
                if not pdf_file and lesson.pdf_notes.exists():
                    # Keep the existing file if no new file is uploaded
                    del pdf_data['file']
                
                PDFNote.objects.update_or_create(
                    lesson=lesson,
                    defaults=pdf_data
                )

            messages.success(request, "Lesson updated successfully!")
            return redirect('dashboard-chapters-lesson-list', chapter_id=chapter.id)
        else:
            print("Form errors:", form.errors)
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = LessonFormContent(instance=lesson)

    context = {
        "title": "Update Lesson",
        "form": form,
        "chapter": chapter,
        "pdf_note": pdf_note,
    }
    return render(request, "dashboard/content/lesson/update-lesson.html", context)






@login_required(login_url='dashboard-login')
def chapter_lesson_delete(request,chapter_id,lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    lesson.is_deleted = True
    lesson.save()
    return redirect('dashboard-chapters-lesson-list', chapter_id=chapter_id)


@login_required(login_url='dashboard-login')
def lesson_exam_add(request, lesson_id):
    if request.user.user_type == 1 or request.user.user_type == 2:
        lesson = get_object_or_404(Lesson, id=lesson_id)
        print(lesson,"{{{{{{}}}}}}")
        
        if request.method == 'POST':
            form = LessonExamForm(request.POST, request.FILES)
            if form.is_valid():
                exam = form.save(commit=False)
                exam.lesson = lesson
                exam.save()
                # Check if chapter exists before trying to access its id
                if lesson.chapter:
                    return redirect('dashboard-chapters-lesson-list', chapter_id=lesson.chapter.id)
                else:
                    # Fallback if no chapter is associated
                    return redirect('dashboard-home')
            else:
                print("Form errors:", form.errors)
        else:
            form = LessonExamForm()

        context = {
            "title": "Add Exam",
            "form": form,
            "lesson": lesson,
        }
        return render(request, "dashboard/content/lesson/exam/add-exam.html", context)
    else:
        return redirect('/')


from dashboard.forms.content.lesson import LessonExamForm
@login_required(login_url='dashboard-login')
def lesson_exam_update(request, exam_id):
    if request.user.user_type == 1 or request.user.user_type == 2:
        exam = get_object_or_404(Exam, id=exam_id)
        lesson = exam.lesson
        
        if request.method == 'POST':
            form = LessonExamForm(request.POST, request.FILES, instance=exam)
            if form.is_valid():
                form.save()
                # Check if chapter exists before trying to access its id
                if lesson and lesson.chapter:
                    return redirect('dashboard-chapters-lesson-list', chapter_id=lesson.chapter.id)
                else:
                    # Fallback if no chapter is associated
                    return redirect('dashboard-home')
            else:
                print("Form errors:", form.errors)
        else:
            form = LessonExamForm(instance=exam)

        context = {
            "title": "Update Exam",
            "form": form,
            "lesson": lesson,
            "exam": exam,
        }
        return render(request, "dashboard/content/lesson/exam/update-exam.html", context)
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def lesson_exam_delete(request, exam_id):
    if request.user.user_type == 1 or request.user.user_type == 2:
        exam = get_object_or_404(Exam, id=exam_id)
        lesson = exam.lesson
        
        exam.is_deleted = True
        exam.save()
        
        # Check if chapter exists before trying to access its id
        if lesson and lesson.chapter:
            return redirect('dashboard-chapters-lesson-list', chapter_id=lesson.chapter.id)
        else:
            # Fallback if no chapter is associated
            return redirect('dashboard-home')
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def chapter_question_list(request, chapter_id):
    if request.user.user_type == 1 or request.user.user_type == 2:
        # Get questions related to the chapter
        questions = Question.objects.filter(is_deleted=False, chapter_id=chapter_id)

        # Search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            questions = questions.filter(question_description__icontains=search_query)

        # Date filtering
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')

        if start_date:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                questions = questions.filter(created__gte=start_date)
            except ValueError:
                start_date = None

        if end_date:
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date() + timedelta(days=1)
                questions = questions.filter(created__lt=end_date)
            except ValueError:
                end_date = None

        paginator = Paginator(questions, 25) 
        page_number = request.GET.get('page')
        paginated_questions = paginator.get_page(page_number)

        context = {
            'chapter': chapter_id,
            'questions': paginated_questions,
            'search_query': search_query,
            'start_date': start_date,
            'end_date': end_date,
        }

        return render(request, 'dashboard/content/question/lesson-question.html', context)
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def chapter_detail_question(request,pk):
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 10))
    search_value = request.GET.get("search[value]", "")
    order_column = int(request.GET.get("order[0][column]", 0))
    order_dir = request.GET.get("order[0][dir]", "desc")
    
    order_columns = {
        0: 'id',
        1: 'question_description',
        2: 'hint',
        3: 'created'
    }
    
    order_field = order_columns.get(order_column, 'id')
    if order_dir == 'desc':
        order_field = '-' + order_field
    
    questions = Question.objects.filter(is_deleted=False, chapter_id=pk)
    
    if search_value:
        questions = questions.filter(
            Q(question_description__icontains=search_value) |
            Q(hint__icontains=search_value) 
        )
    
    total_records = questions.count()

    questions = questions.order_by(order_field)
    paginator = Paginator(questions, length)
    page_number = (start // length) + 1
    page_obj = paginator.get_page(page_number)

    data = []
    for question in page_obj:
        options_str = ', '.join(filter(None, question.options)) if question.options else "N/A"
        right_answers_str = ', '.join(filter(None, question.right_answers)) if question.right_answers else "N/A"
        
        if options_str.strip() == "":
            options_str = "N/A"
        if right_answers_str.strip() == "":
            right_answers_str = "N/A"
        
        data.append({
            "id": question.id,
            "question_description": question.question_description if question.question_description else "N/A",
            "hint": question.hint if question.hint else "N/A",
            "options": options_str,
            "right_answers": right_answers_str,
            "created": timezone.localtime(question.created).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    response = {
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data,
    }

    return JsonResponse(response)



@login_required(login_url='dashboard-login')
def chapter_question_add(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 2: 
        chapter=Chapter.objects.get(id=pk,is_deleted=False)
        
        if request.method == 'POST':
            form = QuestionForm(request.POST)  
            if form.is_valid():
                question_type = form.cleaned_data.get('question_type')
                question_description = form.cleaned_data.get('question_description')
                hint = form.cleaned_data.get('hint')
                options = request.POST.getlist('options[]')
                answers = request.POST.getlist('answers[]')

                question = Question(
                    question_type=question_type,
                    question_description=question_description,
                    hint=hint,
                    options=options,
                    right_answers=answers,
                    chapter=chapter
                )
                question.save()
                messages.success(request, "Question added successfully.")
                return redirect('dashboard-chapter-question-list',chapter_id=pk)  
            else:
                return render(request, 'dashboard/content/question/add-lesson-question.html', {'form': form ,'lesson':pk})

        else:
            form = QuestionForm()  

        return render(request, 'dashboard/content/question/add-lesson-question.html', {'form': form ,'lesson':pk})
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def chapter_question_update(request,question_id,chapter_id):
    if request.user.user_type == 1 or request.user.user_type == 2: 
    
        question = get_object_or_404(Question, id=question_id)
        chapter = Chapter.objects.get(id=chapter_id,is_deleted=False)
        
        if request.method == 'POST':
            form = QuestionForm(request.POST, instance=question)  
            if form.is_valid():
                question_type = form.cleaned_data.get('question_type')
                question_description = form.cleaned_data.get('question_description')
                hint = form.cleaned_data.get('hint')
                options = request.POST.getlist('options[]')
                answers = request.POST.getlist('answers[]')

                question.question_type = question_type
                question.question_description = question_description
                question.hint = hint
                question.options = options
                question.right_answers = answers
                question.chapter = chapter
                question.save()

                messages.success(request, "Question updated successfully.")
                return redirect('dashboard-chapter-question-list', chapter_id=chapter.id)  
            else:
                return render(request, 'dashboard/content/lesson/lesson_question_update.html', { 'form': form,
            'question': question,
            'options': question.options,
            'answers': question.right_answers})

        else:
            form = QuestionForm(instance=question)  

        return render(request, 'dashboard/content/lesson/lesson_question_update.html', {'form': form,
            'question': question,
            'options': question.options,
            'answers': question.right_answers})

    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def chapter_question_delete(request,question_id, chapter_id):
    if request.method == 'POST':
        question = get_object_or_404(Question, id=question_id)
        question.is_deleted = True
        question.save()
        messages.success(request, "Question deleted successfully.")
        return redirect('dashboard-chapter-question-list', chapter_id=chapter_id)
    messages.error(request, "Failed to delete question.")
    return redirect('dashboard-chapter-question-list', chapter_id=chapter_id)
    



def upload_question_file(request, chapter_id):
    if request.method == "POST":
        uploaded_file = request.FILES.get('file', None)

        if uploaded_file is None:
            return render(request, 'upload_questions.html', {"error": "No file uploaded."})

        file_extension = uploaded_file.name.split('.')[-1].lower()

        if file_extension == 'docx':
            handle_docx_file(uploaded_file, chapter_id)
        else:
            return render(request, 'upload_questions.html', {"error": "Unsupported file format!"})

        return redirect('dashboard-chapter-question-list', pk=chapter_id)

    return redirect('dashboard-chapter-question-list', pk=chapter_id)


def handle_docx_file(file, chapter_id):
    document = Document(file)

    for table_index, table in enumerate(document.tables):
        num_rows = len(table.rows)
        num_cols = len(table.columns)

        question_desc = table.cell(0, 1).text.strip()
        if not question_desc:
            continue  

        options = []
        correct_answer = None

        for option_index, j in enumerate(range(2, 6)):  
            option_text = table.cell(j, 1).text.strip() 
            option_status = table.cell(j, 2).text.strip().lower()  

            if option_text:
                option_id = option_index + 1
                option_data = {"id": option_id, "text": option_text}
                options.append(option_data)

                if option_status == 'correct':
                    correct_answer = option_data 

        options = [opt for opt in options if opt]

        try:
            marks = float(table.cell(num_rows - 1, 1).text.strip())
        except ValueError:
            marks = 0 

        Question.objects.create(
            question_description=question_desc,
            options=options,
            right_answers=[correct_answer] if correct_answer else [], 
            mark=marks,
            question_type=3, 
            chapter_id=chapter_id
        )

        # print(f"Saved question: {question_desc} with options: {options} and correct answer: {correct_answer}")
