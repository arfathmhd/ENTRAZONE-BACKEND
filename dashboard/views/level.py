
from dashboard.views.imports import *


@login_required(login_url='dashboard-login')
def manager(request, pk):
    if request.user.user_type == 1 or  request.user.user_type == 2:
    
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        sort_option = request.GET.get('sort', 'name_ascending')  

        if start_date and start_date.lower() != 'null':
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                start_date = None

        if end_date and end_date.lower() != 'null':
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date() + timedelta(days=1)  
            except ValueError:
                end_date = None
        talentsubject  = TalentHuntSubject.objects.get(id=pk, is_deleted=False)

        level_filter = Level.objects.filter(is_deleted=False, talenthuntsubject=pk)

        if start_date and end_date:
            level_filter = level_filter.filter(created__range=[start_date, end_date])

        if sort_option == 'name_ascending':
            level_filter = level_filter.order_by('created')
        elif sort_option == 'name_descending':
            level_filter = level_filter.order_by('-created')
        # elif sort_option == 'date_ascending':
        #     level_filter = level_filter.order_by('created')
        # elif sort_option == 'date_descending':
        #     level_filter = level_filter.order_by('-created')

        paginator = Paginator(level_filter, 25)
        page_number = request.GET.get('page')
        levels_paginated = paginator.get_page(page_number)

        context = {
            'pk': pk,  
            'levels': levels_paginated,
            'start_date': start_date,
            'end_date': end_date,
            'current_sort': sort_option,
            'talentsubject':talentsubject
        }

        return render(request, 'dashboard/level/levels.html', context)
    else:
        return redirect('/')


