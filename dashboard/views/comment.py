from dashboard.views.imports import *


@login_required(login_url='dashboard-login')
def manager(request):
    if request.user.user_type == 1 or request.user.user_type == 2:
        sort_option = request.GET.get('sort', 'id_descending')  
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        search_query = request.GET.get('search', '')  
        selected_course = request.GET.get('course_id', None)


        if start_date and start_date.lower() != 'null':
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start_date = None

        if end_date and end_date.lower() != 'null':
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date() + timedelta(days=1)
        else:
            end_date = None

        # Filter for parent comments only (not replies)
        comment_filter = Comment.objects.filter(is_deleted=False, parent_comment=None)

        # Apply date range filter if provided
        if start_date and end_date:
            comment_filter = comment_filter.filter(created__range=[start_date, end_date])
        
        # Apply search filter if provided
        if search_query:
            comment_filter = comment_filter.filter(
                Q(user__name__icontains=search_query) |
                Q(content__icontains=search_query)
            )
        
         # Filter by course if course_id is provided
        if selected_course and selected_course != 'all':
            comment_filter = comment_filter.filter(
                Q(video__lesson__folder__chapter__subject__course_id=selected_course) |
                Q(video__lesson__chapter__subject__course_id=selected_course) |
                Q(pdf_note__lesson__folder__chapter__subject__course_id=selected_course) |
                Q(pdf_note__lesson__chapter__subject__course_id=selected_course)
            )

        # Apply sorting
        if sort_option == 'ascending':
            comments = comment_filter.order_by('id')
        elif sort_option == 'descending':
            comments = comment_filter.order_by('-id')
        elif sort_option == 'name_ascending':
            comments = comment_filter.order_by('user__name')
        elif sort_option == 'name_descending':
            comments = comment_filter.order_by('-user__name')
        else:
            comments = comment_filter.order_by('-id')  

        paginator = Paginator(comments, 25)  
        page_number = request.GET.get('page')
        paginated_comments = paginator.get_page(page_number)
        
        course_filter = Course.objects.filter(is_deleted=False)

        context = {
            'comments': paginated_comments,  
            'current_sort': sort_option,  
            'start_date': start_date, 
            'end_date': end_date, 
            'search_query': search_query,
            'course_filter': course_filter,
            'selected_course': selected_course,
        }

        return render(request, 'dashboard/comment/comment.html', context)
    else:
        return redirect('/')

def list(request):
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 10))
    search_value = request.GET.get("search[value]", "").strip()
    order_column = int(request.GET.get("order[0][column]", 0))
    order_dir = request.GET.get("order[0][dir]", "desc")
    course_id = request.GET.get("course_id", None)
    
    print(f"Course ID in list function: {course_id}")  # Debug print

    comments = Comment.objects.filter(is_deleted=False)

    order_columns = {
        0: 'id',
        1: 'user',
        2: 'content',
        3: 'created',
    }

    order_field = order_columns.get(order_column, 'id')
    if order_dir == 'desc':
        order_field = '-' + order_field

    if search_value:
        comments = comments.filter(
            Q(user__name__icontains=search_value) |
            Q(content__icontains=search_value)
        )
        

    total_records = comments.count()

    comments = comments.order_by(order_field)

    paginator = Paginator(comments, length)
    page_number = (start // length) + 1
    page_obj = paginator.get_page(page_number)

    data = []
    for comment in page_obj:
        video_data = {
            "video_url": comment.video.url if comment.video and comment.video.url else "N/A",
            "video_title": comment.video.title if comment.video and comment.video.title else "N/A",
            "video_is_free": comment.video.is_free if comment.video else False
        } if comment.video else None

        pdf_note_data = {
            "pdf_title": comment.pdf_note.title if comment.pdf_note and comment.pdf_note.title else "N/A",
            "pdf_is_free": comment.pdf_note.is_free if comment.pdf_note else False,
            "pdf_file_url": comment.pdf_note.file.url if comment.pdf_note and comment.pdf_note.file else "N/A"
        } if comment.pdf_note else None

        data.append({
            "id": comment.id,
            "user": comment.user.name if comment.user.name else "N/A",
            "customer_id": comment.user.id, 
            "content": comment.content,
            "video": video_data,  
            "pdf_note": pdf_note_data, 
            "created": timezone.localtime(comment.created).strftime('%Y-%m-%d %H:%M:%S'),
        })

    response = {
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data,
    }

    return JsonResponse(response)




def delete(request,pk):
    try:
        comment = Comment.objects.get(id=pk)
        comment.is_deleted = True
        comment.save()
        messages.success(request, 'Comment deleted successfully')
    except Comment.DoesNotExist:
        messages.error(request, 'Comment not found')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('dashboard-comment-manager') 

@login_required(login_url='dashboard-login')
def add_reply(request, comment_id):
    if request.method == 'POST':
        try:
            parent_comment = Comment.objects.get(id=comment_id, is_deleted=False)
            content = request.POST.get('content')
            
            if content:
                # Create the reply
                reply = Comment(
                    user=request.user,
                    content=content,
                    parent_comment=parent_comment,
                    video=parent_comment.video,
                    pdf_note=parent_comment.pdf_note
                )
                reply.save()
                messages.success(request, 'Reply added successfully')
            else:
                messages.error(request, 'Reply content cannot be empty')
                
        except Comment.DoesNotExist:
            messages.error(request, 'Comment not found')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('dashboard-comment-manager')

@login_required(login_url='dashboard-login')
def get_replies(request, comment_id):
    try:
        replies = Comment.objects.filter(parent_comment_id=comment_id, is_deleted=False).order_by('created')
        
        data = []
        for reply in replies:
            data.append({
                'id': reply.id,
                'user': reply.user.name if reply.user.name else 'N/A',
                'content': reply.content,
                'created': timezone.localtime(reply.created).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return JsonResponse({'status': 'success', 'replies': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def delete_reply(request, pk):
    try:
        reply = Comment.objects.get(id=pk)
        reply.is_deleted = True
        reply.save()
        return JsonResponse({'status': 'success'})
    except Comment.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Reply not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})