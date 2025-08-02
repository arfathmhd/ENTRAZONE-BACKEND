import os, string, random
import uuid
import base64
from datetime import datetime
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, Group, Permission
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from ckeditor.fields import RichTextField
from django.core.validators import MinValueValidator, MaxValueValidator
from Crypto.Cipher import AES
from django.conf import settings
from django.utils.translation import gettext_lazy as _



class MyUserManager(BaseUserManager):
    def _create_user(self, username, password, **extra_fields):
        if not username:
            raise ValueError("Username must be set")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        # user.save(using=self._db)
        user.save()
        return user
    def create_user(self, username, password=None, **extra_fields):
        # Set any default values for regular users here if needed
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True) 
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("name", "Superuser")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(username, password, **extra_fields)
    

def get_random_string():
    chars = string.ascii_lowercase
    strin = "".join(random.choice(chars) for _ in range(6))
    date = datetime.now().strftime("%m%d%H%M%S")
    return "f" + date + strin


class CustomUser(AbstractBaseUser):
    
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        tmp = get_random_string()
        filename = "%s.%s" % (tmp, ext)
        return os.path.join("user_images", filename)
    
    TYPE_CHOICES = (
        (0, "No Special Access"),
        (1, "Admin"),
        (2, "Content manager"),
        (3, "Admission manager"),
        (4, "Mentor"),
        
    )

    STATE_CHOICES = [
    ('0', 'Andhra Pradesh'),
    ('1', 'Arunachal Pradesh'),
    ('2', 'Assam'),
    ('3', 'Bihar'),
    ('4', 'Chhattisgarh'),
    ('5', 'Goa'),
    ('6', 'Gujarat'),
    ('7', 'Haryana'),
    ('8', 'Himachal Pradesh'),
    ('9', 'Jharkhand'),
    ('10', 'Karnataka'),
    ('11', 'Kerala'),
    ('12', 'Madhya Pradesh'),
    ('13', 'Maharashtra'),
    ('14', 'Manipur'),
    ('15', 'Meghalaya'),
    ('16', 'Mizoram'),
    ('17', 'Nagaland'),
    ('18', 'Odisha'),
    ('19', 'Punjab'),
    ('20', 'Rajasthan'),
    ('21', 'Sikkim'),
    ('22', 'Tamil Nadu'),
    ('23', 'Telangana'),
    ]

    username = models.CharField(
        unique=True,
        max_length=150,
        error_messages={
            "unique": _("A staff with this phone/email number already exists."),
        },
    )
    email = models.EmailField( null=True, blank=True)
    default_course = models.ForeignKey('Course', on_delete=models.SET_NULL,null=True,blank=True)
    image=models.ImageField(upload_to=get_file_path, null=True, blank=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    district = models.CharField(max_length=2, choices=STATE_CHOICES)
    user_type = models.IntegerField(default=0, choices=TYPE_CHOICES)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    address = models.TextField(blank=True, null=True)
    is_superuser = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    suspended_date = models.DateTimeField(null=True, blank=True)
    old_id = models.IntegerField(default=0)

    objects = MyUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username or "No name"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def has_perm(self, perm, obj=None):
        return self.is_superuser or self.user_permissions.filter(codename=perm).exists()

    def has_module_perms(self, app_label):
        return self.is_superuser or self.user_permissions.filter(content_type__app_label=app_label).exists()


    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',
        blank=True,
        help_text="Groups this user belongs to.",
        related_query_name='customuser'
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_set',
        blank=True,
        help_text="Specific permissions for this user.",
        related_query_name='customuser'
    )
    def save(self, *args, **kwargs):
   
        if self.password and not self.password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2')):
        
            self.password = make_password(self.password)
        
        super().save(*args, **kwargs)


