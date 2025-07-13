
from dashboard.views.imports import *


@login_required(login_url='dashboard-login')
def manager(request):
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
    
    user_filter = Schedule.objects.filter(is_deleted=False)
    
    if start_date and end_date:
        user_filter = user_filter.filter(created__range=[start_date, end_date])
 
    elif sort_option == 'name_ascending':
        user_list = user_filter.order_by('created')
    elif sort_option == 'name_descending':
        user_list = user_filter.order_by('-created')
    else:
        user_list = user_filter.order_by('-id')

    paginator = Paginator(user_list, 25)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    staff_count = user_filter.count()

    context = {
        "schedules": users,
        "current_sort": sort_option,
        "start_date": start_date,
        "end_date": end_date,
        "staff_count": staff_count,
    }


    return render(request, "dashboard/content/schedule/schedule.html", context)




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
        1: 'title',
        2: 'lesson',
        3: 'exam',
        4: 'date'
    }
    
    order_field = order_columns.get(order_column, 'id')
    if order_dir == 'desc':
        order_field = '-' + order_field
    
    schedule = Schedule.objects.filter(is_deleted=False)
    
    if search_value:
        schedule = schedule.filter(
            Q(title__icontains=search_value) |
            Q(lesson__lesson_name__icontains=search_value) |
            Q(exam__title__icontains=search_value)
        )
    
    total_records = schedule.count()

    schedule = schedule.order_by(order_field)
    paginator = Paginator(schedule, length)
    page_number = (start // length) + 1
    page_obj = paginator.get_page(page_number)

    data = []
    for schedule in page_obj:
       
        
        data.append({
            "id": schedule.id,
            "title": schedule.title if schedule.title else "N/A",
            "lesson": schedule.lesson.lesson_name if schedule.lesson else "N/A",
            "exam": schedule.exam.title if schedule.exam else "N/A",
            "date":timezone.localtime(schedule.date).strftime('%Y-%m-%d %H:%M:%S')
             
            
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
    if request.method == 'POST':
        form = ScheduleForm(request.POST)  
        if form.is_valid():

            form.save()
            messages.success(request, "Schedule added successfully.")
            return redirect('dashboard-schedule-manager')  
        else:
            return render(request, 'dashboard/content/schedule/add-schedule.html', {'form': form})

    else:
        form = ScheduleForm()  

    return render(request, 'dashboard/content/schedule/add-schedule.html', {'form': form})



@login_required(login_url='dashboard-login')
def update(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    
    if request.method == 'POST':
        form = ScheduleForm(request.POST, instance=schedule)  
        
        if form.is_valid():
            form.save()  
            messages.success(request, "Schedule updated successfully.")
            return redirect('dashboard-schedule-manager')  
        else:
            return render(request, 'dashboard/content/schedule/update-schedule.html', {'form': form})

    else:
        form = ScheduleForm(instance=schedule)  

    return render(request, 'dashboard/content/schedule/update-schedule.html', {'form': form})


@login_required(login_url='dashboard-login')
def delete(request, pk):
    if request.method == 'POST':
        schedule = get_object_or_404(Schedule, pk=pk)
        schedule.is_deleted = True
        schedule.save()
        messages.success(request, 'Schedule deleted successfully.')
        return redirect('dashboard-schedule-manager')
    messages.error(request, 'Failed to delete Schedule.')
    return redirect('dashboard-schedule-manager')
   