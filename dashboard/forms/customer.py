from django import forms
from django.core.exceptions import ValidationError
from dashboard.views.imports import *  # Import necessary models
from datetime import datetime
# from django.core.files.images import get_image_dimensions

class PaymentPlanForm(forms.Form):
    
    payment_plan_type = forms.ChoiceField(
        choices=[('existing', 'Use Existing Plan'), ('new', 'Create New Plan')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='existing',
        required=True
    )
    
    existing_plan = forms.ModelChoiceField(
        queryset=FeePaymentPlan.objects.filter(is_deleted=False),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    plan_name = forms.CharField(
        max_length=100, 
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    total_amount = forms.DecimalField(
        max_digits=10, 
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    number_of_installments = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        required=False
    )
    
    installment_frequency = forms.ChoiceField(
        choices=FeePaymentPlan.FREQUENCY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    custom_start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )
    
    custom_end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )
    
    discount = forms.DecimalField(
        max_digits=10, 
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        initial=0.00,
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        payment_plan_type = cleaned_data.get('payment_plan_type')
        
        if payment_plan_type == 'existing':
            if not cleaned_data.get('existing_plan'):
                self.add_error('existing_plan', 'Please select an existing payment plan')
        else:  # new plan
            if not cleaned_data.get('plan_name'):
                self.add_error('plan_name', 'Plan name is required')
            if not cleaned_data.get('total_amount'):
                self.add_error('total_amount', 'Total amount is required')
            if not cleaned_data.get('number_of_installments'):
                self.add_error('number_of_installments', 'Number of installments is required')
            if not cleaned_data.get('installment_frequency'):
                self.add_error('installment_frequency', 'Installment frequency is required')
                
            # Validate custom date fields if custom_date frequency is selected
            frequency = cleaned_data.get('installment_frequency')
            if frequency == 'custom_date':
                if not cleaned_data.get('custom_start_date'):
                    self.add_error('custom_start_date', 'Start date is required for custom date frequency')
                if not cleaned_data.get('custom_end_date'):
                    self.add_error('custom_end_date', 'End date is required for custom date frequency')
                if cleaned_data.get('custom_start_date') and cleaned_data.get('custom_end_date'):
                    if cleaned_data.get('custom_start_date') >= cleaned_data.get('custom_end_date'):
                        self.add_error('custom_end_date', 'End date must be after start date')
        
        return cleaned_data


class CustomerForm(forms.ModelForm):
    image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control-file'}),
    )

    # Custom widget to include batch dates as data attributes
    class BatchSelectWidget(forms.Select):
        def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
            option = super().create_option(name, value, label, selected, index, subindex, attrs)
            
            # Skip if no value or empty value
            if not value or value == '':
                return option
                
            # Extract the actual ID value from ModelChoiceIteratorValue if needed
            batch_id = None
            if hasattr(value, 'value'):
                batch_id = value.value
            else:
                try:
                    batch_id = int(value)
                except (TypeError, ValueError):
                    return option
                    
            # Get the batch object and add data attributes for start_date and batch_expiry
            try:
                batch = Batch.objects.get(pk=batch_id)
                option['attrs']['data-start-date'] = batch.start_date.isoformat()
                option['attrs']['data-end-date'] = batch.batch_expiry.isoformat()
            except (Batch.DoesNotExist, ValueError, TypeError):
                pass
                
            return option
    
    batches = forms.ModelChoiceField(
        queryset=Batch.objects.filter(is_deleted=False, batch_expiry__gte=timezone.now().date()),
        widget=BatchSelectWidget(attrs={'class': 'form-select'}),
        required=False,
    )

    class Meta:
        model = CustomUser
        fields = ['image', 'name', 'email', 'phone_number', 'district', 'batches']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'district': forms.Select(attrs={'class': 'form-control', 'required': True}),
        }

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)

        # Set required fields
        self.fields['name'].required = True
        self.fields['email'].required = True
        self.fields['phone_number'].required = True
        self.fields['district'].required = True
        
        # Set district choices
        self.fields['district'].widget.choices = CustomUser.DISTRICT_CHOICES

        # Handle existing batches for the user
        if self.instance and self.instance.pk:
            subscriptions = Subscription.objects.filter(user=self.instance, is_deleted=False).prefetch_related('batch')
            selected_batches = [batch for subscription in subscriptions for batch in subscription.batch.all()]
            self.fields['batches'].initial = selected_batches

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if CustomUser.objects.exclude(id=self.instance.id).filter(name=name, is_deleted=False).exists():
            raise forms.ValidationError("A user with this name already exists.")
        return name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.exclude(id=self.instance.id).filter(email=email, is_deleted=False).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not phone_number.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        if len(phone_number) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        if CustomUser.objects.exclude(id=self.instance.id if self.instance else None).filter(
            phone_number=phone_number, is_deleted=False
        ).exists():
            raise forms.ValidationError("A user with this phone number already exists.")
        return phone_number

    def clean_image(self):
        image = self.cleaned_data.get('image')

        # Check for image size (optional, e.g., max 5 MB)
        # if noimage:
            # image_width, image_height = get_image_dimensions(image)
            # max_size = 5 * 1024 * 1024  # Max size in bytes (5MB)
            
            # if image.size > max_size:
            #     raise ValidationError("Image size cannot be more than 5MB.")
            
            # if image_width < 500 or image_height < 500:
                # raise ValidationError("Image dimensions should be at least 500x500 pixels.")

        return image

    def clean_batches(self):
        batch = self.cleaned_data.get('batches')

        # Ensure a batch is selected if it's required
        if not batch:
            raise ValidationError("A batch must be selected.")

        return batch

    def save(self, commit=True, payment_plan_data=None):
        instance = super().save(commit=False)

        # Handle image upload (if any)
        if self.cleaned_data.get('image'):
            instance.image = self.cleaned_data.get('image')

        instance.save()

        selected_batch = self.cleaned_data.get('batches')

        # Handle batch subscription and payment plan
        if selected_batch:
            # Create subscription first, then add the batch to the many-to-many relationship
            subscription = Subscription.objects.create(user=instance)
            subscription.batch.add(selected_batch)
            
            # Handle payment plan if provided
            if payment_plan_data:
                payment_plan_type = payment_plan_data.get('payment_plan_type')
                
                if payment_plan_type == 'existing':
                    # Use existing payment plan
                    payment_plan = payment_plan_data.get('existing_plan')
                    if payment_plan:
                        subscription.payment_plan = payment_plan
                        subscription.save()
                        self._generate_installments(subscription, payment_plan)
                else:
                    # Create new payment plan
                    # Create the payment plan with all fields including custom dates if provided
                    new_plan = FeePaymentPlan.objects.create(
                        name=payment_plan_data.get('plan_name'),
                        total_amount=payment_plan_data.get('total_amount'),
                        number_of_installments=payment_plan_data.get('number_of_installments'),
                        frequency=payment_plan_data.get('installment_frequency', 'monthly'),
                        discount=payment_plan_data.get('discount', 0.00)
                    )
                    
                    # Store custom dates as attributes for use in _generate_installments
                    if payment_plan_data.get('installment_frequency') == 'custom_date':
                        new_plan.custom_start_date = payment_plan_data.get('custom_start_date')
                        new_plan.custom_end_date = payment_plan_data.get('custom_end_date')
                    subscription.payment_plan = new_plan
                    subscription.save()
                    self._generate_installments(subscription, new_plan)

        return instance
        
    def _generate_installments(self, subscription, payment_plan):
        """Generate installments based on payment plan and its frequency"""
        if not payment_plan or not payment_plan.number_of_installments:
            return
            
        # Calculate amount per installment (accounting for discount)
        total_after_discount = payment_plan.total_amount - payment_plan.discount
        amount_per_installment = total_after_discount / payment_plan.number_of_installments
        
        # Set the first due date to today by default
        current_date = timezone.now().date()
        
        # Get frequency from the payment plan
        frequency = payment_plan.frequency
        
        # Handle custom date range or batch duration
        custom_start_date = getattr(payment_plan, 'custom_start_date', None)
        custom_end_date = getattr(payment_plan, 'custom_end_date', None)
        
        # For batch duration, use the batch dates
        if frequency == 'batch_duration':
            # Get the first batch from the many-to-many relationship
            batch = subscription.batch.first()
            if batch:
                start_date = batch.start_date
                end_date = batch.batch_expiry
            else:
                # Fallback to default behavior if no batch is found
                return
            
            # Calculate date intervals between start and end date
            total_days = (end_date - start_date).days
            interval_days = max(1, total_days // payment_plan.number_of_installments)
            
            # Create installments
            for i in range(payment_plan.number_of_installments):
                # For the last installment, use the end date
                if i == payment_plan.number_of_installments - 1:
                    due_date = end_date
                else:
                    due_date = start_date + timezone.timedelta(days=interval_days * i)
                
                # Create the installment
                FeeInstallment.objects.create(
                    subscription=subscription,
                    due_date=due_date,
                    amount_due=amount_per_installment,
                    status='PENDING',
                    discount_applied=payment_plan.discount / payment_plan.number_of_installments
                )
            
            # Update subscription totals and return
            subscription.update_payment_totals()
            return
        
        # For custom date range
        elif frequency == 'custom_date' and custom_start_date and custom_end_date:
            start_date = custom_start_date
            end_date = custom_end_date
            
            # Calculate date intervals between start and end date
            total_days = (end_date - start_date).days
            interval_days = max(1, total_days // payment_plan.number_of_installments)
            
            # Create installments
            for i in range(payment_plan.number_of_installments):
                # For the last installment, use the end date
                if i == payment_plan.number_of_installments - 1:
                    due_date = end_date
                else:
                    due_date = start_date + timezone.timedelta(days=interval_days * i)
                
                # Create the installment
                FeeInstallment.objects.create(
                    subscription=subscription,
                    due_date=due_date,
                    amount_due=amount_per_installment,
                    status='PENDING',
                    discount_applied=payment_plan.discount / payment_plan.number_of_installments
                )
            
            # Update subscription totals and return
            subscription.update_payment_totals()
            return
        
        # Standard frequency options (weekly, monthly, yearly)
        for i in range(payment_plan.number_of_installments):
            if frequency == 'weekly':
                due_date = current_date + timezone.timedelta(days=7 * i)
            elif frequency == 'yearly':
                due_date = current_date + timezone.timedelta(days=365 * i)
            else:  # monthly (default)
                # Add months to the date
                month = current_date.month - 1 + i  # -1 to convert to 0-based indexing
                year = current_date.year + month // 12
                month = month % 12 + 1  # Convert back to 1-based indexing
                day = min(current_date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
                due_date = datetime(year, month, day).date()
            
            # Create the installment
            FeeInstallment.objects.create(
                subscription=subscription,
                due_date=due_date,
                amount_due=amount_per_installment,
                status='PENDING',
                discount_applied=payment_plan.discount / payment_plan.number_of_installments
            )
        
        # Update subscription totals
        subscription.update_payment_totals()


class SubscriptionCustomerForm(forms.Form):
    def __init__(self, *args, **kwargs):
        customer = kwargs.pop('customer', None)  
        super().__init__(*args, **kwargs)

        if customer:
            subscribed_batches = Subscription.objects.filter(user=customer,is_deleted=False).values_list('batch', flat=True)
            self.fields['batch'].queryset = Batch.objects.filter(is_deleted=False).exclude(id__in=subscribed_batches)
        else:
            self.fields['batch'].queryset = Batch.objects.filter(is_deleted=False)

    batch = forms.ModelChoiceField(
        queryset=Batch.objects.none(), 
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class SubscriptionForm(forms.ModelForm):
    student_id = forms.IntegerField(
        label="Student ID", 
        widget=forms.NumberInput(attrs={'placeholder': 'Enter Student ID'})
    )
    
    class Meta:
        model = Subscription
        fields = ['batch', 'student_id']
        widgets = {
            'batch': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super(SubscriptionForm, self).__init__(*args, **kwargs)
        # Dynamically populate the batch dropdown
        self.fields['batch'].queryset = Batch.objects.all()
        self.fields['batch'].empty_label = "Select a Batch"