class Batch(models.Model):
    batch_name = models.CharField(max_length=100)
    start_date = models.DateField()
    batch_expiry = models.DateField()
    late_batch = models.BooleanField(default=False)
    batch_price = models.DecimalField(max_digits=10, decimal_places=2)
    course = models.ForeignKey('Course', on_delete=models.CASCADE)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Batch for {self.course.course_name}, {self.batch_expiry}, {self.batch_price}"
    


class FeePaymentPlan(models.Model):
    FREQUENCY_CHOICES = (
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('custom_date', 'Custom Date'),
        ('batch_duration', 'Batch Duration'),
    )
    
    name = models.CharField(max_length=100, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    number_of_installments = models.PositiveIntegerField(blank=True, null=True)
    frequency = models.CharField(max_length=150, choices=FREQUENCY_CHOICES, default='monthly')
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        frequency_display = dict(self.FREQUENCY_CHOICES).get(self.frequency, 'Monthly')
        return f"{self.name} - ₹{self.total_amount} in {self.number_of_installments} {frequency_display} installments"


class Subscription(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    batch = models.ManyToManyField(Batch, blank=True, null=True)
    custom_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_plan = models.ForeignKey(FeePaymentPlan, on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_due = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Subscription of {self.user.name} "
        
    def update_payment_totals(self):
        """Update total paid and due amounts"""
        paid = self.installments.filter(is_paid=True).aggregate(total=models.Sum('amount_due'))['total'] or 0
        due = self.installments.filter(is_paid=False).aggregate(total=models.Sum('amount_due'))['total'] or 0
        
        self.total_paid = paid
        self.total_due = due
        self.save()
        
    def get_next_due_installment(self):
        """Get the next due installment"""
        return self.installments.filter(is_paid=False).order_by('due_date').first()
        
    def get_payment_status(self):
        """Get overall payment status"""
        if self.total_due == 0:
            return 'PAID'
        
        overdue = self.installments.filter(status='OVERDUE').exists()
        if overdue:
            return 'OVERDUE'
            
        return 'PENDING'


class FeeInstallment(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('PROCESSING', 'Processing'),
        ('FAILED', 'Failed'),
    )

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="installments")
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    paid_on = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    payment_link = models.URLField(blank=True, null=True)
    payment_link_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    payment_link_expires = models.DateTimeField(null=True, blank=True)
    payment_attempts = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"₹{self.amount_due} due on {self.due_date} for {self.subscription.user.name}"
    
    def is_expired(self):
        """Check if payment link has expired"""
        if not self.payment_link_expires:
            return False
        return timezone.now() > self.payment_link_expires
    
    def mark_as_paid(self, reference=None):
        """Mark installment as paid"""
        self.is_paid = True
        self.status = 'PAID'
        self.paid_on = timezone.now()
        if reference:
            self.payment_reference = reference
        self.save()
        
    def generate_payment_link(self, base_url):
        """Generate a shareable payment link"""
        # Set expiry to 7 days from now
        self.payment_link_expires = timezone.now() + timezone.timedelta(days=7)
        self.payment_link = f"{base_url}/pay/{self.payment_link_uuid}/"
        self.save()
        return self.payment_link


class HDFCPaymentConfig(models.Model):
    """Configuration for HDFC SmartGateway payment gateway"""
    merchant_id = models.CharField(max_length=100, help_text="HDFC Merchant ID", null=True, blank=True)
    access_code = models.CharField(max_length=100, help_text="HDFC Access Code", null=True, blank=True)
    working_key = models.CharField(max_length=100, help_text="HDFC Working Key for encryption", null=True, blank=True)
    api_key = models.CharField(max_length=100, help_text="HDFC API Key", null=True, blank=True)
    payment_page_client_id = models.CharField(max_length=100, help_text="HDFC Payment Page Client ID", null=True, blank=True)
    is_production = models.BooleanField(default=False, help_text="Use production environment")
    # Webhook configuration
    webhook_url = models.URLField(max_length=255, help_text="URL where SmartGateway will send webhook events", blank=True, null=True)
    webhook_username = models.CharField(max_length=100, help_text="Username for Basic Auth webhook authentication", blank=True, null=True)
    webhook_password = models.CharField(max_length=100, help_text="Password for Basic Auth webhook authentication", blank=True, null=True)
    webhook_secret = models.CharField(max_length=100, help_text="Secret for additional webhook signature verification", blank=True, null=True)
    webhook_custom_headers = models.JSONField(default=dict, blank=True, help_text="Custom headers for webhook authentication")
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"HDFC Config - {'Production' if self.is_production else 'Test'}"
    
    @property
    def api_url(self):
        """Get the appropriate API URL based on environment"""
        if self.is_production:
            return "https://smartgatewayuat.hdfcbank.com"
        return "https://smartgatewayuat.hdfcbank.com"
    
    def generate_checksum(self, merchant_data):
        """Generate checksum for HDFC payment"""
        return self.encrypt(merchant_data, self.working_key)
    
    @staticmethod
    def encrypt(data, working_key):
        """Encrypt data using working key"""
        iv = '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
        aes = AES.new(working_key.encode(), AES.MODE_CBC, iv.encode())
        encrypted_data = aes.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()
    
    @staticmethod
    def decrypt(encrypted_data, working_key):
        """Decrypt data using working key"""
        iv = '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
        encrypted_data = base64.b64decode(encrypted_data)
        aes = AES.new(working_key.encode(), AES.MODE_CBC, iv.encode())
        decrypted_data = aes.decrypt(encrypted_data).decode().strip()
        return decrypted_data




class PaymentTransaction(models.Model):
    """Record of payment transactions"""
    STATUS_CHOICES = (
        ('INITIATED', 'Initiated'),
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILURE', 'Failure'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    )
    
    installment = models.ForeignKey(FeeInstallment, on_delete=models.CASCADE, related_name='transactions')
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    transaction_uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    order_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INITIATED')
    payment_mode = models.CharField(max_length=50, blank=True, null=True)
    bank_ref_number = models.CharField(max_length=100, blank=True, null=True)
    gateway_response = models.JSONField(blank=True, null=True)
    payment_link = models.URLField(blank=True, null=True)
    payment_link_expiry = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.order_id} - ₹{self.amount} - {self.status}"
    
    def is_expired(self):
        """Check if payment link has expired"""
        if not self.payment_link_expiry:
            return False
        return timezone.now() > self.payment_link_expiry
    
    def update_installment_status(self):
        """Update the associated installment status based on transaction status"""
        if self.status == 'SUCCESS':
            self.installment.mark_as_paid(reference=self.transaction_id)
            # Update subscription totals
            self.installment.subscription.update_payment_totals()
            self.installment.subscription.last_payment_date = timezone.now()
            self.installment.subscription.save()
        elif self.status == 'FAILURE':
            self.installment.status = 'FAILED'
            self.installment.payment_attempts += 1
            self.installment.save()

class WebhookLog(models.Model):
    """Model to log payment gateway webhook data"""

    
    STATUS_CHOICES = (
        ('RECEIVED', 'Received'),
        ('PROCESSED', 'Processed'),
        ('FAILED', 'Failed'),
        ('INVALID', 'Invalid'),
        ('DUPLICATE', 'Duplicate'),
    )
    
    webhook_id = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Unique ID of the webhook event from SmartGateway")
    webhook_date = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the webhook was created by SmartGateway")
    order_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    transaction = models.ForeignKey(PaymentTransaction, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=100, blank=True, null=True, help_text="Type of webhook event")
    request_data = models.JSONField(default=dict)
    headers = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    signature_valid = models.BooleanField(null=True, blank=True, help_text="Whether signature validation passed")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RECEIVED')
    error_message = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created']
        verbose_name = 'Webhook Log'
        verbose_name_plural = 'Webhook Logs'
    
    def __str__(self):
        return f"Webhook - {self.order_id or 'Unknown'} ({self.created.strftime('%Y-%m-%d %H:%M:%S')})"


class Course(models.Model):
    LANGUAGE_CHOICES = (
        ('English', 'English'),
        # ('Hindi', 'Hindi'),
        # ('Telugu', 'Telugu'),
        # ('Tamil', 'Tamil'),
        # ('Kannada', 'Kannada'),
        ('Malayalam', 'Malayalam'),
        # ('Marathi', 'Marathi'),
        # ('Gujarati', 'Gujarati'),
        # ('Punjabi', 'Punjabi'),
        # ('Bengali', 'Bengali'),
    )
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        tmp = get_random_string()
        filename = "%s.%s" % (tmp, ext)
        return os.path.join("course_images", filename)
    
    course_name = models.CharField(max_length=200)
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='Malayalam')
    description = models.TextField()
    image = models.ImageField(upload_to=get_file_path, null=True, blank=True)
    duration = models.CharField(max_length=100,default=0)
    number_of_lessons = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    old_id = models.IntegerField(default=0)
    
    def __str__(self):
        return self.course_name  or 'No title'


class Subject(models.Model):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        tmp = get_random_string()
        filename = "%s.%s" % (tmp, ext)
        return os.path.join("subject_images", filename)
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='subjects')
    subject_name = models.CharField(max_length=200)
    image=models.ImageField(upload_to=get_file_path, null=True, blank=True)
    description = models.TextField()
    is_free = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    old_id = models.IntegerField(default=0)
    order = models.IntegerField(default=0)
    
    def __str__(self):
        return self.subject_name  or 'No title'


