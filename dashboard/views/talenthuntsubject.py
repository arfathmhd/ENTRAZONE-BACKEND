
from dashboard.views.imports import *

@login_required(login_url='dashboard-login')
def manager(request, pk):
    if request.user.user_type == 1 or  request.user.user_type == 2:
    
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        sort_option = request.GET.get('sort')

        if start_date and start_date.lower() != 'null':
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                start_date = None

        if end_date and end_date.lower() != 'null':
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date() + timedelta(days=1)  
            except ValueError:
                end_date = None

        talenthunt_subject_filter = TalentHuntSubject.objects.filter(is_deleted=False, talentHunt=pk)

        if start_date and end_date:
            talenthunt_subject_filter = talenthunt_subject_filter.filter(created__range=[start_date, end_date])

        if sort_option == 'name_ascending':
            talenthunt_subject_filter = talenthunt_subject_filter.order_by('title')
        elif sort_option == 'name_descending':
            talenthunt_subject_filter = talenthunt_subject_filter.order_by('-title')

        paginator = Paginator(talenthunt_subject_filter, 25)
        page_number = request.GET.get('page')
        talenthunts_subject_paginated = paginator.get_page(page_number)

        context = {
            "talenthunts": talenthunts_subject_paginated,
            "start_date": start_date,
            "end_date": end_date,
            "current_sort": sort_option,
            "pk": pk  
        }

        return render(request, 'dashboard/talenthunt/talenthunt-subject.html', context)
    else:
        return redirect ('/')

@login_required(login_url='dashboard-login')
def list(request,pk):
    
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
        # 4: 'created',
    }
    
    order_field = order_columns.get(order_column, 'id')
    if order_dir == 'desc':
        order_field = '-' + order_field
    
    talenthunt = TalentHuntSubject.objects.filter(is_deleted=False,talentHunt=pk)
    
    if search_value:
        talenthunt = talenthunt.filter(
            Q(subject_name__icontains=search_value)|
            Q(description__icontains=search_value)|
            Q(created__icontains=search_value)
        )
    
    total_records = talenthunt.count()

    talenthunt = talenthunt.order_by(order_field)
    paginator = Paginator(talenthunt, length)
    page_number = (start // length) + 1
    page_obj = paginator.get_page(page_number)

    data = []
    for talenthunt in page_obj:
        data.append({
            "id": talenthunt.id,
            "title":talenthunt.title if  talenthunt.title else "N/A",
            "subject": talenthunt.subject.subject_name if talenthunt.subject else "N/A",
            # "created": talenthunt.created.strftime('%Y-%m-%d %I:%M %p')
             "created": timezone.localtime(talenthunt.created).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    response = {
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data,
    }

    return JsonResponse(response)




@login_required(login_url='dashboard-login')
def add(request, pk):
    if request.user.user_type == 1 or  request.user.user_type == 2:
    
        try:
            talenthunt = TalentHunt.objects.get(id=pk, is_deleted=False)
        except TalentHunt.DoesNotExist:
            messages.error(request, "TalentHunt not found.")
            return redirect('dashboard-talenthunt-subject-manager',pk)
        
        if request.method == "POST":
            form = TalentHuntSubjectForm(request.POST, request.FILES, course=talenthunt.course)
            if form.is_valid():
                subject = form.cleaned_data.get('subject')
                talenthuntsubject = form.save(commit=False)
                talenthuntsubject.subject = subject
                talenthuntsubject.talentHunt = talenthunt
                talenthuntsubject.save()

                messages.success(request, "TalentHunt added successfully!")
                return redirect('dashboard-talenthunt-subject-manager', pk)
            else:
                context = {
                    "title": "Add Subject",
                    "form": form,
                    "pk": pk
                }
                return render(request, "dashboard/talenthunt/talenthunt-subject-add.html", context)
        else:
            form = TalentHuntSubjectForm(course=talenthunt.course)
            context = {
                "title": "Add TalentHunt",
                "form": form,
                "pk": pk
            }
            return render(request, "dashboard/talenthunt/talenthunt-subject-add.html", context)
    else:
        return redirect ('/')



@login_required(login_url='dashboard-login')
def update(request, pk):
    if request.user.user_type == 1 or  request.user.user_type == 2:
    
        try:
            talenthuntsubject = TalentHuntSubject.objects.get(id=pk)
            talenthunt = talenthuntsubject.talentHunt
        except TalentHuntSubject.DoesNotExist:
            messages.error(request, "TalentHuntSubject not found.")
            return redirect('dashboard-talenthunt-subject-manager', pk)

        if request.method == "POST":
            form = TalentHuntSubjectForm(request.POST, request.FILES, instance=talenthuntsubject, course=talenthunt.course)
            if form.is_valid():

                form.save()
                messages.success(request, "TalentHuntSubject updated successfully!")
                return redirect('dashboard-talenthunt-subject-manager', pk=talenthunt.id)
            else:
                context = {
                    "title": "Update TalentHuntSubject",
                    "form": form,
                    "pk": pk
                }
                return render(request, "dashboard/talenthunt/talenthunt-subject-update.html", context)
        else:
            form = TalentHuntSubjectForm(instance=talenthuntsubject, course=talenthunt.course)
            context = {
                "title": "Update TalentHuntSubject",
                "form": form,
                "pk": pk
            }
            return render(request, "dashboard/talenthunt/talenthunt-subject-update.html", context)
    else:
        return redirect ('/')

@login_required(login_url='dashboard-login')
def delete(request, pk):
    if request.method == "POST":
        talenthuntsubject = get_object_or_404(TalentHuntSubject, pk=pk, is_deleted=False)

        talenthuntsubject.is_deleted = True
        talenthuntsubject.save()

        messages.success(request, "TalentHuntSubject deleted successfully!")
        return redirect('dashboard-talenthunt-subject-manager',pk)
    else:
        messages.error(request, "Invalid request method.")
        return redirect('dashboard-talenthunt-subject-manager')






@login_required(login_url='dashboard-login')
def fetch_course_subjects(request):
    course_id = request.GET.get('course_id')
    if course_id:
        subjects = Subject.objects.filter(course_id=course_id, is_deleted=False).order_by('order')
        subjects_data = [{'id': subject.id, 'name': subject.subject_name} for subject in subjects]
        return JsonResponse({'subjects': subjects_data})
    else:
        return JsonResponse({'subjects': []}, status=400) 
    






