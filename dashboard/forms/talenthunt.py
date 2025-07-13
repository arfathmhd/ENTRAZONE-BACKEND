from django import forms
from dashboard.models import Subject ,Course ,TalentHunt

class TalentHuntForm(forms.ModelForm):
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_deleted=False),
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        empty_label="Select a Course"
    )
   
   
    class Meta:
        model = TalentHunt
        fields = ['title', 'course']
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
