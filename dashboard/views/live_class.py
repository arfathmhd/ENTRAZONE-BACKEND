from dashboard.views.imports import *


from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Prefetch, Count
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.urls import reverse
from django.core.paginator import Paginator
import json

from dashboard.models import LiveClass, BatchLiveClass, Batch, Course


@login_required(login_url='dashboard-login')
def live_class_manager(request):
    """View for managing live classes"""
    if request.user.user_type not in [1, 2]:  # Admin or Teacher
        return redirect('dashboard-home')
    
    current_time = timezone.now()
    
    # Get filter parameters
    platform = request.GET.get('platform', '')
    status = request.GET.get('status', '')
    
    # Base query for live classes
    live_classes_query = LiveClass.objects.filter(is_deleted=False)
    
    # Apply filters
    if platform:
        live_classes_query = live_classes_query.filter(platform=platform)
    
    # Get all live classes with their assignments
    live_classes = []
    upcoming_classes = []
    completed_classes = []
    
    for live_class in live_classes_query:
        # Get assignments (batches and courses)
        batch_live_classes = BatchLiveClass.objects.filter(
            live_class=live_class,
            is_deleted=False
        ).select_related('batch', 'course')
        
        assignments = []
        for blc in batch_live_classes:
            if blc.batch:
                assignments.append({
                    'type': 'batch',
                    'name': blc.batch.batch_name,
                    'id': blc.batch.id
                })
            elif blc.course:
                assignments.append({
                    'type': 'course',
                    'name': blc.course.course_name,
                    'id': blc.course.id
                })
        
        # Create live class data object
        live_class_data = {
            'id': live_class.id,
            'title': live_class.title,
            'description': live_class.description,
            'platform': live_class.platform,
            'meeting_url': live_class.meeting_url,
            'start_time': live_class.start_time,
            'end_time': live_class.end_time,
            'created': live_class.created,
            'is_active': live_class.is_active,
            'assignments': assignments
        }
        
        # Apply status filter and categorize
        if status == 'upcoming' and live_class.end_time <= current_time:
            continue
        elif status == 'completed' and live_class.end_time > current_time:
            continue
        
        # Add to appropriate lists
        live_classes.append(live_class_data)
        
        if live_class.end_time > current_time:
            upcoming_classes.append(live_class_data)
        else:
            completed_classes.append(live_class_data)
    
    # Sort the lists
    live_classes.sort(key=lambda x: x['end_time'], reverse=True)
    upcoming_classes.sort(key=lambda x: x['start_time'], reverse=True)
    completed_classes.sort(key=lambda x: x['end_time'], reverse=True)
    
    # Get all batches and courses for assignment
    batches = Batch.objects.filter(is_deleted=False).select_related('course')
    courses = Course.objects.filter(is_deleted=False)
    
    context = {
        'live_classes': live_classes,
        'upcoming_classes': upcoming_classes,
        'completed_classes': completed_classes,
        'batches': batches,
        'courses': courses,
        'current_time': current_time
    }
    
    return render(request, 'dashboard/live_class/live_class_manager.html', context)


