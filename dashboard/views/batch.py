from dashboard.views.imports import *
from django.db.models import F, Subquery, OuterRef
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from django.db.models import Sum

@login_required(login_url='dashboard-login')
def manager(request):
    if request.user.user_type == 1 or request.user.user_type == 3 or request.user.user_type == 4:

        sort_option = request.GET.get('sort')
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        
        if start_date and start_date.lower() != 'null':
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start_date = None

        if end_date and end_date.lower() != 'null':
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date() + timedelta(days=1)
        else:
            end_date = None

        # batch_filter = Batch.objects.filter(is_deleted=False, batch_expiry__gte=timezone.now().date())
        batch_filter = Batch.objects.filter(is_deleted=False ).prefetch_related(
            Prefetch(
                'batch_mentors',
                queryset=BatchMentor.objects.filter(is_deleted=False).select_related('mentor'),
                to_attr='active_mentors'
            )
        )
                
        if start_date and end_date:
            batch_filter = batch_filter.filter(start_date__range=[start_date, end_date])
        
        if sort_option == 'name_ascending':
            batches = batch_filter.order_by('batch_name')
        elif sort_option == 'descending':
            batches = batch_filter.order_by('-batch_name')
        else:
            batches = batch_filter.order_by('-id')
            
        # Get today's date for checking if batches have ended
        today = timezone.now().date()
        
        # Create a dictionary to store batch sync info
        batch_sync_info = {}
        
        # For each batch, check if it has new content and hasn't ended yet
        for batch in batch_filter:
            # Check if batch hasn't ended yet
            batch_not_ended = batch.batch_expiry >= today
            
            course = batch.course
            
            # Get all lessons for the course
            all_course_lessons = Lesson.objects.filter(is_deleted=False, chapter__subject__course=course).order_by('order')
            # Get all folders for the course
            all_course_folders = Folder.objects.filter(is_deleted=False, parent_folder=None, chapter__subject__course=course).order_by('order')
            
            # Get existing batch lessons and folders
            existing_lesson_ids = BatchLesson.objects.filter(
                batch=batch, lesson__isnull=False, is_deleted=False
            ).values_list('lesson_id', flat=True)
            
            existing_folder_ids = BatchLesson.objects.filter(
                batch=batch, folder__isnull=False, is_deleted=False
            ).values_list('folder_id', flat=True)
            
            # Find lessons that are not in folders (standalone lessons)
            standalone_lessons = all_course_lessons.filter(folder__isnull=True)
            
            # Find new standalone lessons and new folders
            new_standalone_lessons = standalone_lessons.exclude(id__in=existing_lesson_ids)
            new_folders = all_course_folders.exclude(id__in=existing_folder_ids)
            
            # Count lessons in new folders that would be added
            lessons_in_new_folders_count = 0
            for folder in new_folders:
                lessons_in_new_folders_count += Lesson.objects.filter(folder=folder, is_deleted=False).count()
            
            # Calculate new content counts
            new_standalone_lesson_count = new_standalone_lessons.count()
            new_folder_count = new_folders.count()
            
            # Total new content count (standalone lessons + folders)
            new_content_count = new_standalone_lesson_count + new_folder_count
            
            # Check if there's new content
            has_new_content = new_content_count > 0
            
            # Store sync info for this batch
            batch_sync_info[batch.id] = {
                'has_new_content': has_new_content,
                'new_content_count': new_content_count,
                'new_standalone_lesson_count': new_standalone_lesson_count,
                'new_folder_count': new_folder_count,
                'lessons_in_new_folders_count': lessons_in_new_folders_count,
                'batch_not_ended': batch_not_ended
            }
        
        paginator = Paginator(batches, 25)  
        page_number = request.GET.get('page')
        batches_paginated = paginator.get_page(page_number)

        context = {
            "batches": batches_paginated,
            "current_sort": sort_option,
            "start_date": start_date,
            "end_date": end_date,
            "user": request.user,
            "batch_sync_info": batch_sync_info,
            "today": today
        }

        return render(request, "dashboard/batch/batch.html", context)
    return render(request, "dashboard/home/index.html", context)



