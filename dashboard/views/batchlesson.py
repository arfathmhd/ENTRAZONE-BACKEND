from dashboard.views.imports import *
from dashboard.forms.batchlesson import BatchLessonForm, BatchFolderForm

def batchlesson_delete(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 3 :
        batch_lesson = get_object_or_404(BatchLesson, pk=pk)
        batch_lesson.is_deleted = True
        batch_lesson.save()
        messages.success(request, "Batch lesson deleted successfully!")
        return redirect('dashboard-batch-schedule-manager', pk=batch_lesson.batch.id)
    return redirect('/')



@login_required(login_url='dashboard-login')
def batchlesson_update(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 3 :
        batch_lesson = get_object_or_404(BatchLesson, pk=pk)

        if request.method == 'POST':
            form = BatchLessonForm(request.POST, instance=batch_lesson)
            if form.is_valid():
                form.save()
                messages.success(request, "Batch lesson updated successfully!")
                return redirect('dashboard-batch-schedule-manager', pk=batch_lesson.batch.id)
        else:
            form = BatchLessonForm(instance=batch_lesson)

        context = {
            'form': form,
            'batch_lesson': batch_lesson,
        }
        return render(request, 'dashboard/batch/update-batch-lesson.html', context)
    return redirect('/')

@login_required(login_url='dashboard-login')
def batch_folder_update(request, pk):
    if request.user.user_type == 1 or request.user.user_type == 3 :
        batch_folder = get_object_or_404(BatchLesson, pk=pk)

        if request.method == 'POST':
            form = BatchFolderForm(request.POST, instance=batch_folder)
            if form.is_valid():
                form.save()
                messages.success(request, "Batch lesson updated successfully!")
                return redirect('dashboard-batch-schedule-manager', pk=batch_folder.batch.id)
        else:
            form = BatchFolderForm(instance=batch_folder)

        context = {
            'form': form,
            'batch_folder': batch_folder,
        }
        return render(request, 'dashboard/batch/update-batch-folder.html', context)
    return redirect('/')