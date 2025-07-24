from django.db.models import Count, Q, Exists, OuterRef
from django.utils import timezone
from dashboard.models import (
    Subscription, 
    Batch, 
    Course, 
    Banner, 
    Notification, 
    StudentNotification, 
    BatchMentor
)

class HomeService:
    """
    Service class for handling home page data operations.
    Follows the service layer pattern to separate business logic from views.
    """
    
    @staticmethod
    def get_course_subscription_count(course):
        """Get the number of unique users subscribed to a course."""
        return Subscription.objects.filter(
            batch__course=course,
            is_deleted=False
        ).values('user').distinct().count()
    
    @staticmethod
    def check_course_completion_status(course):
        """Check if a course is completed (all batches expired)."""
        current_date = timezone.now().date()
        has_active_batches = Batch.objects.filter(
            course=course,
            batch_expiry__gt=current_date,
            is_deleted=False
        ).exists()
        
        # A course is completed if it has no active batches but has at least one batch
        return not has_active_batches and Batch.objects.filter(course=course).exists()
    
    @classmethod
    def get_course_data(cls, course, is_default=False):
        """Get formatted course data including subscription count, completion status, and subjects."""
        subjects = course.subjects.filter(is_deleted=False).order_by('order')
        
        subject_data = [{
            'subject_id': subject.id,
            'subject_name': subject.subject_name,
            'description': subject.description,
            'image': subject.image.url if subject.image else '',
            'is_free': subject.is_free,
            'order': subject.order
        } for subject in subjects]
        
        return {
            'course_id': course.id,
            'course_name': course.course_name,
            'is_default': is_default,
            'subscription_count': cls.get_course_subscription_count(course),
            'is_completed': cls.check_course_completion_status(course),
            'mentors': [], 
            'subjects': subject_data,  
        }
    
    @classmethod
    def get_mentors_for_batch(cls, batch):
        """Get all mentors for a specific batch."""
        batch_mentors = BatchMentor.objects.filter(
            batch=batch, 
            is_deleted=False
        ).select_related('mentor')
        
        mentors = []
        for batch_mentor in batch_mentors:
            if batch_mentor.mentor:
                mentor_info = {
                    'name': batch_mentor.mentor.name or 'Unnamed',
                    'phone_number': batch_mentor.mentor.phone_number or 'No phone'
                }
                mentors.append(mentor_info)
                
        return mentors
    
    @classmethod
    def get_subscribed_courses(cls, user):
        """Get all courses the user is subscribed to with relevant data."""
        default_course_id = user.default_course.id if user.default_course else None
        
        # Get all user subscriptions with related batches
        subscriptions = Subscription.objects.filter(
            user=user, 
            is_deleted=False
        ).prefetch_related('batch')
        
        # Dictionary to track courses and their data
        course_data = {}
        subscribed_course_ids = set()
        
        for subscription in subscriptions:
            for batch in subscription.batch.all():
                course = batch.course
                course_id = course.id
                subscribed_course_ids.add(course_id)
                
                # Initialize course data if not already present
                if course_id not in course_data:
                    course_data[course_id] = cls.get_course_data(
                        course, 
                        is_default=(course_id == default_course_id)
                    )
                
                # Get mentors for this batch and add to course data
                batch_mentors = cls.get_mentors_for_batch(batch)
                
                # Add unique mentors to the course data
                for mentor in batch_mentors:
                    if mentor not in course_data[course_id]['mentors']:
                        course_data[course_id]['mentors'].append(mentor)
        
        # Convert dictionary to list
        subscribed_courses = list(course_data.values())
        
        # Sort: non-completed courses first, then by subscription count (descending)
        subscribed_courses.sort(key=lambda x: (x['is_completed'], -x['subscription_count']))
        
        return subscribed_courses, subscribed_course_ids
    
    @classmethod
    def get_default_course(cls, user, subscribed_course_ids):
        """Get the user's default course if not already in subscribed courses."""
        if not user.default_course or user.default_course.id in subscribed_course_ids:
            return []
            
        default_course = user.default_course
        default_course_data = [cls.get_course_data(default_course, is_default=True)]
        
        return default_course_data
    
    @classmethod
    def get_unsubscribed_courses(cls, subscribed_course_ids):
        """Get all courses the user is not subscribed to."""
        unsubscribed_courses = Course.objects.filter(
            is_deleted=False
        ).exclude(
            id__in=subscribed_course_ids
        )
        
        unsubscribed_courses_data = [
            cls.get_course_data(course) 
            for course in unsubscribed_courses
        ]
        
        # Sort: non-completed courses first, then by subscription count (descending)
        unsubscribed_courses_data.sort(key=lambda x: (x['is_completed'], -x['subscription_count']))
        
        return unsubscribed_courses_data
    
    @staticmethod
    def get_banners():
        """Get all active banners."""
        banners = Banner.objects.filter(is_deleted=False).order_by('-created')
        
        return [{
            'banner_id': banner.id if banner.id else "",
            'banner_image': banner.image.url if banner.image else "",
            'title': banner.title if banner.title else "",
        } for banner in banners]
    
    @classmethod
    def process_notifications(cls, user):
        """Process notifications for the user and return unread count."""
        student_notifications = StudentNotification.objects.filter(
            student=user,
            is_deleted=False
        )
        
        unread_notifications = student_notifications.filter(is_read=False).values_list('notification_id', flat=True)
        unread_count = unread_notifications.count()
        has_unread = unread_count > 0
        
        return has_unread, unread_count
    
    @classmethod
    def get_home_data(cls, user):
        """Get all data needed for the home page."""
        # Get subscribed courses
        subscribed_courses, subscribed_course_ids = cls.get_subscribed_courses(user)
        
        # Get default course if not in subscribed courses
        default_course = cls.get_default_course(user, subscribed_course_ids)
        
        # Combine subscribed and default courses
        combined_courses = subscribed_courses + default_course
        
        # Get unsubscribed courses
        unsubscribed_courses = cls.get_unsubscribed_courses(subscribed_course_ids)
        
        # Get banners
        banners = cls.get_banners()
        
        # Process notifications
        has_unread_notifications, unread_count = cls.process_notifications(user)
        
        return {
            "status": "success",
            "message": "Home data retrieved successfully",
            "subscribed_courses_empty": len(combined_courses) == 0,
            "subscribed_courses": combined_courses,
            "notifications": has_unread_notifications,
            "unread": unread_count,
            "banners": banners,
            "unsubscribed_courses": unsubscribed_courses,
            "is_suspended": user.is_suspended,
            "suspended_date": user.suspended_date,
        }
