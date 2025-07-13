from django.db import transaction
from dashboard.views.imports import *

@login_required(login_url='dashboard-login')
def manager(request):
    if request.user.user_type == 1 or request.user.user_type == 2:
        sort_option = request.GET.get('sort')
        
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)

        if start_date and start_date.lower() != 'null':
            start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y-%m-%d")
        else:
            start_date = None

        if end_date and end_date.lower() != 'null':
            end_date = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            end_date = None
        
        user_filter = Lesson.objects.filter(is_deleted=False).order_by('order')
        
        if start_date and end_date:
            user_filter = user_filter.filter(created__range=[start_date, end_date])
        
        # Assign user_list to avoid UnboundLocalError
        if sort_option == 'name_ascending':
            user_list = user_filter.order_by('created')
        elif sort_option == 'name_descending':
            user_list = user_filter.order_by('-created')
        else:
            user_list = user_filter.order_by('-id')

        paginator = Paginator(user_list, 25)
        page_number = request.GET.get('page')
        users = paginator.get_page(page_number)

        staff_count = user_filter.count()
        folders = Folder.objects.filter(is_deleted=False, parent_folder=None).order_by('order')
        context = {
            "lessons": users,
            "current_sort": sort_option,
            "start_date": start_date,
            "end_date": end_date,
            "staff_count": staff_count,
            "folders": folders,
        }

        return render(request, "dashboard/lesson/lesson.html", context)

    else:
        return redirect('/')



@login_required(login_url='dashboard-login')
def add(request):
    if request.user.user_type == 1 or  request.user.user_type == 2:
    
        if request.method == "POST":
                form = LessonForm(request.POST, request.FILES)
                if form.is_valid():
                    lesson = form.save(commit=False)
                    chapter = form.cleaned_data.get('chapter')
                    visible_in_days = form.cleaned_data.get('visible_in_days')
                    if not lesson.visible_in_days:
                        lesson.visible_in_days = 0
                    else:
                        lesson.visible_in_days = visible_in_days
                    lesson.chapter = chapter
                    lesson.save()

                    video_title = form.cleaned_data.get('video_title')
                    video_url = form.cleaned_data.get('video_url')
                    video_is_downloadable = form.cleaned_data.get('video_is_downloadable')
                    video_is_free = form.cleaned_data.get('video_is_free')
                    tp_stream= form.cleaned_data.get('tp_stream'),
                    m3u8 = form.cleaned_data.get('m3u8')
                    m3u8_is_downloadable = form.cleaned_data.get('m3u8_is_downloadable')
                    m3u8_is_free = form.cleaned_data.get('m3u8_is_free')

                    
                    pdf_title = form.cleaned_data.get('pdf_title')
                    pdf_file = form.cleaned_data.get('pdf_file')
                    pdf_is_downloadable = form.cleaned_data.get('pdf_is_downloadable')
                    pdf_is_free = form.cleaned_data.get('pdf_is_free')

                    if video_url or m3u8 or tp_stream:
                        Video.objects.create(
                            lesson=lesson,
                            title=video_title,
                            url=video_url,
                            is_downloadable=video_is_downloadable,
                            is_free=video_is_free,
                            tp_stream=tp_stream,
                            m3u8=m3u8,  
                            m3u8_is_downloadable=m3u8_is_downloadable,
                            m3u8_is_free=m3u8_is_free,
                        )

                

                    if pdf_file:
                        PDFNote.objects.create(
                            lesson=lesson,
                            title=pdf_title if pdf_title else None,
                            file=pdf_file,
                            is_downloadable=pdf_is_downloadable,
                            is_free=pdf_is_free,
                        )

                    messages.success(request, "Lesson and related content added successfully!")
                    return redirect('dashboard-lesson')
                else:
                    context = {
                        "title": "Add Lesson",
                        "form": form,
                    }
                    return render(request, "dashboard/lesson/add-lesson.html", context)
        else:
                form = LessonForm()  
                context = {
                    "title": "Add Lesson ",
                    "form": form,
                }
                return render(request, "dashboard/lesson/add-lesson.html", context)
    else:
            return redirect('/')
    

