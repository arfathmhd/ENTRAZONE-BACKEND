from django import forms
from dashboard.models import Banner

class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = ['title', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter banner title'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }