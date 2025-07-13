from dashboard.forms.currentaffairs import CurrentAffairsForm
from dashboard.views.imports import *
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from dashboard.models import Video, PDFNote, Exam, CurrentAffairs
from django.contrib import messages
from django.http import JsonResponse


@login_required(login_url='dashboard-login')
def manager(request):
    if request.user.user_type == 1 or request.user.user_type == 2: 
    
        sort_option = request.GET.get('sort')
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)

        # Parse dates if provided
        if start_date and start_date.lower() != 'null':
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_date = None

        if end_date and end_date.lower() != 'null':
            end_date = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        else:
            end_date = None

        # Get all CurrentAffairs objects (assuming you need to filter based on these)
        current_affairs = CurrentAffairs.objects.filter(is_deleted=False)

        # Apply date range filtering if provided
        if start_date and end_date:
            current_affairs = current_affairs.filter(created__range=[start_date, end_date])

        # Apply sorting based on the selected option
        if sort_option == 'name_ascending':
            current_affairs = current_affairs.order_by('title')
        elif sort_option == 'name_descending':
            current_affairs = current_affairs.order_by('-title')
        else:  # Default sorting by created date
            current_affairs = current_affairs.order_by('-created')

        paginator = Paginator(current_affairs, 25)
        page_number = request.GET.get('page')
        items = paginator.get_page(page_number)

        # Get exams related to current affairs and not deleted
        exams = Exam.objects.filter(current_affair__isnull=False, is_deleted=False)
        
        context = {
            "current_affairs": items,
            "current_sort": sort_option,
            "start_date": start_date.strftime("%Y-%m-%d") if start_date else '',
            "end_date": (end_date - timedelta(days=1)).strftime("%Y-%m-%d") if end_date else '',
            "staff_count": len(current_affairs),
            "exams": exams,
        }

        return render(request, "dashboard/current_affairs/currentaffair.html", context)
    else:
        return redirect('dashboard-login')

@login_required(login_url='dashboard-login')
def add(request):
    if request.user.user_type == 1 or request.user.user_type == 2: 
    
        if request.method == "POST":
            form = CurrentAffairsForm(request.POST, request.FILES)
            if form.is_valid():
                # Save Current Affairs
                current_affair = CurrentAffairs(
                    title=form.cleaned_data.get('currentaffair_name'),
                    description=form.cleaned_data.get('description'),
                    image=request.FILES.get('image')
                )
                current_affair.save()
                
                # Check if exam data is provided
                exam_title = request.POST.get('exam_title')
                if exam_title:
                    exam_duration = request.POST.get('exam_duration')
                    exam_number_of_attempt = request.POST.get('exam_number_of_attempt', 1)
                    exam_is_shuffle = request.POST.get('exam_is_shuffle') == 'on'
                    exam_is_free = request.POST.get('exam_is_free') == 'on'
                    
                    # Create the exam
                    Exam.objects.create(
                        title=exam_title,
                        duration=exam_duration,
                        number_of_attempt=int(exam_number_of_attempt),
                        is_shuffle=exam_is_shuffle,
                        is_free=exam_is_free,
                        current_affair=current_affair
                    )

                # Save Video
                video_title = form.cleaned_data.get('video_title')
                video_url = form.cleaned_data.get('video_url')
                video_is_downloadable = form.cleaned_data.get('video_is_downloadable')
                video_is_free = form.cleaned_data.get('video_is_free')

                m3u8 = form.cleaned_data.get('m3u8')
                m3u8_is_downloadable = form.cleaned_data.get('m3u8_is_downloadable')
                m3u8_is_free = form.cleaned_data.get('m3u8_is_free')

                tp_stream = form.cleaned_data.get('tp_stream')

                if video_url or m3u8 or tp_stream:
                    Video.objects.create(
                        currentaffair=current_affair,  
                        title=video_title,
                        url=video_url,
                        is_downloadable=video_is_downloadable,
                        is_free=video_is_free,
                        current_affair=True,
                        m3u8=m3u8,
                        m3u8_is_downloadable=m3u8_is_downloadable,
                        m3u8_is_free=m3u8_is_free,
                        tp_stream=tp_stream
                    )

                # Save PDF Note
                pdf_title = form.cleaned_data.get('pdf_title')
                pdf_file = form.cleaned_data.get('pdf_file')
                pdf_is_downloadable = form.cleaned_data.get('pdf_is_downloadable')
                pdf_is_free = form.cleaned_data.get('pdf_is_free')

                if pdf_file:
                    PDFNote.objects.create(
                        currentaffair=current_affair,  
                        title=pdf_title,
                        file=pdf_file,
                        is_downloadable=pdf_is_downloadable,
                        is_free=pdf_is_free,
                        current_affair=True,
                    )

                messages.success(request, "Content added successfully!")
                return redirect('dashboard-currentaffair-detail', pk=current_affair.id)

            else:
                context = {
                    "title": "Add Current Affair Content",
                    "form": form,
                }
                return render(request, "dashboard/current_affairs/add-lesson.html", context)

        else:
            form = CurrentAffairsForm()  
            context = {
                "title": "Add Current Affair Content",
                "form": form,
            }
            return render(request, "dashboard/current_affairs/add-lesson.html", context)
    else:
        return redirect('/')
  

