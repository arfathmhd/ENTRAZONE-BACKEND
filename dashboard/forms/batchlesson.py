
from django import forms
from dashboard.views.imports import *
class BatchLessonForm(forms.ModelForm):
    lesson = forms.ModelChoiceField(queryset=Lesson.objects.filter(is_deleted=False).order_by('order'), required=True)

    class Meta:
        model = BatchLesson
        fields = ['lesson', 'visible_in_days'] 

class BatchFolderForm(forms.ModelForm):
    folder = forms.ModelChoiceField(queryset=Folder.objects.filter(is_deleted=False).order_by('order'), required=True)

    class Meta:
        model = BatchLesson
        fields = ['folder', 'visible_in_days'] 