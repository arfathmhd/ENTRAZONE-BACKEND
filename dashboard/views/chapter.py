
from dashboard.views.imports import *

@login_required(login_url='dashboard-login')
def manager(request):
    if request.user.user_type == 1 or request.user.user_type == 2:
        sort_option = request.GET.get('sort')
        
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)

        if start_date and start_date.lower() != 'null':
            start_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            start_date = None

        if end_date and end_date.lower() != 'null':
            end_date = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            end_date = None
        
        user_filter = Chapter.objects.filter(is_deleted=False)

        # Ensure user_list is always assigned
        if start_date and end_date:
            user_filter = user_filter.filter(created__range=[start_date, end_date])

        # Assign user_list after filtering
        if sort_option == 'name_ascending':
            user_list = user_filter.order_by('chapter_name')
        elif sort_option == 'name_descending':
            user_list = user_filter.order_by('-chapter_name')
        else:
            user_list = user_filter.order_by('order')  # Ensure user_list is always assigned

        paginator = Paginator(user_list, 25)  # No more UnboundLocalError
        page_number = request.GET.get('page')
        users = paginator.get_page(page_number)

        staff_count = user_filter.count()

        context = {
            "chapters": users,
            "current_sort": sort_option,
            "start_date": start_date,
            "end_date": end_date,
            "staff_count": staff_count,
        }

        return render(request, "dashboard/chapter/chapter.html", context)

    return redirect('/')

@login_required(login_url='dashboard-login')
def list(request):
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 10))  
    search_value = request.GET.get("search[value]", "")
    order_column = int(request.GET.get("order[0][column]", 0))
    order_dir = request.GET.get("order[0][dir]", "desc")
    

    order_columns = {
        0: 'id',
        1: 'chapter_name',
        2: 'description',
        3:'subject',
        # 4: 'created',
    }
    
    order_field = order_columns.get(order_column, 'id')
    if order_dir == 'desc':
        order_field = '-' + order_field
    
    chapters = Chapter.objects.filter(is_deleted=False).order_by('-id')
    
    if search_value:
        chapters = chapters.filter(
            Q(chapter_name__icontains=search_value)|
            Q(description__icontains=search_value)|
            Q(subject__subject_name__icontains=search_value)|
            Q(created__icontains=search_value)
        )
    
    total_records = chapters.count()

    chapters = chapters.order_by(order_field)
    paginator = Paginator(chapters, length)
    page_number = (start // length) + 1
    page_obj = paginator.get_page(page_number)

    data = []
    for chapter in page_obj:
        data.append({
            "id": chapter.id,
            "image": chapter.image.url if chapter.image else None,
            "chapter_name": chapter.chapter_name,
            "subject": chapter.subject.subject_name,
            "description": chapter.description,
            "created": timezone.localtime(chapter.created).strftime('%Y-%m-%d %H:%M:%S')

        })
    
    response = {
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data,
    }

    return JsonResponse(response)


from dashboard.forms.chapter import ChapterForm

@login_required(login_url='dashboard-login')
def add(request):
    if request.user.user_type == 1 or request.user.user_type == 2:
        if request.method == "POST":
                form = ChapterForm(request.POST, request.FILES)
                if form.is_valid():
                    chapter = form.save(commit=False)
                    subject = form.cleaned_data.get('subject')
                    chapter.subject = subject
                    chapter.save()

                
                    messages.success(request, "Chapter and subject information added successfully!")
                    return redirect('dashboard-chapter')
                else:
                    context = {
                        "title": "Add Chapter",
                        "form": form,
                    }
                    return render(request, "dashboard//chapter/add-chapter.html", context)
        else:
                form = ChapterForm()  
                context = {
                    "title": "Add Chapter ",
                    "form": form,
                }
                return render(request, "dashboard/chapter/add-chapter.html", context)
    else:
        return redirect('/')



from dashboard.forms.chapter import ChapterForm
@login_required(login_url='dashboard-login')
def update(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 2:
        chapter = get_object_or_404(Chapter, pk=pk)
        
        if request.method == "POST":
            form = ChapterForm(request.POST, request.FILES, instance=chapter)
            if form.is_valid():
                chapter = form.save(commit=False)
                subject = form.cleaned_data.get('subject')
                chapter.subject = subject
                
                chapter.save()
                
                messages.success(request, "Chapter and subject information updated successfully!")
                return redirect('dashboard-chapter')
            else:
                context = {
                    "form": form,
                }
                return render(request, "dashboard/chapter/update-chapter.html", context)
        else:
            form = ChapterForm(instance=chapter)
            context = {
                "form": form,
            }
            return render(request, "dashboard/chapter/update-chapter.html", context)
    else:
        return redirect('/')


@login_required(login_url='dashboard-login')
def delete(request,pk):
    if request.method == "POST":
            chapter = get_object_or_404(Chapter, id=pk)
            chapter.is_deleted = True
            chapter.save()
            return JsonResponse({"message": "Chapter deleted successfully"})
     
    return JsonResponse({"message": "Invalid request"}, status=400)
     