@login_required(login_url='dashboard-login')
@require_POST
def live_class_add(request):
    """Add a new live class"""
    if request.user.user_type not in [1, 2]:  # Admin or Teacher
        return redirect('dashboard-home')
    
    try:
        # Extract form data
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        platform = request.POST.get('platform')
        meeting_url = request.POST.get('meeting_url')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        # Validate required fields
        if not all([title, platform, meeting_url, start_time, end_time]):
            messages.error(request, 'Please fill all required fields')
            return redirect('dashboard-live-class-manager')
        
        # Parse datetime strings to datetime objects and make them timezone-aware
        from datetime import datetime
        try:
            # Parse the datetime strings
            start_datetime = datetime.fromisoformat(start_time)
            end_datetime = datetime.fromisoformat(end_time)
            
            # Make them timezone-aware if they're naive
            if start_datetime.tzinfo is None:
                start_datetime = timezone.make_aware(start_datetime)
            if end_datetime.tzinfo is None:
                end_datetime = timezone.make_aware(end_datetime)
        except ValueError:
            messages.error(request, 'Invalid date/time format')
            return redirect('dashboard-live-class-manager')
        
        # Validate start time is not in the past
        current_time = timezone.now()
        if start_datetime < current_time:
            messages.error(request, 'Start time cannot be in the past')
            return redirect('dashboard-live-class-manager')
        
        # Validate end time is after start time
        if end_datetime <= start_datetime:
            messages.error(request, 'End time must be after start time')
            return redirect('dashboard-live-class-manager')
        
        # Validate class duration is reasonable (not more than 24 hours)
        duration = end_datetime - start_datetime
        if duration.total_seconds() > 24 * 60 * 60:  # 24 hours in seconds
            messages.error(request, 'Live class duration cannot exceed 24 hours')
            return redirect('dashboard-live-class-manager')
        
        # Create new live class with timezone-aware datetimes
        live_class = LiveClass.objects.create(
            title=title,
            description=description,
            platform=platform,
            meeting_url=meeting_url,
            start_time=start_datetime,
            end_time=end_datetime
        )
        
        messages.success(request, f'Live class "{title}" created successfully')
        
    except Exception as e:
        messages.error(request, f'Error creating live class: {str(e)}')
    
    return redirect('dashboard-live-class-manager')


@login_required(login_url='dashboard-login')
@require_POST
def live_class_edit(request):
    """Edit an existing live class"""
    if request.user.user_type not in [1, 2]:  # Admin or Teacher
        return redirect('dashboard-home')
    
    try:
        # Extract form data
        live_class_id = request.POST.get('live_class_id')
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        platform = request.POST.get('platform')
        meeting_url = request.POST.get('meeting_url')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        # Validate required fields
        if not all([live_class_id, title, platform, meeting_url, start_time, end_time]):
            messages.error(request, 'Please fill all required fields')
            return redirect('dashboard-live-class-manager')
        
        # Parse datetime strings to datetime objects
        from datetime import datetime
        try:
            start_datetime = datetime.fromisoformat(start_time)
            end_datetime = datetime.fromisoformat(end_time)
        except ValueError:
            messages.error(request, 'Invalid date/time format')
            return redirect('dashboard-live-class-manager')
        
        # Validate end time is after start time
        if end_datetime <= start_datetime:
            messages.error(request, 'End time must be after start time')
            return redirect('dashboard-live-class-manager')
        
        # Validate class duration is reasonable (not more than 24 hours)
        duration = end_datetime - start_datetime
        if duration.total_seconds() > 24 * 60 * 60:  # 24 hours in seconds
            messages.error(request, 'Live class duration cannot exceed 24 hours')
            return redirect('dashboard-live-class-manager')
        
        # Get and update live class
        live_class = get_object_or_404(LiveClass, id=live_class_id, is_deleted=False)
        
        # For edit, we don't validate if start time is in the past
        # as we might be editing an ongoing or past class
        
        live_class.title = title
        live_class.description = description
        live_class.platform = platform
        live_class.meeting_url = meeting_url
        live_class.start_time = start_time
        live_class.end_time = end_time
        live_class.save()
        
        messages.success(request, f'Live class "{title}" updated successfully')
        
    except Exception as e:
        messages.error(request, f'Error updating live class: {str(e)}')
    
    return redirect('dashboard-live-class-manager')


@login_required(login_url='dashboard-login')
@require_POST
def live_class_delete(request):
    """Soft delete a live class"""
    if request.user.user_type not in [1, 2]:  # Admin or Teacher
        return redirect('dashboard-home')
    
    try:
        # Extract form data
        live_class_id = request.POST.get('live_class_id')
        
        # Get and soft delete live class
        live_class = get_object_or_404(LiveClass, id=live_class_id, is_deleted=False)
        live_class.is_deleted = True
        live_class.save()
        
        # Also soft delete all assignments
        BatchLiveClass.objects.filter(live_class=live_class).update(is_deleted=True)
        
        messages.success(request, f'Live class "{live_class.title}" deleted successfully')
        
    except Exception as e:
        messages.error(request, f'Error deleting live class: {str(e)}')
    
    return redirect('dashboard-live-class-manager')


