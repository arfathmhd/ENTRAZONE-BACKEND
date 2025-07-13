
from dashboard.views.imports import *


@login_required(login_url='dashboard-login')
def manager(request):
    return render(request, 'dashboard/question/manager.html')




@login_required(login_url='dashboard-login')
def list(request):
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
    
    questions = Question.objects.filter(is_deleted=False)
    
    if search_value:
        questions = questions.filter(
            Q(question_description__icontains=search_value) |
            Q(hint__icontains=search_value) |
            Q(exam__name__icontains=search_value)
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
            "exam": question.exam.title if question.exam else "N/A",
            "options": options_str,
            "right_answers": right_answers_str,
            "negative_mark": question.negative_mark,
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
def add(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST)  
        if form.is_valid():
            question_type = form.cleaned_data.get('question_type')
            question_description = form.cleaned_data.get('question_description')
            hint = form.cleaned_data.get('hint')
            exam_id = form.cleaned_data.get('exam')
            talenthunt = form.cleaned_data.get('talenthunt')
            chapter = form.cleaned_data.get('chapter')
            raw_options = request.POST.getlist('options[]')
            options = [{"id": index + 1, "text": opt.strip()} for index, opt in enumerate(raw_options) if opt.strip()]

            #   print(options,"options")
            raw_answers = request.POST.getlist('answers[]')
            answers = [{"id": opt["id"], "text": opt["text"]} for opt in options if opt["text"] in raw_answers]
 


           
            if exam_id:
                question = Question(
                    question_type=question_type,
                    question_description=question_description,
                    hint=hint,
                    options=options,
                    right_answers=answers,
                    exam=exam_id

                )
            elif talenthunt:
                 question = Question(
                    question_type=question_type,
                    question_description=question_description,
                    hint=hint,
                    options=options,
                    right_answers=answers,
                    talenthunt=talenthunt

                )
            elif chapter:
                question = Question(
                    question_type=question_type,
                    question_description=question_description,
                    hint=hint,
                    options=options,
                    right_answers=answers,
                    chapter=chapter
                )

            question.save()
            messages.success(request, "Question added successfully.")
            return redirect('dashboard-question-manager')  
        else:
            return render(request, 'dashboard/question/add.html', {'form': form})

    else:
        form = QuestionForm()  

    return render(request, 'dashboard/question/add.html', {'form': form})



@login_required(login_url='dashboard-login')
def update(request, pk):
    question = get_object_or_404(Question, pk=pk)
    
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            question_type = form.cleaned_data.get('question_type')
            question_description = form.cleaned_data.get('question_description')
            hint = form.cleaned_data.get('hint')
            exam_id = form.cleaned_data.get('exam')
            talenthunt = form.cleaned_data.get('talenthunt')
            chapter = form.cleaned_data.get('chapter')
            options = request.POST.getlist('options[]')
            answers = request.POST.getlist('answers[]')

            question.question_type = question_type
            question.question_description = question_description
            question.hint = hint
            if exam_id:
                question.exam = exam_id
            elif talenthunt:
                question.talenthunt = talenthunt
            elif chapter:
                question.chapter = chapter
            question.options = options
            question.right_answers = answers
            question.save()
            messages.success(request, 'Question updated successfully.')
            return redirect('dashboard-question-manager')  
    else:
        form = QuestionForm(instance=question)
    
    return render(request, 'dashboard/exam/update-exam-question.html', {
        'form': form,
        'question': question,
        'options': question.options,
        'answers': question.right_answers
    })




@login_required(login_url='dashboard-login')
def delete(request, pk):
    if request.method == 'POST':
        question = get_object_or_404(Question, pk=pk)
        question.is_deleted = True
        question.save()
        messages.success(request, 'Question deleted successfully.')
        return redirect('dashboard-question-manager')
    messages.error(request, 'Failed to delete question.')
    return redirect('dashboard-question-manager')


@login_required(login_url='dashboard-login')
def question_reports(request):
    reports = Report.objects.filter(is_deleted=False).order_by('-created')
    context = {
        'reports': reports,
    }
    return render(request, 'dashboard/exam/question_reports.html', context)

@login_required(login_url='dashboard-login')
def question_report_detail(request, pk):
    report = get_object_or_404(Report, pk=pk, is_deleted=False)
    context = {
        'report': report
    }
    return render(request, 'dashboard/exam/question_report_detail.html', context)

@login_required(login_url='dashboard-login')
def question_report_resolve(request, pk):
    if request.method == 'POST':
        report = get_object_or_404(Report, pk=pk)
        report.is_deleted = True
        report.save()
        messages.success(request, 'Report has been marked as resolved.')
        return redirect('dashboard-question-reports')
    return redirect('dashboard-question-report-detail', pk=pk)