class Chapter(models.Model):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        tmp = get_random_string()
        filename = "%s.%s" % (tmp, ext)
        return os.path.join("chapter_images", filename)
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='chapters')
    chapter_name = models.CharField(max_length=200)
    image = models.ImageField(upload_to=get_file_path, null=True, blank=True)
    description = models.TextField()
    is_free = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    old_id = models.IntegerField(default=0)
    order = models.IntegerField(default=0)
    
    def __str__(self):
        return self.chapter_name  or 'No title'
    

class Folder(models.Model):
    title = models.CharField(max_length=255)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='folders')
    parent_folder = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_folders')
    name = models.CharField(max_length=200)
    # is_free = models.BooleanField(default=True)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    old_id = models.IntegerField(default=0)
    order = models.IntegerField(default=0)
    visible_in_days = models.IntegerField(default=0)
    
    def __str__(self):
        return self.title  or 'No title'
    
    def get_breadcrumbs(self):
        breadcrumbs = []
        current_folder = self
        while current_folder:
            breadcrumbs.append({
                'id': current_folder.id,
                'title': current_folder.title,
                'parent_folder': current_folder.parent_folder.id if current_folder.parent_folder else None,
                'type': 'folder',
            })
            current_folder = current_folder.parent_folder

        # Add chapter, subject, course
        if self.chapter:
            breadcrumbs.append({
                'id': self.chapter.id,
                'title': self.chapter.chapter_name,
                'type': 'chapter',
            })
            if self.chapter.subject:
                breadcrumbs.append({
                    'id': self.chapter.subject.id,
                    'title': self.chapter.subject.subject_name,
                    'type': 'subject',
                })
                if self.chapter.subject.course:
                    breadcrumbs.append({
                        'id': self.chapter.subject.course.id,
                        'title': self.chapter.subject.course.course_name,
                        'type': 'course',
                    })

        breadcrumbs.reverse()
        return breadcrumbs