def send_live_class_notification(live_class, target_type, target_obj):
    """
    Send notification to students when a live class is assigned to a batch or course
    
    Args:
        live_class: The LiveClass instance
        target_type: 'batch' or 'course'
        target_obj: The Batch or Course instance
    """
    from dashboard.models import Notification, Subscription, CustomUser
    from dashboard.utils.onesignal import onesignal_request
    
    # Create notification record
    notification = Notification.objects.create(
        title=f"New Live Class: {live_class.title}",
        message=f"A new live class has been scheduled for {live_class.start_time.strftime('%d %b %Y, %I:%M %p')}.",
        notification_type='batch' if target_type == 'batch' else 'course'
    )
    
    # Link notification to the appropriate target
    if target_type == 'batch':
        notification.batches.add(target_obj)
    else:  # course
        notification.courses.add(target_obj)
    
    # Get target user IDs based on notification type
    target_user_ids = []
    
    if target_type == 'batch':
        # Get all students enrolled in the batch
        subscriptions = Subscription.objects.filter(batch=target_obj, is_deleted=False)
        for subscription in subscriptions:
            if subscription.user.user_type == 0 and not subscription.user.is_deleted:
                # Using phone number as external ID for OneSignal
                if subscription.user.phone_number:
                    target_user_ids.append(str(subscription.user.phone_number))
    
    elif target_type == 'course':
        # Get all batches for the course
        from dashboard.models import Batch
        course_batches = Batch.objects.filter(course=target_obj, is_deleted=False)
        
        # Get all students subscribed to these batches
        subscriptions = Subscription.objects.filter(batch__in=course_batches, is_deleted=False)
        for subscription in subscriptions:
            if subscription.user.user_type == 0 and not subscription.user.is_deleted:
                # Using phone number as external ID for OneSignal
                if subscription.user.phone_number:
                    target_user_ids.append(str(subscription.user.phone_number))
    
    # Remove duplicates
    target_user_ids = list(set(target_user_ids))
    
    # Send push notification if there are target users
    if target_user_ids:
        try:
            # Prepare notification content
            heading = f"New Live Class: {live_class.title}"
            content = f"A new live class has been scheduled for {live_class.start_time.strftime('%d %b %Y, %I:%M %p')}."
            
            # Send the push notification
            onesignal_request(
                heading=heading,
                content=content,
                user_ids=target_user_ids
            )
            
            return len(target_user_ids)
        except Exception as e:
            print(f"Error sending push notification: {str(e)}")
            return 0
    
    return 0

