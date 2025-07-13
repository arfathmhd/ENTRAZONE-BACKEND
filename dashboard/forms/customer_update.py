from django import forms
from dashboard.views.imports import *  # Import necessary models

class CustomerUpdateForm(forms.ModelForm):
    """
    A simplified form for updating only specific customer fields: name, email, district, and image.
    """
    class Meta:
        model = CustomUser
        fields = ['name', 'email', 'district', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
            'district': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'required': False, 'id': 'id_image_input'}),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError("Name is required.")
        return name
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError("Email is required.")
        return email
