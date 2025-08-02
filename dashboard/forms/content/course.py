from django import forms
from dashboard.models import Course

class AddForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['course_name', 'language', 'description', 'number_of_lessons', 'duration']
        widgets = {
            'course_name': forms.TextInput(attrs={'class': 'form-control'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
            # 'image': forms.FileInput(attrs={'class': 'form-control', 'type': 'file'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'cols': 40}),
            'number_of_lessons': forms.NumberInput(attrs={'class': 'form-control'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter course duration '}),
        }
        error_messages = {
            'course_name': {
                'required': "Course name is required.",
            },
            'language': {
                'required': "Language is required.",
            },
            # 'image': {
            #     'required': "An image is required.",
            # },
            'description': {
                'required': "A description is required.",
            },
            'number_of_lessons': {
                'required': "Number of lessons is required.",
                'invalid': "Enter a valid number of lessons.",
            },
            'duration': {
                'required': "Duration is required.",
                'invalid': "Enter a valid duration.",
            },
        }

    def __init__(self, *args, **kwargs):
        super(AddForm, self).__init__(*args, **kwargs)
        self.fields['course_name'].required = True
        self.fields['language'].required = True
        self.fields['description'].required = False
        self.fields['number_of_lessons'].required = True
        self.fields['duration'].required = True

    def clean(self):
       
        cleaned_data = super().clean()

        course_name = cleaned_data.get('course_name')
        if not course_name:
            self.add_error('course_name', "Course name is required.")
            
        language = cleaned_data.get('language')
        if not language:
            self.add_error('language', "Language is required.")

        number_of_lessons = cleaned_data.get('number_of_lessons')
        if number_of_lessons is not None and number_of_lessons <= 0:
            self.add_error('number_of_lessons', "Number of lessons must be greater than 0.")

        duration = cleaned_data.get('duration')
        if duration:
            try:
                duration = int(duration)
            except ValueError:
                self.add_error('duration', "Enter a valid duration.")
            else:
                if duration <= 0:
                    self.add_error('duration', "Duration must be greater than 0.")
        cleaned_data['duration'] = duration

        return cleaned_data

    def save(self, commit=True):
  
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance
