from dashboard.views.imports import *
from django import forms


# class SuccessStoriesForm(forms.ModelForm):
#     class Meta:
#         model = SuccessStory
#         fields = ['image']
#         widgets = {
#             'image': forms.FileInput(attrs={'class': 'form-control'}),
#         }

#     def clean_image(self):
#         image = self.cleaned_data.get('image')
#         if not image:
#             self.add_error('image', "An image is required for the success story.")
#         return image