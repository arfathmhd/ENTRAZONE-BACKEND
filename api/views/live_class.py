from dashboard.views.imports import *
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils.timezone import localtime
from dashboard.models import BatchLiveClass, LiveClass, Course, Subscription

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def live_class(request):
    current_time = timezone.now()
    user = request.user
    # First get all user subscriptions
    subscriptions = Subscription.objects.filter(user=user, is_deleted=False)

    # Get batches from subscriptions
    subscription_batches = []
    subscription_courses = set()
    for subscription in subscriptions:
        subscription_batches.extend(list(subscription.batch.filter(is_deleted=False)))
        # Get courses from subscriptions
        for batch in subscription.batch.filter(is_deleted=False):
            if batch.course:
                subscription_courses.add(batch.course)

    # Get default course if exists
    default_course = None
    default_course_batches = []
    if user.default_course:
        default_course = user.default_course
        default_course_batches = list(default_course.batch_set.filter(is_deleted=False))

    # Combine all batches and remove duplicates
    all_batches = list(set(subscription_batches + default_course_batches))
    
    # Combine all courses (from subscriptions and default course)
    all_courses = list(subscription_courses)
    if default_course:
        all_courses.append(default_course)

    # Get live classes for these batches and courses
    batch_live_classes = BatchLiveClass.objects.filter(
        Q(batch__in=all_batches) | Q(course__in=all_courses),
        is_deleted=False,
        is_active=True,
        live_class__is_deleted=False,
        live_class__is_active=True
    ).select_related('live_class', 'batch', 'course')

    # Separate upcoming and completed classes
    upcoming_classes = []
    completed_classes = []

    for blc in batch_live_classes:
        # Determine source (batch or course)
        source_name = None
        is_from_subscription = False
        is_from_default_course = False
        source_type = 'batch'  # Default to batch
        
        if blc.batch:
            source_name = blc.batch.batch_name
            is_from_subscription = blc.batch in subscription_batches
            is_from_default_course = blc.batch in default_course_batches
        elif blc.course:
            source_name = blc.course.course_name
            source_type = 'course'
            is_from_subscription = blc.course in subscription_courses
            is_from_default_course = blc.course == default_course
        
        live_class_data = {
            'id': blc.live_class.id,
            'title': blc.live_class.title,
            'description': blc.live_class.description,
            'platform': blc.live_class.platform,
            'meeting_url': blc.live_class.meeting_url,
            'start_time': localtime(blc.live_class.start_time).strftime('%I:%M %p'),
            'end_time': localtime(blc.live_class.end_time).strftime('%I:%M %p'),
            'date': blc.live_class.end_time.strftime('%d %b %Y'),
            'month': blc.live_class.end_time.strftime('%B %Y'),
            'source_name': source_name,
            'source_type': source_type,  # 'batch' or 'course'
            'is_from_subscription': is_from_subscription,
            'is_from_default_course': is_from_default_course,
            'end_time_raw': blc.live_class.end_time  # Store raw datetime object for sorting
        }

        if blc.live_class.end_time > current_time:
            upcoming_classes.append(live_class_data)
        else:
            completed_classes.append(live_class_data)

    # Sort upcoming classes by start_time (earliest first)
    upcoming_classes.sort(key=lambda x: x['end_time_raw'])

    # Sort completed classes by end_time (newest first)
    completed_classes.sort(key=lambda x: x['end_time_raw'], reverse=True)

    # Remove raw datetime after sorting
    for item in upcoming_classes + completed_classes:
        del item['end_time_raw']

    response_data = {
        'upcoming_classes': upcoming_classes,
        'completed_classes': completed_classes,
        'subscription_count': len(subscriptions),
        'has_default_course': user.default_course is not None
    }

    return JsonResponse(response_data)
