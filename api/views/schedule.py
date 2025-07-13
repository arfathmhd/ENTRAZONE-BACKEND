from datetime import datetime, timedelta
from dashboard.views.imports import *
from datetime import datetime, date

@api_view(["GET"])
def schedule_list(request):

    # Get user and query parameters
    user = request.user
    course_id = request.query_params.get('course_id')  
    filter_date = request.query_params.get('date')
    is_suspended = user.is_suspended
    
    # Handle suspended users - they can only access schedules up to their suspension date
    if is_suspended and user.suspended_date:
        suspended_date = user.suspended_date.date() if isinstance(user.suspended_date, datetime) else user.suspended_date
        today_date = datetime.today().date()
        
        if not filter_date:
            # If no date is provided, use suspended date as the filter date
            filter_date = suspended_date.strftime('%Y-%m-%d')
        else:
            # If date is provided, ensure it's not after suspension date
            try:
                requested_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
                if requested_date > suspended_date:
                    return Response({
                        "status": "error",
                        "message": "Your account is suspended.",
                        "courses": [],
                        "batch_created": "",
                        "batch_end": "",
                        "batch_id": None,
                        "data": {}
                    }, status=status.HTTP_200_OK)
            except ValueError:
                # Invalid date format will be handled in the next block
                pass
    
    if filter_date:
        try:
            filter_date = datetime.strptime(filter_date, '%Y-%m-%d').date() 
            today_date = datetime.today().date()  

            if filter_date > today_date:
                # return Response({
                #     "status": "error",
                #     "message": "You can't access tomorrow's lessons.",
                #     "data": []
                # }, status=status.HTTP_200_OK)
                pass

        except ValueError:
            return Response({
                "status": "error",
                "message": "Invalid date format. Please use 'YYYY-MM-DD'.",
                "courses": [],
                "batch_created": "",
                "batch_end": "",
                "batch_id": None,
                "data": {}
            }, status=status.HTTP_200_OK)

    # Only get the default course
    combined_courses = []
    if user.default_course:
        combined_courses = [{
            'course_id': user.default_course.id,
            'course_name': user.default_course.course_name if user.default_course.course_name else "N/A",
            'is_default': True
        }]

    # Get batch based on course_id or default course
    if course_id:
        try:
            course = Course.objects.get(id=course_id, is_deleted=False)
            batch = Batch.objects.filter(course=course, is_deleted=False).last()
            if not batch:
                return Response({
                    "status": "error",
                    "message": "No batches available for this course",
                    "courses": [],
                    "batch_created": "",
                    "batch_end": "",
                    "batch_id": None,
                    "data": {}
                }, status=status.HTTP_200_OK)
        except Course.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Course not found",
                "courses": [],
                "batch_created": "",
                "batch_end": "",
                "batch_id": None,
                "data": {}
            }, status.HTTP_200_OK)
    else:
        # No course_id provided, use default course
        if not user.default_course:
            return Response({
                "status": "error",
                "message": "User does not have a default course",
                "courses": [],
                "batch_created": "",
                "batch_end": "",
                "batch_id": None,
                "data": {}
            }, status.HTTP_200_OK)
        
        course = user.default_course
        batch = Batch.objects.filter(course=course, is_deleted=False).last()
        if not batch:
            return Response({
                "status": "error",
                "message": "No batches available for the selected course",
                "courses": [],
                "batch_created": "",
                "batch_end": "",
                "batch_id": None,
                "data": {}
            }, status.HTTP_200_OK)

    # Check if the batch has ended
    today = datetime.today().date()
    if batch.batch_expiry < today:
        return Response({
            "status": "error",
            "message": "Batch has ended",
            "courses": combined_courses,
            "batch_created": batch.start_date.strftime("%Y-%m-%d %H:%M") if batch else "",
            "batch_end": batch.batch_expiry.strftime("%Y-%m-%d %H:%M") if batch else "",
            "batch_id": batch.id if batch else None,
            "data": {}
        }, status=status.HTTP_200_OK)

    # Check if the user has a subscription for this batch
    is_subscribed = Subscription.objects.filter(user=user, batch=batch, is_deleted=False, batch__is_deleted=False).exists()
    
    # If user is not subscribed, return empty data
    if not is_subscribed:
        return Response({
            "status": "error",
            "message": "You don't have a subscription for this course batch",
            "courses": combined_courses,
            "batch_created": batch.start_date.strftime("%Y-%m-%d %H:%M") if batch else "",
            "batch_end": batch.batch_expiry.strftime("%Y-%m-%d %H:%M") if batch else "",
            "batch_id": batch.id if batch else None,
            "data": {}
        }, status=status.HTTP_200_OK)

    # Get all folders for this course
    folders = Folder.objects.filter(chapter__subject__course=course, is_deleted=False).order_by('order')

    batch_lessons = BatchLesson.objects.filter(batch=batch, is_deleted=False)
    batch_lessons_data = []
    processed_folder_ids = set()  # Track processed folders to avoid duplicates

    if filter_date:
        try:
            if isinstance(batch.start_date, datetime):
                batch_start_date = batch.start_date.date()
            elif isinstance(batch.start_date, date):
                batch_start_date = batch.start_date
            else:
                raise AttributeError("Batch start date is not a valid date")

            actual_difference = (filter_date - batch_start_date).days
            # Map actual difference to visible_in_days
            # If difference is 0, we want visible_in_days=1
            # If difference is 1, we want visible_in_days=2, etc.
            date_difference = actual_difference + 1
        except AttributeError as e:
            return Response({
                "status": "error",
                "message": "Batch start date is not available or invalid.",
                "courses": [],
                "batch_created":"",
                "batch_end":"",
                "batch_id": None,
                "data": {}
            }, status=status.HTTP_200_OK)
    else:
        date_difference = None

    # Helper function to process folder data
    def process_folder(folder, visible_in_days):
        if folder.id in processed_folder_ids:
            return None
        
        processed_folder_ids.add(folder.id)
        
        folder_data = {
            "folder_id": folder.id,
            "folder_title": folder.title,
            "visible_in_days": visible_in_days,
            "lessons": [],
            "sub_folders": [],
        }
        
        # Fetch lessons in the folder
        lessons_in_folder = Lesson.objects.filter(folder=folder, is_deleted=False).order_by('order')
        for lesson in lessons_in_folder:
            lesson_info = get_lesson_info(lesson, visible_in_days)
            folder_data["lessons"].append(lesson_info)
            
        # Fetch subfolders
        sub_folders = Folder.objects.filter(parent_folder=folder, is_deleted=False).order_by('order')
        for sub_folder in sub_folders:
            sub_folder_data = process_folder(sub_folder, visible_in_days)
            if sub_folder_data:
                folder_data["sub_folders"].append(sub_folder_data)
                
        return folder_data
    
    # Helper function to get lesson info
    def get_lesson_info(lesson, visible_in_days):
        lesson_info = {
            "lesson_id": lesson.id,
            "lesson_name": lesson.lesson_name if lesson.lesson_name else "N/A",
            "lesson_description": lesson.description if lesson.description else "N/A",
            "visible_in_days": visible_in_days,
            "is_free": lesson.is_free if hasattr(lesson, 'is_free') else False,
            "videos": [],
            "pdf_notes": []
        }
        
        # Fetch videos associated with the lesson
        videos = Video.objects.filter(lesson=lesson, is_deleted=False)
        for video in videos:
            video_url = video.url.split('=')[-1] if 'www.youtube.com' in video.url else video.url
            lesson_info["videos"].append({
                "video_id": video.id,
                "title": video.title if video.title else "N/A",
                "url": video_url,
                "m3u8": video.m3u8 if video.m3u8 else "",
                "tp_stream": video.tp_stream if video.tp_stream else "",
                "is_downloadable": video.is_downloadable,
                "is_free": video.is_free
            })
            
        # Fetch PDF notes associated with the lesson
        pdf_notes = PDFNote.objects.filter(lesson=lesson, is_deleted=False)
        for pdf_note in pdf_notes:
            lesson_info["pdf_notes"].append({
                "note_id": pdf_note.id,
                "title": pdf_note.title if pdf_note.title else "N/A",
                "file_url": pdf_note.file.url if pdf_note.file else "N/A",
                "is_downloadable": pdf_note.is_downloadable,
                "is_free": pdf_note.is_free
            })
            
        return lesson_info

    # First, process all BatchLessons
    for batch_lesson in batch_lessons:
        # Convert visible_in_days to int for comparison
        try:
            visible_days = int(batch_lesson.visible_in_days)
        except (ValueError, TypeError, AttributeError):
            visible_days = 0
            
        if date_difference is not None and visible_days != date_difference:
            continue
            
        # Process folder-based batch lessons
        if batch_lesson.folder:
            folder = batch_lesson.folder
            folder_data = process_folder(folder, batch_lesson.visible_in_days)
            if folder_data:
                batch_lessons_data.append(folder_data)
                
        # Process lesson-based batch lessons
        elif batch_lesson.lesson:
            lesson = batch_lesson.lesson
            lesson_info = get_lesson_info(lesson, batch_lesson.visible_in_days)
            batch_lessons_data.append(lesson_info)

    # Now process any folders that weren't included in batch lessons but should be shown
    # This ensures folders appear both inside folder lessons and outside lessons
    if date_difference is None:  # Only do this when not filtering by date
        for folder in folders:
            if folder.id not in processed_folder_ids and folder.parent_folder is None:
                # Only process top-level folders that haven't been processed yet
                folder_data = process_folder(folder, 0)  # Default visible_in_days to 0
                if folder_data:
                    batch_lessons_data.append(folder_data)

    if not batch_lessons_data:
        return Response({
            "status": "success",
            "message": "No lessons available for this course",
            "courses": combined_courses,
            "batch_created": batch.start_date.strftime("%Y-%m-%d %H:%M"),
            "batch_end": batch.batch_expiry.strftime("%Y-%m-%d %H:%M"),
            "batch_id": batch.id,
            "is_subscribed": is_subscribed,
            "data": {}
        }, status=status.HTTP_200_OK)

    # Get schedules for the current date if filter_date is provided
    schedules_data = []
    if filter_date:
        schedules = Schedule.objects.filter(
            lesson__in=[bl.lesson for bl in batch_lessons if bl.lesson],
            date__date=filter_date,
            is_deleted=False
        )
        for schedule in schedules:
            schedules_data.append({
                "id": schedule.id,
                "title": schedule.title,
                "lesson_id": schedule.lesson.id if schedule.lesson else None,
                "exam_id": schedule.exam.id if schedule.exam else None,
                "date": schedule.date.strftime("%Y-%m-%d %H:%M")
            })

    # Process batch lessons data to add type field
    processed_data = []
    for item in batch_lessons_data:
        if "folder_id" in item:
            # This is a folder
            schedule_item = {
                "type": "folder",
                **item,
                "lessons": [{
                    "type": "lesson",
                    **lesson
                } for lesson in item.get("lessons", [])],
                "sub_folders": [{
                    "type": "folder",
                    **sub_folder,
                    "lessons": [{
                        "type": "lesson",
                        **sub_lesson
                    } for sub_lesson in sub_folder.get("lessons", [])]
                } for sub_folder in item.get("sub_folders", [])]
            }
        else:
            # This is a lesson
            schedule_item = {
                "type": "lesson",
                **item
            }
        processed_data.append(schedule_item)

    # Add all data to response
    response_data = {
        "status": "success",
        "message": "Data fetched successfully" + (
            " (Note: Your account is suspended. You can only access schedules up to your suspension date.)" 
            if is_suspended else ""
        ),
        "courses": combined_courses,
        "batch_created": batch.start_date.strftime("%Y-%m-%d %H:%M"),
        "batch_end": batch.batch_expiry.strftime("%Y-%m-%d %H:%M"),
        "batch_id": batch.id,
        "is_subscribed": is_subscribed,
        "is_suspended": is_suspended,
        "suspended_date": user.suspended_date.strftime("%Y-%m-%d %H:%M") if is_suspended and user.suspended_date else None,
        "data": {
            "schedules": processed_data
        }
    }
    return Response(response_data, status=status.HTTP_200_OK)
