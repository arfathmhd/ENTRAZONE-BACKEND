from dashboard.views.imports import *


@login_required(login_url='dashboard-login')
def manager(request):
    if request.user.user_type == 1 or  request.user.user_type == 2:
        sort_option = request.GET.get('sort')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        try:
            if start_date and start_date.lower() != 'null':
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date() + timedelta(days=1)  
            else:
                start_date = None

            if end_date and end_date.lower() != 'null':
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date() + timedelta(days=1)  
            else:
                end_date = None
        except ValueError:
            start_date = None
            end_date = None
        print(start_date)
        print(end_date,"{{{{{[]}}}}}")
        filtered_exams = Exam.objects.filter(is_deleted=False)
        
        if start_date and end_date:
            filtered_exams = filtered_exams.filter(created__range=[start_date, end_date])

        if sort_option == 'name_ascending':
            exams = filtered_exams.order_by('title')  
        elif sort_option == 'name_descending':
            exams = filtered_exams.order_by('-title')  
        else:
            exams = filtered_exams.order_by('-created') 
        
        paginator = Paginator(exams, 25)
        page_number = request.GET.get('page')
        exams_paginated = paginator.get_page(page_number)

        context = {
            "exams": exams_paginated,
            "current_sort": sort_option,
            "start_date": start_date,
            "end_date": end_date,
        }

        return render(request, "dashboard/exam/exam.html", context)
    else:
        return redirect('/')
    