@login_required(login_url='dashboard-login')
def add(request):
    if request.user.user_type == 1 or request.user.user_type == 3 or request.user.user_type == 4:
        if request.method == "POST":
            form = BatchForm(request.POST, request.FILES)
            
            if form.is_valid():
                batch = form.save(commit=False)
                start_date = batch.start_date
                course = batch.course 

                current_date = timezone.now().date()
                available_days = (batch.batch_expiry - start_date).days + 1

                course_duration = int(course.duration)
                number_of_lessons = int(course.number_of_lessons)

                # Determine if the batch is late
                if number_of_lessons > available_days: 
                    batch.late_batch = True

                batch.save()

                
                # Calculate lessons distribution when the batch is not late
                total_lessons = number_of_lessons
                course_duration_days = course_duration

                if course_duration_days == 0:
                    lessons_per_day = 0  # or some default behavior
                    messages.warning(request, "Course duration is zero. Default lessons per day set to 0.")
                else:
                    lessons_per_day = total_lessons / course_duration_days

                # Get folders and lessons for the course
                folders = Folder.objects.filter(is_deleted=False, parent_folder=None, chapter__subject__course=course).order_by('order')
                standalone_lessons = Lesson.objects.filter(
                        is_deleted=False, chapter__subject__course=course,
                        folder__isnull=True
                    ).order_by('order')
                
                # Calculate total visible days from folders
                total_visible_days = folders.count() or 0
                
                # Calculate days needed for standalone lessons
                standalone_lessons_days = standalone_lessons.count()
                
                # Calculate total required days
                total_required_days = total_visible_days + standalone_lessons_days
                # Check if we need to scale down due to course duration constraints
                scaling_factor = 1.0
                if total_required_days > course_duration_days and course_duration_days > 0:
                    scaling_factor = course_duration_days / total_required_days
                    messages.info(request, f"Total required days ({total_required_days}) exceeds course duration ({course_duration_days}). Visibility days have been proportionally adjusted.")
                
                # Also check against available days (batch expiry - start date)
                if total_required_days > available_days and available_days > 0:
                    # Use the more restrictive scaling factor
                    available_scaling = available_days / total_required_days
                    if available_scaling < scaling_factor:
                        scaling_factor = available_scaling
                        messages.info(request, f"Total required days ({total_required_days}) exceeds available days ({available_days}). Visibility days have been proportionally adjusted.")
                
                visible_day_count = 1
                max_folder_day = total_visible_days
                
                # Create BatchLessons for folders with adjusted visible days if necessary
                for folder in folders:
                    # Calculate adjusted visible days if scaling is needed
                    if scaling_factor < 1.0:
                        adjusted_days = max(1, int(folder.visible_in_days * scaling_factor))
                    else:
                        adjusted_days = folder.visible_in_days if folder.visible_in_days > 0 else 1
                        
                    BatchLesson.objects.create(
                        batch=batch,
                        folder=folder,
                        visible_in_days=str(adjusted_days),
                    )
                    visible_day_count += adjusted_days
                
                # Calculate adjusted max folder day based on scaling
                if scaling_factor < 1.0:
                    max_folder_day = max(1, int(max_folder_day * scaling_factor))
                
                # Start standalone lessons after the adjusted max folder day
                lesson_start_day = max_folder_day + 1
                
                # Calculate how many days we have left for standalone lessons
                remaining_days = available_days - max_folder_day
                
                # If we have standalone lessons but not enough remaining days, adjust further
                if standalone_lessons.exists() and remaining_days < standalone_lessons.count():
                    # We need to distribute standalone lessons across remaining days
                    standalone_scaling = remaining_days / standalone_lessons.count() if standalone_lessons.count() > 0 else 1.0
                    messages.info(request, f"Standalone lessons ({standalone_lessons.count()}) exceed remaining days ({remaining_days}). Adjusting distribution.")
                else:
                    standalone_scaling = 1.0
                
                # Create BatchLessons for standalone lessons with proper day assignment
                current_day = lesson_start_day
                lessons_per_day = max(1, int(standalone_lessons.count() / remaining_days)) if remaining_days > 0 else 1
                
                for i, lesson in enumerate(standalone_lessons):
                    # Calculate which day this lesson should be on
                    if standalone_scaling < 1.0:
                        # When we need to compress, multiple lessons may share the same day
                        day_index = min(current_day + (i // lessons_per_day), available_days)
                    else:
                        # Otherwise, increment by one day for each lesson
                        day_index = min(current_day + i, available_days)
                    
                    BatchLesson.objects.create(
                        batch=batch,
                        lesson=lesson,
                        visible_in_days=str(day_index),
                    )
                
                # Update the lesson_start_day for the warning message
                if standalone_lessons.exists():
                    lesson_start_day = day_index + 1
                
                # Ensure all content is scheduled within available days
                if lesson_start_day > available_days and standalone_lessons.exists():
                    messages.warning(request, f"Some content may not be visible within the batch expiry period ({available_days} days).")
                    

                messages.success(request, "Batch added successfully!")
                return redirect('dashboard-batch')
            else:
                messages.error(request, "Please correct the errors")

        else:
            form = BatchForm()
        
        context = {
            "title": "Add Batch",
            "form": form,
        }
        return render(request, "dashboard/batch/add-batch.html", context)
    return redirect('/')   



@login_required(login_url='dashboard-login')
def update(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 3 or request.user.user_type == 4:
      
        batch = get_object_or_404(Batch, pk=pk, is_deleted=False)
        
        if request.method == "POST":
            form = BatchForm(request.POST, request.FILES, instance=batch)
            if form.is_valid():
                form.save()
                messages.success(request, "Batch updated successfully!")
                return redirect('dashboard-batch')
            else:
                context = {
                    "title": "Update Batch | Dashboard",
                    "form": form,
                    "batch": batch,
                }
                return render(request, "dashboard/batch/update-batch.html", context)
        else:
            form = BatchForm(instance=batch)
            context = {
                "title": "Update Batch",
                "form": form,
                "batch": batch,
            }
            return render(request, "dashboard/batch/update-batch.html", context)

    return redirect('/')


@login_required(login_url='dashboard-login')
def delete(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 3 :
        if request.method == "POST":
            batch = get_object_or_404(Batch, pk=pk)
            batch.is_deleted = True
            batch.save()
            messages.success(request, "Batch deleted successfully!")
            return redirect('dashboard-batch')
        else:
            messages.error(request, "Invalid request .")
            return redirect('dashboard-batch')
    return redirect('/')

@login_required(login_url='dashboard-login')
def subscription_view(request,pk):
    context={
        "pk": pk 
    }
    return render(request, "dashboard/batch/customer.html",context)


@login_required(login_url='dashboard-login')
def subscription(request, pk): 
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 10))
    search_value = request.GET.get("search[value]", "").strip()
    order_column = int(request.GET.get("order[0][column]", 0))
    order_dir = request.GET.get("order[0][dir]", "desc")

    subscriptions = Subscription.objects.filter(batch__id=pk, is_deleted=False)

    users = CustomUser.objects.filter(
        subscription__in=subscriptions,  
        is_deleted=False
    )

    order_columns = {
        0: 'id',
        1: 'name',
        2: 'email',
        3: 'district',
        4: 'phone_number',
    }
    
    order_field = order_columns.get(order_column, 'id')
    if order_dir == 'desc':
        order_field = '-' + order_field

    if search_value:
        users = users.filter(
            Q(name__icontains=search_value) |
            Q(phone_number__icontains=search_value) |
            Q(district__icontains=search_value) |
            Q(email__icontains=search_value)
        )

    total_records = users.count()

    users = users.order_by(order_field).prefetch_related(
        Prefetch(
            'subscription_set',
            queryset=Subscription.objects.filter(is_deleted=False).prefetch_related('batch__course')
        )
    )

    paginator = Paginator(users, length)
    page_number = (start // length) + 1
    page_obj = paginator.get_page(page_number)

    data = []
    for user in page_obj:
        user_subscriptions = user.subscription_set.filter(batch__id=pk)

        subscription_details = []
        for subscription in user_subscriptions:
            for batch in subscription.batch.all():
                course_name = getattr(batch.course, "course_name", "N/A")
                start_date = batch.start_date.strftime("%d-%m-%Y") if batch.start_date else "N/A"
                expiry_date = batch.batch_expiry.strftime("%d-%m-%Y") if batch.batch_expiry else "N/A"
                subscription_details.append(
                    f'<span style="color: blue;">{course_name}</span> '
                    f'(<span style="color: green;">Start: {start_date}, '
                    f'<span style="color: red;">Expiry: {expiry_date}</span>)'
                )

        subscriptions_display = '<br>'.join(subscription_details) if subscription_details else "N/A"

        data.append({
            "id": user.id,
            "username": user.name if user.name else "N/A",
            "email": user.email if user.email else "N/A",
            "district": user.get_district_display() if user.district else "N/A",
            "phone_number": user.phone_number if user.phone_number else "N/A",
            "batch_names_display": subscriptions_display,
            "created": timezone.localtime(user.created).strftime('%Y-%m-%d %H:%M:%S')
        })

    response = {
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data,
    }

    return JsonResponse(response)



@login_required(login_url='dashboard-login')
def add_customer(request, batch_id):
    if request.user.user_type == 1 or request.user.user_type == 3:    
        if request.method == "POST":
            form = BatchCustomerForm(request.POST, request.FILES)
            if form.is_valid():
                customer = form.save(commit=False)
                customer.save()

                batch = Batch.objects.get(id=batch_id)
                subscription = Subscription.objects.create(user=customer)
            
                subscription.batch.add(batch) 
                subscription.save()

                messages.success(request, "Customer added successfully!")
                return redirect('dashboard-batch-subscripton-manager', pk=batch_id)
            else:
                context = {
                    "title": "Add Customer | Dashboard",
                    "form": form,
                    "batch_id":batch_id
                }
                return render(request, "dashboard/batch/customer_add .html", context)
        else:
            form = BatchCustomerForm()  
            context = {
                "title": "Add Customer",
                "form": form,
                "batch_id":batch_id
            }
            return render(request, "dashboard/batch/customer_add .html", context)

    else:
        return redirect('/')


@login_required(login_url='dashboard-login')
def update_customer(request, batch_id,customer_id):
    if request.user.user_type == 1 or request.user.user_type == 3:
        customer = get_object_or_404(CustomUser, pk=customer_id)
        if request.method == "POST":
            form = CustomerForm(request.POST, request.FILES, instance=customer)
            if form.is_valid():
                updated_customer = form.save(commit=False)
                updated_customer.save()

                batches = form.cleaned_data.get('batches',None)
                subscription = Subscription.objects.get(user=updated_customer)
                subscription.batch .set(batches)  
                subscription.save()

                messages.success(request, "Customer updated successfully!")
                return redirect('dashboard-batch-subscripton-manager',pk=batch_id)
            else:
                context = {
                    "title": "Update Customer | Dashboard",
                    "form": form,
                }
                return render(request, "dashboard/batch/customer_update.html", context)
        else:
            form = CustomerForm(instance=customer)
            context = {
                "title": "Update Customer",
                "form": form,
            }
            return render(request, "dashboard/batch/customer_update.html", context)
    else:
        return redirect('/')


@login_required(login_url='dashboard-login')
def delete_customer(request, customer_id,batch_id):
    if request.user.user_type == 1 or request.user.user_type == 3:
        customer = get_object_or_404(CustomUser, id=customer_id)
        batch = get_object_or_404(Batch, id=batch_id)
        
        # Find the subscription for this customer and batch
        subscription = Subscription.objects.filter(user=customer, batch=batch).first()
        
        if subscription:
            subscription.is_deleted = True
            subscription.save()
            messages.success(request, "Customer subscription deleted successfully!")
        else:
            messages.error(request, "Subscription not found!")
            
        return redirect('dashboard-batch-subscripton-manager', pk=batch_id)
    else:
        return render(request, "dashboard/home/index.html")


@login_required(login_url='dashboard-login')
def batch_students(request, batch_id):
    """View to display all students enrolled in a specific batch"""
    if request.user.user_type in [1, 3, 4]:  # Admin, Admission manager, or Mentor
        batch = get_object_or_404(Batch, id=batch_id, is_deleted=False)
        
        # Get all subscriptions for this batch
        subscriptions = Subscription.objects.filter(
            batch=batch,
            is_deleted=False
        ).select_related('user')
        
        # Get all students from these subscriptions
        students = [subscription.user for subscription in subscriptions]
        
        # Sort students by name
        students.sort(key=lambda x: x.name if x.name else '')
        
        # Pagination
        paginator = Paginator(students, 25)  # Show 25 students per page
        page_number = request.GET.get('page')
        students_paginated = paginator.get_page(page_number)
        
        context = {
            "title": f"Students in {batch.batch_name}",
            "batch": batch,
            "students": students_paginated,
            "total_students": len(students),
        }
        
        return render(request, "dashboard/batch/batch_students.html", context)
    else:
        return render(request, "dashboard/home/index.html")


@login_required(login_url='dashboard-login')
def export_batch_students(request, batch_id):
    """Export students from a batch as Excel or PDF"""
    if request.user.user_type in [1, 3, 4]:  # Admin, Admission manager, or Mentor
        batch = get_object_or_404(Batch, id=batch_id, is_deleted=False)
        
        # Get all subscriptions for this batch
        subscriptions = Subscription.objects.filter(
            batch=batch,
            is_deleted=False
        ).select_related('user')
        
        # Get all students from these subscriptions
        students = [subscription.user for subscription in subscriptions]
        
        # Sort students by name
        students.sort(key=lambda x: x.name if x.name else '')
        
        # Get export format from request (default to excel if not specified)
        export_format = request.GET.get('format', 'excel')
        
        if export_format == 'pdf':
            
            # Create a file-like buffer to receive PDF data
            buffer = BytesIO()
            
            # Create the PDF object using the buffer as its "file"
            doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
            
            # Create styles
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            
            # Container for the 'Flowable' objects
            elements = []
            
            # Add title
            title = Paragraph(f"Students in {batch.batch_name}", title_style)
            elements.append(title)
            elements.append(Spacer(1, 20))
            
            # Create table data
            data = [['Sl No', 'Student Name', 'Phone Number', 'Email']]
            
            # Add student data
            for i, student in enumerate(students, 1):
                data.append([
                    i,
                    student.name if student.name else 'N/A',
                    student.phone_number if student.phone_number else 'N/A',
                    student.email if student.email else 'N/A'
                ])
            
            # Create table
            table = Table(data)
            
            # Add minimal style to table
            style = TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Bold header
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),             # Center align all cells
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),     # Thin border
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8)               # Some padding for header
            ])
            table.setStyle(style)
            
            # Add table to elements
            elements.append(table)
            
            # Build PDF
            doc.build(elements)
            
            # Get the value of the BytesIO buffer and write it to the response
            pdf = buffer.getvalue()
            buffer.close()
            
            # Create the HttpResponse object with PDF header
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{batch.batch_name}_students_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
            response.write(pdf)
            
        else:  # Excel format (default)
            # Create the HttpResponse object with Excel header
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{batch.batch_name}_students_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            
            # Create CSV writer
            writer = csv.writer(response)
            
            # Write header row
            writer.writerow(['Sl No', 'Student Name', 'Phone Number', 'Email'])
            
            # Write data rows
            for i, student in enumerate(students, 1):
                writer.writerow([
                    i, 
                    student.name if student.name else 'N/A',
                    student.phone_number if student.phone_number else 'N/A', 
                    student.email if student.email else 'N/A'
                ])
        
        return response
    else:
        return redirect('dashboard-home')


