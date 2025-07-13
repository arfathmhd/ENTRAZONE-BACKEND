from django import forms
from dashboard.views.imports import *

class StaffForm(forms.ModelForm):
    image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control-file'}),
    )
    user_type = forms.ChoiceField(
        choices=CustomUser.TYPE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    class Meta:
        model = CustomUser
        fields = ['image', 'name', 'email', 'password', 'phone_number', 'user_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['name'].required = True
        self.fields['phone_number'].required = True

        if self.instance and self.instance.pk:
            # Form is being used to update an existing user
            self.fields['password'].required = False
            self.fields['password'].widget.attrs['placeholder'] = "Leave blank to keep the current password"
        else:
            # Form is being used to create a new user
            self.fields['password'].required = True
            # Remove placeholder for add form
            if 'placeholder' in self.fields['password'].widget.attrs:
                del self.fields['password'].widget.attrs['placeholder']

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if CustomUser.objects.exclude(id=self.instance.id if self.instance else None).filter(
            name=name, is_deleted=False, is_staff=True
        ).exists():
            raise forms.ValidationError("A user with this name already exists.")
        return name

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not phone_number.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        if len(phone_number) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        if CustomUser.objects.exclude(id=self.instance.id if self.instance else None).filter(
            phone_number=phone_number, is_deleted=False, is_staff=True
        ).exists():
            raise forms.ValidationError("A user with this phone number already exists.")
        return phone_number

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if self.instance and self.instance.pk and not password:
            return None
        elif password and len(password) < 4:
            raise forms.ValidationError("Password must be at least 4 characters long.")
        return password

    def save(self, commit=True):
        instance = super().save(commit=False)
        password = self.cleaned_data.get('password')

        if self.cleaned_data.get('image'):
            instance.image = self.cleaned_data.get('image')

        if password:
            instance.set_password(password)
        elif self.instance.pk:
            instance.password = CustomUser.objects.get(pk=self.instance.pk).password

        if commit:
            instance.save()
        return instance




class PasswordSettingForm(forms.Form):
    user_id = forms.IntegerField(widget=forms.HiddenInput)
    password = forms.CharField(label='New Password', widget=forms.PasswordInput)
    confirm_password = forms.CharField(label='Confirm New Password', widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        user_id = kwargs.pop('user_id', None)
        super().__init__(*args, **kwargs)
        if user_id:
            self.fields['user_id'].initial = user_id

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                self.add_error('confirm_password', "Passwords do not match. Please enter them again.")
        
        return cleaned_data

    def save(self, user):
        new_password = self.cleaned_data['password']
        user.set_password(new_password)
        user.save()