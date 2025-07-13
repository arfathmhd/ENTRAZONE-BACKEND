from decimal import Decimal
from dashboard.views.imports import *
import csv
import xlsxwriter
from io import BytesIO
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dashboard.forms.customer_update import CustomerUpdateForm
# Ensure we have all necessary models imported
from django.http import HttpResponse
from django.db.models import Avg, F, Count
# PDF generation imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet



@login_required(login_url='dashboard-login')
def manager(request):
    if request.user.user_type == 1 or request.user.user_type == 3 or request.user.user_type == 4:
        sort_option = request.GET.get('sort')
        
        
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        search_query = request.GET.get('search', '')  

        if start_date and start_date.lower() != 'null':
            start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y-%m-%d")
        else:
            start_date = None

        if end_date and end_date.lower() != 'null':
            end_date = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            end_date = None
        
        user_filter = CustomUser.objects.filter(is_deleted=False, is_staff=False, is_active=True, is_superuser=False)
        
        if start_date and end_date:
            user_filter = user_filter.filter(created__range=[start_date, end_date])
        
        if search_query:
            user_filter = user_filter.filter(
                Q(name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(id__icontains=search_query)  
            )
        if sort_option == 'ascending':
            user_list = user_filter.order_by('id')
        elif sort_option == 'descending':
            user_list = user_filter.order_by('-id')
        elif sort_option == 'name_ascending':
            user_list = user_filter.order_by('name')
        elif sort_option == 'name_descending':
            user_list = user_filter.order_by('-name')
        else:
            user_list = user_filter.order_by('-id')

        paginator = Paginator(user_list, 25)
        page_number = request.GET.get('page')
        users = paginator.get_page(page_number)

        context = {
            "users": users,
            "current_sort": sort_option,
            "start_date": start_date,
            "end_date": end_date,
            "search_query": search_query 
        }

        return render(request, "dashboard/student/student_grid.html", context)

    else:
        return redirect('/')



@login_required(login_url='dashboard-login')
def list(request):
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 10))
    search_value = request.GET.get("search[value]", "").strip()
    order_column = int(request.GET.get("order[0][column]", 0))
    order_dir = request.GET.get("order[0][dir]", "desc")

    users = CustomUser.objects.filter(is_deleted=False,is_staff=False,is_superuser=False)

    order_columns = {
        0: 'id',
        1: 'username',
        2: 'email',
        3: 'district',
        4: 'phone_number',
    }

    order_field = order_columns.get(order_column, 'id')
    if order_dir == 'desc':
        order_field = '-' + order_field

    if search_value:
        users = users.filter(
            Q(name__icontains=search_value) |
            Q(phone_number__icontains=search_value) |
            Q(district__icontains=search_value) |
            Q(email__icontains=search_value)
        )

    total_records = users.count()

    active_batches_prefetch = Prefetch(
      'subscription_set', 
     queryset=Subscription.objects.filter(
        is_deleted=False
     ).prefetch_related(
        Prefetch(
            'batch',
            queryset=Batch.objects.filter(
                batch_expiry__gte=timezone.now().date(),
                is_deleted=False
            ).select_related('course')
        )
    )
    ) 

    users = users.order_by(order_field).prefetch_related(active_batches_prefetch)

    paginator = Paginator(users, length)
    page_number = (start // length) + 1
    page_obj = paginator.get_page(page_number)

    data = []
    for user in page_obj:
        subscriptions = user.subscription_set.all()
        subscription_details = []

        for subscription in subscriptions:
            for batch in subscription.batch.all():
                course_name = getattr(batch.course, "course_name", "N/A")
                start_date = batch.start_date.strftime("%d-%m-%Y") if batch.start_date else "N/A"
                expiry_date = batch.batch_expiry.strftime("%d-%m-%Y") if batch.batch_expiry else "N/A"
                subscription_details.append(
                    f'<span style="color: blue;">{course_name}</span> '
                    f'(<span style="color: green;">Start: {start_date}, '
                    f'<span style="color: red;">Expiry: {expiry_date}</span>)'
                )

        subscriptions_display = '<br>'.join(subscription_details) if subscription_details else "N/A"

        data.append({
            "id": user.id,
            "username": user.name if user.name else "N/A",
            "email": user.email if user.email else "N/A",
            "district": user.get_district_display() if user.district else "N/A",
            "phone_number": user.phone_number if user.phone_number else "N/A",
            "batch_names_display": subscriptions_display,
           "created": timezone.localtime(user.created).strftime('%Y-%m-%d %H:%M:%S')
        })

    response = {
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data,
    }

    return JsonResponse(response)



@login_required(login_url='dashboard-login')
def add(request):
    if request.user.user_type == 1 or request.user.user_type == 3:
        if request.method == "POST":
            form = CustomerForm(request.POST, request.FILES)
            payment_plan_form = PaymentPlanForm(request.POST)
            
            forms_valid = form.is_valid()
            payment_plan_valid = payment_plan_form.is_valid()
            
            if forms_valid and payment_plan_valid:
                # Don't save the form yet, just get the data
                phone = form.cleaned_data['phone_number']
                name = form.cleaned_data['name']

                if not phone or not name:
                    messages.error(request, "Both phone number and name are required to generate a username.")
                    return render(request, 'dashboard/student/add-student.html', {
                        'form': form,
                        'payment_plan_form': payment_plan_form
                    })

                # Generate username from phone and name
                formatted_name = name.replace(" ", "_").lower()  
                username = f"{phone}_{formatted_name}"

                if CustomUser.objects.filter(username=username).exists():
                    messages.error(request, "This username is already taken. Please choose a different name or phone number.")
                    return render(request, 'dashboard/student/add-student.html', {
                        'form': form,
                        'payment_plan_form': payment_plan_form
                    })

                # Prepare form for saving
                customer = form.instance
                customer.username = username
                customer.is_active = True
                
                # Save with payment plan data - only call save once
                payment_plan_data = payment_plan_form.cleaned_data
                customer = form.save(payment_plan_data=payment_plan_data)
                
                messages.success(request, "Customer added successfully with payment plan!")
                return redirect('dashboard-customer')
            else:
                errors = form.errors
                messages.error(request, errors)
                context = {
                    "title": "Add Customer | Dashboard",
                    "form": form,
                    "payment_plan_form": payment_plan_form,
                }
                return render(request, "dashboard/student/add-student.html", context)
        else:
            form = CustomerForm()  
            payment_plan_form = PaymentPlanForm()
            context = {
                "title": "Add Customer",
                "form": form,
                "payment_plan_form": payment_plan_form,
            }
            return render(request, "dashboard/student/add-student.html", context)

    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def update(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 3 or request.user.user_type == 4:
        is_mentor = request.user.user_type == 4
        customer = get_object_or_404(CustomUser, pk=pk)
        
        if request.method == "POST":
            form = CustomerUpdateForm(request.POST, request.FILES, instance=customer)
            if form.is_valid():
                updated_customer = form.save(commit=False)
                
                # Check if the remove_image parameter is present
                if 'remove_image' in request.POST:
                    # If the user wants to remove the image
                    if updated_customer.image:
                        # Delete the physical file
                        if updated_customer.image.storage.exists(updated_customer.image.name):
                            updated_customer.image.storage.delete(updated_customer.image.name)
                        # Clear the image field
                        updated_customer.image = None
                # Check if a new file was uploaded
                elif 'image' in request.FILES:
                    # If there's an existing image, delete it first
                    if customer.image and customer.image.name != request.FILES['image'].name:
                        if customer.image.storage.exists(customer.image.name):
                            customer.image.storage.delete(customer.image.name)
                
                updated_customer.save()
                messages.success(request, "Student updated successfully!")
                return redirect('dashboard-customer')
            else:
                context = {
                    "title": "Update Student | Dashboard",
                    "form": form,
                    "is_mentor": is_mentor,
                }
                return render(request, "dashboard/student/update-student.html", context)
        else:
            form = CustomerUpdateForm(instance=customer)
            context = {
                "title": "Update Student",
                "form": form,
                "is_mentor": is_mentor,
            }
            return render(request, "dashboard/student/update-student.html", context)
    else:
        return redirect('/')


@login_required(login_url='dashboard-login')
def delete(request,pk):
    if request.method == "POST":
        customer = get_object_or_404(CustomUser, pk=pk)
        customer.is_deleted = True
        customer.save()
        messages.success(request, "Customer deleted successfully!")
        return redirect('dashboard-customer')
    else:
        messages.error(request, "Invalid request .")
        return redirect('dashboard-customer')

@login_required(login_url='dashboard-login')
def suspend_student(request,pk):
    if request.user.user_type == 1 or request.user.user_type == 3 or request.user.user_type == 4:
        if request.method == "POST":
            customer = get_object_or_404(CustomUser, pk=pk)
            customer.is_suspended = True
            customer.suspended_date = timezone.now()
            customer.save()
            messages.success(request, "Customer suspended successfully!")
        return redirect('dashboard-customer')
    else:
        messages.error(request, "Invalid request .")
        return redirect('dashboard-customer')
    

@login_required(login_url='dashboard-login')
def unsuspend_student(request,pk):
    if request.user.user_type == 1 or request.user.user_type == 3 or request.user.user_type == 4:
        if request.method == "POST":
            customer = get_object_or_404(CustomUser, pk=pk)
            customer.is_suspended = False
            customer.suspended_date = None
            customer.save()
            messages.success(request, "Customer unsuspended successfully!")
        return redirect('dashboard-customer')
    else:
        messages.error(request, "Invalid request .")
        return redirect('dashboard-customer')
    
@login_required(login_url='dashboard-login')
def detail(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 3 or request.user.user_type == 4:
        customer = get_object_or_404(CustomUser, pk=pk)
        
        subscriptions = Subscription.objects.filter(user=customer, is_deleted=False).prefetch_related('batch')

        batch_details = []
        for subscription in subscriptions:  
            for batch in subscription.batch.all():
                batch_details.append({
                    'start_date': batch.start_date,
                    'expiry_date': batch.batch_expiry,
                    'price': batch.batch_price,
                    'course_name': batch.course.course_name,
                    'subscription_id': subscription.id
                })
        
        # Fetch all progressions of the student where exam is null (level progressions)
        level_progressions = StudentProgress.objects.filter(student__id=pk, is_deleted=False, exam__isnull=True).select_related('level')

        # Get exam type filter parameter
        exam_type_filter = request.GET.get('exam_type', '')
        
        # Fetch all progressions of the student where exam is not null (exam progressions)
        exam_progressions_query = StudentProgress.objects.filter(student__id=pk, is_deleted=False, exam__isnull=False).select_related('exam')
        
        # Apply exam type filter if provided
        if exam_type_filter:
            exam_progressions = exam_progressions_query.filter(exam__exam_type=exam_type_filter)
        else:
            exam_progressions = exam_progressions_query

        # Prepare progress data for level progressions
        progress_data = []
        for progress in level_progressions:
            details = progress.details.filter(is_deleted=False).select_related('question')
            
            # Filter questions
            correct_answers = details.filter(is_correct=True)
            wrong_answers = details.filter(is_correct=False, answered=True)
            unanswered_questions = details.filter(answered=False)

            # Add detailed question data to progress
            progress_data.append({
                'level': progress.level,
                'correct_answers': [
                    {
                        'question': detail.question.question_description,
                        'your_answer': detail.selected_option,
                        'correct_answer': detail.question.right_answers,
                    }
                    for detail in correct_answers
                ],
                'wrong_answers': [
                    {
                        'question': detail.question.question_description,
                        'your_answer': detail.selected_option,
                        'correct_answer': detail.question.right_answers,
                    }
                    for detail in wrong_answers
                ],
                'unanswered_questions': [
                    {
                        'question': detail.question.question_description,
                    }
                    for detail in unanswered_questions
                ],
                'total_questions': details.count(),
            })
        
        exam_progress_data = []
        for progress in exam_progressions:
            details = progress.details.filter(is_deleted=False).select_related('question')
            
            # Filter questions
            correct_answers = details.filter(is_correct=True)
            wrong_answers = details.filter(is_correct=False, answered=True)
            unanswered_questions = details.filter(answered=False)

            # Add detailed question data to progress
            exam_progress_data.append({
                'exam': progress.exam,
                'correct_answers': [
                    {
                        'question': detail.question.question_description,
                        'your_answer': detail.selected_option,
                        'correct_answer': detail.question.right_answers,
                    }
                    for detail in correct_answers
                ],
                'wrong_answers': [
                    {
                        'question': detail.question.question_description,
                        'your_answer': detail.selected_option,
                        'correct_answer': detail.question.right_answers,
                    }
                    for detail in wrong_answers
                ],
                'unanswered_questions': [
                    {
                        'question': detail.question.question_description,
                    }
                    for detail in unanswered_questions
                ],
                'total_questions': details.count(),
            })

        subscribed_batches = Subscription.objects.filter(user=customer, is_deleted=False).values_list('batch', flat=True)

        available_batches = Batch.objects.filter(is_deleted=False).exclude(id__in=subscribed_batches)
        
        # Get available payment plans for the dropdown
        available_payment_plans = FeePaymentPlan.objects.filter(is_deleted=False)

        # Get all available exam types for the filter dropdown
        exam_types = Exam.EXAM_TYPE_CHOICES
        
        context = {
            "title": "Customer Detail",
            "customer": customer,
            "subscriptions": subscriptions,
            "batch_details": batch_details,
            "student": level_progressions.first().student if level_progressions.exists() else None,
            "progress_data": progress_data,  
            "exam_progress_data": exam_progress_data,
            "available_batches": available_batches,
            "available_payment_plans": available_payment_plans,
            "exam_types": exam_types,
            "selected_exam_type": exam_type_filter,
            # "page_obj": page_obj,
        }
        
        return render(request, "dashboard/student/student-details.html", context)
    else:
        return redirect('/')



@login_required(login_url='dashboard-login')
def subscription_customer_update(request,pk):
    if request.user.user_type == 1 or request.user.user_type == 3:
        customer = get_object_or_404(CustomUser, pk=pk)
        if request.method == "POST":
            form = CustomerForm(request.POST, request.FILES, instance=customer)
            if form.is_valid():
                updated_customer = form.save(commit=False)
                updated_customer.save()

                batches = form.cleaned_data.get('batches')
                subscription = Subscription.objects.get(user=updated_customer)
                subscription.batch  .set(batches)  
                subscription.save()

                messages.success(request, "Customer updated successfully!")
                return redirect('dashboard-user-detail',pk)
            else:
                context = {
                    "title": "Update Customer | Dashboard",
                    "form": form,
                }
                return render(request, "dashboard/customer/update.html", context)
        else:
            form = CustomerForm(instance=customer)
            context = {
                "title": "Update Customer",
                "form": form,
            }
            return render(request, "dashboard/customer/update.html", context)
        
    else:
        return redirect('/')




@login_required(login_url='dashboard-login')
def subscription_add(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 3:
        customer = CustomUser.objects.get(id=pk, is_deleted=False)

        if request.method == "POST":
            form = SubscriptionCustomerForm(request.POST, request.FILES, customer=customer)
            if form.is_valid():
                batch = form.cleaned_data.get('batch')

                # Create or get existing subscription
                subscription, created = Subscription.objects.get_or_create(user=customer,is_deleted=False)
                
                if batch:
                    if subscription.batch.filter(id=batch.id).exists():
                        messages.error(request, "This batch is already added to the subscription.")
                    else:
                        subscription.batch.add(batch)
                        messages.success(request, "Subscription added successfully!")
                
                subscription.save()
                return redirect('dashboard-user-detail', pk)
            else:
                context = {
                    "form": form,
                    "pk": pk
                }
                return render(request, "dashboard/customer/batch_add.html", context)
        else:
            form = SubscriptionCustomerForm(customer=customer)
            context = {
                "title": "Add Batch",
                "form": form,
                "pk": pk
            }
            return render(request, "dashboard/customer/batch_add.html", context)
    else:
        return redirect('/')



@login_required(login_url='dashboard-login')
def subscription_delete(request,pk):
    if request.method == 'POST':
        subscription= Subscription.objects.get(id=pk)
        user_id=subscription.user.id
        subscription.is_deleted = True
        subscription.save()
        messages.success(request, " deleted successfully!")
        return redirect('dashboard-user-detail',pk=user_id)
    else:
        messages.success(request, " Action denied!")
        return redirect('dashboard-user-detail',pk=user_id)




def result(request,pk):
    return render(request,'dashboard/student/student-result.html')


def export_talenthunt_results_pdf(request, pk):
    """
    Export TalentHunt results for a specific student as PDF file
    """
    if request.user.user_type not in [1, 3, 4]:
        messages.error(request, "You don't have permission to access this resource.")
        return redirect('/')
        
    customer = get_object_or_404(CustomUser, pk=pk)
    
    # Fetch all progressions of the student where exam is null (level progressions)
    level_progressions = StudentProgress.objects.filter(
        student__id=pk, is_deleted=False, exam__isnull=True
    ).select_related('level')
    
    # Create a file-like buffer to receive PDF data
    buffer = BytesIO()
    
    # Create the PDF object using the buffer as its "file"
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    
    # Create styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Add title
    elements.append(Paragraph(f"TalentHunt Results for {customer.name}", title_style))
    elements.append(Spacer(1, 20))
    
    # Add student information
    elements.append(Paragraph("Student Information", subtitle_style))
    elements.append(Spacer(1, 10))
    
    # Student info table
    student_data = [
        ['ID', str(customer.id)],
        ['Name', customer.name or 'N/A'],
        ['Email', customer.email or 'N/A'],
        ['Phone', customer.phone_number or 'N/A']
    ]
    
    student_table = Table(student_data, colWidths=[100, 300])
    student_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
    ]))
    
    elements.append(student_table)
    elements.append(Spacer(1, 20))
    
    # Add summary table header
    elements.append(Paragraph("TalentHunt Results Summary", subtitle_style))
    elements.append(Spacer(1, 10))
    
    # Create summary table data
    summary_data = [
        ['Level', 'Total Questions', 'Correct Answers', 'Wrong Answers', 'Unanswered', 'Score (%)']
    ]
    
    # Add data rows to summary table
    for progress in level_progressions:
        details = progress.details.filter(is_deleted=False).select_related('question')
        
        # Filter questions
        correct_answers = details.filter(is_correct=True)
        wrong_answers = details.filter(is_correct=False, answered=True)
        unanswered_questions = details.filter(answered=False)
        
        total_questions = details.count()
        correct_count = correct_answers.count()
        
        # Calculate score percentage
        score_percentage = 0
        if total_questions > 0:
            score_percentage = (correct_count / total_questions) * 100
        
        # Get level title
        level_title = progress.level.title
        if hasattr(progress.level, 'talenthuntsubject') and hasattr(progress.level.talenthuntsubject, 'talentHunt'):
            level_title = f"{progress.level.talenthuntsubject.talentHunt.title} - {level_title}"
        
        # Add row to summary data
        summary_data.append([
            level_title,
            str(total_questions),
            str(correct_count),
            str(wrong_answers.count()),
            str(unanswered_questions.count()),
            f"{score_percentage:.2f}%"
        ])
    
    # Create summary table
    summary_table = Table(summary_data, colWidths=[200, 100, 100, 100, 100, 100])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8)
    ]))
    
    elements.append(summary_table)
    
    # Add detailed results for each level
    for i, progress in enumerate(level_progressions):
        elements.append(Spacer(1, 30))
        
        # Get level title
        level_title = progress.level.title
        if hasattr(progress.level, 'talenthuntsubject') and hasattr(progress.level.talenthuntsubject, 'talentHunt'):
            level_title = f"{progress.level.talenthuntsubject.talentHunt.title} - {level_title}"
        
        elements.append(Paragraph(f"Level: {level_title}", subtitle_style))
        elements.append(Spacer(1, 10))
        
        details = progress.details.filter(is_deleted=False).select_related('question')
        correct_answers = details.filter(is_correct=True)
        wrong_answers = details.filter(is_correct=False, answered=True)
        unanswered_questions = details.filter(answered=False)
        
        # Add correct answers section if there are any
        if correct_answers.exists():
            elements.append(Paragraph("Correct Answers", subtitle_style))
            elements.append(Spacer(1, 5))
            
            correct_data = [['Question', 'Your Answer', 'Correct Answer']]
            
            for detail in correct_answers:
                correct_answer_text = ''
                if detail.question.right_answers and len(detail.question.right_answers) > 0:
                    correct_answer_text = detail.question.right_answers[0].get('text', '')
                
                correct_data.append([
                    detail.question.question_description,
                    detail.selected_option or 'N/A',
                    correct_answer_text
                ])
            
            correct_table = Table(correct_data, colWidths=[250, 150, 150])
            correct_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6)
            ]))
            
            elements.append(correct_table)
        
        # Add wrong answers section if there are any
        if wrong_answers.exists():
            elements.append(Spacer(1, 15))
            elements.append(Paragraph("Wrong Answers", subtitle_style))
            elements.append(Spacer(1, 5))
            
            wrong_data = [['Question', 'Your Answer', 'Correct Answer']]
            
            for detail in wrong_answers:
                correct_answer_text = ''
                if detail.question.right_answers and len(detail.question.right_answers) > 0:
                    correct_answer_text = detail.question.right_answers[0].get('text', '')
                
                wrong_data.append([
                    detail.question.question_description,
                    detail.selected_option or 'N/A',
                    correct_answer_text
                ])
            
            wrong_table = Table(wrong_data, colWidths=[250, 150, 150])
            wrong_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6)
            ]))
            
            elements.append(wrong_table)
        
        # Add unanswered questions section if there are any
        if unanswered_questions.exists():
            elements.append(Spacer(1, 15))
            elements.append(Paragraph("Unanswered Questions", subtitle_style))
            elements.append(Spacer(1, 5))
            
            unanswered_data = [['Question']]
            
            for detail in unanswered_questions:
                unanswered_data.append([detail.question.question_description])
            
            unanswered_table = Table(unanswered_data, colWidths=[550])
            unanswered_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6)
            ]))
            
            elements.append(unanswered_table)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create the HttpResponse object with PDF header
    filename = f"{customer.name}_talenthunt_results.pdf"
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    
    return response

