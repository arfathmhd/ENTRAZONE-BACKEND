from django import forms
from dashboard.models import Lesson, Exam
from django.core.exceptions import ValidationError
from django.db.models import Max


class LessonForm(forms.ModelForm):
   
    visible_in_days = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0})
    )
    is_free = forms.BooleanField(
        required=False,
        label="Lesson Is Free",  # Custom label to display in the template
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    lesson_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}))

    video_title = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    video_url = forms.CharField(required=False, label='Video Key', widget=forms.TextInput(attrs={'class': 'form-control'}))
    video_is_downloadable = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    video_is_free = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    m3u8 = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    tp_stream = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    m3u8_is_downloadable = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    m3u8_is_free = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    pdf_title = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    pdf_file = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    pdf_is_downloadable = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    pdf_is_free = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    order = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))


    class Meta:
        model = Lesson
        fields = ['lesson_name', 'description', 'chapter',
                   'm3u8','m3u8_is_downloadable','m3u8_is_free', 'order',
                      'visible_in_days','video_title', 'video_url', 'video_is_downloadable','tp_stream', 'video_is_free', 'pdf_title', 'pdf_file', 'pdf_is_downloadable', 'pdf_is_free','is_free']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        chapter = kwargs.get('initial', {}).get('chapter')
        max_order = Lesson.objects.filter(chapter=chapter).aggregate(Max('order'))['order__max'] or 0
 
        self.fields['order'].initial = max_order + 1
        if self.instance.pk:
            video = self.instance.videos.first()
            pdf = self.instance.pdf_notes.first()
            self.fields['order'].initial = self.instance.order
            if video:
                self.fields['video_title'].initial = video.title
                self.fields['video_url'].initial = video.url
                self.fields['video_is_downloadable'].initial = video.is_downloadable
                self.fields['video_is_free'].initial = video.is_free
                self.fields['m3u8'].initial = video.m3u8
                self.fields['tp_stream'].initial = video.tp_stream
                self.fields['m3u8_is_free'].initial = video.m3u8_is_free
                self.fields['m3u8_is_downloadable'].initial = video.m3u8_is_downloadable

            if pdf:
                self.fields['pdf_title'].initial = pdf.title
                self.fields['pdf_is_downloadable'].initial = pdf.is_downloadable
                self.fields['pdf_is_free'].initial = pdf.is_free
                self.fields['pdf_file'].initial = pdf.file.url

    def clean(self):
        cleaned_data = super().clean()
        video_url = cleaned_data.get('video_url')
        m3u8_url = cleaned_data.get('m3u8')
        tp_stream = cleaned_data.get('tp_stream')
        pdf_file = cleaned_data.get('pdf_file')
        pdf_title = cleaned_data.get('pdf_title')
        
        has_video = bool(video_url or m3u8_url or tp_stream)
        has_pdf = bool(pdf_file or (pdf_title and self.instance.pk and self.instance.pdf_notes.exists()))
        
        # if has_video and has_pdf:
        #     raise ValidationError("You can only add either video OR PDF, not both.")
            
        # if not has_video and not has_pdf:
        #     raise ValidationError("Either video content (YouTube URL, M3U8 URL, or TP Stream) or PDF file must be provided.")
            
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance



class LessonExamForm(forms.ModelForm):
    number_of_attempt = forms.IntegerField(
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter number of attempts allowed', 'min': '1'}),
        help_text="Number of times a student can attempt this exam"
    )
    
    is_shuffle = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Shuffle questions for each attempt"
    )
    
    class Meta:
        model = Exam
        fields = ['title', 'duration', 'subject', 'is_free', 'number_of_attempt', 'is_shuffle']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter exam title'}),
            'duration': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'is_free': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make subject optional
        self.fields['subject'].required = False
        # Make title required
        self.fields['title'].required = True