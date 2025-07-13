from django import forms
from dashboard.models import Notification, Course, Batch, CustomUser

class NotificationForm(forms.ModelForm):
    # Add fields for targeting options with Select2 support
    notification_type = forms.ChoiceField(
        choices=Notification.NOTIFICATION_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control select2', 'id': 'notification_type'})
    )
    
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.filter(is_deleted=False),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2', 'id': 'courses_select', 'style': 'width: 100%;'})
    )
    
    batches = forms.ModelMultipleChoiceField(
        queryset=Batch.objects.filter(is_deleted=False),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2', 'id': 'batches_select', 'style': 'width: 100%;'})
    )
    
    students = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(is_deleted=False, user_type=0),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2', 'id': 'students_select', 'style': 'width: 100%;'})
    )
    
    class Meta:
        model = Notification
        fields = ['image', 'title', 'message', 'notification_type', 'courses', 'batches', 'students'] 
        
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Notification Title'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Notification Message'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            # Save many-to-many relationships after the instance is saved
            self.save_m2m()
        return instance