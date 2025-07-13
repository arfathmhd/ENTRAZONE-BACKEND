

from dashboard.views.imports import *
from django.contrib.auth import logout

def login(request):
    if 'username' in request.session:
        return redirect('/')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if not username or not password:
            messages.error(request, 'Please fill all the fields')
            return redirect('/login/')
        
        if not CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username does not exist')
            return redirect('/login/')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            auth_login(request, user)
            request.session['username'] = username
            messages.success(request, ' Logged in!')
            return redirect('/')
        else:
            messages.error(request, 'Incorrect password')
            return redirect('/login/')
            
    return render(request, "dashboard/login/login.html")


def custom_logout(request):
    """
    Custom logout view that flushes all session data and redirects to login.
    """
    request.session.flush()  # Flush all session data
    logout(request)  # Logout the user
    return redirect('dashboard-login')