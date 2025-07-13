from django import forms
from dashboard.models import Chapter,Lesson , Schedule ,Exam
from django.core.exceptions import ValidationError

class ScheduleForm(forms.ModelForm):
    lesson = forms.ModelChoiceField(
        queryset=Lesson.objects.filter(is_deleted=False).order_by('order'),
        widget=forms.Select(attrs={'class': 'form-control', }),
        empty_label="Select a lesson",required=False  
    )
    exam = forms.ModelChoiceField(
        queryset=Exam.objects.filter(is_deleted=False),
        widget=forms.Select(attrs={'class': 'form-control', }),
        empty_label="Select an exam",required=False  
    )

    class Meta:
        model = Schedule
        fields = ['title', 'lesson', 'exam', 'date']

        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter title' , 'required': 'True'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'placeholder': 'Enter date'}),
        }

    def clean(self):
        cleaned_data = super().clean()

        lesson = cleaned_data.get("lesson")
        exam = cleaned_data.get("exam")

        if not lesson and not exam:
            raise forms.ValidationError("Please select either a lesson or an exam.")  

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance