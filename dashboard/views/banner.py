from dashboard.views.imports import *
from dashboard.forms.banner import BannerForm

@login_required(login_url='dashboard-login')
def manager(request):
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)
    search_query = request.GET.get('search', '')  

    if start_date and start_date.lower() != 'null':
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start_date = None

    if end_date and end_date.lower() != 'null':
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date() + timedelta(days=1)
    else:
        end_date = None

    banners = Banner.objects.filter(is_deleted=False).order_by('-created')
    
    # Filter by date range if provided
    if start_date and end_date:
        banners = banners.filter(created__range=[start_date, end_date])
    
    # Filter by search query if provided
    if search_query:
        banners = banners.filter(title__icontains=search_query)
    
    # Get featured banners for slider (showing the latest 5)
    featured_banners = banners[:5]
    
    # Prepare form for modal
    form = BannerForm()
    
    context = {
        'banners': banners,
        'featured_banners': featured_banners,
        'search_query': search_query,
        'form': form
    }

    return render(request, 'dashboard/banner/banner.html', context)

@login_required(login_url='dashboard-login')
def add(request):
    if request.method == 'POST':
        form = BannerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Banner added successfully!')
            return redirect('dashboard-banner-manager')
        else:
            messages.error(request, 'Error adding banner. Please check the form.')
            return redirect('dashboard-banner-manager')
    else:
        form = BannerForm()
    
    return render(request, 'dashboard/banner/banner.html', {'form': form})

@login_required(login_url='dashboard-login')
def update(request, pk):
    banner = get_object_or_404(Banner, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        form = BannerForm(request.POST, request.FILES, instance=banner)
        if form.is_valid():
            form.save()
            messages.success(request, 'Banner updated successfully!')
            return redirect('dashboard-banner-manager')
        else:
            messages.error(request, 'Error updating banner. Please check the form.')
    else:
        form = BannerForm(instance=banner)
    
    return render(request, 'dashboard/banner/banner_update.html', {'form': form, 'banner': banner})


@login_required(login_url='dashboard-login')
def delete(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    
    if request.method == 'POST':
        # Soft delete
        banner.is_deleted = True
        banner.save()
        messages.success(request, 'Banner deleted successfully!')
        return redirect('dashboard-banner-manager')
    
    return redirect('dashboard-banner-manager')