@login_required(login_url='dashboard-login')
def export_talenthunt_results(request, pk):
    """
    Export TalentHunt results for a specific student as Excel file
    """
    if request.user.user_type not in [1, 3, 4]:
        messages.error(request, "You don't have permission to access this resource.")
        return redirect('/')
        
    customer = get_object_or_404(CustomUser, pk=pk)
    
    # Fetch all progressions of the student where exam is null (level progressions)
    level_progressions = StudentProgress.objects.filter(
        student__id=pk, is_deleted=False, exam__isnull=True
    ).select_related('level')
    
    if request.GET.get('format') == 'pdf':
        return export_talenthunt_results_pdf(request, pk)
    
    # Create a BytesIO object to store the Excel file   
    output = BytesIO()
    
    # Create an Excel workbook and add a worksheet
    workbook = xlsxwriter.Workbook(output)
    
    # Add formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#f0f0f0',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'text_wrap': True,
    })
    
    # Create summary worksheet
    summary_sheet = workbook.add_worksheet('Summary')
    
    # Write student information
    summary_sheet.write(0, 0, 'Student Information', header_format)
    summary_sheet.merge_range('A1:F1', 'Student Information', header_format)
    
    summary_sheet.write(1, 0, 'ID', header_format)
    summary_sheet.write(1, 1, customer.id, cell_format)
    
    summary_sheet.write(2, 0, 'Name', header_format)
    summary_sheet.write(2, 1, customer.name, cell_format)
    
    summary_sheet.write(3, 0, 'Email', header_format)
    summary_sheet.write(3, 1, customer.email, cell_format)
    
    summary_sheet.write(4, 0, 'Phone', header_format)
    summary_sheet.write(4, 1, customer.phone_number, cell_format)
    
    # Write TalentHunt summary
    summary_sheet.write(6, 0, 'TalentHunt Results Summary', header_format)
    summary_sheet.merge_range('A7:F7', 'TalentHunt Results Summary', header_format)
    
    summary_sheet.write(8, 0, 'Level', header_format)
    summary_sheet.write(8, 1, 'Total Questions', header_format)
    summary_sheet.write(8, 2, 'Correct Answers', header_format)
    summary_sheet.write(8, 3, 'Wrong Answers', header_format)
    summary_sheet.write(8, 4, 'Unanswered', header_format)
    summary_sheet.write(8, 5, 'Score (%)', header_format)
    
    row = 9
    for i, progress in enumerate(level_progressions):
        details = progress.details.filter(is_deleted=False).select_related('question')
        
        # Filter questions
        correct_answers = details.filter(is_correct=True)
        wrong_answers = details.filter(is_correct=False, answered=True)
        unanswered_questions = details.filter(answered=False)
        
        total_questions = details.count()
        correct_count = correct_answers.count()
        
        # Calculate score percentage
        score_percentage = 0
        if total_questions > 0:
            score_percentage = (correct_count / total_questions) * 100
        
        # Write summary row
        level_title = progress.level.title
        if hasattr(progress.level, 'talenthuntsubject') and hasattr(progress.level.talenthuntsubject, 'talentHunt'):
            level_title = f"{progress.level.talenthuntsubject.talentHunt.title} - {level_title}"
            
        summary_sheet.write(row, 0, level_title, cell_format)
        summary_sheet.write(row, 1, total_questions, cell_format)
        summary_sheet.write(row, 2, correct_count, cell_format)
        summary_sheet.write(row, 3, wrong_answers.count(), cell_format)
        summary_sheet.write(row, 4, unanswered_questions.count(), cell_format)
        summary_sheet.write(row, 5, f"{score_percentage:.2f}%", cell_format)
        
        row += 1
        
        # Create detailed worksheet for each level
        detail_sheet = workbook.add_worksheet(f'Level {i+1}')
        
        # Write level information
        detail_sheet.merge_range('A1:D1', f'Level: {level_title}', header_format)
        
        # Write headers for correct answers
        detail_sheet.merge_range('A3:D3', 'Correct Answers', header_format)
        detail_sheet.write(3, 0, 'Question', header_format)
        detail_sheet.write(3, 1, 'Your Answer', header_format)
        detail_sheet.write(3, 2, 'Correct Answer', header_format)
        
        # Write correct answers
        row_detail = 4
        for detail in correct_answers:
            detail_sheet.write(row_detail, 0, detail.question.question_description, cell_format)
            detail_sheet.write(row_detail, 1, detail.selected_option, cell_format)
            if detail.question.right_answers and len(detail.question.right_answers) > 0:
                detail_sheet.write(row_detail, 2, detail.question.right_answers[0].get('text', ''), cell_format)
            row_detail += 1
        
        # Write headers for wrong answers
        row_detail += 1
        detail_sheet.merge_range(f'A{row_detail}:D{row_detail}', 'Wrong Answers', header_format)
        row_detail += 1
        detail_sheet.write(row_detail, 0, 'Question', header_format)
        detail_sheet.write(row_detail, 1, 'Your Answer', header_format)
        detail_sheet.write(row_detail, 2, 'Correct Answer', header_format)
        row_detail += 1
        
        # Write wrong answers
        for detail in wrong_answers:
            detail_sheet.write(row_detail, 0, detail.question.question_description, cell_format)
            detail_sheet.write(row_detail, 1, detail.selected_option, cell_format)
            if detail.question.right_answers and len(detail.question.right_answers) > 0:
                detail_sheet.write(row_detail, 2, detail.question.right_answers[0].get('text', ''), cell_format)
            row_detail += 1
        
        # Write headers for unanswered questions
        row_detail += 1
        detail_sheet.merge_range(f'A{row_detail}:D{row_detail}', 'Unanswered Questions', header_format)
        row_detail += 1
        detail_sheet.write(row_detail, 0, 'Question', header_format)
        row_detail += 1
        
        # Write unanswered questions
        for detail in unanswered_questions:
            detail_sheet.write(row_detail, 0, detail.question.question_description, cell_format)
            row_detail += 1
    
    # Set column widths
    summary_sheet.set_column('A:A', 30)
    summary_sheet.set_column('B:F', 15)
    
    workbook.close()
    
    # Rewind the buffer
    output.seek(0)
    
    # Create the HttpResponse with appropriate headers
    filename = f"{customer.name}_talenthunt_results.xlsx"
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


