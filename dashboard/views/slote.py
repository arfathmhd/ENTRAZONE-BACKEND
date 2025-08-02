from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.http import HttpResponse, JsonResponse
from dashboard.views.imports import *
from dashboard.models import VideoRating, Video
from django.core.paginator import Paginator
from django.template.loader import render_to_string



@login_required(login_url='dashboard-login')
def manager(request):
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

    # Retrieve slots that are not deleted
    slots = Slot.objects.filter(is_deleted=False)
    
    # Filter by date range if provided
    if start_date and end_date:
        slots = slots.filter(created__range=[start_date, end_date])
    
    # Sorting options
    if sort_option == 'ascending':
        slots = slots.order_by('id')
    elif sort_option == 'descending':
        slots = slots.order_by('-id')
    elif sort_option == 'name_ascending':
        slots = slots.order_by('subject__subject_name')
    elif sort_option == 'name_descending':
        slots = slots.order_by('-subject__subject_name')
    else:
        slots = slots.order_by('-id')

    # Pagination
    paginator = Paginator(slots, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Count total slots
    staff_count = slots.count()

    context = {
        "slots": page_obj,
        "current_sort": sort_option,
        "start_date": start_date,
        "end_date": end_date,
        "staff_count": staff_count,
    }
    # templates/dashboard/slote/slote.html

    return render(request, "dashboard/slote/slote.html", context)

@login_required(login_url='dashboard-login')
def add_slot(request):
    if request.method == "POST":
        course_id = request.POST.get("course")
        subject_id = request.POST.get("subject")
        date = request.POST.get("date")
        available_sessions = request.POST.get("available_sessions")

        if course_id and subject_id:
            try:
                course = Course.objects.get(id=course_id)
                subject = Subject.objects.get(id=subject_id)

                Slot.objects.create(
                    course=course,
                    subject=subject,
                    date=date,
                    available_sessions=available_sessions,
                    total_slots=available_sessions
                )
                messages.success(request, "Slot added successfully!")
                return redirect("dashboard-slote-manager")

            except Course.DoesNotExist:
                messages.error(request, "Invalid Course selected.")
            except Subject.DoesNotExist:
                messages.error(request, "Invalid Subject selected.")

    courses = Course.objects.all()

    return render(request, "dashboard/slote/add-slote.html", {"courses": courses})
@login_required(login_url='dashboard-login')
def get_subjects(request):
    course_id = request.GET.get("course_id")
    if course_id:
        subjects = Subject.objects.filter(course_id=course_id, is_deleted=False).values("id", "subject_name")
        return JsonResponse(list(subjects), safe=False)
    return JsonResponse([], safe=False)





@login_required(login_url='dashboard-login')
def update_slot(request, slot_id):
    slot = get_object_or_404(Slot, id=slot_id)

    if request.method == "POST":
        course_id = request.POST.get("course")
        subject_id = request.POST.get("subject")
        date = request.POST.get("date")
        available_sessions = request.POST.get("available_sessions")

        if course_id and subject_id:
            try:
                course = Course.objects.get(id=course_id)
                subject = Subject.objects.get(id=subject_id)

                slot.course = course
                slot.subject = subject
                slot.date = date
                slot.total_slots = available_sessions
                slot.save()

                messages.success(request, "Slot updated successfully!")
                return redirect("dashboard-slote-manager")

            except Course.DoesNotExist:
                messages.error(request, "Invalid Course selected.")
            except Subject.DoesNotExist:
                messages.error(request, "Invalid Subject selected.")

    courses = Course.objects.all()
    subjects = Subject.objects.filter(course=slot.course)  # Load subjects related to the slot's course

    return render(request, "dashboard/slote/update-slote.html", {
        "slot": slot,
        "courses": courses,
        "subjects": subjects
    })

@login_required(login_url='dashboard-login')
def delete(request, slot_id):
    slot = get_object_or_404(Slot, id=slot_id)

    if request.method == 'POST':
        slot.is_deleted = True
        slot.save()
        messages.success(request, "Slot deleted successfully.")
        return redirect('dashboard-slote-manager')  
    messages.error(request, "Failed to delete slot.")
    return render(request, 'dashboard/slote/manager', {'slot': slot})



@login_required(login_url='dashboard-login')
def booked_manager(request):
    sort_option = request.GET.get('sort')
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)

    # Parse start_date and end_date
    if start_date and start_date.lower() != 'null':
        start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y-%m-%d")
    else:
        start_date = None

    if end_date and end_date.lower() != 'null':
        end_date = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        end_date = None

    # Retrieve bookings that are not deleted
    bookings = Booking.objects.filter(is_deleted=False)
    
    # Filter by date range if provided
    if start_date and end_date:
        bookings = bookings.filter(created__range=[start_date, end_date])
    
    # Sorting options
    if sort_option == 'ascending':
        bookings = bookings.order_by('id')
    elif sort_option == 'descending':
        bookings = bookings.order_by('-id')
    
    # Pagination
    paginator = Paginator(bookings, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Count total bookings
    booking_count = bookings.count()

    context = {
        "bookings": page_obj,
        "current_sort": sort_option,
        "start_date": start_date,
        "end_date": end_date,
        "booking_count": booking_count,
    }

    # Render the template
    return render(request, "dashboard/sesstion-booked/booking.html", context)