@login_required(login_url='dashboard-login')    
def update(request, pk):
    if request.user.user_type == 1 or  request.user.user_type == 2:
    
        lesson = get_object_or_404(Lesson, pk=pk)
        
        if request.method == "POST":
            form = LessonForm(request.POST, request.FILES, instance=lesson)
            if form.is_valid():
                lesson = form.save(commit=False)
                chapter = form.cleaned_data.get('chapter')
                visible_in_days = form.cleaned_data.get('visible_in_days')
                lesson.visible_in_days = visible_in_days
                lesson.chapter = chapter
                lesson.save()
                
                # Update or create video - always update regardless of whether URL is provided
                video_data = {
                    'title': form.cleaned_data.get('video_title'),
                    'url': form.cleaned_data.get('video_url'),
                    'm3u8': form.cleaned_data.get('m3u8'),
                    'tp_stream': form.cleaned_data.get('tp_stream'),
                    'm3u8_is_free': form.cleaned_data.get('m3u8_is_free'),
                    'm3u8_is_downloadable': form.cleaned_data.get('m3u8_is_downloadable'),
                    'is_downloadable': form.cleaned_data.get('video_is_downloadable'),
                    'is_free': form.cleaned_data.get('video_is_free'),
                    'lesson': lesson,
                }
                # Always update video data, even if just the title changes
                Video.objects.update_or_create(lesson=lesson, defaults=video_data)
                
               
                pdf_data = {
                    'title': form.cleaned_data.get('pdf_title'),
                    'is_downloadable': form.cleaned_data.get('pdf_is_downloadable'),
                    'is_free': form.cleaned_data.get('pdf_is_free'),
                    'lesson': lesson,
                }
                if request.FILES.get('pdf_file'):
                    pdf_data['file'] = request.FILES['pdf_file']
                PDFNote.objects.update_or_create(lesson=lesson, defaults=pdf_data)
                
                messages.success(request, "Lesson and related content updated successfully!")
                return redirect('dashboard-lesson')
            else:
                context = {
                    "title": "Update Lesson",
                    "form": form,
                }
                return render(request, "dashboard/lesson/update-lesson.html", context)
        else:
            form = LessonForm(instance=lesson)
            context = {
                "title": "Update Lesson",
                "form": form,
            }
            return render(request, "dashboard/lesson/update-lesson.html", context)
    else:
            return redirect('/')
        

@login_required(login_url='dashboard-login')    
def delete(request, pk):
    if request.method == "POST":
            lesson = get_object_or_404(Lesson, id=pk)
            lesson.is_deleted = True
            lesson.save()
            return JsonResponse({"message": "lesson deleted successfully"})
     
    return JsonResponse({"message": "Invalid request"}, status=400)


@login_required(login_url='dashboard-login')   
def get_courses_subject_chapters(request):
    if request.method == "GET":
        course_id = request.GET.get('course_id', None)
        subject_id = request.GET.get('subject_id', None)
        chapter_id = request.GET.get('chapter_id', None)

        courses = Course.objects.filter(is_deleted=False)
        response_data = {"courses": list(courses.values())}

        if course_id:
            subjects = Subject.objects.filter(is_deleted=False, course_id=course_id).order_by('order')
            response_data["subjects"] = list(subjects.values())
            
            if subject_id:
                chapters = Chapter.objects.filter(is_deleted=False, subject_id=subject_id).order_by('order')
                response_data["chapters"] = list(chapters.values())
                
        if chapter_id:
            # Get root folders (no parent folder)
            folders = Folder.objects.filter(
                is_deleted=False,
                chapter_id=chapter_id,
                parent_folder__isnull=True
            ).order_by('order').values('id', 'title')

            # Get all subfolders and build folder hierarchy
            folder_data = []
            has_folders = False
            for folder in folders:
                subfolders = list(Folder.objects.filter(
                    is_deleted=False,
                    parent_folder_id=folder['id']
                ).order_by('order').values('id', 'title'))
                
                folder_info = {
                    'id': folder['id'],
                    'title': folder['title'],
                    'subfolders': subfolders,
                    'has_subfolders': len(subfolders) > 0
                }
                folder_data.append(folder_info)
                has_folders = True
            
            response_data["folders"] = folder_data
            response_data["has_folders"] = has_folders
        
        return JsonResponse(response_data)


def copy_folder(folder, target_chapter=None, target_parent=None):
    
    # If target_chapter is None and we have a parent folder, use the parent's chapter
    if target_chapter is None and target_parent is not None:
        target_chapter = target_parent.chapter
    # If still None, use the original folder's chapter
    elif target_chapter is None:
        target_chapter = folder.chapter
        
    new_folder = Folder.objects.create(
        title=folder.title,
        chapter=target_chapter,
        parent_folder=target_parent,
        name=folder.name,
        is_deleted=folder.is_deleted,
    )

    # Copy lessons under this folder
    for lesson in folder.lesson_set.all():
        copy_lesson(lesson, target_chapter=target_chapter, target_folder=new_folder)

    # Copy subfolders recursively - pass the target_chapter to ensure it's not None
    for sub in folder.sub_folders.all():
        copy_folder(sub, target_chapter=target_chapter, target_parent=new_folder)

    return new_folder