@login_required(login_url='dashboard-login')
def update(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 2: 
    
        current_affair = get_object_or_404(CurrentAffairs, pk=pk)

        if request.method == "POST":
            form = CurrentAffairsForm(request.POST, request.FILES)
            if form.is_valid():

                current_affair.title = form.cleaned_data.get('currentaffair_name')
                current_affair.description = form.cleaned_data.get('description')
                current_affair.image = form.cleaned_data.get('image', current_affair.image)  
                current_affair.save()

                video_title = form.cleaned_data.get('video_title')
                video_url = form.cleaned_data.get('video_url')
                m3u8 = form.cleaned_data.get('m3u8')
                video_is_downloadable = form.cleaned_data.get('video_is_downloadable')
                video_is_free = form.cleaned_data.get('video_is_free')
                m3u8_is_downloadable = form.cleaned_data.get('m3u8_is_downloadable', False)
                m3u8_is_free = form.cleaned_data.get('m3u8_is_free', False)

                # Update or create video if there is any URL or title
                video = Video.objects.filter(currentaffair=current_affair).first()  # Fetch existing video
                if video:  # Update existing video
                    if video_url or video_title or m3u8:  # Only update if new data is provided
                        video.title = video_title or video.title
                        video.url = video_url or video.url
                        video.is_downloadable = video_is_downloadable
                        video.is_free = video_is_free
                        video.m3u8 = m3u8
                        video.m3u8_is_downloadable = m3u8_is_downloadable
                        video.m3u8_is_free = m3u8_is_free
                        video.save()
                else:  # Create new video if none exists
                    if video_url or video_title or m3u8:  # Only create if data exists
                        Video.objects.create(
                            currentaffair=current_affair,
                            title=video_title,
                            url=video_url,
                            is_downloadable=video_is_downloadable,
                            is_free=video_is_free,
                            m3u8=m3u8,
                            m3u8_is_downloadable=m3u8_is_downloadable,
                            m3u8_is_free=m3u8_is_free,
                        )

                # Handle PDF Note Data
                pdf_title = form.cleaned_data.get('pdf_title')
                pdf_file = form.cleaned_data.get('pdf_file')
                pdf_is_downloadable = form.cleaned_data.get('pdf_is_downloadable')
                pdf_is_free = form.cleaned_data.get('pdf_is_free')

                # Update or create PDF if there is a file or title
                pdf_note = PDFNote.objects.filter(currentaffair=current_affair).first()  # Fetch existing PDF
                if pdf_note:  # Update existing PDF
                    if pdf_file or pdf_title:  # Only update if new data is provided
                        pdf_note.title = pdf_title or pdf_note.title
                        pdf_note.file = pdf_file or pdf_note.file
                        pdf_note.is_downloadable = pdf_is_downloadable
                        pdf_note.is_free = pdf_is_free
                        pdf_note.save()
                else:  # Create new PDF if none exists
                    if pdf_file or pdf_title:  # Only create if data exists
                        PDFNote.objects.create(
                            currentaffair=current_affair,
                            title=pdf_title,
                            file=pdf_file,
                            is_downloadable=pdf_is_downloadable,
                            is_free=pdf_is_free,
                        )

                messages.success(request, "Current Affair content updated successfully!")
                return redirect('dashboard-currentaffair')
            else:
                messages.error(request, "There was an error in updating the content.")
                context = {
                    'form': form,
                    'current_affair': current_affair
                }
                return render(request, 'dashboard/current_affairs/update-lesson.html', context)

        else:
            # Fetch the related video and PDF note data to pre-fill the form
            video = Video.objects.filter(currentaffair=current_affair).first()
            pdf_note = PDFNote.objects.filter(currentaffair=current_affair).first()

            initial_data = {
                'currentaffair_name': current_affair.title,
                'description': current_affair.description,
                'image': current_affair.image,
                'video_title': video.title if video else '',
                'video_url': video.url if video else '',
                'video_is_downloadable': video.is_downloadable if video else False,
                'video_is_free': video.is_free if video else False,
                'm3u8': video.m3u8 if video else '',
                'tp_stream': video.tp_stream     if video else '',
                'm3u8_is_downloadable': video.m3u8_is_downloadable if video else False,
                'm3u8_is_free': video.m3u8_is_free if video else False,
                'pdf_title': pdf_note.title if pdf_note else '',
                'pdf_file': pdf_note.file if pdf_note else None,
                'pdf_is_downloadable': pdf_note.is_downloadable if pdf_note else False,
                'pdf_is_free': pdf_note.is_free if pdf_note else False,
            }

            form = CurrentAffairsForm(initial=initial_data)

            context = {
                'title': "Update Current Affair",
                'form': form,
                'current_affair': current_affair
            }
            return render(request, 'dashboard/current_affairs/update-lesson.html', context)
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')    
def delete(request, pk):
    currentaffairs = get_object_or_404(CurrentAffairs, id=pk)
    currentaffairs.is_deleted = True
    currentaffairs.save()
    return JsonResponse({"message": "Currentaffairs deleted successfully"})
     
     


@login_required(login_url='dashboard-login')
def detail(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 2:
        current_affair = get_object_or_404(CurrentAffairs, pk=pk, is_deleted=False)
        
        # Get videos and PDFs related to this current affair
        videos = Video.objects.filter(currentaffair=current_affair)
        pdfs = PDFNote.objects.filter(currentaffair=current_affair)
        
        # Get exams related to this current affair
        exams = Exam.objects.filter(current_affair=current_affair, is_deleted=False)
        
        context = {
            "current_affair": current_affair,
            "videos": videos,
            "pdfs": pdfs,
            "exams": exams,
        }
        
        return render(request, "dashboard/current_affairs/currentaffair-detail.html", context)
    else:
        return redirect('dashboard-login')

@login_required(login_url='dashboard-login')
def add_exam(request):
    if request.user.user_type == 1 or request.user.user_type == 2:
        if request.method == 'POST':
            title = request.POST.get('title')
            duration = request.POST.get('duration')
            number_of_attempt = request.POST.get('number_of_attempt')
            is_shuffle = request.POST.get('is_shuffle') == 'on'
            is_free = request.POST.get('is_free') == 'on'
            current_affair_id = request.POST.get('current_affair_id')
            
            if not current_affair_id:
                messages.error(request, "Current Affair ID is required")
                return redirect('dashboard-currentaffair')
                
            current_affair = get_object_or_404(CurrentAffairs, id=current_affair_id)
            
            # Create the exam
            exam = Exam(
                title=title,
                duration=duration,
                number_of_attempt=int(number_of_attempt),
                is_shuffle=is_shuffle,
                is_free=is_free,
                current_affair=current_affair
            )
            exam.save()
            
            messages.success(request, "Exam added successfully!")
            return redirect('dashboard-currentaffair-detail', pk=current_affair_id)
        else:
            return redirect('dashboard-currentaffair')
    else:
        return redirect('dashboard-login')

@login_required(login_url='dashboard-login')
def update_exam(request, exam_id):
    if request.user.user_type == 1 or request.user.user_type == 2:
        exam = get_object_or_404(Exam, id=exam_id)
        
        if request.method == 'POST':
            title = request.POST.get('title')
            number_of_attempt = request.POST.get('number_of_attempt')
            is_shuffle = request.POST.get('is_shuffle') == 'on'
            is_free = request.POST.get('is_free') == 'on'
            
            # Update all exam fields
            exam.title = title
            exam.number_of_attempt = number_of_attempt
            exam.is_shuffle = is_shuffle
            exam.is_free = is_free
            exam.save()
            
            messages.success(request, "Exam updated successfully!")
            
            # Redirect back to the current affair detail page
            if exam.current_affair:
                return redirect('dashboard-currentaffair-detail', pk=exam.current_affair.id)
            else:
                return redirect('dashboard-currentaffair')
        else:
            return redirect('dashboard-currentaffair')
    else:
        return redirect('dashboard-login')

@login_required(login_url='dashboard-login')
def delete_exam(request, exam_id):
    if request.user.user_type == 1 or request.user.user_type == 2:
        exam = get_object_or_404(Exam, id=exam_id)
        current_affair_id = None
        
        if exam.current_affair:
            current_affair_id = exam.current_affair.id
            
        exam.is_deleted = True
        exam.save()
        
        messages.success(request, "Exam deleted successfully!")
        
        if current_affair_id:
            return redirect('dashboard-currentaffair-detail', pk=current_affair_id)
        else:
            return redirect('dashboard-currentaffair')
    else:
        return redirect('dashboard-login')
