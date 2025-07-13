from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from dashboard.models import CustomUser
from django.core.paginator import Paginator
from datetime import datetime, timedelta

@login_required
def student_search(request):
    """
    View for searching students by name.
    """
    if request.user.user_type == 1 or request.user.user_type == 3:
        query = request.GET.get('q', '')
        sort_option = request.GET.get('sort')
        
        # Filter active, non-staff, non-superuser users
        user_filter = CustomUser.objects.filter(is_deleted=False, is_staff=False, is_active=True, is_superuser=False)
        
        if query:
            # Search for students by name or email
            user_filter = user_filter.filter(
                Q(name__icontains=query) | 
                Q(email__icontains=query) |
                Q(id__icontains=query)
            )
        
        # Apply sorting
        if sort_option == 'name_ascending':
            user_list = user_filter.order_by('name')
        elif sort_option == 'name_descending':
            user_list = user_filter.order_by('-name')
        else:
            user_list = user_filter.order_by('-id')  # Default sorting
        
        # Pagination
        paginator = Paginator(user_list, 25)  # 25 students per page
        page_number = request.GET.get('page')
        users = paginator.get_page(page_number)
        
        context = {
            "users": users,
            "query": query,
            "current_sort": sort_option
        }
        
        return render(request, 'dashboard/student/search-results.html', context)
    else:
        return redirect('/')