def copy_lesson(lesson, target_chapter=None, target_folder=None):
    # If target_folder is provided, use its chapter and set folder
    # If no target_folder, use target_chapter directly and set folder to None
    new_lesson = Lesson.objects.create(
        folder=target_folder,
        chapter=target_folder.chapter if target_folder else target_chapter,
        lesson_name=lesson.lesson_name,
        image=lesson.image,
        description=lesson.description,
        visible_in_days=lesson.visible_in_days,
        is_free=lesson.is_free,
        is_deleted=lesson.is_deleted,
    )

    # Copy related Videos
    for video in lesson.videos.all():
        Video.objects.create(
            lesson=new_lesson,
            title=video.title,
            url=video.url,
            m3u8=video.m3u8,
            tp_stream=video.tp_stream,
            is_downloadable=video.is_downloadable,
            is_free=video.is_free,
            m3u8_is_downloadable=video.m3u8_is_downloadable,
            m3u8_is_free=video.m3u8_is_free,
            created=video.created,
            is_deleted=video.is_deleted,
        )

    # Copy related PDFNotes
    for note in lesson.pdf_notes.all():
        PDFNote.objects.create(
            lesson=new_lesson,
            title=note.title,
            file=note.file,
            is_downloadable=note.is_downloadable,
            is_free=note.is_free,
            created=note.created,
            is_deleted=note.is_deleted,
        )

    return new_lesson

def move_folder(folder, target_chapter=None, target_parent=None):
    @transaction.atomic
    def _move(f, new_chapter, new_parent):
        # Update folder's references
        f.chapter = new_chapter if not new_parent else new_parent.chapter
        f.parent_folder = new_parent
        f.save()

        # Update all lessons in this folder
        for lesson in f.lesson_set.all():
            lesson.chapter = None  # Clear chapter reference since it's in folder
            lesson.folder = f      # Keep folder reference
            lesson.save()

        # Recursively update all subfolders
        for sub in f.sub_folders.all():
            _move(sub, new_chapter=f.chapter, new_parent=f)

    _move(folder, target_chapter, target_parent)

def move_lesson(lesson, target_chapter=None, target_folder=None):
    # Case 1: Moving to a folder
    if target_folder:
        lesson.folder = target_folder
        lesson.chapter = None  # Clear chapter reference since folder has chapter
    # Case 2: Moving directly to a chapter
    elif target_chapter:
        lesson.folder = None  # Clear folder reference
        lesson.chapter = target_chapter
    # Save the changes
    lesson.save()


def copy_folder_view(request, folder_id):
    folder = get_object_or_404(Folder, id=folder_id)

    if request.method == 'POST':
        target_chapter_id = request.POST.get('target_chapter_id')
        target_folder_id = request.POST.get('target_folder_id')
        
        try:
            chapter = Chapter.objects.filter(id=target_chapter_id).first() if target_chapter_id else None
            parent_folder = Folder.objects.filter(id=target_folder_id).first() if target_folder_id else None
            copy_folder(folder, target_chapter=chapter, target_parent=parent_folder)
            return JsonResponse({'status': 'success', 'message': 'Folder copied successfully'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


def move_folder_view(request, folder_id):
    folder = get_object_or_404(Folder, id=folder_id)

    if request.method == 'POST':
        target_chapter_id = request.POST.get('target_chapter_id')
        target_folder_id = request.POST.get('target_folder_id')

        try:
            chapter = Chapter.objects.filter(id=target_chapter_id).first() if target_chapter_id else None
            parent_folder = Folder.objects.filter(id=target_folder_id).first() if target_folder_id else None

            move_folder(folder, target_chapter=chapter, target_parent=parent_folder)
            return JsonResponse({'status': 'success', 'message': 'Folder moved successfully'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

def copy_lesson_view(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if request.method == 'POST':
        target_chapter_id = request.POST.get('target_chapter_id')
        target_folder_id = request.POST.get('target_folder_id')

        try:
            chapter = Chapter.objects.filter(id=target_chapter_id).first() if target_chapter_id else None
            folder = Folder.objects.filter(id=target_folder_id).first() if target_folder_id else None

            copy_lesson(lesson, target_chapter=chapter, target_folder=folder)
            return JsonResponse({'status': 'success', 'message': 'Lesson copied successfully'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


def move_lesson_view(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if request.method == 'POST':
        target_chapter_id = request.POST.get('target_chapter_id')
        target_folder_id = request.POST.get('target_folder_id')

        try:
            chapter = Chapter.objects.filter(id=target_chapter_id).first() if target_chapter_id else None
            folder = Folder.objects.filter(id=target_folder_id).first() if target_folder_id else None

            move_lesson(lesson, target_chapter=chapter, target_folder=folder)
            return JsonResponse({'status': 'success', 'message': 'Lesson moved successfully'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