class Lesson(models.Model):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        tmp = get_random_string()
        filename = "%s.%s" % (tmp, ext)
        return os.path.join("lesson_images", filename)
    
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE,  null=True, blank=True ,related_name='lessons')
    lesson_name = models.CharField(max_length=200)
    image = models.ImageField(upload_to=get_file_path, null=True, blank=True)
    description = models.TextField()
    visible_in_days = models.IntegerField(default=0) 
    is_free = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    old_id = models.IntegerField(default=0)
    order = models.IntegerField(default=0)
    
    def __str__(self):
        return self.lesson_name  or 'No title'
    


class CurrentAffairs(models.Model):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        tmp = get_random_string()
        filename = "%s.%s" % (tmp, ext)
        return os.path.join("currentaffairs_images", filename)
    
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to=get_file_path, null=True, blank=True)
    is_free = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    old_id = models.IntegerField(default=0)

    def __str__(self):
        return self.title or 'No title'     

class Video(models.Model):
    lesson = models.ForeignKey(Lesson,null=True,blank=True, on_delete=models.CASCADE, related_name='videos')
    currentaffair = models.ForeignKey(CurrentAffairs,null=True,blank=True, on_delete=models.CASCADE, related_name='currentaffair_videos')
    title = models.CharField(max_length=200)
    url = models.CharField(max_length=150, null=True,blank=True)
    is_downloadable = models.BooleanField(default=False)
    is_free = models.BooleanField(default=False)

    current_affair = models.BooleanField(default=False)
    m3u8 = models.CharField(max_length=150, null=True,blank=True)
    m3u8_is_downloadable = models.BooleanField(default=False)
    m3u8_is_free = models.BooleanField(default=False)
    # is_m3u8=models.BooleanField(default=False)
    tp_stream = models.CharField(max_length=150, null=True,blank=True)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    old_id = models.IntegerField(default=0)

    def __str__(self):
        return self.title  or 'No title'

    

