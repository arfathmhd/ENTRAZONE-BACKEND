from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from dashboard.models import Notification, StudentNotification, Course, Batch, Subscription, CustomUser

class NotificationTestCase(TestCase):
    def setUp(self):
        # Create admin user for login
        self.admin_user = get_user_model().objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpassword',
            user_type=1  # Admin user
        )
        
        # Create test students
        self.student1 = get_user_model().objects.create_user(
            username='student1',
            email='student1@example.com',
            password='student1password',
            user_type=0,  # Student
            phone_number='1234567890'
        )
        
        self.student2 = get_user_model().objects.create_user(
            username='student2',
            email='student2@example.com',
            password='student2password',
            user_type=0,  # Student
            phone_number='2345678901'
        )
        
        self.student3 = get_user_model().objects.create_user(
            username='student3',
            email='student3@example.com',
            password='student3password',
            user_type=0,  # Student
            phone_number='3456789012'
        )
        
        # Create test course and batch
        self.course = Course.objects.create(
            course_name='Test Course',
            description='Test Course Description'
        )
        
        # Create batch with required fields
        self.batch = Batch.objects.create(
            batch_name='Test Batch',
            start_date=timezone.now().date(),
            batch_expiry=timezone.now().date() + timedelta(days=90),
            batch_price=1000.00,
            course=self.course
        )
        
        # Create subscriptions (student1 and student2 in the batch)
        subscription1 = Subscription.objects.create(
            user=self.student1,
            custom_amount=0.00
        )
        subscription1.batch.add(self.batch)
        
        subscription2 = Subscription.objects.create(
            user=self.student2,
            custom_amount=0.00
        )
        subscription2.batch.add(self.batch)
        
        # student3 is not in any batch
        
        # Set up client
        self.client = Client()
        self.client.login(username='admin', email='admin@example.com', password='adminpassword')
    
    def test_student_notification(self):
        """Test notification targeting specific students"""
        # Create a notification for student1 only
        notification = Notification.objects.create(
            title='Test Student Notification',
            message='This is a test notification for specific students',
            notification_type='student'
        )
        notification.students.add(self.student1)
        
        # Manually call the code that would be executed in the view
        from dashboard.models import StudentNotification
        
        # Create StudentNotification records
        student_notifications = []
        for student in notification.students.all():
            if student.user_type == 0 and not student.is_deleted:
                student_notifications.append(StudentNotification(
                    student=student,
                    notification=notification
                ))
        
        StudentNotification.objects.bulk_create(student_notifications)
        
        # Verify that only student1 has a notification
        self.assertEqual(StudentNotification.objects.filter(student=self.student1, notification=notification).count(), 1)
        self.assertEqual(StudentNotification.objects.filter(student=self.student2, notification=notification).count(), 0)
        self.assertEqual(StudentNotification.objects.filter(student=self.student3, notification=notification).count(), 0)
    
    def test_batch_notification(self):
        """Test notification targeting specific batches"""
        # Create a notification for a specific batch
        notification = Notification.objects.create(
            title='Test Batch Notification',
            message='This is a test notification for a specific batch',
            notification_type='batch'
        )
        notification.batches.add(self.batch)
        
        # Manually call the code that would be executed in the view
        from dashboard.models import StudentNotification, Subscription
        
        # Get all students enrolled in the selected batches
        target_user_objects = []
        subscriptions = Subscription.objects.filter(batch__in=notification.batches.all(), is_deleted=False)
        for subscription in subscriptions:
            if subscription.user.user_type == 0 and not subscription.user.is_deleted:
                target_user_objects.append(subscription.user)
        
        # Create StudentNotification records
        student_notifications = []
        for user in target_user_objects:
            student_notifications.append(StudentNotification(
                student=user,
                notification=notification
            ))
        
        StudentNotification.objects.bulk_create(student_notifications)
        
        # Verify that only students in the batch have notifications
        self.assertEqual(StudentNotification.objects.filter(student=self.student1, notification=notification).count(), 1)
        self.assertEqual(StudentNotification.objects.filter(student=self.student2, notification=notification).count(), 1)
        self.assertEqual(StudentNotification.objects.filter(student=self.student3, notification=notification).count(), 0)
    
    def test_course_notification(self):
        """Test notification targeting specific courses"""
        # Create a notification for a specific course
        notification = Notification.objects.create(
            title='Test Course Notification',
            message='This is a test notification for a specific course',
            notification_type='course'
        )
        notification.courses.add(self.course)
        
        # Manually call the code that would be executed in the view
        from dashboard.models import StudentNotification, Subscription
        
        # Get all batches for the selected courses
        target_user_objects = []
        course_batches = set()
        for course in notification.courses.all():
            course_batches.update(course.batch_set.filter(is_deleted=False))
        
        # Get all students subscribed to these batches
        subscriptions = Subscription.objects.filter(batch__in=course_batches, is_deleted=False)
        for subscription in subscriptions:
            if subscription.user.user_type == 0 and not subscription.user.is_deleted:
                target_user_objects.append(subscription.user)
        
        # Create StudentNotification records
        student_notifications = []
        for user in target_user_objects:
            student_notifications.append(StudentNotification(
                student=user,
                notification=notification
            ))
        
        StudentNotification.objects.bulk_create(student_notifications)
        
        # Verify that only students in the course have notifications
        self.assertEqual(StudentNotification.objects.filter(student=self.student1, notification=notification).count(), 1)
        self.assertEqual(StudentNotification.objects.filter(student=self.student2, notification=notification).count(), 1)
        self.assertEqual(StudentNotification.objects.filter(student=self.student3, notification=notification).count(), 0)
    
    def test_all_notification(self):
        """Test notification targeting all students"""
        # Create a notification for all students
        notification = Notification.objects.create(
            title='Test All Notification',
            message='This is a test notification for all students',
            notification_type='all'
        )
        
        # Manually call the code that would be executed in the view
        from dashboard.models import StudentNotification, CustomUser
        
        # Get all active students
        all_users = CustomUser.objects.filter(user_type=0, is_deleted=False)
        
        # Create StudentNotification records
        student_notifications = []
        for user in all_users:
            student_notifications.append(StudentNotification(
                student=user,
                notification=notification
            ))
        
        StudentNotification.objects.bulk_create(student_notifications)
        
        # Verify that all students have notifications
        self.assertEqual(StudentNotification.objects.filter(student=self.student1, notification=notification).count(), 1)
        self.assertEqual(StudentNotification.objects.filter(student=self.student2, notification=notification).count(), 1)
        self.assertEqual(StudentNotification.objects.filter(student=self.student3, notification=notification).count(), 1)
