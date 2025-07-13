from dashboard.views.imports import *


@login_required(login_url='dashboard-login')
def manager(request, folder_id):
    if request.user.user_type == 1 or  request.user.user_type == 2:
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

        folders = Folder.objects.filter(parent_folder_id=folder_id, is_deleted=False).order_by('order')
        exams = Exam.objects.filter(folder=folder_id, is_deleted=False)
        current_folder = Folder.objects.filter(id=folder_id, is_deleted=False).last()
        lessons = Lesson.objects.filter(folder=folder_id, is_deleted=False).order_by('order')

        if start_date and end_date:
            lessons = lessons.filter(created__range=[start_date, end_date])

        if sort_option == 'name_ascending':
            lessons = lessons.order_by('lesson_name')  
        elif sort_option == 'name_descending':
            lessons = lessons.order_by('-lesson_name')
        else:
            lessons = lessons.order_by('order')  

        chapter = None
        if lessons.exists():
            # Get chapter directly from lesson
            first_lesson = lessons.first()
            if first_lesson.chapter:
                chapter = first_lesson.chapter
            elif first_lesson.folder:
                chapter = first_lesson.folder.chapter

        chapter_id = chapter.id if chapter else None
        # print(f"Chapter ID: {chapter_id}")

        paginator = Paginator(lessons, 25)  
        page_number = request.GET.get('page')
        paginated_lessons = paginator.get_page(page_number)
        context = {
            "folder_id": folder_id,
            "folders": folders,  
            "lessons": paginated_lessons,
            "current_sort": sort_option,
            "start_date": start_date,
            "end_date": end_date,
            "lesson_count": lessons.count(),  
            "chapter": chapter_id,
            "current_folder": current_folder,
            "exams": exams,
        }

        return render(request, "dashboard/content/folder/folder.html", context)

    else:
        return redirect('/')

#adding folder inside the lesson

@csrf_exempt
def add(request):
    if request.user.user_type == 1 or  request.user.user_type == 2:
        if request.method == 'POST':
            data = json.loads(request.body.decode("utf-8"))
            folder_name = data.get('folder_name')
            visible_in_days = data.get('visible_in_days', 0)
            chapter_id = data.get('chapter_id', None)
            parent_id = data.get('parent_id', None)

            if not folder_name:
                return JsonResponse({'success': False, 'error': 'Folder name is required'})

            if chapter_id is not None and parent_id is None:
                try:
                    chapter = Chapter.objects.get(id=chapter_id)
                    folder = Folder.objects.create(title=folder_name, chapter=chapter, visible_in_days=visible_in_days)

                    return JsonResponse({'success': True, 'folder_id': folder.id})
                except Chapter.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Chapter not found'})
            elif parent_id is not None:
                parent_folder = Folder.objects.get(id=parent_id)
                folder = Folder.objects.create(title=folder_name, parent_folder=parent_folder, chapter=parent_folder.chapter, visible_in_days=visible_in_days)
                return JsonResponse({'success': True, 'folder_id': folder.id})

            return JsonResponse({'success': False, 'error': 'Invalid request'})

        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    else:
        return redirect('/')



@csrf_exempt  
def update(request):
    if request.user.user_type == 1 or  request.user.user_type == 2:
        if request.method == "POST":
            try:
                data = json.loads(request.body)
                folder_id = data.get('folder_id')
                new_folder_name = data.get('new_folder_name')
                visible_in_days = data.get('new_visible_in_days', 0)

                if not folder_id or not new_folder_name:
                    return JsonResponse({'success': False, 'error': 'Folder ID and new name are required.'})

                folder = get_object_or_404(Folder, pk=folder_id)

                folder.title = new_folder_name
                folder.visible_in_days = visible_in_days
                folder.save()

                return JsonResponse({'success': True})

            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})

        return JsonResponse({'success': False, 'error': 'Invalid request method.'})
    else:
        return redirect('/')

def delete(request):
    try:
        data = json.loads(request.body)  
        pk = data.get('folder_id')
        folder = Folder.objects.get(id=pk)
        folder.is_deleted = True
        folder.save()
        return JsonResponse({'success': True})
    except Folder.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Folder not found.'}, status=404)
  


  