@login_required(login_url='dashboard-login')
def list(request,pk):

    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 10))  
    search_value = request.GET.get("search[value]", "")
    order_column = int(request.GET.get("order[0][column]", 0))
    order_dir = request.GET.get("order[0][dir]", "desc")
    

    order_columns = {
        0: 'id',
        3: 'course',

    }
    
    order_field = order_columns.get(order_column, 'id')
    if order_dir == 'desc':
        order_field = '-' + order_field
    
    level = Level.objects.filter(is_deleted=False,talenthuntsubject=pk)
    
    if search_value:
        level = level.filter(
            Q(title__icontains=search_value)|
            Q(number__icontains=search_value)|
            Q(created__icontains=search_value)
        )
    
    total_records = level.count()

    level = level.order_by(order_field)
    paginator = Paginator(level, length)
    page_number = (start // length) + 1
    page_obj = paginator.get_page(page_number)

    data = []
    for level in page_obj:
        data.append({
            "id": level.id,
            "title":level.title if  level.title else "N/A",
            "number": level.number if level.number else "N/A",
             "created": timezone.localtime(level.created).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    response = {
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data,
    }

    return JsonResponse(response)


@login_required(login_url='dashboard-login')
def add(request,pk):
    if request.user.user_type == 1 or  request.user.user_type == 2:
    
        if request.method == "POST":
            talenthuntsubject= TalentHuntSubject.objects.get(id=pk)
            form = LevelForm(request.POST, request.FILES)
            if form.is_valid():
                level = form.save(commit=False)
                level.talenthuntsubject = talenthuntsubject

                level.save()

                
                messages.success(request, "Level  added successfully!")
                return redirect('dashboard-level-manager',pk)
            else:
                context = {
                    "title": "Add Subject",
                    "form": form,
                    "pk":pk,
                }
                return render(request, "dashboard/level/add-level.html", context)
        else:
                form = LevelForm()  
                context = {
                    "title": "Add level ",
                    "form": form,
                    "pk":pk,
                }
                return render(request, "dashboard/level/add-level.html", context)
        
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def update(request, pk, level_id):
    if request.user.user_type == 1 or  request.user.user_type == 2:
    
        talenthuntsubject = get_object_or_404(TalentHuntSubject, id=pk)
        level = get_object_or_404(Level, id=level_id, talenthuntsubject=talenthuntsubject)
        
        if request.method == "POST":
            form = LevelForm(request.POST, request.FILES, instance=level)
            if form.is_valid():
                form.save()
                messages.success(request, "Level updated successfully!")
                return redirect('dashboard-level-manager', pk)
            else:
                context = {
                    "title": "Update Level",
                    "form": form,
                    "pk": pk,
                    "level_id": level_id
                }
                return render(request, "dashboard/level/update-level.html", context)
        
        else:
            form = LevelForm(instance=level)
            context = {
                "title": "Update Level",
                "form": form,
                "pk": pk,
                "level_id": level_id
            }
            return render(request, "dashboard/level/update-level.html", context)
        
    else:
        return redirect('/')
    


@login_required(login_url='dashboard-login')
def delete(request, pk):
    level = get_object_or_404(Level, id=pk)

    if request.method == "POST":
        level.is_deleted = True
        level.save()
        messages.success(request, "Level deleted successfully!")
        return redirect('dashboard-level-manager', pk)

    context = {
        "title": "Delete Level",
        "pk": pk,
    }
    return redirect('dashboard-level-question-manager',context)  



@login_required(login_url='dashboard-login')
def level_question_manager(request, pk):
    if request.user.user_type == 1 or  request.user.user_type == 2:
    
        search_query = request.GET.get('search', '')  
        start_date = request.GET.get('start_date', '')  
        end_date = request.GET.get('end_date', '') 
        sort_option = request.GET.get('sort', 'created')  
        level= Level.objects.get(id=pk, is_deleted=False)
        questions = Question.objects.filter(is_deleted=False, level=pk)

        if search_query:
            questions = questions.filter(text__icontains=search_query)

        if start_date and start_date.lower() != 'null':
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                start_date = None

        if end_date and end_date.lower() != 'null':
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date() + timedelta(days=1)  
            except ValueError:
                end_date = None
        print(sort_option,"{{{{}}}}")
        print(start_date)
        print(end_date)
        if sort_option == 'name_ascending':
            questions = questions.order_by('id')
        elif sort_option == 'name_descending':
            questions = questions.order_by('-id')
        else:
            questions = questions.order_by('-id')  

        paginator = Paginator(questions, 25) 
        page_number = request.GET.get('page')
        paginated_questions = paginator.get_page(page_number)

        context = {
            'pk': pk,
            'questions': paginated_questions,
            'search_query': search_query,
            'start_date': start_date,
            'end_date': end_date,
            'current_sort': sort_option,
            'level':level,
            'Level':level.id,
        }

        return render(request, 'dashboard/level/level-question.html', context)
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def level_question_list(request,pk):
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 10))
    search_value = request.GET.get("search[value]", "")
    order_column = int(request.GET.get("order[0][column]", 0))
    order_dir = request.GET.get("order[0][dir]", "desc")
    
    order_columns = {
        0: 'id',
        1: 'question_description',
        2: 'hint',
        3: 'exam__title',
        4: 'created'
    }
    
    order_field = order_columns.get(order_column, 'id')
    if order_dir == 'desc':
        order_field = '-' + order_field
    
    questions = Question.objects.filter(is_deleted=False,level=pk)
    
    if search_value:
        questions = questions.filter(
            Q(question_description__icontains=search_value) |
            Q(hint__icontains=search_value) 
        )
    
    total_records = questions.count()

    questions = questions.order_by(order_field)
    paginator = Paginator(questions, length)
    page_number = (start // length) + 1
    page_obj = paginator.get_page(page_number)

    data = []
    for question in page_obj:
        options_str = ', '.join(filter(None, question.options)) if question.options else "N/A"
        right_answers_str = ', '.join(filter(None, question.right_answers)) if question.right_answers else "N/A"
        
        if options_str.strip() == "":
            options_str = "N/A"
        if right_answers_str.strip() == "":
            right_answers_str = "N/A"
        
        data.append({
            "id": question.id,
            "question_description": question.question_description if question.question_description else "N/A",
            "hint": question.hint if question.hint else "N/A",
            "options": options_str,
            "right_answers": right_answers_str,
             "created": timezone.localtime(question.created).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    response = {
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data,
    }

    return JsonResponse(response)



@login_required(login_url='dashboard-login')
def level_question_add(request,pk):
    if request.user.user_type == 1 or  request.user.user_type == 2:
    
        if request.method == 'POST':
            form = QuestionForm(request.POST)  
            if form.is_valid():
                level=Level.objects.get(id=pk,is_deleted=False)
                question_type = form.cleaned_data.get('question_type')
                question_description = form.cleaned_data.get('question_description')
                hint = form.cleaned_data.get('hint')
                raw_options = request.POST.getlist('options[]')
                options = [{"id": index + 1, "text": opt.strip()} for index, opt in enumerate(raw_options) if opt.strip()]

                raw_answers = request.POST.getlist('answers[]')
                answers = [{"id": opt["id"], "text": opt["text"]} for opt in options if opt["text"] in raw_answers]

                question = Question(
                    question_type=question_type,
                    question_description=question_description,
                    hint=hint,
                    options=options,
                    right_answers=answers,
                    level=level

                )

                question.save()
                messages.success(request, "Question added successfully.")
                return redirect('dashboard-level-question-manager',pk)  
            
            else:
                return render(request, 'dashboard/level/add-level-question.html', {'form': form ,'pk':pk, 'question': question})

        else:
            form = QuestionForm()  

        return render(request, 'dashboard/level/add-level-question.html', {'form': form ,'pk':pk , 'question': None})
    else:
        return redirect('/')
    

@login_required(login_url='dashboard-login')
def level_question_update(request, pk):
    if request.user.user_type == 1 or  request.user.user_type == 2:
    
        question = get_object_or_404(Question, id=pk)

        if request.method == 'POST':
            form = QuestionForm(request.POST, instance=question)
            if form.is_valid():
                question_type = form.cleaned_data.get('question_type')
                question_description = form.cleaned_data.get('question_description')
                hint = form.cleaned_data.get('hint')
                
                # Extract options and answers from POST request
                raw_options = request.POST.getlist('options[]')
                options = [{"id": index + 1, "text": opt.strip()} for index, opt in enumerate(raw_options) if opt.strip()]

                raw_answers = request.POST.getlist('answers[]')
                answers = [{"id": opt["id"], "text": opt["text"]} for opt in options if opt["text"] in raw_answers]

                # Update question details
                question.question_type = question_type
                question.question_description = question_description
                question.hint = hint
                question.options = options  # Save as list
                question.right_answers = answers  # Save as list
                question.save()

                # Update master question, if exists
                if question.master_question:
                    master_question = Question.objects.get(id=question.master_question, is_deleted=False)
                    master_question.question_type = question_type
                    master_question.question_description = question_description
                    master_question.hint = hint
                    master_question.options = options
                    master_question.right_answers = answers
                    master_question.save()

                # Update related questions
                related_questions = Question.objects.filter(master_question=question.id, is_deleted=False)
                for related_question in related_questions:
                    related_question.question_type = question_type
                    related_question.question_description = question_description
                    related_question.hint = hint
                    related_question.options = options
                    related_question.right_answers = answers
                    related_question.save()

                messages.success(request, 'Question updated successfully.')
                return redirect('dashboard-level-question-manager', pk=question.level.id)

        else:
            form = QuestionForm(instance=question)
            
            # Preprocess options for display in form (extract only "text")
            options = [opt["text"] for opt in question.options] if question.options else []
            answers = [ans["text"] for ans in question.right_answers] if question.right_answers else []

        return render(request, 'dashboard/level/update-level-question.html', {
            'form': form,
            'question': question,
            'options': options,  # Pass only the text of the options
            'answers': answers,  # Pass only the text of the answers
        })
    else:
        return redirect('/')

@login_required(login_url='dashboard-login')
def level_question_delete(request,pk):
    question = get_object_or_404(Question, id=pk)

    if request.method == "POST":
        question.is_deleted = True
        question.save()
        messages.success(request, "Question deleted successfully!")
        return redirect('dashboard-level-question-manager',pk=question.level.id)  
   
    return redirect('dashboard-level-question-manager',pk=question.level.id)  



@login_required(login_url='dashboard-login')
@csrf_exempt  
def paste(request):
    if request.method == 'POST':
        ids_json = request.POST.get('ids')
        level_id = request.POST.get('level_id')
        
        print(ids_json, level_id)

        try:
            level = Level.objects.get(id=level_id, is_deleted=False)
        except Level.DoesNotExist:
            return JsonResponse({'error': 'Level does not exist.'}, status=404)

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
                
                if Question.objects.filter(level=level, master_question=i, is_deleted=False).exists() or \
                   Question.objects.filter(level=level, id=master_question.master_question, is_deleted=False).exists() or \
                   Question.objects.filter(level=level, id=i, is_deleted=False).exists():
                    already_exists.append(i)
                    continue

                question = Question.objects.create(
                    question_type=master_question.question_type,
                    question_description=master_question.question_description,
                    hint=master_question.hint,
                    options=master_question.options,
                    right_answers=master_question.right_answers,
                    level=level,
                )
                
                question.master_question = master_question.master_question or i
                question.save()

                success_count += 1
            except ObjectDoesNotExist:
                error_messages.append(f"Master question with ID {i} does not exist.")
            except Exception as e:
                error_messages.append(f"Error creating question with ID {i}: {str(e)}")

        if success_count == 0 and not already_exists:
            return JsonResponse({'message': 'No questions were created.', 'errors': error_messages}, status=400)

        response_data = {
            'message': f'Successfully added {success_count} question(s) to the level.',
            'errors': error_messages,
        }
        if already_exists:
            response_data['existing'] = f"The following questions already existed in the level: {', '.join(map(str, already_exists))}"

        return JsonResponse(response_data, status=200)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)







def upload_question_file(request, level_id):
    if request.method == "POST":
        uploaded_file = request.FILES.get('file', None)

        if uploaded_file is None:
            return render(request, 'upload_questions.html', {"error": "No file uploaded."})

        file_extension = uploaded_file.name.split('.')[-1].lower()

        if file_extension == 'docx':
            try:
                handle_docx_file(uploaded_file, level_id)
            except Exception as e:
                return render(request, 'upload_questions.html', {"error": f"Error processing file: {str(e)}"})
        else:
            return render(request, 'upload_questions.html', {"error": "Unsupported file format!"})

        return redirect('dashboard-level-question-manager', pk=level_id)

    return redirect('dashboard-level-question-manager', pk=level_id)
from uuid import uuid4

def handle_docx_file(file, level_id, question_type=3): 
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
            level_id=level_id
        )

        print(f"Saved question: {question_desc} with options: {options} and correct answer: {correct_answer}")
