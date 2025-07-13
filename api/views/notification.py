from dashboard.views.imports import *
from django.utils import timezone
from django.utils.timezone import localtime
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_notifications(request):
    try:
        # Calculate 24 hours ago from now
        last_24_hours = timezone.now() - timezone.timedelta(hours=24)
        
        # Get all unread notifications that have StudentNotification records for this user
        unread_notifications = Notification.objects.filter(
            is_deleted=False,
            studentnotification__student=request.user,
            studentnotification__is_read=False
        )

        # Get read notifications from last 24 hours that have StudentNotification records for this user
        read_notifications_24h = Notification.objects.filter(
            is_deleted=False,
            created__gte=last_24_hours,
            studentnotification__student=request.user,
            studentnotification__is_read=True
        )

        # Combine both querysets
        notifications = unread_notifications.union(read_notifications_24h).order_by('-created')

        # Rest of the code remains the same
        data = []
        for notification in notifications:
            try:
                student_notification = StudentNotification.objects.get(
                    student=request.user,
                    notification=notification
                )
                if not student_notification.is_read:
                    student_notification.is_read = True
                    student_notification.save()
            except StudentNotification.DoesNotExist:
                continue

            data.append({
                'id': notification.id if notification.id else "",
                'title': notification.title if notification.title else "",
                'message': notification.message if notification.message else "",
                'image': notification.image.url if notification.image else "",
                'created': localtime(notification.created).strftime("%Y-%m-%d %H:%M"),
                'is_read': student_notification.is_read
            })

        return Response({
            "status": "success", 
            "message": "Notifications retrieved successfully",
            "unread": unread_notifications.count(),
            "data": data
        })

    except Exception as e:
        error_message = str(e)
        print(f"Error in unread_notifications: {error_message}")
        return Response({
            "status": "error",
            "message": f"An error occurred: {error_message}",
            "data": []
        }, status=status.HTTP_200_OK)