from dashboard.forms.content.lesson import LessonForm  as LessonFormFolder
def lesson_add(request, pk):
    if request.user.user_type == 1 or  request.user.user_type == 2:

        try:
            chapter = Folder.objects.get(id=pk, is_deleted=False)
        except Folder.DoesNotExist:
            messages.error(request, "Folder not found.")
            return redirect('dashboard-course')

        if request.method == 'POST':
            form = LessonFormFolder(request.POST, request.FILES)
            if form.is_valid():
                lesson = form.save(commit=False)
                lesson.folder = chapter
                visible_in_days = form.cleaned_data.get('visible_in_days')
                lesson.visible_in_days = visible_in_days if visible_in_days else 0
                lesson.save()

                video_title = form.cleaned_data.get('video_title')
                video_url = form.cleaned_data.get('video_url')
                video_is_downloadable = form.cleaned_data.get('video_is_downloadable')
                video_is_free = form.cleaned_data.get('video_is_free')
                m3u8 = form.cleaned_data.get('m3u8')
                tp_stream = form.cleaned_data.get('tp_stream')
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
                        m3u8=m3u8,
                        tp_stream=tp_stream,
                        m3u8_is_downloadable=m3u8_is_downloadable,
                        m3u8_is_free=m3u8_is_free,
                    )

                if pdf_file is not None:
                    PDFNote.objects.create(
                        lesson=lesson,
                        title=pdf_title if pdf_title else None,
                        file=pdf_file,
                        is_downloadable=pdf_is_downloadable,
                        is_free=pdf_is_free,
                    )

                messages.success(request, "Lesson added successfully!")
                return redirect('dashboard-folder', folder_id=pk)
            else:
                # Log form errors
                print(form.errors)  # Output the errors for debugging
                for error in form.non_field_errors():
                    messages.error(request, error)
                # messages.error(request, form.errors)

        else:
            form = LessonFormFolder()

        context = {
            "form": form,
            "chapter": pk,
            "current_folder": chapter,
        }
        return render(request, "dashboard/content/folder/add-lesson.html", context)
    else:
        return redirect('/')


@login_required(login_url='dashboard-login')
def lesson_update(request, pk, folder_id):
    if request.user.user_type == 1 or  request.user.user_type == 2:
    
        lesson = get_object_or_404(Lesson, id=pk, is_deleted=False)
        folder = get_object_or_404(Folder, id=folder_id, is_deleted=False)

        # Fetch existing Video and PDFNote related to the lesson
        video = Video.objects.filter(lesson=lesson).first()
        pdf = PDFNote.objects.filter(lesson=lesson).first()

        if request.method == 'POST':
            form = LessonFormFolder(request.POST, request.FILES, instance=lesson)
            if form.is_valid():
                lesson = form.save(commit=False)
                lesson.folder = folder
                visible_in_days = form .cleaned_data.get('visible_in_days')
                if not lesson.visible_in_days:
                    lesson.visible_in_days = 0
                else:
                    lesson.visible_in_days = visible_in_days
                lesson.save()
                video_title = form.cleaned_data.get('video_title')
                video_url = form.cleaned_data.get('video_url')
                video_is_downloadable = form.cleaned_data.get('video_is_downloadable')
                video_is_free = form.cleaned_data.get('video_is_free')
                m3u8 = form.cleaned_data.get('m3u8')
                tp_stream = form.cleaned_data.get('tp_stream')
                m3u8_is_downloadable = form.cleaned_data.get('m3u8_is_downloadable')
                m3u8_is_free = form.cleaned_data.get('m3u8_is_free')
                # Update or create video
                if video_title:
                    Video.objects.update_or_create(
                        lesson=lesson,
                        defaults={
                            'title': video_title,
                            'url': video_url,
                            'is_downloadable': video_is_downloadable,
                            'is_free': video_is_free,
                            'm3u8': m3u8,
                            'tp_stream': tp_stream,
                            'm3u8_is_downloadable': m3u8_is_downloadable,
                            'm3u8_is_free': m3u8_is_free,
                        }
                    )

                pdf_title = form.cleaned_data.get('pdf_title')
                pdf_file = form.cleaned_data.get('pdf_file')
                pdf_is_downloadable = form.cleaned_data.get('pdf_is_downloadable')
                pdf_is_free = form.cleaned_data.get('pdf_is_free')

                # Update or create PDF
                if pdf_title:
                    PDFNote.objects.update_or_create(
                        lesson=lesson,
                        defaults={
                            'title': pdf_title if pdf_title else None,
                            'file': pdf_file,
                            'is_downloadable': pdf_is_downloadable,
                            'is_free': pdf_is_free,
                        }
                    )

                messages.success(request, "Lesson updated successfully!")
                return redirect('dashboard-folder', folder_id=folder_id)
            else:
                # Log form errors
                print(form.errors)  # Output the errors for debugging
                for error in form.non_field_errors():
                    messages.error(request, error)
        else:
            # # Prepopulate form with existing video and PDF data
            initial_data = {
                'video_title': video.title if video else '',
                'video_url': video.url if video else '',
                'video_is_downloadable': video.is_downloadable if video else False,
                'video_is_free': video.is_free if video else False,
                'm3u8': video.m3u8 if video else '',
                'tp_stream': video.tp_stream if video else '',
                'm3u8_is_downloadable': video.m3u8_is_downloadable if video else False,
                'm3u8_is_free': video.m3u8_is_free if video else False,
                    
                'pdf_title': pdf.title if pdf else '',
                'pdf_file': pdf.file if pdf else None,
                'pdf_is_downloadable': pdf.is_downloadable if pdf else False,
                'pdf_is_free': pdf.is_free if pdf else False,
            }
            form = LessonFormFolder(instance=lesson, initial=initial_data)

        context = {
            "title": "Update Lesson",
            "form": form,
        }
        return render(request, "dashboard/content/folder/update-lesson.html", context)

    else:
        return redirect('/')



@login_required(login_url='dashboard-login')
def lesson_delete(request, folder_id, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    lesson.is_deleted = True
    lesson.save()

    return redirect('dashboard-folder', folder_id=folder_id)
