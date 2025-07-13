from django import forms
from dashboard.models import Subject, Course, TalentHuntSubject

class TalentHuntSubjectForm(forms.ModelForm):
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),  
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        empty_label="Select a subject"
    )

    class Meta:
        model = TalentHuntSubject
        fields = ['title', 'subject']
        widgets = {
            'title': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter title'}
            ),
        }

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)  
        super().__init__(*args, **kwargs)
        
        if course:
            self.fields['subject'].queryset = Subject.objects.filter(course=course, is_deleted=False).order_by('order')

    def clean_title(self):
        title = self.cleaned_data.get('title')
        
        if TalentHuntSubject.objects.filter(title=title).exists():
            raise forms.ValidationError(f"A Talent Hunt subject with the title '{title}' already exists.")
       
        return title

    # def clean_subject(self):
    #     subject = self.cleaned_data.get('subject')

    #     course = self.initial.get('course')  

    #     if subject and subject.course != course:
    #         raise forms.ValidationError("The selected subject does not belong to the specified course.")

    #     return subject

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        
        if commit:
            instance.save()
            
        return instance
