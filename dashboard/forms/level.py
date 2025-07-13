from django import forms
from dashboard.models import TalentHuntSubject,Level,Question
from ckeditor_uploader.widgets import CKEditorUploadingWidget
class LevelForm(forms.ModelForm):
   
    
   
    class Meta:
        model = Level
        fields = ['title','number' ]
        widgets = {
                'title': forms.TextInput(
                    attrs={'class': 'form-control', 'placeholder': 'Enter title'}
                ),
                
            }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
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


       