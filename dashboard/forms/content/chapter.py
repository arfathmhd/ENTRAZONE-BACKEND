from django import forms
from django.core.exceptions import ValidationError
from dashboard.models import Chapter
from django.db.models import Max

class   ChapterForm(forms.ModelForm):
    is_free = forms.BooleanField(
        required=False,
        label="Chapter Is Free",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    order = forms.IntegerField(
        required=False,
        label="Chapter Order",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Chapter
        fields = ['chapter_name', 'description', 'is_free', 'order']
        widgets = {
            'chapter_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'cols': 40}),
    }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        max_order = Chapter.objects.filter(subject=kwargs.get('initial', {}).get('subject')).aggregate(Max('order'))['order__max'] or 0
        self.fields['order'].initial = max_order + 1

    def clean_chapter_name(self):
        """
        Custom validation for chapter_name.
        """
        chapter_name = self.cleaned_data.get('chapter_name')
        if not chapter_name:
            raise ValidationError("Chapter name is required.")
        # elif len(chapter_name) < 5:
        #     raise ValidationError("Chapter name must be at least 5 characters long.")
        return chapter_name

    # def clean_description(self):
        """
        Custom validation for description.
        """
        # description = self.cleaned_data.get('description')
        # if not description:
        #     raise ValidationError("A description is required.")
        # elif len(description) < 10:
        #     raise ValidationError("Description must be at least 10 characters long.")
        # return description

    def clean(self):
        """
        Custom clean method to validate all fields and add global or field-specific errors.
        """
        cleaned_data = super().clean()

        # Example: Validate image (if image field is required and has constraints)
        # if image and hasattr(image, 'size'):
        #     max_size_kb = 500  # Limit: 500 KB
        #     if image.size > max_size_kb * 1024:
                # self.add_error('image', f"Image size must not exceed {max_size_kb} KB.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance




# class ChapterExamForm(forms.ModelForm):
    