def export_exam_results_pdf(request, pk):
    """
    Export Exam results for a specific student as PDF file
    """
    if request.user.user_type not in [1, 3, 4]:
        messages.error(request, "You don't have permission to access this resource.")
        return redirect('/')
        
    customer = get_object_or_404(CustomUser, pk=pk)
    
    # Get exam type filter parameter
    exam_type_filter = request.GET.get('exam_type', '')
    
    # Fetch all progressions of the student where exam is not null (exam progressions)
    exam_progressions_query = StudentProgress.objects.filter(
        student__id=pk, is_deleted=False, exam__isnull=False
    ).select_related('exam')
    
    # Apply exam type filter if provided
    if exam_type_filter:
        exam_progressions = exam_progressions_query.filter(exam__exam_type=exam_type_filter)
    else:
        exam_progressions = exam_progressions_query
    
    # Create a file-like buffer to receive PDF data
    buffer = BytesIO()
    
    # Create the PDF object using the buffer as its "file"
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    
    # Create styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Add title
    elements.append(Paragraph(f"Exam Results for {customer.name}", title_style))
    elements.append(Spacer(1, 20))
    
    # Add student information
    elements.append(Paragraph("Student Information", subtitle_style))
    elements.append(Spacer(1, 10))
    
    # Student info table
    student_data = [
        ['ID', str(customer.id)],
        ['Name', customer.name or 'N/A'],
        ['Email', customer.email or 'N/A'],
        ['Phone', customer.phone_number or 'N/A']
    ]
    
    student_table = Table(student_data, colWidths=[100, 300])
    student_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
    ]))
    
    elements.append(student_table)
    elements.append(Spacer(1, 20))
    
    # Add summary table header
    elements.append(Paragraph("Exam Results Summary", subtitle_style))
    elements.append(Spacer(1, 10))
    
    # Create summary table data
    summary_data = [
        ['Exam', 'Total Questions', 'Correct Answers', 'Wrong Answers', 'Unanswered', 'Negative Marks', 'Score (%)']
    ]
    
    # Add data rows to summary table
    for progress in exam_progressions:
        details = progress.details.filter(is_deleted=False).select_related('question')
        
        # Filter questions
        correct_answers = details.filter(is_correct=True)
        wrong_answers = details.filter(is_correct=False, answered=True)
        unanswered_questions = details.filter(answered=False)
        
        total_questions = details.count()
        correct_count = correct_answers.count()
        
        # Get total marks and negative marks
        total_marks_obtained = correct_answers.aggregate(models.Sum('marks_obtained'))['marks_obtained__sum'] or 0
        total_negative_marks = wrong_answers.aggregate(models.Sum('negative_marks'))['negative_marks__sum'] or 0
        
        # Calculate net score after applying negative marking
        net_score = total_marks_obtained - total_negative_marks
        
        # Calculate maximum possible score
        max_possible_score = sum(q.question.mark or 0 for q in details)
        
        # Calculate score percentage with negative marking
        score_percentage = 0
        if max_possible_score > 0:
            score_percentage = (net_score / max_possible_score) * 100
        
        # Get exam title
        exam_title = progress.exam.title if progress.exam else "Unknown Exam"
        
        # Add row to summary data
        summary_data.append([
            exam_title,
            str(total_questions),
            str(correct_count),
            str(wrong_answers.count()),
            str(unanswered_questions.count()),
            f"{total_negative_marks:.2f}",
            f"{score_percentage:.2f}%"
        ])
    
    # Create summary table
    summary_table = Table(summary_data, colWidths=[150, 100, 100, 100, 100, 100, 100])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8)
    ]))
    
    elements.append(summary_table)
    
    # Add detailed results for each exam
    for i, progress in enumerate(exam_progressions):
        elements.append(Spacer(1, 30))
        
        # Get exam title
        exam_title = progress.exam.title if progress.exam else f"Exam {i+1}"
        
        elements.append(Paragraph(f"Exam: {exam_title}", subtitle_style))
        elements.append(Spacer(1, 10))
        
        details = progress.details.filter(is_deleted=False).select_related('question')
        correct_answers = details.filter(is_correct=True)
        wrong_answers = details.filter(is_correct=False, answered=True)
        unanswered_questions = details.filter(answered=False)
        
        # Get total marks and negative marks
        total_marks_obtained = correct_answers.aggregate(models.Sum('marks_obtained'))['marks_obtained__sum'] or 0
        total_negative_marks = wrong_answers.aggregate(models.Sum('negative_marks'))['negative_marks__sum'] or 0
        net_score = total_marks_obtained - total_negative_marks
        
        # Add exam score summary
        score_data = [
            ['Total Marks Obtained', f"{total_marks_obtained:.2f}", 'Negative Marks', f"{total_negative_marks:.2f}"],
            ['Net Score', f"{net_score:.2f}", '', '']
        ]
        
        score_table = Table(score_data, colWidths=[150, 100, 150, 100])
        score_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
        ]))
        
        elements.append(score_table)
        elements.append(Spacer(1, 15))
        
        # Add correct answers section if there are any
        if correct_answers.exists():
            elements.append(Paragraph("Correct Answers", subtitle_style))
            elements.append(Spacer(1, 5))
            
            correct_data = [['Question', 'Your Answer', 'Correct Answer', 'Marks']]
            
            for detail in correct_answers:
                correct_answer_text = ''
                if detail.question.right_answers and len(detail.question.right_answers) > 0:
                    correct_answer_text = detail.question.right_answers[0].get('text', '')
                
                correct_data.append([
                    detail.question.question_description,
                    detail.selected_option or 'N/A',
                    correct_answer_text,
                    str(detail.marks_obtained or 0)
                ])
            
            correct_table = Table(correct_data, colWidths=[250, 100, 100, 50])
            correct_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6)
            ]))
            
            elements.append(correct_table)
        
        # Add wrong answers section if there are any
        if wrong_answers.exists():
            elements.append(Spacer(1, 15))
            elements.append(Paragraph("Wrong Answers", subtitle_style))
            elements.append(Spacer(1, 5))
            
            wrong_data = [['Question', 'Your Answer', 'Correct Answer', 'Negative Marks']]
            
            for detail in wrong_answers:
                correct_answer_text = ''
                if detail.question.right_answers and len(detail.question.right_answers) > 0:
                    correct_answer_text = detail.question.right_answers[0].get('text', '')
                
                wrong_data.append([
                    detail.question.question_description,
                    detail.selected_option or 'N/A',
                    correct_answer_text,
                    str(detail.negative_marks or 0)
                ])
            
            wrong_table = Table(wrong_data, colWidths=[250, 100, 100, 50])
            wrong_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6)
            ]))
            
            elements.append(wrong_table)
        
        # Add unanswered questions section if there are any
        if unanswered_questions.exists():
            elements.append(Spacer(1, 15))
            elements.append(Paragraph("Unanswered Questions", subtitle_style))
            elements.append(Spacer(1, 5))
            
            unanswered_data = [['Question']]
            
            for detail in unanswered_questions:
                unanswered_data.append([detail.question.question_description])
            
            unanswered_table = Table(unanswered_data, colWidths=[550])
            unanswered_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6)
            ]))
            
            elements.append(unanswered_table)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create the HttpResponse object with PDF header
    filename = f"{customer.name}_exam_results.pdf"
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    
    return response

