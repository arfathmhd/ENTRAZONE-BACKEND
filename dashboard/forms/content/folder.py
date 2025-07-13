from django import forms
from dashboard.views.imports import *

class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ['title']

    def __init__(self, *args, **kwargs):
        super(FolderForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs['class'] = 'form-control'