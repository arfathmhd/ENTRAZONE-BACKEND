
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
            end_date = None  # Assuming you meant to set it to None when it's 'null'

        user_filter = Subject.objects.filter(is_deleted=False).order_by('order')

        # Ensure user_list is always assigned
        if start_date and end_date:
            user_filter = user_filter.filter(created__range=[start_date, end_date])

        # Assign user_list after filtering
        if sort_option == 'name_ascending':
            user_list = user_filter.order_by('subject_name')
        elif sort_option == 'name_descending':
            user_list = user_filter.order_by('-subject_name')
        else:
            user_list = user_filter.order_by('order')

        paginator = Paginator(user_list, 25)  # No more UnboundLocalError
        page_number = request.GET.get('page')
        users = paginator.get_page(page_number)

        staff_count = user_filter.count()

        context = {
            "subjects": users,
            "current_sort": sort_option,
            "start_date": start_date,
            "end_date": end_date,
            "staff_count": staff_count,
        }

        return render(request, "dashboard/subject/subject.html", context)

    else:
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
            1: 'subject_name',
            2: 'description',
            3:'course',
        }
        
        order_field = order_columns.get(order_column, 'id')
        if order_dir == 'desc':
            order_field = '-' + order_field
        else:
            order_field = 'order'
        
        subjects = Subject.objects.filter(is_deleted=False)
        
        if search_value:
            subjects = subjects.filter(
                Q(subject_name__icontains=search_value)|
                Q(description__icontains=search_value)|
                Q(course__course_name__icontains=search_value)|
                Q(created__icontains=search_value)
            )
        
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
                "course": subject.course.course_name,
                "description": subject.description,
                "created": timezone.localtime(subject.created).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        response = {
            "draw": draw,
            "recordsTotal": total_records,
            "recordsFiltered": total_records,
            "data": data,
        }

        return JsonResponse(response)






@login_required(login_url='dashboard-login')
def add(request):
    if request.user.user_type == 1 or  request.user.user_type == 2:
        
        if request.method == "POST":
                form = SubjectForm(request.POST, request.FILES)
                if form.is_valid():
                    subject = form.save(commit=False)
                    course= form.cleaned_data.get('course')
                    subject.course = course


                
                    subject.save()

                
                    messages.success(request, "Subject and course information added successfully!")
                    return redirect('dashboard-subject')
                else:
                    context = {
                        "title": "Add Subject",
                        "form": form,
                    }
                    return render(request, "dashboard/subject/add-subject.html", context)
        else:
                form = SubjectForm()  
                context = {
                    "title": "Add Subject ",
                    "form": form,
                }
                return render(request, "dashboard/subject/add-subject.html", context)
    else:
            return redirect('/')


@login_required(login_url='dashboard-login')
def get_max_subject_order(request):
    """AJAX endpoint to get the maximum order value for subjects in a selected course"""
    from django.http import JsonResponse
    from django.db.models import Max
    from dashboard.models import Subject
    
    if request.method == "GET" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        course_id = request.GET.get('course_id')
        if course_id:
            max_order = Subject.objects.filter(course_id=course_id, is_deleted=False).aggregate(
                max_order=Max('order')
            )['max_order'] or 0
            return JsonResponse({'max_order': max_order + 1})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)



@login_required(login_url='dashboard-login')
def update(request, pk):
    if request.user.user_type == 1 or  request.user.user_type == 2:
        subject = get_object_or_404(Subject, pk=pk)
        
        if request.method == "POST":
            form = SubjectForm(request.POST, request.FILES, instance=subject)
            if form.is_valid():
                subject = form.save(commit=False)
                course = form.cleaned_data.get('course')
                subject.course = course
                
                subject.save()
                
                messages.success(request, "Subject and course information updated successfully!")
                return redirect('dashboard-subject')
            else:
                context = {
                    "title": "Update Subject",
                    "form": form,
                }
                return render(request, "dashboard/subject/update-subject.html", context)
        else:
            form = SubjectForm(instance=subject)
            context = {
                "title": "Update Subject",
                "form": form,
            }
            return render(request, "dashboard/subject/update-subject.html", context)
    else:
        return redirect('/')


@login_required(login_url='dashboard-login')
def delete(request,pk):
    if request.method == "POST":
            subject = get_object_or_404(Subject, id=pk)
            subject.is_deleted = True
            subject.save()
            return JsonResponse({"message": "Subject deleted successfully"})
     
    return JsonResponse({"message": "Invalid request"}, status=400)
     