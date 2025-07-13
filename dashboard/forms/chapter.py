from django import forms
from django.core.exceptions import ValidationError
from dashboard.models import Chapter, Subject

class ChapterForm(forms.ModelForm):
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(is_deleted=False).order_by('order'),
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        empty_label="Select a subject",
    )
    is_free = forms.BooleanField(
        required=False,
        label="Chapter Is Free",  # Custom label to display in the template
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
   
    class Meta:
        model = Chapter
        fields = ['chapter_name',  'description', 'subject', 'is_free']
        widgets = {
            'chapter_name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter chapter name'}
            ),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'cols': 40, 'placeholder': 'Enter a brief description'}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        
        # Extract field values
        chapter_name = cleaned_data.get('chapter_name')
        subject = cleaned_data.get('subject')
        description = cleaned_data.get('description')
        
        # Validate that the chapter_name is not empty and has a reasonable length
        if not chapter_name :
            self.add_error('chapter_name', 'Chapter name is required.')
        
        # Validate that a subject is selected
        if not subject:
            self.add_error('subject', 'Please select a subject for the chapter.')
        
        # Validate that a description is provided
        # if not description:
        #     self.add_error('description', 'Please provide a description for the chapter.')
        
        # Optionally, validate image if required (if you have an image requirement)
        # if not image:
        #     self.add_error('image', 'Please upload an image for the chapter.')
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance
