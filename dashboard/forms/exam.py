from django import forms
from dashboard.models import Exam, Subject,Question
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from datetime import timedelta
class ExamForm(forms.ModelForm):

    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(is_deleted=False).order_by('order'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    duration = forms.TimeField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter duration in HH:MM:SS'}),
        initial=timedelta(minutes=60),
        help_text="Format: HH:MM:SS"
    )
    
    number_of_attempt = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter number of attempts allowed', 'min': '1'}),
        initial=1,
        help_text="Number of times a student can attempt this exam"
    )
    
    is_shuffle = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Shuffle questions for each attempt"
    )
    exam_type = forms.ChoiceField(
        choices=Exam.EXAM_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_exam_type'}),
        initial=Exam.EXAM_TYPE_CHOICES[0][0],
        help_text="Select exam type"
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'id_start_date'}),
        required=False,
        help_text="Select start date"
    )
    
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'id_end_date'}),
        required=False,
        help_text="Select end date"
    )
    
    class Meta:
        model = Exam
        fields = ['title', 'subject', 'duration', 'number_of_attempt', 'is_shuffle', 'exam_type', 'start_date', 'end_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter exam title'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        exam_type = cleaned_data.get('exam_type')
        
        # If exam type is daily, set start_date and end_date to None
        if exam_type == 'daily':
            cleaned_data['start_date'] = None
            cleaned_data['end_date'] = None
        else:
            # For other exam types, dates might be required
            start_date = cleaned_data.get('start_date')
            end_date = cleaned_data.get('end_date')
            
            # Validate dates if provided
            if start_date and end_date and start_date > end_date:
                self.add_error('end_date', 'End date must be after start date')
        
        return cleaned_data

    def save(self, commit=True):    
        instance = super().save(commit=False)
        
        # Set dates to None if exam type is daily
        if instance.exam_type == 'daily':
            instance.start_date = None
            instance.end_date = None
            
        if commit:
            instance.save()
        return instance




class QuestionForm(forms.ModelForm):
    # question_description = forms.CharField(widget=CKEditorUploadingWidget())
    question_description = forms.CharField(widget=CKEditorUploadingWidget())
    hint = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Question
        fields = [
            'question_type',
            'question_description',
            'hint',
            'options',
            'right_answers',
        ]
        widgets = {
            'question_type': forms.Select(attrs={'class': 'form-control'}),
            'question_description': forms.Textarea(attrs={'class': 'form-control', 'id': 'editor1'}),
            'hint': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter hint'}),
            'options': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter options separated by commas'}),
            'right_answers': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter right answers separated by commas'}),
        }
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['question_description'].initial = self.fields['question_description'].initial or ''
            self.fields['hint'].initial = self.fields['hint'].initial or ''