@login_required(login_url='dashboard-login')
def merge(request):
    merge_days = request.GET.get('merge_days')
    batch_id = request.GET.get('batch_id')

    if not merge_days or int(merge_days) <= 0:
        return HttpResponse("Invalid merge days provided.")

    batch = get_object_or_404(Batch, id=batch_id)
    course = batch.course

    # Clear existing batch lessons
    BatchLesson.objects.filter(batch=batch).delete()

    # Get all folders and lessons
    folders = Folder.objects.filter(
        is_deleted=False,
        parent_folder=None, 
        chapter__subject__course=course
    ).order_by('order')

    standalone_lessons = Lesson.objects.filter(
        is_deleted=False, 
        chapter__subject__course=course,
        folder__isnull=True  # Only get lessons not in folders
    ).order_by('order')

    current_day = 1  # Start with day 1

    # First, handle folders
    for folder in folders:
        
        BatchLesson.objects.create(
            batch=batch,
            folder=folder,
            visible_in_days=str(current_day)
        )
        
        current_day += 1  # Move to next day after handling folder and its lessons

    # Now handle non-folder lessons
    remaining_days = int(merge_days) - len(folders)
    if remaining_days <= 0:
        return JsonResponse({
            'success': False, 
            'message': 'Not enough days to distribute lessons. Increase merge days.'
        })

    total_lessons = len(standalone_lessons)
    lessons_per_day = (total_lessons + remaining_days - 1) // remaining_days  # Ceiling division

    # Distribute remaining lessons
    current_day_lessons = 0

    for lesson in standalone_lessons:
        # Create new day if we've reached lessons per day limit
        if current_day_lessons >= lessons_per_day:
            current_day += 1
            current_day_lessons = 0
            
            # Check if we've exceeded merge days
            if current_day > int(merge_days):
                break

        BatchLesson.objects.create(
            batch=batch,
            lesson=lesson,
            visible_in_days=str(current_day)
        )
        current_day_lessons += 1

    return JsonResponse({
        'success': True,
        'message': 'Lessons successfully merged and scheduled.',
        'folders_count': len(folders),
        'lessons_count': total_lessons,
        'lessons_per_day': lessons_per_day
    })


@login_required(login_url='dashboard-login')
def schedule(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 3:
        batch = get_object_or_404(Batch, id=pk)
        course = batch.course
        
        # Check for new lessons that aren't in the batch yet
        if request.GET.get('sync_lessons') == 'true' or request.method == 'POST' and request.POST.get('sync_lessons'):
            # Get all lessons for the course
            all_course_folders = Folder.objects.filter(is_deleted=False, parent_folder=None, chapter__subject__course=course).order_by('order')
            all_course_standalone_lessons = Lesson.objects.filter(
                is_deleted=False, chapter__subject__course=course,
                folder__isnull=True
            ).order_by('order')
            
            # Get existing batch lessons and folders
            existing_lesson_ids = BatchLesson.objects.filter(
                batch=batch, lesson__isnull=False, is_deleted=False
            ).values_list('lesson_id', flat=True)
            
            existing_folder_ids = BatchLesson.objects.filter(
                batch=batch, folder__isnull=False, is_deleted=False
            ).values_list('folder_id', flat=True)
            
            # Find new standalone lessons and folders
            new_standalone_lessons = all_course_standalone_lessons.exclude(id__in=existing_lesson_ids)
            new_folders = all_course_folders.exclude(id__in=existing_folder_ids)
            
            # Calculate batch duration in days
            batch_duration = (batch.batch_expiry - batch.start_date).days + 1
            
            # Get today's date
            today = timezone.now().date()
            
            # Calculate days elapsed since batch start
            days_elapsed = (today - batch.start_date).days + 1
            days_elapsed = max(1, min(days_elapsed, batch_duration))  # Ensure it's within batch duration
            
            # Calculate days remaining in the batch
            days_remaining = max(0, batch_duration - days_elapsed)
            
            # Get maximum visible day for folders and lessons separately
            max_folder_day_result = BatchLesson.objects.filter(
                batch=batch, folder__isnull=False, is_deleted=False
            ).aggregate(max_day=models.Max('visible_in_days'))
            
            max_lesson_day_result = BatchLesson.objects.filter(
                batch=batch, lesson__isnull=False, folder__isnull=True, is_deleted=False
            ).aggregate(max_day=models.Max('visible_in_days'))
            
            # Get the maximum day for folders and lessons
            max_folder_day = int(max_folder_day_result['max_day'] or days_elapsed)
            max_lesson_day = int(max_lesson_day_result['max_day'] or days_elapsed)
            
            # Count new content
            new_folder_count = new_folders.count()
            new_standalone_lesson_count = new_standalone_lessons.count()
            total_new_items = new_folder_count + new_standalone_lesson_count
            
            # Calculate if we need to scale down due to limited remaining days
            scaling_needed = total_new_items > days_remaining and days_remaining > 0
            scaling_factor = days_remaining / total_new_items if scaling_needed else 1.0
            
            # Calculate days for folders and standalone lessons
            folder_days = new_folder_count
            if scaling_needed:
                folder_days = max(1, int(new_folder_count * scaling_factor))
            
            standalone_lesson_days = days_remaining - folder_days
            standalone_lesson_days = max(0, standalone_lesson_days)
            
            # Start folders after the last folder day
            folder_start_day = max_folder_day + 1
            
            # Add new folders first, starting after the last folder day
            current_folder_day = folder_start_day
            for folder in new_folders:
                # Ensure we don't exceed batch duration
                if current_folder_day > batch_duration:
                    current_folder_day = batch_duration
                
                BatchLesson.objects.create(
                    batch=batch,
                    folder=folder,
                    visible_in_days=str(current_folder_day)
                )
                
                # Increment day counter for next folder
                if current_folder_day < batch_duration:
                    current_folder_day += 1
            
            # Start standalone lessons after the last lesson day
            lesson_start_day = max_lesson_day + 1
            
            # Add standalone lessons
            if new_standalone_lessons.exists():
                # Calculate how many lessons per day we need to fit
                lessons_per_day = 1
                remaining_days_for_lessons = batch_duration - lesson_start_day + 1
                
                if remaining_days_for_lessons > 0 and new_standalone_lesson_count > remaining_days_for_lessons:
                    lessons_per_day = (new_standalone_lesson_count + remaining_days_for_lessons - 1) // remaining_days_for_lessons
                    messages.warning(request, f"Some standalone lessons will share the same visibility day due to limited remaining days.")
                
                # Distribute standalone lessons
                for i, lesson in enumerate(new_standalone_lessons):
                    # Calculate which day this lesson should be on
                    if lessons_per_day > 1:
                        # When we need to compress, multiple lessons may share the same day
                        day_index = min(lesson_start_day + (i // lessons_per_day), batch_duration)
                    else:
                        # Otherwise, increment by one day for each lesson
                        day_index = min(lesson_start_day + i, batch_duration)
                    
                    BatchLesson.objects.create(
                        batch=batch,
                        lesson=lesson,
                        visible_in_days=str(day_index)
                    )
            
            if new_standalone_lessons.count() > 0 or new_folders.count() > 0:
                messages.success(request, f"Added {new_standalone_lessons.count()} new standalone lessons and {new_folders.count()} new folders to the batch.")
            else:
                messages.info(request, "No new lessons or folders found to add to the batch.")
                
            return redirect('dashboard-batch-schedule-manager', pk=pk)

        batch_lessons = BatchLesson.objects.filter(is_deleted=False, batch=batch).order_by('visible_in_days')

        page_number = request.GET.get('page')
        paginator = Paginator(batch_lessons, 25)  
        batch_lessons_paginated = paginator.get_page(page_number)

        # Check if there are any new lessons not in the batch
        # Get all lessons for the course
        all_course_lessons = Lesson.objects.filter(is_deleted=False, chapter__subject__course=course).order_by('order')
        # Get all folders for the course
        all_course_folders = Folder.objects.filter(is_deleted=False, parent_folder=None, chapter__subject__course=course).order_by('order')
        
        # Get existing batch lessons and folders
        existing_lesson_ids = BatchLesson.objects.filter(
            batch=batch, lesson__isnull=False, is_deleted=False
        ).values_list('lesson_id', flat=True)
        
        existing_folder_ids = BatchLesson.objects.filter(
            batch=batch, folder__isnull=False, is_deleted=False
        ).values_list('folder_id', flat=True)
        
        # Find lessons that are not in folders (standalone lessons)
        standalone_lessons = all_course_lessons.filter(folder__isnull=True)
        
        # Find new standalone lessons and new folders
        new_standalone_lessons = standalone_lessons.exclude(id__in=existing_lesson_ids)
        new_folders = all_course_folders.exclude(id__in=existing_folder_ids)
        
        # Count new content
        new_standalone_lesson_count = new_standalone_lessons.count()
        new_folder_count = new_folders.count()
        
        # Check if there's new content
        has_new_content = (new_standalone_lesson_count > 0) or (new_folder_count > 0)

        context = {
            'batch': batch,
            'batch_lessons': batch_lessons_paginated,  
            'paginator': paginator,
            'user': request.user,
            'has_new_content': has_new_content,
            'new_lesson_count': new_standalone_lesson_count,
            'new_folder_count': new_folder_count
        }

        return render(request, 'dashboard/batch/schedule.html', context)
    else:
        return redirect('/')