@login_required(login_url='dashboard-login')
def live_class_assign(request):
    """Assign a live class to batches or courses"""
    if request.user.user_type not in [1, 2]:  # Admin or Teacher
        return redirect('dashboard-home')
    
    # Get all live classes
    live_classes = LiveClass.objects.filter(is_deleted=False).order_by('-end_time')
    
    # Get all non-expired batches and courses
    from django.utils import timezone
    current_date = timezone.now().date()
    
    # Get only non-expired batches
    batches = Batch.objects.filter(
        is_deleted=False,
        batch_expiry__gt=current_date  # Only batches that haven't expired
    ).select_related('course').order_by('batch_name')
    
    # Get all active courses
    courses = Course.objects.filter(is_deleted=False).order_by('course_name')
    
    context = {
        'live_classes': live_classes,
        'batches': batches,
        'courses': courses
    }
    
    # Get selected live class if any
    selected_live_class_id = request.GET.get('live_class_id')
    if selected_live_class_id:
        try:
            selected_live_class = LiveClass.objects.get(id=selected_live_class_id, is_deleted=False)
            context['selected_live_class'] = selected_live_class
            context['selected_live_class_id'] = selected_live_class_id
            
            # Get current assignments
            batch_live_classes = BatchLiveClass.objects.filter(
                live_class=selected_live_class,
                is_deleted=False
            ).select_related('batch', 'course')
            
            current_assignments = []
            assigned_batch_ids = []
            assigned_course_ids = []
            
            for blc in batch_live_classes:
                if blc.batch:
                    current_assignments.append({
                        'type': 'batch',
                        'name': blc.batch.batch_name,
                        'assignment_id': blc.id
                    })
                    assigned_batch_ids.append(blc.batch.id)
                elif blc.course:
                    current_assignments.append({
                        'type': 'course',
                        'name': blc.course.course_name,
                        'assignment_id': blc.id
                    })
                    assigned_course_ids.append(blc.course.id)
            
            context['current_assignments'] = current_assignments
            context['assigned_batch_ids'] = assigned_batch_ids
            context['assigned_course_ids'] = assigned_course_ids
            
        except LiveClass.DoesNotExist:
            messages.error(request, 'Live class not found')
    
    # Handle POST request for assigning
    if request.method == 'POST':
        try:
            # Extract form data
            live_class_id = request.POST.get('live_class_id')
            assignment_type = request.POST.get('assignment_type')
            
            # Validate required fields
            if not live_class_id or not assignment_type:
                messages.error(request, 'Missing required fields')
                return redirect('dashboard-live-class-assign')
            
            # Get live class
            live_class = get_object_or_404(LiveClass, id=live_class_id, is_deleted=False)
            
            # Create assignment based on type
            if assignment_type == 'batch':
                batch_ids = request.POST.getlist('batch_ids')
                
                if not batch_ids:
                    messages.error(request, 'Please select at least one batch')
                    return redirect('dashboard-live-class-assign')
                
                # Get existing assignments
                existing_batch_assignments = BatchLiveClass.objects.filter(
                    live_class=live_class,
                    batch__isnull=False,
                    is_deleted=False
                ).values_list('batch_id', flat=True)
                
                # Determine which to add and which to remove
                to_add = [int(bid) for bid in batch_ids if int(bid) not in existing_batch_assignments]
                to_remove = [bid for bid in existing_batch_assignments if bid not in [int(bid) for bid in batch_ids]]
                
                # Add new assignments
                notification_sent_count = 0
                for batch_id in to_add:
                    batch = get_object_or_404(Batch, id=batch_id, is_deleted=False)
                    BatchLiveClass.objects.create(
                        live_class=live_class,
                        batch=batch
                    )
                    
                    # Send notification to students in this batch
                    try:
                        sent_count = send_live_class_notification(live_class, 'batch', batch)
                        notification_sent_count += sent_count
                    except Exception as e:
                        print(f"Error sending notification to batch {batch.batch_name}: {str(e)}")
                
                # Remove assignments that were unchecked
                BatchLiveClass.objects.filter(
                    live_class=live_class,
                    batch_id__in=to_remove
                ).update(is_deleted=True)
                
                if to_add:
                    success_msg = f'Live class assigned to {len(to_add)} batch(es) successfully'
                    if notification_sent_count > 0:
                        success_msg += f' and notifications sent to {notification_sent_count} student(s)'
                    messages.success(request, success_msg)
                if to_remove:
                    messages.info(request, f'Live class unassigned from {len(to_remove)} batch(es)')
                if not to_add and not to_remove:
                    messages.info(request, 'No changes made to batch assignments')
                    
            elif assignment_type == 'course':
                course_ids = request.POST.getlist('course_ids')
                
                if not course_ids:
                    messages.error(request, 'Please select at least one course')
                    return redirect('dashboard-live-class-assign')
                
                # Get existing assignments
                existing_course_assignments = BatchLiveClass.objects.filter(
                    live_class=live_class,
                    course__isnull=False,
                    is_deleted=False
                ).values_list('course_id', flat=True)
                
                # Determine which to add and which to remove
                to_add = [int(cid) for cid in course_ids if int(cid) not in existing_course_assignments]
                to_remove = [cid for cid in existing_course_assignments if cid not in [int(cid) for cid in course_ids]]
                
                # Add new assignments
                notification_sent_count = 0
                for course_id in to_add:
                    course = get_object_or_404(Course, id=course_id, is_deleted=False)
                    BatchLiveClass.objects.create(
                        live_class=live_class,
                        course=course
                    )
                    
                    # Send notification to students in this course
                    try:
                        sent_count = send_live_class_notification(live_class, 'course', course)
                        notification_sent_count += sent_count
                    except Exception as e:
                        print(f"Error sending notification to course {course.course_name}: {str(e)}")
                
                # Remove assignments that were unchecked
                BatchLiveClass.objects.filter(
                    live_class=live_class,
                    course_id__in=to_remove
                ).update(is_deleted=True)
                
                if to_add:
                    success_msg = f'Live class assigned to {len(to_add)} course(s) successfully'
                    if notification_sent_count > 0:
                        success_msg += f' and notifications sent to {notification_sent_count} student(s)'
                    messages.success(request, success_msg)
                if to_remove:
                    messages.info(request, f'Live class unassigned from {len(to_remove)} course(s)')
                if not to_add and not to_remove:
                    messages.info(request, 'No changes made to course assignments')
            else:
                messages.error(request, 'Invalid assignment type')
            
            # Redirect to the same page with the live class selected
            return HttpResponseRedirect(reverse('dashboard-live-class-assign') + f'?live_class_id={live_class_id}')
            
        except Exception as e:
            messages.error(request, f'Error assigning live class: {str(e)}')
            return redirect('dashboard-live-class-assign')
    
    return render(request, 'dashboard/live_class/assign_live_class.html', context)


