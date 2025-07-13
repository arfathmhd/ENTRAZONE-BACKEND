from django import forms
from dashboard.models import Chapter,Lesson
from django.core.exceptions import ValidationError


class LessonForm(forms.ModelForm):
    chapter = forms.ModelChoiceField(
        queryset=Chapter.objects.filter(is_deleted=False).order_by('order'),
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        empty_label="Select a chapter",
    )
    visible_in_days = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0})
    )
    is_free = forms.BooleanField(
        required=False,
        label="Lesson Is Free",  
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    lesson_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}))

    video_title = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    video_url = forms.CharField(required=False, label='Video Key', widget=forms.TextInput(attrs={'class': 'form-control'}))
    video_is_downloadable = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    video_is_free = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    tp_stream = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    m3u8 = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    m3u8_is_downloadable = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    m3u8_is_free = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    pdf_title = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    pdf_file = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    pdf_is_downloadable = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    pdf_is_free = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model = Lesson
        fields = ['lesson_name',  'description', 'chapter', 'visible_in_days',
                 'video_title', 'video_url', 'video_is_downloadable', 'video_is_free','tp_stream',
                  'm3u8', 'm3u8_is_downloadable', 'm3u8_is_free',
                 'pdf_title', 'pdf_file', 'pdf_is_downloadable', 'pdf_is_free', 'is_free']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("#################")
        
        if self.instance.pk:
            video = self.instance.videos.first()
            pdf = self.instance.pdf_notes.first()
            
            if video:
                self.fields['video_title'].initial = video.title
                self.fields['video_url'].initial = video.url
                self.fields['video_is_downloadable'].initial = video.is_downloadable
                self.fields['video_is_free'].initial = video.is_free
          
                self.fields['tp_stream'].initial = video.tp_stream
                self.fields['m3u8'].initial = video.m3u8
                self.fields['m3u8_is_downloadable'].initial = video.m3u8_is_downloadable
                self.fields['m3u8_is_free'].initial = video.m3u8_is_free
            
                
            if pdf:
                self.fields['pdf_title'].initial = pdf.title
                self.fields['pdf_is_downloadable'].initial = pdf.is_downloadable
                self.fields['pdf_is_free'].initial = pdf.is_free
                self.fields['pdf_file'].initial = pdf.file.url

    def clean(self):
        cleaned_data = super().clean()
        video_url = cleaned_data.get('video_url')
        # m3u8_url = cleaned_data.get('m3u8_url')
        pdf_file = cleaned_data.get('pdf_file')

        # if not video_url and not pdf_file and not m3u8_url:
        #     raise ValidationError("Either video URL, M3U8 URL or PDF file must be provided.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance
