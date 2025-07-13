from django import forms
from dashboard.models import Subject

class SubjectForm(forms.ModelForm):
    is_free = forms.BooleanField(
        required=False,
        label="Subject Is Free",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Subject
        fields = ['subject_name', 'description', 'is_free']
        widgets = {
            'subject_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'cols': 40}),
        }

    def clean(self):
        cleaned_data = super().clean()

        # Validate subject_name
        subject_name = cleaned_data.get('subject_name')
        if not subject_name :
            self.add_error('subject_name', 'Subject name is required.')

        # Validate description
        # description = cleaned_data.get('description')
        # if not description :
        #     self.add_error('description', 'Description is required.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Save instance only if there are no validation errors
        if not self.errors and commit:
            instance.save()

        return instance