@login_required(login_url='dashboard-login')
@require_GET
def live_class_get(request):
    """Get live class details for AJAX requests"""
    if request.user.user_type not in [1, 2]:  # Admin or Teacher
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        live_class_id = request.GET.get('live_class_id')
        live_class = get_object_or_404(LiveClass, id=live_class_id, is_deleted=False)
        
        # Get assignments
        batch_live_classes = BatchLiveClass.objects.filter(
            live_class=live_class,
            is_deleted=False
        ).select_related('batch', 'course')
        
        assignments = []
        for blc in batch_live_classes:
            if blc.batch:
                assignments.append({
                    'type': 'batch',
                    'name': blc.batch.batch_name,
                    'id': blc.batch.id
                })
            elif blc.course:
                assignments.append({
                    'type': 'course',
                    'name': blc.course.course_name,
                    'id': blc.course.id
                })
        
        data = {
            'id': live_class.id,
            'title': live_class.title,
            'description': live_class.description,
            'platform': live_class.platform,
            'meeting_url': live_class.meeting_url,
            'start_time': live_class.start_time.isoformat(),
            'end_time': live_class.end_time.isoformat(),
            'is_active': live_class.is_active,
            'assignments': assignments
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required(login_url='dashboard-login')
@require_POST
def live_class_assignment_delete(request):
    """Delete an assignment (batch or course) from a live class"""
    if request.user.user_type not in [1, 2]:  # Admin or Teacher
        return redirect('dashboard-home')
    
    try:
        assignment_id = request.POST.get('assignment_id')
        
        # Get and soft delete assignment
        assignment = get_object_or_404(BatchLiveClass, id=assignment_id, is_deleted=False)
        assignment.is_deleted = True
        assignment.save()
        
        if assignment.batch:
            messages.success(request, f'Assignment to batch removed successfully')
        elif assignment.course:
            messages.success(request, f'Assignment to course removed successfully')
        
    except Exception as e:
        messages.error(request, f'Error removing assignment: {str(e)}')
    
    return redirect('dashboard-live-class-manager')