@login_required(login_url='dashboard-login')
def list(request):
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 10))
    search_value = request.GET.get("search[value]", "")
    order_column = int(request.GET.get("order[0][column]", 0))
    order_dir = request.GET.get("order[0][dir]", "asc")
    
    order_columns = {
        0: 'id',
        1: 'exam__title',
        2: 'subject__subject_name',
        3: 'duration',
        4: 'created'
    }
    
    order_field = order_columns.get(order_column, 'id')
    if order_dir == 'desc':
        order_field = '-' + order_field
    
    exam = Exam.objects.filter(is_deleted=False) 
    
    if search_value:
        exam = exam.filter(
            Q(created__icontains=search_value)|
            Q(subject__subject_name__icontains=search_value) |
            Q(duration__icontains=search_value)|
            Q(title__icontains=search_value)
        )
    
    total_records = exam.count()
   
    exam = exam.order_by(order_field)
    paginator = Paginator(exam, length)
    page_number = (start // length) + 1
    page_obj = paginator.get_page(page_number)

    data = []
    for exam in page_obj:
        data.append({
            "id": exam.id,
            "title": exam.title if exam.title else "N/A",
            "subject": exam.subject.subject_name if exam.subject else "N/A",
            "duration": exam.duration if exam.duration else "N/A",
            "created": timezone.localtime(exam.created).strftime('%Y-%m-%d %H:%M:%S')
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
    if request.user.user_type == 1 or request.user.user_type == 2:
        if request.method == 'POST':
            form = ExamForm(request.POST)  
            if form.is_valid():
                # The form's clean() and save() methods will handle the date logic based on exam_type
                exam = form.save()
                messages.success(request, "Exam added successfully.")
                return redirect('dashboard-exam-manager')  
            else:
                return render(request, 'dashboard/exam/add-exam.html', {'form': form})

        else:
            form = ExamForm()  

        return render(request, 'dashboard/exam/add-exam.html', {'form': form})
    else:
        return redirect('/')


@login_required(login_url='dashboard-login')
def update(request, pk):
    if request.user.user_type == 1 or  request.user.user_type == 2:
        exam = get_object_or_404(Exam, pk=pk)

        if request.method == 'POST':
            form = ExamForm(request.POST, instance=exam)
            if form.is_valid():
                form.save()
                messages.success(request, "Exam updated successfully.")
                return redirect('dashboard-exam-manager') 
            else:
                messages.error(request, "Failed to update exam. Please check the form for errors.")
        else:
            form = ExamForm(instance=exam)
        

        return render(request, 'dashboard/exam/update-exam.html', {'form': form})
    else:
        return redirect('/')


@login_required(login_url='dashboard-login')
def delete(request, pk):
    exam = get_object_or_404(Exam, pk=pk)

    if request.method == 'POST':
        exam.is_deleted = True
        exam.save()
        messages.success(request, "Exam deleted successfully.")
        return redirect('dashboard-exam-manager')  
    messages.error(request, "Failed to delete exam.")
    return render(request, 'dashboard/exam/manager', {'exam': exam})











@login_required(login_url='dashboard-login')
def exam_question_manager(request, exam_id):
    if request.user.user_type == 1 or  request.user.user_type == 2:
    
        sort_option = request.GET.get('sort')
        
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)

        if start_date and start_date.lower() != 'null':
            start_date = datetime.strptime(start_date, "%d-%m-%Y").date()
        else:
            start_date = None

        if end_date and end_date.lower() != 'null':
            end_date = datetime.strptime(end_date,"%d-%m-%Y").date() + timedelta(days=1)
        else:
            end_date = None

        question_filter = Question.objects.filter(is_deleted=False, exam=exam_id)

        if start_date and end_date:
            question_filter = question_filter.filter(created__range=[start_date, end_date])

        if sort_option == 'name_ascending':
            questions = question_filter.order_by('created')
        elif sort_option == 'name_descending':
            questions = question_filter.order_by('-created')
        else:
            questions = question_filter.order_by('-id')  

        # Pagination
        paginator = Paginator(questions, 25)  # Show 25 questions per page
        page_number = request.GET.get('page')
        questions_page = paginator.get_page(page_number)

        context = {
            'questions': questions_page,
            'current_sort': sort_option,
            'start_date': start_date,
            'end_date': end_date,
            'exam_id': exam_id,
            'paginator': paginator,  # Pass paginator to the template if needed
        }

        return render(request, 'dashboard/exam/exam-question.html', context)
    else:
        return redirect('/')




@login_required(login_url='dashboard-login')
def exam_question_add(request, exam_id):
    if request.user.user_type == 1 or  request.user.user_type == 2:
        exam=Exam.objects.get(id=exam_id,is_deleted=False)
        
        if request.method == 'POST':
            form = QuestionForm(request.POST)  
            if form.is_valid():
                question_type = form.cleaned_data.get('question_type')
                question_description = request.POST.get('question_description')
                if not question_description:
                    messages.error(request, 'Question description is required.')
                    return redirect('exam-question-add', exam_id=exam_id)
                hint = request.POST.get('hint')
                negative_mark = form.cleaned_data.get('negative_mark')
                raw_options = request.POST.getlist('options[]')
                options = [{"id": index + 1, "text": opt.strip()} for index, opt in enumerate(raw_options) if opt.strip()]
                raw_answers = request.POST.getlist('answers[]')
                right_answers = [{"id": opt["id"], "text": opt["text"]} for opt in options if opt["text"] in raw_answers]

                question = Question(
                    question_type=question_type,
                    question_description=question_description,
                    hint=hint,
                    negative_mark=negative_mark,
                    options=options,
                    right_answers=right_answers,
                    exam_id=exam.id
                )
                question.save()
                messages.success(request, "Question added successfully.")
                return redirect('dashboard-exam-question-manager',exam_id=exam_id)  
            else:
                messages.error(request, "Failed to add question. Please add description")
                raw_options = request.POST.getlist('options[]')
                raw_answers = request.POST.getlist('answers[]')
                return render(request, 'dashboard/exam/add-exam-question.html', {
                    'form': form,
                    'exam': exam_id,
                    'options': raw_options,
                    'answers': raw_answers
                })
        else:
            form = QuestionForm()
            return render(request, 'dashboard/exam/add-exam-question.html', {
                'form': form,
                'exam': exam_id,
                'options': [],
                'answers': []
            })
    else:
        return redirect('/')



@login_required(login_url='dashboard-login')
def exam_question_update(request, exam_id, question_id):
    if request.user.user_type == 1 or  request.user.user_type == 2:
        question = get_object_or_404(Question, pk=question_id)
        exam = get_object_or_404(Exam, id=exam_id)

        if request.method == 'POST':
            form = QuestionForm(request.POST, instance=question)
            if form.is_valid():
                question_type = form.cleaned_data.get('question_type')
                question_description = form.cleaned_data.get('question_description')
                hint = form.cleaned_data.get('hint')
                negative_mark = form.cleaned_data.get('negative_mark')

                raw_options = request.POST.getlist('options[]')
                options = [{"id": index + 1, "text": opt.strip()} for index, opt in enumerate(raw_options) if opt.strip()]

                raw_answers = request.POST.getlist('answers[]')
                answers = [{"id": opt["id"], "text": opt["text"]} for opt in options if opt["text"] in raw_answers]

                question.question_type = question_type
                question.question_description = question_description
                question.hint = hint
                question.negative_mark = negative_mark
                question.exam = exam
                question.options = options
                question.right_answers = answers
                question.save()

                if question.master_question:
                    try:
                        master_question = Question.objects.get(id=question.master_question, is_deleted=False)
                        master_question.question_type = question_type
                        master_question.question_description = question_description
                        master_question.hint = hint
                        master_question.negative_mark = negative_mark
                        master_question.options = options
                        master_question.right_answers = answers
                        master_question.save()
                    except Question.DoesNotExist:
                        messages.error(request, 'The master question does not exist or has been deleted.')
                        return redirect('dashboard-exam-question-manager', exam_id=exam_id)

                related_questions = Question.objects.filter(master_question=question.id, is_deleted=False)
                for related_question in related_questions:
                    related_question.question_type = question_type
                    related_question.question_description = question_description
                    related_question.hint = hint
                    related_question.negative_mark = negative_mark
                    related_question.options = options
                    related_question.right_answers = answers
                    related_question.save()

                messages.success(request, 'Question updated successfully.')
                return redirect('dashboard-exam-question-manager', exam_id=exam_id)
        else:
            form = QuestionForm(instance=question)
            options = [opt["text"] for opt in question.options] if question.options else []
            answers = [ans["text"] for ans in question.right_answers] if question.right_answers else []

        return render(request, 'dashboard/exam/update-exam-question.html', {
            'form': form,
            'question': question,
            'options': options,  
            'answers': answers   
        })
    else:
        return redirect('/')






@login_required(login_url='dashboard-login')
def exam_question_delete(request,question_id):
    if request.method == 'POST':
        question = get_object_or_404(Question, pk=question_id)
        question.is_deleted = True
        question.save()
        messages.success(request, 'Question deleted successfully.')
        return redirect('dashboard-exam-question-manager',exam_id=question.exam.id)  
    messages.error(request, 'Failed to delete question.')
    return redirect('dashboard-exam-question-manager',exam_id=question.exam.id)  
   


@login_required(login_url='dashboard-login')
def paste(request):
    if request.method == 'POST':
        ids_json = request.POST.get('ids')
        exam_id = request.POST.get('exam_id')

        try:
            exam = Exam.objects.get(id=exam_id, is_deleted=False)
        except Exam.DoesNotExist:
            return JsonResponse({'error': 'Exam does not exist.'}, status=404)

        try:
            ids = json.loads(ids_json) if ids_json else []
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid IDs format. Must be valid JSON.'}, status=400)

        if not all(str(i).isdigit() for i in ids):
            return JsonResponse({'error': 'All IDs must be numeric.'}, status=400)

        success_count = 0
        error_messages = []
        already_exists = []

        for i in ids:
            try:
                master_question = Question.objects.get(id=i)

                if Question.objects.filter(exam=exam, master_question=i, is_deleted=False).exists() or \
                   Question.objects.filter(exam=exam, id=master_question.master_question, is_deleted=False).exists() or \
                   Question.objects.filter(exam=exam, id=i, is_deleted=False).exists():
                    already_exists.append(i)
                    continue

                question = Question.objects.create(
                    question_type=master_question.question_type,
                    question_description=master_question.question_description,
                    hint=master_question.hint,
                    options=master_question.options,
                    right_answers=master_question.right_answers,
                    exam=exam,
                )
                if master_question.master_question:
                    question.master_question = master_question.master_question
                question.master_question = i
                question.save()
                success_count += 1  

            except ObjectDoesNotExist:
                error_messages.append(f"Master question with ID {i} does not exist.")
            except Exception as e:
                error_messages.append(f"Error creating question with ID {i}: {str(e)}")

        response_data = {}
        if success_count > 0:
            response_data['message'] = f'Successfully added {success_count} question(s) to the exam.'
        
        if already_exists:
            response_data['existing'] = f"The following questions already existed in the exam: {', '.join(map(str, already_exists))}"

        if error_messages:
            response_data['errors'] = error_messages

        if not response_data:
            return JsonResponse({'error': 'No questions were processed.'}, status=400)

        return JsonResponse(response_data, status=200)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)


def upload_question_file(request, exam_id):
    if request.method == "POST":
        uploaded_file = request.FILES.get('file', None)

        if uploaded_file is None:
            return render(request, 'upload_questions.html', {"error": "No file uploaded."})

        file_extension = uploaded_file.name.split('.')[-1].lower()

        if file_extension == 'docx':
            try:
                handle_docx_file(uploaded_file, exam_id)
            except Exception as e:
                return render(request, 'upload_questions.html', {"error": f"Error processing file: {str(e)}"})
        else:
            return render(request, 'upload_questions.html', {"error": "Unsupported file format!"})

        return redirect('dashboard-exam-question-manager', exam_id=exam_id)

    return redirect('dashboard-exam-question-manager', exam_id=exam_id)


def handle_docx_file(file, exam_id, question_type=3): 
    document = Document(file)

    for table_index, table in enumerate(document.tables):
        num_rows = len(table.rows)
        num_cols = len(table.columns)

        question_desc = table.cell(0, 1).text.strip()
        if not question_desc:
            continue  

        options = []
        correct_answer = None

        for option_index, j in enumerate(range(2, 6)):  
            option_text = table.cell(j, 1).text.strip() 
            option_status = table.cell(j, 2).text.strip().lower()  

            if option_text:
                option_id = option_index + 1
                option_data = {"id": option_id, "text": option_text}
                options.append(option_data)

                if option_status == 'correct':
                    correct_answer = option_data 

        options = [opt for opt in options if opt]

        try:
            marks = float(table.cell(num_rows - 1, 1).text.strip())
        except ValueError:
            marks = 0 

        Question.objects.create(
            question_description=question_desc,
            options=options,
            right_answers=[correct_answer] if correct_answer else [], 
            mark=marks,
            question_type=question_type, 
            exam_id=exam_id
        )

        # print(f"Saved question: {question_desc} with options: {options} and correct answer: {correct_answer}")