@login_required(login_url='dashboard-login')
def export_exam_results(request, pk):
    """
    Export Exam results for a specific student as Excel file
    """
    if request.user.user_type not in [1, 3, 4]:
        messages.error(request, "You don't have permission to access this resource.")
        return redirect('/')
        
    customer = get_object_or_404(CustomUser, pk=pk)
    
    # Get filter parameters
    exam_type_filter = request.GET.get('exam_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Fetch all progressions of the student where exam is not null (exam progressions)
    exam_progressions_query = StudentProgress.objects.filter(
        student__id=pk, is_deleted=False, exam__isnull=False
    ).select_related('exam')
    
    # Apply exam type filter if provided
    if exam_type_filter:
        exam_progressions_query = exam_progressions_query.filter(exam__exam_type=exam_type_filter)
    
    # Apply date range filters if provided
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            exam_progressions_query = exam_progressions_query.filter(created__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            exam_progressions_query = exam_progressions_query.filter(created__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Get final queryset
    exam_progressions = exam_progressions_query
    
    if request.GET.get('format') == 'pdf':
        return export_exam_results_pdf(request, pk)
    
    # Create a BytesIO object to store the Excel file
    output = BytesIO()
    
    # Create an Excel workbook and add a worksheet
    workbook = xlsxwriter.Workbook(output)
    
    # Add formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#f0f0f0',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'text_wrap': True,
    })
    
    # Create summary worksheet
    summary_sheet = workbook.add_worksheet('Summary')
    
    # Write student information
    summary_sheet.write(0, 0, 'Student Information', header_format)
    summary_sheet.merge_range('A1:F1', 'Student Information', header_format)
    
    summary_sheet.write(1, 0, 'ID', header_format)
    summary_sheet.write(1, 1, customer.id, cell_format)
    
    summary_sheet.write(2, 0, 'Name', header_format)
    summary_sheet.write(2, 1, customer.name, cell_format)
    
    summary_sheet.write(3, 0, 'Email', header_format)
    summary_sheet.write(3, 1, customer.email, cell_format)
    
    summary_sheet.write(4, 0, 'Phone', header_format)
    summary_sheet.write(4, 1, customer.phone_number, cell_format)
    
    # Write Exam summary
    summary_sheet.write(6, 0, 'Exam Results Summary', header_format)
    summary_sheet.merge_range('A7:G7', 'Exam Results Summary', header_format)
    
    summary_sheet.write(8, 0, 'Exam', header_format)
    summary_sheet.write(8, 1, 'Total Questions', header_format)
    summary_sheet.write(8, 2, 'Correct Answers', header_format)
    summary_sheet.write(8, 3, 'Wrong Answers', header_format)
    summary_sheet.write(8, 4, 'Unanswered', header_format)
    summary_sheet.write(8, 5, 'Negative Marks', header_format)
    summary_sheet.write(8, 6, 'Score (%)', header_format)
    
    row = 9
    for i, progress in enumerate(exam_progressions):
        details = progress.details.filter(is_deleted=False).select_related('question')
        
        # Filter questions
        correct_answers = details.filter(is_correct=True)
        wrong_answers = details.filter(is_correct=False, answered=True)
        unanswered_questions = details.filter(answered=False)
        
        total_questions = details.count()
        correct_count = correct_answers.count()
        
        # Get total marks and negative marks
        total_marks_obtained = correct_answers.aggregate(models.Sum('marks_obtained'))['marks_obtained__sum'] or 0
        total_negative_marks = wrong_answers.aggregate(models.Sum('negative_marks'))['negative_marks__sum'] or 0
        
        # Calculate net score after applying negative marking
        net_score = total_marks_obtained - total_negative_marks
        
        # Calculate maximum possible score
        max_possible_score = sum(q.question.mark or 0 for q in details)
        
        # Calculate score percentage with negative marking
        score_percentage = 0
        if max_possible_score > 0:
            score_percentage = (net_score / max_possible_score) * 100
        
        # Write summary row
        exam_title = progress.exam.title if progress.exam else f"Exam {i+1}"
            
        summary_sheet.write(row, 0, exam_title, cell_format)
        summary_sheet.write(row, 1, total_questions, cell_format)
        summary_sheet.write(row, 2, correct_count, cell_format)
        summary_sheet.write(row, 3, wrong_answers.count(), cell_format)
        summary_sheet.write(row, 4, unanswered_questions.count(), cell_format)
        summary_sheet.write(row, 5, f"{total_negative_marks:.2f}", cell_format)
        summary_sheet.write(row, 6, f"{score_percentage:.2f}%", cell_format)
        
        row += 1
        
        # Create detailed worksheet for each exam
        detail_sheet = workbook.add_worksheet(f'Exam {i+1}')
        
        # Write exam information
        detail_sheet.merge_range('A1:E1', f'Exam: {exam_title}', header_format)
        
        # Add exam score summary with negative marking
        detail_sheet.write(1, 0, 'Total Marks Obtained:', header_format)
        detail_sheet.write(1, 1, f"{total_marks_obtained:.2f}", cell_format)
        
        detail_sheet.write(1, 2, 'Negative Marks:', header_format)
        detail_sheet.write(1, 3, f"{total_negative_marks:.2f}", cell_format)
        
        detail_sheet.write(2, 0, 'Net Score:', header_format)
        detail_sheet.write(2, 1, f"{net_score:.2f}", cell_format)
        
        # Write headers for correct answers
        detail_sheet.merge_range('A3:E3', 'Correct Answers', header_format)
        detail_sheet.write(3, 0, 'Question', header_format)
        detail_sheet.write(3, 1, 'Your Answer', header_format)
        detail_sheet.write(3, 2, 'Correct Answer', header_format)
        detail_sheet.write(3, 3, 'Marks', header_format)
        
        # Write correct answers
        row_detail = 4
        for detail in correct_answers:
            detail_sheet.write(row_detail, 0, detail.question.question_description, cell_format)
            detail_sheet.write(row_detail, 1, detail.selected_option, cell_format)
            if detail.question.right_answers and len(detail.question.right_answers) > 0:
                detail_sheet.write(row_detail, 2, detail.question.right_answers[0].get('text', ''), cell_format)
            detail_sheet.write(row_detail, 3, detail.marks_obtained or 0, cell_format)
            row_detail += 1
        
        # Write headers for wrong answers
        row_detail += 1
        detail_sheet.merge_range(f'A{row_detail}:E{row_detail}', 'Wrong Answers', header_format)
        row_detail += 1
        detail_sheet.write(row_detail, 0, 'Question', header_format)
        detail_sheet.write(row_detail, 1, 'Your Answer', header_format)
        detail_sheet.write(row_detail, 2, 'Correct Answer', header_format)
        detail_sheet.write(row_detail, 3, 'Negative Marks', header_format)
        row_detail += 1
        
        # Write wrong answers
        for detail in wrong_answers:
            detail_sheet.write(row_detail, 0, detail.question.question_description, cell_format)
            detail_sheet.write(row_detail, 1, detail.selected_option, cell_format)
            if detail.question.right_answers and len(detail.question.right_answers) > 0:
                detail_sheet.write(row_detail, 2, detail.question.right_answers[0].get('text', ''), cell_format)
            detail_sheet.write(row_detail, 3, detail.negative_marks or 0, cell_format)
            row_detail += 1
        
        # Write headers for unanswered questions
        row_detail += 1
        detail_sheet.merge_range(f'A{row_detail}:E{row_detail}', 'Unanswered Questions', header_format)
        row_detail += 1
        detail_sheet.write(row_detail, 0, 'Question', header_format)
        row_detail += 1
        
        # Write unanswered questions
        for detail in unanswered_questions:
            detail_sheet.write(row_detail, 0, detail.question.question_description, cell_format)
            row_detail += 1
    
    # Set column widths
    summary_sheet.set_column('A:A', 30)
    summary_sheet.set_column('B:G', 15)
    
    workbook.close()
    
    # Rewind the buffer
    output.seek(0)
    
    # Create the HttpResponse with appropriate headers
    filename = f"{customer.name}_exam_results.xlsx"
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


def create_installments_for_plan(payment_plan, subscription):
    """
    Create installments for a payment plan associated with a subscription
    """
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    
    # Calculate the amount per installment
    total_after_discount = payment_plan.total_amount - payment_plan.discount
    amount_per_installment = total_after_discount / payment_plan.number_of_installments
    
    # Set the first due date as today by default
    current_date = datetime.now().date()
    
    # Get frequency from the payment plan
    frequency = payment_plan.frequency
    
    # Handle custom date range or batch duration
    custom_start_date = getattr(payment_plan, 'custom_start_date', None)
    custom_end_date = getattr(payment_plan, 'custom_end_date', None)
    
    # For batch duration, use the batch dates
    if frequency == 'batch_duration':
        # Get the first batch from the many-to-many relationship
        batch = subscription.batch.first()
        if batch:
            start_date = batch.start_date
            end_date = batch.batch_expiry
            
            # Calculate date intervals between start and end date
            total_days = (end_date - start_date).days
            interval_days = max(1, total_days // payment_plan.number_of_installments)
            
            # Create installments
            for i in range(payment_plan.number_of_installments):
                # For the last installment, use the end date
                if i == payment_plan.number_of_installments - 1:
                    due_date = end_date
                else:
                    due_date = start_date + timedelta(days=interval_days * i)
                
                # Create the installment
                FeeInstallment.objects.create(
                    subscription=subscription,
                    due_date=due_date,
                    amount_due=amount_per_installment,
                    status='PENDING',
                    discount_applied=payment_plan.discount / payment_plan.number_of_installments if hasattr(payment_plan, 'discount') else 0
                )
            return
    
    # For custom date range
    elif frequency == 'custom_date' and custom_start_date and custom_end_date:
        start_date = custom_start_date
        end_date = custom_end_date
        
        # Calculate date intervals between start and end date
        total_days = (end_date - start_date).days
        interval_days = max(1, total_days // payment_plan.number_of_installments)
        
        # Create installments
        for i in range(payment_plan.number_of_installments):
            # For the last installment, use the end date
            if i == payment_plan.number_of_installments - 1:
                due_date = end_date
            else:
                due_date = start_date + timedelta(days=interval_days * i)
            
            # Create the installment
            FeeInstallment.objects.create(
                subscription=subscription,
                due_date=due_date,
                amount_due=amount_per_installment,
                status='PENDING',
                discount_applied=payment_plan.discount / payment_plan.number_of_installments if hasattr(payment_plan, 'discount') else 0
            )
        return
    
    # Standard frequency options (weekly, monthly, yearly)
    for i in range(payment_plan.number_of_installments):
        if i == 0:
            # First installment due today
            due_date = current_date
        else:
            # Calculate next due date based on frequency
            if payment_plan.frequency == 'weekly':
                due_date = current_date + timedelta(days=7 * i)
            elif payment_plan.frequency == 'yearly':
                due_date = current_date + relativedelta(years=i)
            else:  # monthly is default
                due_date = current_date + relativedelta(months=i)
        
        # Create the installment with correct field names
        FeeInstallment.objects.create(
            subscription=subscription,
            amount_due=amount_per_installment,
            due_date=due_date,
            status='PENDING',
            discount_applied=payment_plan.discount / payment_plan.number_of_installments if hasattr(payment_plan, 'discount') else 0
        )


def admission_add(request, pk):
    customer = get_object_or_404(CustomUser, pk=pk)

    if request.method == 'POST':
        # First, validate the batch selection
        batch_id = request.POST.get('batch')
        if not batch_id:
            messages.error(request, "Please select a batch to subscribe to.")
            return redirect('dashboard-user-detail', pk=pk)
            
        batch = get_object_or_404(Batch, id=batch_id)
        
        # Check if subscription already exists for this user and batch
        existing_subscription = Subscription.objects.filter(
            user=customer,
            batch=batch
        ).exists()

        if existing_subscription:
            messages.warning(request, f"Subscription already exists for batch: {batch.batch_name}")
            return redirect('dashboard-user-detail', pk=pk)
        
        # Process the payment plan form
        form = PaymentPlanForm(request.POST)
        
        if form.is_valid():
            # Create a new subscription for the selected batch
            subscription = Subscription.objects.create(user=customer)
            subscription.batch.add(batch)
            
            # Handle payment plan based on form data
            payment_plan_type = form.cleaned_data['payment_plan_type']
            
            if payment_plan_type == 'existing':
                # Use existing payment plan
                payment_plan = form.cleaned_data.get('existing_plan')
                if payment_plan:
                    # Associate the payment plan with the subscription
                    subscription.payment_plan = payment_plan
                    subscription.save()
                    create_installments_for_plan(payment_plan, subscription)
                    messages.success(request, f"Subscription added with existing payment plan for batch: {batch.batch_name}")
                else:
                    messages.warning(request, f"Subscription added without a payment plan for batch: {batch.batch_name}")
            elif payment_plan_type == 'new':
                try:
                    # Create the payment plan using form data
                    payment_plan = FeePaymentPlan.objects.create(
                        name=form.cleaned_data['plan_name'],
                        total_amount=form.cleaned_data['total_amount'],
                        discount=form.cleaned_data['discount'] or Decimal('0.00'),
                        number_of_installments=form.cleaned_data['number_of_installments'],
                        frequency=form.cleaned_data['installment_frequency']
                    )
                    
                    # Store custom dates as attributes for use in create_installments_for_plan
                    if form.cleaned_data['installment_frequency'] == 'custom_date':
                        custom_start_date = request.POST.get('custom_start_date')
                        custom_end_date = request.POST.get('custom_end_date')
                        if custom_start_date and custom_end_date:
                            from datetime import datetime
                            payment_plan.custom_start_date = datetime.strptime(custom_start_date, '%Y-%m-%d').date()
                            payment_plan.custom_end_date = datetime.strptime(custom_end_date, '%Y-%m-%d').date()
                    
                    # Associate the payment plan with the subscription
                    subscription.payment_plan = payment_plan
                    subscription.save()
                    
                    # Create installments
                    create_installments_for_plan(payment_plan, subscription)
                    
                    messages.success(request, f"Subscription added with new payment plan for batch: {batch.batch_name}")
                except Exception as e:
                    messages.error(request, f"Error creating payment plan: {str(e)}")
            else:
                messages.success(request, f"Subscription added for batch: {batch.batch_name}")
        else:
            # Form validation failed
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            
            # Still create the subscription but without a payment plan
            subscription = Subscription.objects.create(user=customer)
            subscription.batch.add(batch)
            messages.warning(request, f"Subscription added without payment plan due to form errors for batch: {batch.batch_name}")
        
        return redirect('dashboard-user-detail', pk=pk)
    
    return redirect('dashboard-user-detail', pk=pk)


@login_required(login_url='dashboard-login')
def student_progress_report(request, pk):
    """
    Generate a comprehensive progress report for a student based on their exam performance
    """
    if request.user.user_type not in [1, 3, 4]:  # Admin, Teacher, Staff
        messages.error(request, "You don't have permission to access this resource.")
        return redirect('/')
        
    customer = get_object_or_404(CustomUser, pk=pk)
    
    # Get filter parameters
    exam_type_filter = request.GET.get('exam_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base query for exam progressions
    exam_progressions_query = StudentProgress.objects.filter(
        student__id=pk, is_deleted=False, exam__isnull=False
    ).select_related('exam')
    
    # Apply filters
    if exam_type_filter:
        exam_progressions_query = exam_progressions_query.filter(exam__exam_type=exam_type_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            exam_progressions_query = exam_progressions_query.filter(created__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            exam_progressions_query = exam_progressions_query.filter(created__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Order by date
    exam_progressions = exam_progressions_query.order_by('-created')
    
    # Calculate overall statistics
    total_exams = exam_progressions.count()
    passed_exams = exam_progressions.filter(passed=True).count()
    
    # Calculate average scores
    if total_exams > 0:
        avg_score_percentage = exam_progressions.aggregate(
            avg_score=Avg(F('marks_obtained') * 100 / F('total_marks'))
        )['avg_score'] or 0
    else:
        avg_score_percentage = 0
    
    # Get performance by exam type
    performance_by_type = []
    for exam_type, exam_type_label in Exam.EXAM_TYPE_CHOICES:
        type_exams = exam_progressions.filter(exam__exam_type=exam_type)
        type_count = type_exams.count()
        
        if type_count > 0:
            type_passed = type_exams.filter(passed=True).count()
            type_avg_score = type_exams.aggregate(
                avg_score=Avg(F('marks_obtained') * 100 / F('total_marks'))
            )['avg_score'] or 0
            
            performance_by_type.append({
                'type': exam_type_label,
                'count': type_count,
                'passed': type_passed,
                'pass_rate': (type_passed / type_count) * 100 if type_count > 0 else 0,
                'avg_score': type_avg_score
            })
    
    # Get performance trend over time (last 10 exams)
    recent_exams = exam_progressions[:10]
    trend_data = []
    
    for progress in recent_exams:
        if progress.total_marks > 0:
            score_percentage = (progress.marks_obtained / progress.total_marks) * 100
        else:
            score_percentage = 0
            
        trend_data.append({
            'date': progress.created.strftime('%Y-%m-%d'),
            'exam': progress.exam.title,
            'type': progress.exam.get_exam_type_display() if progress.exam.exam_type else 'Unknown',
            'score': score_percentage,
            'passed': progress.passed
        })
    
    # Get detailed exam data
    detailed_exam_data = []
    
    for progress in exam_progressions:
        details = progress.details.filter(is_deleted=False).select_related('question')
        
        # Calculate statistics
        total_questions = details.count()
        correct_answers = details.filter(is_correct=True).count()
        wrong_answers = details.filter(is_correct=False, answered=True).count()
        unanswered = details.filter(answered=False).count()
        
        if total_questions > 0:
            accuracy = (correct_answers / total_questions) * 100
        else:
            accuracy = 0

        detailed_exam_data.append({
            'exam': progress.exam,
            'date': progress.created,
            'marks_obtained': progress.marks_obtained,
            'total_marks': progress.total_marks,
            'percentage': (progress.marks_obtained / progress.total_marks) * 100 if progress.total_marks > 0 else 0,
            'passed': progress.passed,
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'wrong_answers': wrong_answers,
            'unanswered': unanswered,
            'accuracy': accuracy
        })
    
    context = {
        'title': f"{customer.name}'s Progress Report",
        'customer': customer,
        'exam_types': Exam.EXAM_TYPE_CHOICES,
        'selected_exam_type': exam_type_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_exams': total_exams,
        'passed_exams': passed_exams,
        'pass_rate': (passed_exams / total_exams) * 100 if total_exams > 0 else 0,
        'avg_score_percentage': avg_score_percentage,
        'performance_by_type': performance_by_type,
        'trend_data': trend_data,
        'detailed_exam_data': detailed_exam_data
    }
    
    return render(request, "dashboard/student/student-progress-report.html", context)


@login_required(login_url='dashboard-login')
def student_talenthunt_report(request, pk):
    """
    Generate a comprehensive progress report for a student based on their TalentHunt performance
    """
    if request.user.user_type not in [1, 3, 4]:  # Admin, Teacher, Staff
        messages.error(request, "You don't have permission to access this resource.")
        return redirect('/')
        
    customer = get_object_or_404(CustomUser, pk=pk)
    
    # Get filter parameters
    talenthunt_filter = request.GET.get('talenthunt', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base query for TalentHunt progressions
    level_progressions_query = StudentProgress.objects.filter(
        student__id=pk, is_deleted=False, exam__isnull=True, level__isnull=False
    ).select_related('level', 'level__talenthuntsubject', 'level__talenthuntsubject__talentHunt')

    # Apply filters
    if talenthunt_filter:
        level_progressions_query = level_progressions_query.filter(level__talenthuntsubject__talentHunt__id=talenthunt_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            level_progressions_query = level_progressions_query.filter(created__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            level_progressions_query = level_progressions_query.filter(created__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Order by date
    level_progressions = level_progressions_query.order_by('-created')
    
    # Calculate overall statistics
    total_attempts = level_progressions.count()
    
    # Calculate passed attempts, pass rate, and average score
    total_score_percentage = 0
    
    for progress in level_progressions:
        details = progress.details.filter(is_deleted=False).select_related('question')
        total_questions = details.count()
        correct_answers = details.filter(is_correct=True).count()
        
        if total_questions > 0:
            score_percentage = (correct_answers / total_questions) * 100
            total_score_percentage += score_percentage
    
    # Calculate pass rate and average score
    avg_score_percentage = total_score_percentage / total_attempts if total_attempts > 0 else 0
    
    # Get all TalentHunt tests for filter dropdown
    talenthunt_tests = TalentHunt.objects.filter(is_deleted=False)
    
    # Calculate performance by TalentHunt test
    performance_by_test = []
    for test in talenthunt_tests:
        test_attempts = level_progressions.filter(level__talenthuntsubject__talentHunt=test)
        test_count = test_attempts.count()
        
        if test_count > 0:
            # Calculate average score
            total_correct = 0
            total_questions = 0
            
            for progress in test_attempts:
                details = progress.details.filter(is_deleted=False).select_related('question')
                correct_answers = details.filter(is_correct=True).count()
                total_correct += correct_answers
                total_questions += details.count()
            
            avg_score = (total_correct / total_questions) * 100 if total_questions > 0 else 0
            
            performance_by_test.append({
                'test': test.title,
                'count': test_count,
                'avg_score': avg_score
            })
    
    # Get performance trend over time (last 10 attempts)
    recent_attempts = level_progressions[:10]
    trend_data = []
    
    for progress in recent_attempts:
        details = progress.details.filter(is_deleted=False).select_related('question')
        total_questions = details.count()
        correct_answers = details.filter(is_correct=True).count()
        
        if total_questions > 0:
            score_percentage = (correct_answers / total_questions) * 100
        else:
            score_percentage = 0
            
        trend_data.append({
            'date': progress.created,
            'test': progress.level.talenthuntsubject.talentHunt.title if hasattr(progress.level, 'talenthuntsubject') and progress.level.talenthuntsubject else 'Unknown',
            'subject': progress.level.title,
            'score': score_percentage,
        })
    
    # Get detailed TalentHunt data
    detailed_data = []
    
    for progress in level_progressions:
        details = progress.details.filter(is_deleted=False).select_related('question')
        
        # Calculate statistics
        total_questions = details.count()
        correct_answers = details.filter(is_correct=True).count()
        wrong_answers = details.filter(is_correct=False, answered=True).count()
        unanswered = details.filter(answered=False).count()
        
        if total_questions > 0:
            percentage = (correct_answers / total_questions) * 100
            accuracy = (correct_answers / (correct_answers + wrong_answers)) * 100 if (correct_answers + wrong_answers) > 0 else 0
        else:
            percentage = 0
            accuracy = 0

        detailed_data.append({
            'test': progress.level.talenthuntsubject.talentHunt.title if hasattr(progress.level, 'talenthuntsubject') and progress.level.talenthuntsubject else 'Unknown',
            'subject': progress.level.title,
            'date': progress.created,
            'percentage': percentage,
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'wrong_answers': wrong_answers,
            'unanswered': unanswered,
            'accuracy': accuracy,
            'progress_id': progress.id
        })
    
    context = {
        'title': f"{customer.name}'s TalentHunt Report",
        'customer': customer,
        'talenthunt_tests': talenthunt_tests,
        'selected_talenthunt': talenthunt_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_attempts': total_attempts,
        'total_talenthunts': total_attempts,  # For template compatibility
        'avg_score_percentage': avg_score_percentage,
        'performance_by_test': performance_by_test,
        'trend_data': trend_data,
        'detailed_talenthunt_data': detailed_data
    }
    
    return render(request, "dashboard/student/student-talenthunt-report.html", context)
