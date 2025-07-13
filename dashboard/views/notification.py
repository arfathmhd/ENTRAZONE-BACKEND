from dashboard.views.imports import *
from dashboard.forms.notification import NotificationForm
from dashboard.utils.onesignal import onesignal_request


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

    notification_filter = Notification.objects.filter(is_deleted=False)

    if start_date and end_date:
        notification_filter = notification_filter.filter(created__range=[start_date, end_date])

    if sort_option == 'name_ascending':
        notification_list = notification_filter.order_by('created')  
    elif sort_option == 'name_descending':
        notification_list = notification_filter.order_by('-created')  
    else:
        notification_list = notification_filter.order_by('-id') 

    paginator = Paginator(notification_list, 25)  
    page_number = request.GET.get('page')
    notifications = paginator.get_page(page_number)

    notification_count = notification_filter.count()

    context = {
        "notifications": notifications,
        "current_sort": sort_option,
        "start_date": start_date,
        "end_date": end_date,
        "notification_count": notification_count,
    }

    return render(request, 'dashboard/notification/notification.html', context)




@login_required(login_url='dashboard-login')
def add(request):
    if request.method == 'POST':
        form = NotificationForm(request.POST, request.FILES)  
        if form.is_valid():
            notification = form.save()  
            
            # Send push notification via OneSignal
            try:
                # Prepare image URL if an image was uploaded
                image_url = None
                if notification.image and hasattr(notification.image, 'url'):
                    # Get the full URL including domain
                    image_url = request.build_absolute_uri(notification.image.url)
                
                # Prepare collections for target users
                target_user_ids = []  # For OneSignal (contains phone numbers)
                target_user_objects = []  # For StudentNotification records (contains user objects)
                notification_type = notification.notification_type
                
                if notification_type == 'course':
                    # Get all batches for the selected courses
                    selected_courses = Course.objects.filter(id__in=request.POST.getlist('courses'), is_deleted=False)
                    course_batches = set()
                    for course in selected_courses:
                        course_batches.update(course.batch_set.filter(is_deleted=False))
                    
                    # Get all students subscribed to these batches
                    subscriptions = Subscription.objects.filter(batch__in=course_batches, is_deleted=False)
                    for subscription in subscriptions:
                        if subscription.user.user_type == 0 and not subscription.user.is_deleted:
                            target_user_ids.append(str(subscription.user.phone_number))
                            target_user_objects.append(subscription.user)
                
                elif notification_type == 'batch':
                    # Get all students enrolled in the selected batches
                    subscriptions = Subscription.objects.filter(batch__in=request.POST.getlist('batches'), is_deleted=False)
                    for subscription in subscriptions:
                        if subscription.user.user_type == 0 and not subscription.user.is_deleted:
                            target_user_ids.append(str(subscription.user.phone_number))
                            target_user_objects.append(subscription.user)
                
                elif notification_type == 'student':
                    # Send to selected students
                    students = CustomUser.objects.filter(
                        id__in=request.POST.getlist('students'), 
                        user_type=0, is_deleted=False
                    )
                    # Get phone numbers for OneSignal
                    target_user_ids = list(students.values_list('phone_number', flat=True))
                    # Get actual user objects for StudentNotification
                    target_user_objects = list(students)
                
                # Remove duplicates from target_user_ids (for OneSignal)
                target_user_ids = list(set(target_user_ids))
                
                # Remove duplicates from target_user_objects (for StudentNotification)
                target_user_objects = list(set(target_user_objects))
                
                # Create StudentNotification records based on notification type
                student_notifications = []
                
                if notification_type == 'all':
                    # For 'all' type, create StudentNotification records for all active students
                    all_users = CustomUser.objects.filter(user_type=0, is_deleted=False)
                    for user in all_users:
                        student_notifications.append(StudentNotification(
                            student=user,
                            notification=notification
                        ))
                else:
                    # For other types, use the target_user_objects collected above
                    for user in target_user_objects:
                        student_notifications.append(StudentNotification(
                            student=user,
                            notification=notification
                        ))
                
                # Bulk create student notifications
                if student_notifications:
                    StudentNotification.objects.bulk_create(student_notifications)
                
                # Send the push notification
                response = onesignal_request(
                    heading=notification.title,
                    content=notification.message,
                    image_url=image_url,
                    user_ids=target_user_ids if target_user_ids else None
                )
                
            except Exception as e:
                # Log the error but don't prevent notification creation
                print(f"Error sending push notification: {str(e)}")
            
            messages.success(request, "Notification added successfully and push notification sent!")
            return redirect('dashboard-notification-manager')  
        else:
            messages.error(request, "There was an error adding the notification. Please check the form.")
    else:
        form = NotificationForm()

    context = {
        'form': form,
        'title': 'Add Notification'
    }

    return render(request, 'dashboard/notification/add-notification.html', context)


def update(request, pk):
    notification = get_object_or_404(Notification, id=pk)

    if request.method == 'POST':
        form = NotificationForm(request.POST, request.FILES, instance=notification)
        
        if form.is_valid():
            form.save() 
            messages.success(request, "Notification updated successfully!")
            return redirect('dashboard-notification-manager')  
        else:
            messages.error(request, "There was an error updating the notification. Please check the form.")
    else:
        form = NotificationForm(instance=notification)

    context = {
        'form': form,
        'title': 'Update Notification'
    }

    return render(request, 'dashboard/notification/update-notification.html', context)


def delete(request,pk):
    if request.method == "POST":
            subject = get_object_or_404(Notification, id=pk)
            subject.is_deleted = True
            subject.save()
            return JsonResponse({"message": "Notification deleted successfully"})
     
    return JsonResponse({"message": "Invalid request"}, status=400)
