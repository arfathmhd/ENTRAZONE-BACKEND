from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


def mentor_redirect_decorator(view_func):
    """
    Decorator that redirects users with Mentor user type (4) to the student search page.
    Other user types can access the view as normal.
    
    Usage:
        @login_required(login_url='dashboard-login')
        @mentor_redirect_decorator
        def some_view(request):
            # This view will only be accessible to non-mentor users
            ...
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if the user is authenticated and has the Mentor user type (4)
        if request.user.is_authenticated and request.user.user_type == 4:
            messages.info(request, 'As a Mentor, you have been redirected to the student search page.')
            return redirect('dashboard-customer')
        
        # For all other user types, proceed to the view
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def admin_required(view_func):
    """
    Decorator that ensures only Admin users (user_type=1) can access the view.
    Other user types will be redirected to the dashboard home page.
    
    Usage:
        @login_required(login_url='dashboard-login')
        @admin_required
        def admin_only_view(request):
            # This view will only be accessible to admin users
            ...
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type != 1:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard-home')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def content_manager_required(view_func):
    """
    Decorator that ensures only Admin (user_type=1) or Content Manager (user_type=2) 
    users can access the view. Other user types will be redirected to the dashboard home page.
    
    Usage:
        @login_required(login_url='dashboard-login')
        @content_manager_required
        def content_management_view(request):
            # This view will only be accessible to admin and content manager users
            ...
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type not in [1, 2]:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard-home')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
