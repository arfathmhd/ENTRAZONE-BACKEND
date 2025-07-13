
from dashboard.views.imports import *
@login_required(login_url='dashboard-login')
def manager(request):
    if request.user.user_type == 1 or request.user.user_type == 2:
        sort_option = request.GET.get('sort')
        
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)

        if start_date and start_date.lower() != 'null':
            start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y-%m-%d")
        else:
            start_date = None

        if end_date and end_date.lower() != 'null':
            end_date = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            end_date = None

        # Get all chapters
        chapters = Chapter.objects.filter(is_deleted=False)

        # Get all main folders (no parent folders)
        folders = Folder.objects.filter(
            parent_folder=None,
            is_deleted=False
        )  # Efficiently load chapter data

        if start_date and end_date:
            folders = folders.filter(created__range=[start_date, end_date])
        print(sort_option,"folder")
        if sort_option == 'name_ascending':
            folders = folders.order_by('title')  
        elif sort_option == 'name_descending':
            folders = folders.order_by('-title')
        else:
            folders = folders.order_by('order')  

        paginator = Paginator(folders, 25)  
        page_number = request.GET.get('page')
        folders = paginator.get_page(page_number)

        # Use `len()` for the count if you're dealing with a list, else count for querysets
        folder_count = folders.paginator.count  # Get count from the paginator directly
        
        context = {
            "chapters": chapters,
            "folders": folders,
            "current_sort": sort_option,
            "start_date": start_date,
            "end_date": end_date,
            "folder_count": folder_count,  # Corrected the count logic
        }

        return render(request, "dashboard/folder/folder.html", context)

    return redirect('/')


@csrf_exempt  
def update(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            folder_id = data.get('folder_id')
            new_folder_name = data.get('new_folder_name')

            if not folder_id or not new_folder_name:
                return JsonResponse({'success': False, 'error': 'Folder ID and new name are required.'})

            folder = get_object_or_404(Folder, pk=folder_id)

            folder.title = new_folder_name
            folder.save()

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})
