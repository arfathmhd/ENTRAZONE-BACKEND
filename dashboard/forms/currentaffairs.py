from django import forms
from dashboard.models import Video, PDFNote, CurrentAffairs

class CurrentAffairsForm(forms.Form):
    # Common Fields for Current Affairs
    currentaffair_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}))
    image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    # Video Fields
    video_title = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    video_url = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    video_is_downloadable = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    video_is_free = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    m3u8 = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    m3u8_is_downloadable = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    m3u8_is_free = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    video_current_affair = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    tp_stream = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    # PDF Note Fields
    pdf_title = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    pdf_file = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    pdf_is_downloadable = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    pdf_is_free = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    pdf_current_affair = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    # Clean Method to enforce at least one video or pdf is provided
    # def clean(self):
    #     cleaned_data = super().clean()
    #     video_url = cleaned_data.get('video_url')
    #     pdf_file = cleaned_data.get('pdf_file')

    #     # Ensure that at least one of the fields (video_url or pdf_file) is provided
    #     if not video_url or  not pdf_file:
    #         self.add_error('video_url', "Either a video URL or a PDF file must be provided.")
    #         self.add_error('pdf_file', "Either a video URL or a PDF file must be provided.")

    #     return cleaned_data

    def save(self, lesson_instance):
        """
        Save the form data to `Video` and `PDFNote` models where applicable.
        """
        video_data = {
            'lesson': lesson_instance,
            'title': self.cleaned_data.get('video_title'),
            'url': self.cleaned_data.get('video_url'),
            'is_downloadable': self.cleaned_data.get('video_is_downloadable', False),
            'is_free': self.cleaned_data.get('video_is_free', False),
            'm3u8': self.cleaned_data.get('m3u8'),
            'tpstream': self.cleaned_data.get('tp_stream'),
            'm3u8_is_downloadable': self.cleaned_data.get('m3u8_is_downloadable', False),
            'm3u8_is_free': self.cleaned_data.get('m3u8_is_free', False),
            'current_affair': self.cleaned_data.get('video_current_affair', False),
        }

        # Ensure that tp_stream or m3u8 is present before saving
        if (video_data['tpstream'] or video_data['m3u8']) and (video_data['title'] or video_data['url']):
            Video.objects.create(**video_data)

        # Handle PDF Note
        pdf_data = {
            'lesson': lesson_instance,
            'title': self.cleaned_data.get('pdf_title'),
            'file': self.cleaned_data.get('pdf_file'),
            'is_downloadable': self.cleaned_data.get('pdf_is_downloadable', False),
            'is_free': self.cleaned_data.get('pdf_is_free', False),
            'current_affair': self.cleaned_data.get('pdf_current_affair', False),
        }
        if pdf_data['title'] or pdf_data['file']:  
            PDFNote.objects.create(**pdf_data)

        current_affair_data = {
            'title': self.cleaned_data.get('currentaffair_name'),
            'description': self.cleaned_data.get('description'),
            'image': self.cleaned_data.get('image'),
        }
        if current_affair_data['title']:  
            CurrentAffairs.objects.create(**current_affair_data)
