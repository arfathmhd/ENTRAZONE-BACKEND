from django.db.models import Count
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from dashboard.views.imports import *
from django.utils.timezone import now
from dashboard.decorators import mentor_redirect_decorator

        
@login_required(login_url='dashboard-login')
def home(request):
    user = request.user

    total_students = CustomUser.objects.filter(is_deleted=False, is_staff=False, is_superuser=False).count()

    subscribed_users = CustomUser.objects.filter(
        subscription__is_deleted=False,
        is_deleted=False
    ).distinct().count()

    unsubscribed_users = total_students - subscribed_users
    
    custom_users = CustomUser.objects.filter(is_deleted=False, is_superuser=False)
    
    staff = custom_users.filter(is_staff=True).count()
    in_active_staff = custom_users.filter(is_staff=True, is_active=False).count()
    active_staff = custom_users.filter(is_staff=True, is_active=True).count()
    
    total_mentors = custom_users.filter(user_type=4).count()
    active_mentors = custom_users.filter(user_type=4, is_active=True).count()
    in_active_mentors = custom_users.filter(user_type=4, is_active=False).count()
    
    

    courses = Course.objects.filter(is_deleted=False)
    courses_with_subscriptions = []
    batches = Batch.objects.filter(is_deleted=False, batch_expiry__lte=now())
    
    most_subscribed_course_count = 0
    most_subscribed_course_name = ""

    for course in courses:
        # Get subscriptions for this course
        course_subscriptions = Subscription.objects.filter(
            batch__course=course, 
            is_deleted=False
        ).distinct()
        
        subscription_count = course_subscriptions.count()
        
        # Calculate total earnings from paid FeeInstallments
        total_earnings = 0
        
        # Get all paid installments for subscriptions related to this course
        paid_installments = FeeInstallment.objects.filter(
            subscription__in=course_subscriptions,
            is_paid=True,
            is_deleted=False
        )
        
        # Sum up the amount_due from all paid installments
        if paid_installments.exists():
            total_earnings = paid_installments.aggregate(total=models.Sum('amount_due'))['total'] or 0
        
        # Calculate subscription percentage
        subscription_percentage = (subscription_count / total_students) * 100 if total_students > 0 else 0

        courses_with_subscriptions.append({
            'course_name': course.course_name,
            'subscription_count': subscription_count,
            'subscription_percentage': subscription_percentage,  
            'total_earnings': total_earnings,  
        })

        if subscription_count > most_subscribed_course_count:
            most_subscribed_course_count = subscription_count
            most_subscribed_course_name = course.course_name

    # Calculate total earnings across all courses
    total_earnings = sum(course['total_earnings'] for course in courses_with_subscriptions)
    
    context = {
        "user": user,

        "customers": total_students,
        "staff": staff,
        "in_active_staff": in_active_staff,
        "active_staff": active_staff,
        "course_count": courses.count(),
        "courses_with_subscriptions": courses_with_subscriptions,
        "subscribed_users": subscribed_users,
        "non_subscribed_users": unsubscribed_users,
        "batches": batches,
        "total_mentors": total_mentors,
        "active_mentors": active_mentors,
        "in_active_mentors": in_active_mentors,
        "most_subscribed_course_count": most_subscribed_course_count,
        "most_subscribed_course_name": most_subscribed_course_name,
        "total_earnings": total_earnings,
    }

    return render(request, "dashboard/home/index.html", context)