class PDFNote(models.Model):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        tmp = get_random_string()
        filename = "%s.%s" % (tmp, ext)
        return os.path.join("pdf_notes", filename)
    
    lesson = models.ForeignKey(Lesson,null=True,blank=True, on_delete=models.CASCADE, related_name='pdf_notes')
    currentaffair = models.ForeignKey(CurrentAffairs,null=True,blank=True, on_delete=models.CASCADE, related_name='currentaffair_pdf_notes')
    
    title = models.CharField(max_length=255, blank=True, null=True)
    file = models.FileField(upload_to=get_file_path)
    is_downloadable = models.BooleanField(default=False)
    is_free = models.BooleanField(default=False)
    current_affair = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    old_id = models.IntegerField(default=0)

    def __str__(self):
        return self.title  or 'No title'

class Comment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='comments', blank=True, null=True)
    pdf_note = models.ForeignKey(PDFNote, on_delete=models.CASCADE, related_name='comments', blank=True, null=True)
    content = models.TextField()
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)


    def __str__(self):
        return f"Comment by {self.user.name}"
    

class CommentReaction(models.Model):
    REACTION_CHOICES = (
        ('LIKE', 'Like'),
        ('DISLIKE', 'Dislike'),
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reactions')
    reaction = models.CharField(max_length=7, choices=REACTION_CHOICES)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'comment')

    def __str__(self):
        return f"{self.user.name} {self.reaction}d comment by {self.comment.user.name}"

class Like(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='likes', blank=True, null=True)
    pdf_note = models.ForeignKey(PDFNote, on_delete=models.CASCADE, related_name='likes', blank=True, null=True)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'video', 'pdf_note') 

    def __str__(self):
        if self.video:
            return f"{self.user.name} liked video: {self.video.title}"
        elif self.pdf_note:
            return f"{self.user.name} liked PDF: {self.pdf_note.title}"

class TalentHunt(models.Model):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        tmp = get_random_string()
        filename = "%s.%s" % (tmp, ext)
        return os.path.join("talenthunt_images", filename)
    
    title = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to=get_file_path, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    # subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    is_free = models.BooleanField(default=True)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    old_id = models.IntegerField(default=0)

    def __str__(self):
        return self.title or 'No title'
    
