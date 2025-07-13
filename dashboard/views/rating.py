from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.http import HttpResponse, JsonResponse
from dashboard.views.imports import *
from dashboard.models import VideoRating, Video
from django.core.paginator import Paginator
from django.template.loader import render_to_string

@login_required(login_url='dashboard-login')
def video_rating(request):
    # Get only videos that have ratings
    videos = Video.objects.filter(is_deleted=False).annotate(
        avg_rating=Avg('ratings__rating'),
        rating_count=Count('ratings')
    ).filter(rating_count__gt=0).order_by('-avg_rating', '-created')
    
    # Pagination
    paginator = Paginator(videos, 25)  # Show 25 videos per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    print(videos.first().id)
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'dashboard/rating/video_rating.html', context)

@login_required(login_url='dashboard-login')
def video_rating_details(request, video_id):
    """API endpoint to get detailed ratings for a specific video"""
    video = get_object_or_404(Video, id=video_id)
    ratings = VideoRating.objects.filter(video=video).select_related('student')
    
    # Calculate rating distribution
    rating_counts = {}
    for i in range(1, 6):
        rating_counts[i] = ratings.filter(rating=i).count()
    
    # Calculate percentage for each rating
    total_ratings = ratings.count()
    rating_percentages = {}
    for i in range(1, 6):
        if total_ratings > 0:
            rating_percentages[i] = (rating_counts[i] / total_ratings) * 100
        else:
            rating_percentages[i] = 0
    
    context = {
        'video': video,
        'ratings': ratings,
        'rating_counts': rating_counts,
        'rating_percentages': rating_percentages,
        'total_ratings': total_ratings,
        'avg_rating': video.ratings.aggregate(avg=Avg('rating'))['avg'] if total_ratings > 0 else 0
    }
    
    # Render the HTML content for the modal
    html_content = render_to_string('dashboard/rating/video_rating_details.html', context, request)
    return HttpResponse(html_content)
