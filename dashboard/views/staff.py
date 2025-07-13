from dashboard.views.imports import *

@login_required(login_url='dashboard-login')
def manager(request):
    if request.user.user_type == 1 :
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
        
        user_filter = CustomUser.objects.filter(is_deleted=False, is_superuser=False, is_staff=True)
        
        if start_date and end_date:
            user_filter = user_filter.filter(created__range=[start_date, end_date])
        
        if sort_option == 'ascending':
            user_list = user_filter.order_by('id')
        elif sort_option == 'descending':
            user_list = user_filter.order_by('-id')
        elif sort_option == 'name_ascending':
            user_list = user_filter.order_by('name')
        elif sort_option == 'name_descending':
            user_list = user_filter.order_by('-name')
        else:
            user_list = user_filter.order_by('-id')

        paginator = Paginator(user_list, 25)
        page_number = request.GET.get('page')
        users = paginator.get_page(page_number)

        staff_count = user_filter.count()

        context = {
            "users": users,
            "current_sort": sort_option,
            "start_date": start_date,
            "end_date": end_date,
            "staff_count": staff_count,
        }

        return render(request, "dashboard/staff/staffs.html", context)
    else:
        return redirect('/')

def list(request):
    print("hiiiiiiiiiiiiiiiiiiiiiiiiiiii")
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 10))
    search_value = request.GET.get("search[value]", "").strip()
    order_column = int(request.GET.get("order[0][column]", 0))
    order_dir = request.GET.get("order[0][dir]", "desc")

    users = CustomUser.objects.filter(is_deleted=False,is_staff=True)
    print(users)

    order_columns = {
        0: 'id',
        1: 'name',
        4: 'phone_number',
    }

    order_field = order_columns.get(order_column, 'id')
    if order_dir == 'desc':
        order_field = '-' + order_field

    if search_value:
        users = users.filter(
            Q(name__icontains=search_value) |
            Q(phone_number__icontains=search_value) 
        )

    total_records = users.count()

    

    # users = users.order_by(order_field)

    paginator = Paginator(users, length)
    page_number = (start // length) + 1
    page_obj = paginator.get_page(page_number)

    data = []
    for user in page_obj:
       

        

        data.append({
            "id": user.id,
            "username": user.name if user.name else "N/A",
            "phone_number": user.phone_number if user.phone_number else "N/A",
            "created": timezone.localtime(user.created).strftime('%Y-%m-%d %H:%M:%S'),
            "is_disabled": user.is_active 
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
    if request.user.user_type == 1 : 
        if request.method == "POST":
            form = StaffForm(request.POST, request.FILES)
            if form.is_valid():
                customer = form.save(commit=False)
                customer.is_staff = True
                customer.is_active = True

                # Set username dynamically
                if customer.phone_number and customer.name:
                    formatted_name = customer.name.replace(" ", "_").lower()  
                    customer.username = f"{customer.phone_number}_{formatted_name}"
                elif customer.name:
                    customer.username = customer.name.replace(" ", "").lower()
                else:
                    messages.error(
                        request, "Failed to create staff. Name or phone number is required to set the username."
                    )
                    context = {
                        "title": "Add staff | Dashboard",
                        "form": form,
                    }
                    return render(request, "dashboard/staff/add-staff.html", context)

                # Ensure username uniqueness
                if CustomUser.objects.filter(username=customer.username).exists():
                    base_username = customer.username
                    counter = 1
                    while CustomUser.objects.filter(username=f"{base_username}{counter}").exists():
                        counter += 1
                    customer.username = f"{base_username}{counter}"

                customer.save()  # Save the customer after setting username
                messages.success(request, "Staff added successfully!")
                return redirect('dashboard-staff-manager')
            else:
                context = {
                    "title": "Add staff | Dashboard",
                    "form": form,
                }
                return render(request, "dashboard/staff/add-staff.html", context)
        else:
            form = StaffForm()
            context = {
                "title": "Add Customer",
                "form": form,
            }
            return render(request, "dashboard/staff/add-staff.html", context)
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def update(request, pk):
    if request.user.user_type == 1 :
        customer = get_object_or_404(CustomUser, pk=pk)
        if request.method == "POST":
            form = StaffForm(request.POST, request.FILES, instance=customer)
            if form.is_valid():
                updated_customer = form.save(commit=False)
                updated_customer.is_staff = True  
                updated_customer.save()
                messages.success(request, "Customer updated successfully!")
                return redirect('dashboard-staff-manager')
            else:
                context = {
                    "title": "Update Customer | Dashboard",
                    "form": form,
                }
                return render(request, "dashboard/staff/update-staff.html", context)
        else:
            form = StaffForm(instance=customer)
            context = {
                "title": "Update Customer",
                "form": form,
            }
            return render(request, "dashboard/staff/update-staff.html", context)
    else:
        return redirect('/')


@login_required(login_url='dashboard-login')
def disable(request,pk):
    if request.method == "GET":
        customer = get_object_or_404(CustomUser, pk=pk)
        if customer.is_active == False:
            customer.is_active = True
            messages.success(request, "Staff activated successfully!")
        else:
            customer.is_active = False
            messages.error(request, "Staff disabled successfully!")
        customer.save()
      
        return redirect('dashboard-staff-manager')
    else:
        messages.error(request, "Invalid request .")
        return redirect('dashboard-staff-manager')



@login_required(login_url='dashboard-login')
def set_password(request, pk):
    user = CustomUser.objects.get(pk=pk)

    if request.method == 'POST':
        form = PasswordSettingForm(request.POST, user_id=pk)
        if form.is_valid():
            form.save(user)
            messages.success(request, 'Password successfully updated!')
            return redirect('dashboard-staff-manager')
    else:
        form = PasswordSettingForm(user_id=pk)

    return render(request, 'dashboard/staff/password.html', {'form': form, 'pk': pk})


@login_required(login_url='dashboard-login')
def manager_mentor(request):
    mentors = CustomUser.objects.filter(user_type=4, is_active=True)
    batches = Batch.objects.filter(is_deleted=False)
    batch_mentors = BatchMentor.objects.filter(is_deleted=False)
    
    context = {
        'mentors': mentors,
        'batches': batches,
        'batch_mentors': batch_mentors
    }
    
    return render(request, 'dashboard/staff/mentor.html', context)


@login_required(login_url='dashboard-login')
def assign_mentor_to_batch(request):
    """Assign a mentor to multiple batches"""
    if request.method == 'POST':
        try:
            mentor_id = request.POST.get('mentor_id')
            batch_ids = request.POST.get('batch_ids')
            
            if not mentor_id or not batch_ids:
                return JsonResponse({'status': 'error', 'message': 'Mentor and at least one batch are required'})
            
            # Convert comma-separated batch IDs to a list
            batch_id_list = batch_ids.split(',')
            if not batch_id_list:
                return JsonResponse({'status': 'error', 'message': 'No batches selected'})
            
            mentor = CustomUser.objects.get(id=mentor_id)
            
            # Track successful assignments
            successful_assignments = 0
            already_assigned = 0
            failed_assignments = 0
            
            for batch_id in batch_id_list:
                try:
                    batch = Batch.objects.get(id=batch_id, is_deleted=False)
                    
                    # Check if this mentor is already assigned to this batch
                    existing = BatchMentor.objects.filter(mentor=mentor, batch=batch, is_deleted=False).first()
                    if existing:
                        already_assigned += 1
                        continue
                    
                    # Create new assignment
                    BatchMentor.objects.create(mentor=mentor, batch=batch)
                    successful_assignments += 1
                    
                except Batch.DoesNotExist:
                    failed_assignments += 1
                except Exception:
                    failed_assignments += 1
            
            # Prepare response message
            message = f'Successfully assigned mentor to {successful_assignments} batch(es)'
            if already_assigned > 0:
                message += f', {already_assigned} batch(es) were already assigned'
            if failed_assignments > 0:
                message += f', failed to assign {failed_assignments} batch(es)'
            
            return JsonResponse({'status': 'success', 'message': message})
            
        except CustomUser.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Mentor not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@login_required(login_url='dashboard-login')
def remove_mentor_from_batch(request):
    """Remove a mentor from a batch by marking the assignment as deleted"""
    if request.method == 'POST':
        try:
            assignment_id = request.POST.get('assignment_id')
            
            if not assignment_id:
                return JsonResponse({'status': 'error', 'message': 'Assignment ID is required'})
            
            assignment = BatchMentor.objects.get(id=assignment_id)
            assignment.is_deleted = True
            assignment.save()
            
            return JsonResponse({'status': 'success', 'message': 'Mentor removed from batch successfully'})
            
        except BatchMentor.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Assignment not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@login_required(login_url='dashboard-login')
def search_batches(request):
    """Search batches by name for AJAX autocomplete"""
    if request.method == 'GET':
        try:
            query = request.GET.get('query', '')
            
            batches = Batch.objects.filter(
                Q(name__icontains=query) | 
                Q(course__name__icontains=query),
                is_deleted=False
            )[:10]  # Limit to 10 results
            
            results = [{
                'id': batch.id,
                'name': batch.name,
                'course': batch.course.name if batch.course else 'No Course'
            } for batch in batches]
            
            return JsonResponse({'status': 'success', 'results': results})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@login_required(login_url='dashboard-login')
def get_mentor_batches(request):
    """Get batches already assigned to a mentor"""
    if request.method == 'GET':
        try:
            mentor_id = request.GET.get('mentor_id')
            
            if not mentor_id:
                return JsonResponse({'status': 'error', 'message': 'Mentor ID is required'})
            
            # Get all active batch assignments for this mentor
            batch_mentors = BatchMentor.objects.filter(
                mentor_id=mentor_id, 
                is_deleted=False
            ).select_related('batch')
            
            assigned_batches = [{
                'id': bm.batch.id,
                'name': bm.batch.name,
                'course': bm.batch.course.name if bm.batch.course else 'No Course',
                'assignment_id': bm.id
            } for bm in batch_mentors]
            
            return JsonResponse({'status': 'success', 'assigned_batches': assigned_batches})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})