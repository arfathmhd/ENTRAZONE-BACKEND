from django import forms
from dashboard.models import Question, Exam ,Chapter ,TalentHunt
from ckeditor_uploader.widgets import CKEditorUploadingWidget
class QuestionForm(forms.ModelForm):
    # question_description = forms.CharField(widget=CKEditorUploadingWidget())
    question_description = forms.CharField(widget=CKEditorUploadingWidget())
    hint = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    exam= forms.ModelChoiceField(
        queryset=Exam.objects.filter(is_deleted=False),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select a Exam"
        ,required=False
    )
    chapter= forms.ModelChoiceField(
        queryset=Chapter.objects.filter(is_deleted=False).order_by('order'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select a Exam"
        ,required=False
    )
    exam= forms.ModelChoiceField(
        queryset=Exam.objects.filter(is_deleted=False),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select a Chapter",
        required=False
    )
    talenthunt= forms.ModelChoiceField(
        queryset=TalentHunt.objects.filter(is_deleted=False),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select a Talenthunt",
        required=False
    )
    negative_mark = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter negative mark (optional)'})
    )
    class Meta:
        model = Question
        fields = [
            'question_type',
            'question_description',
            'hint',
            'options',
            'right_answers',
            'exam',
            'chapter',
            'talenthunt',
            'negative_mark'
        ]
        widgets = {
            'question_type': forms.Select(attrs={'class': 'form-control'}),
            'question_description': forms.Textarea(attrs={'class': 'form-control', 'id': 'editor1'}),
            'hint': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter hint'}),
            'options': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter options separated by commas'}),
            'right_answers': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter right answers separated by commas'}),
            'exam': forms.Select(attrs={'class': 'form-control'}),
            'chapter': forms.Select(attrs={'class': 'form-control'}),
            'talenthunt': forms.Select(attrs={'class': 'form-control'}),
            'negative_mark': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter negative mark (optional)'})
        }
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['question_description'].initial = self.fields['question_description'].initial or ''
            self.fields['hint'].initial = self.fields['hint'].initial or ''


        def clean(self):
            cleaned_data = super().clean()
            exam = cleaned_data.get('exam')
            chapter = cleaned_data.get('chapter')
            talenthunt = cleaned_data.get('talenthunt')
            if not cleaned_data.get('question_description'):
                self.add_error('question_description', 'Please enter a question description')
            
                exam = cleaned_data.get('exam')
                chapter = cleaned_data.get('chapter')
                talenthunt = cleaned_data.get('talenthunt')

                if not exam and not chapter and not talenthunt:
                    self.add_error(None, "Either exam, chapter, or talenthunt must be provided.")
                
                return cleaned_data

            if not exam and not chapter and not talenthunt:
                self.add_error(None, "Either exam, chapter, or talenthunt must be provided.")