class TalentHuntSubject(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    talentHunt = models.ForeignKey(TalentHunt, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    is_free = models.BooleanField(default=True)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.title or 'No title'
    
class Level(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    number = models.IntegerField( blank=True, null=True)
    duration = models.TimeField(null=True, blank=True)
    talenthuntsubject = models.ForeignKey(TalentHuntSubject, on_delete=models.SET_NULL, null=True, blank=True)
    is_free = models.BooleanField(default=True)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.title or 'No title'
    



class Exam(models.Model):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        tmp = get_random_string()
        filename = "%s.%s" % (tmp, ext)
        return os.path.join("exam_images", filename)
    
    EXAM_TYPE_CHOICES = (
        ('Daily', 'Daily'),
        ('Weekly', 'Weekly'),
        ('Monthly', 'Monthly'),
        ('Model', 'Model'),
        ('Live', 'Live'),
    )
    
    title = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to=get_file_path, null=True, blank=True)
    number_of_attempt = models.IntegerField(default=1)
    duration = models.TimeField(null=True, blank=True)
    exam_type = models.CharField(max_length=255, blank=True, null=True, choices=EXAM_TYPE_CHOICES)
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True)
    chapter = models.ForeignKey('Chapter', on_delete=models.SET_NULL, null=True, blank=True)
    folder = models.ForeignKey('Folder', on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True,related_name='exams')
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True)
    current_affair = models.ForeignKey(CurrentAffairs, on_delete=models.SET_NULL, null=True, blank=True)
    is_free = models.BooleanField(default=True)
    created = models.DateTimeField(default=timezone.now)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    is_shuffle = models.BooleanField(default=False)
    old_id = models.IntegerField(default=0)
    
    def __str__(self):
        return self.title or 'No title'

class Question(models.Model):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        tmp = get_random_string()
        filename = "%s.%s" % (tmp, ext)
        return os.path.join("explanation_images", filename)
    
    
    QUESTION_TYPES = (
        (1, 'Text'),
        (2, 'Image'),
        (3, 'Multiple Choice'),
    )
  
    question_type = models.PositiveIntegerField(choices=QUESTION_TYPES, default=1)
    question_description = RichTextField()
    hint = models.TextField(null=True, blank=True)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    options = models.JSONField(default=list, null=True, blank=True)
    right_answers = models.JSONField(default=list, null=True, blank=True)  
    master_question = models.IntegerField(null=True, blank=True)
    mark = models.IntegerField(default=1,null=True, blank=True)
    negative_mark = models.IntegerField(null=True, blank=True)
    explanation_description = models.CharField( null=True, blank=True)
    explanation_image = models.ImageField(upload_to=get_file_path, null=True, blank=True)
    exam = models.ForeignKey(Exam, on_delete=models.SET_NULL, null=True, blank=True)
    chapter = models.ForeignKey(Chapter, on_delete=models.SET_NULL, null=True, blank=True)
    talenthunt = models.ForeignKey(TalentHunt, on_delete=models.SET_NULL, null=True, blank=True)
    level=models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    old_id = models.IntegerField(default=0)
    
    def __str__(self):
        return self.question_description or 'No question type'



class Schedule(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True)
    exam = models.ForeignKey(Exam, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.title or 'No title'
    


class Banner(models.Model):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        tmp = get_random_string()
        filename = "%s.%s" % (tmp, ext)
        return os.path.join("banner_images", filename)
    
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to=get_file_path)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.title or 'No title'

    # class Meta:
    #     ordering = [ '-created']



class StudentProgress(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='progress',null=True, blank=True)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='student_exams',null=True, blank=True)
    talenthunt = models.ForeignKey(TalentHunt, on_delete=models.CASCADE, related_name='student_talentHunt',null=True, blank=True)
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='student_level',null=True, blank=True)
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    total_marks = models.DecimalField(max_digits=5, decimal_places=2)
    passed = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.name}'s progress "
    
class StudentProgressDetail(models.Model):
    student_progress = models.ForeignKey(StudentProgress, on_delete=models.CASCADE, related_name='details')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.JSONField(default=list, null=True, blank=True) 
    is_correct = models.BooleanField()
    answered=models.BooleanField(default=True)
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2 ,null=True, blank=True)
    negative_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    time_taken = models.CharField(max_length=10, null=True, blank=True)  # Store time in MM:SS format
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Result for question {self.student_progress.id} in {self.student_progress.student.username}"
    

class BatchLesson(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE,null=True, blank=True)
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE,null=True, blank=True)
    visible_in_days = models.IntegerField(default=0) 
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    



class TempUser(models.Model):
    username = models.CharField(max_length=150)
    old_id = models.IntegerField(default=0)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=50)
    email = models.EmailField(null=True, blank=True, max_length=50)
    verified = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)  
    
    def __str__(self):
        if self.name:
            return self.name
        else:
            return self.username


class Otp(models.Model):
    code = models.IntegerField(default=0)
    old_id = models.IntegerField(default=0)
    request_id = models.CharField(max_length=20)
    requested_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, null=True, blank=True
    )
    temp_user = models.ForeignKey(
        TempUser, on_delete=models.CASCADE, null=True, blank=True
    )
    verified = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)




class Notification(models.Model):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        tmp = get_random_string()
        filename = "%s.%s" % (tmp, ext)
        return os.path.join("notification_images", filename)
    
    NOTIFICATION_TYPE_CHOICES = (
        ('all', 'All Users'),
        ('course', 'Course-wise'),
        ('batch', 'Batch-wise'),
        ('student', 'Selected Students'),
    )
    
    image = models.ImageField(upload_to=get_file_path, null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES, default='all')
    courses = models.ManyToManyField(Course, blank=True, related_name='notifications')
    batches = models.ManyToManyField(Batch, blank=True, related_name='notifications')
    installments = models.ForeignKey(FeeInstallment, null=True, blank=True, on_delete=models.CASCADE, related_name='installment_notifications')
    url = models.CharField(max_length=255, null=True, blank=True)
    students = models.ManyToManyField(CustomUser, blank=True, related_name='targeted_notifications')
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    
    
    def __str__(self):
        return self.title or 'No title'
        
class StudentNotification(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.student.username} - {self.notification.title}'
    

class Report(models.Model):
    question = models.ForeignKey(Question,null=True,blank=True, on_delete=models.CASCADE)  
    student = models.ForeignKey(CustomUser,null=True,blank=True, on_delete=models.CASCADE)   
    content = models.CharField(null=True,blank=True)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.student.username} - {self.content}'


class VideoPause(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='video_progress')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='progress')
    minutes_watched = models.TimeField(default='00:00:00')
    total_duration = models.TimeField(default='00:00:00')
    last_updated = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username} - {self.video.title} - {self.minutes_watched} min"


class VideoRating(models.Model):
    """Model for storing video ratings from students"""
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='video_ratings')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('student', 'video')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.username} rated {self.video.title}: {self.rating}/5"


class LiveClass(models.Model):
    PLATFORM_CHOICES = (
        ('google_meet', 'Google Meet'),
        ('zoom', 'Zoom'),
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='google_meet')
    meeting_url = models.URLField(max_length=500)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    old_id = models.IntegerField(default=0)

    

class BatchLiveClass(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True, blank=True, related_name='batch_live_classes')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name='course_live_classes')
    live_class = models.ForeignKey(LiveClass, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)


class BatchMentor(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True, blank=True, related_name='batch_mentors')
    mentor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='mentor_batches')
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    



class Slot(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE,null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE,null=True, blank=True)
    date = models.DateField()
    total_slots = models.PositiveIntegerField(default=1)
    available_sessions = models.PositiveIntegerField(default=1)
    created = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Slot for {self.subject.subject_name} "


class Booking(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bookings')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE,null=True, blank=True)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE,null=True, blank=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE,null=True, blank=True)
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Booking by {self.user.username} for {self.subject.subject_name} on {self.created} "


