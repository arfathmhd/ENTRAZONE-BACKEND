from django import forms
from dashboard.models import Subject, Course
from django.db.models import Max

class SubjectForm(forms.ModelForm):
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_deleted=False),
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        empty_label="Select a Course"
    )
    is_free = forms.BooleanField(
        required=False,
        label="Subject Is Free",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    order = forms.IntegerField(
        required=False,
        label="Subject Order",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Subject
        fields = ['subject_name', 'description', 'course', 'is_free', 'order']
        widgets = {
            'subject_name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter subject name'}
            ),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'cols': 40, 'placeholder': 'Enter a brief description'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subject_name'].required = True
        self.fields['description'].required = False
        
        # Order will be set dynamically via JavaScript when course is selected
        # Only set the initial value if we're editing an existing subject
        if self.instance.pk:
            self.fields['order'].initial = self.instance.order

    def clean_subject_name(self):
        subject_name = self.cleaned_data.get('subject_name')
        course = self.cleaned_data.get('course')

        if Subject.objects.exclude(id=self.instance.id if self.instance else None).filter(
            subject_name=subject_name, course=course, is_deleted=False
        ).exists():
            raise forms.ValidationError(f"A subject with the name '{subject_name}' already exists in this course.")

        return subject_name

    # def clean_description(self):
    #     description = self.cleaned_data.get('description')

    #     if not description or description.strip() == '':
    #         raise forms.ValidationError("Description cannot be empty.")

    #     return description

    def clean_image(self):
        # image = self.cleaned_data.get('image')

        # Optional: Add image validation (e.g., check file type, size, etc.)
        # if image:
        #     # Example: Ensure the file size is less than 5 MB
        #     max_size = 5 * 1024 * 1024  # 5 MB
        #     if image.size > max_size:
        #         raise forms.ValidationError("Image size must be less than 5 MB.")

        #     # Example: Ensure the image is of a certain type (e.g., PNG, JPEG)
        #     if not image.name.lower().endswith(('png', 'jpg', 'jpeg')):
        #         raise forms.ValidationError("Only PNG, JPG, and JPEG image formats are allowed.")

        return image

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()

        return instance
