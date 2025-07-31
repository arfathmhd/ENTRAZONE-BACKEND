from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(CustomUser)
admin.site.register(Batch)
admin.site.register(Course)
admin.site.register(Subject)
admin.site.register(Chapter)
admin.site.register(Lesson)
admin.site.register(Video)
admin.site.register(PDFNote)
admin.site.register(Like)
admin.site.register(Exam)
admin.site.register(Question)
admin.site.register(TalentHunt)
admin.site.register(TalentHuntSubject)
admin.site.register(Level) 
admin.site.register(Schedule) 
admin.site.register(CommentReaction) 



# admin.site.register(SuccessStory) 
admin.site.register(Folder) 
admin.site.register(BatchLesson) 
admin.site.register(TempUser) 
admin.site.register(Otp) 
admin.site.register(Notification) 
admin.site.register(StudentNotification) 
admin.site.register(Banner) 
admin.site.register(Report)
admin.site.register(CurrentAffairs)

admin.site.register(StudentProgressDetail)
admin.site.register(StudentProgress)

admin.site.register(Slot)
admin.site.register(Booking)

@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'webhook_id', 'order_id', 'event_type', 'status', 'signature_valid', 'created', 'webhook_date', 'ip_address')
    list_filter = ('status', 'signature_valid', 'created', 'event_type')
    search_fields = ('order_id', 'event_type', 'error_message', 'request_data')
    readonly_fields = ('created', 'webhook_id', 'webhook_date', 'order_id', 'event_type', 'transaction', 
                       'request_data', 'headers', 'ip_address', 'signature_valid', 'status', 'error_message')
    date_hierarchy = 'created'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        # Allow viewing but not editing
        return True
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete webhook logs
        return request.user.is_superuser


@admin.register(VideoRating)
class VideoRatingAdmin(admin.ModelAdmin):
    list_display = ('student', 'video', 'rating', 'comment', 'created_at')
    list_filter = ('student', 'video', 'rating')
    search_fields = ('student', 'video')
   

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'video', 'pdf_note', 'content', 'is_reply', 'created')
    list_filter = ('user', 'video', 'pdf_note', 'parent_comment')
    search_fields = ('user__name', 'content', 'video__title', 'pdf_note__title')
    
    def is_reply(self, obj):
        return 'Yes' if obj.parent_comment else 'No'
    
    is_reply.short_description = 'Is Reply'

@admin.register(LiveClass)
class LiveClassAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'platform', 'meeting_url', 'start_time', 'end_time', 'created')
    list_filter = ('platform', 'is_active')
    search_fields = ('title', 'description', 'meeting_url')
    

@admin.register(BatchLiveClass)
class BatchLiveClassAdmin(admin.ModelAdmin):
    list_display = ('batch', 'live_class', 'created')
    list_filter = ('batch', 'live_class')
    search_fields = ('batch', 'live_class')


@admin.register(BatchMentor)
class BatchMentorAdmin(admin.ModelAdmin):
    list_display = ('batch', 'mentor', 'created')
    list_filter = ('batch', 'mentor')
    search_fields = ('batch', 'mentor')

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'created')
    list_filter = ('user',)
    search_fields = ('user',)

@admin.register(FeeInstallment)
class FeeInstallmentAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'amount_due', 'due_date', 'status', 'created')
    list_filter = ('subscription', 'status')
    search_fields = ('subscription', 'status')

@admin.register(FeePaymentPlan)
class FeePaymentPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'total_amount', 'number_of_installments', 'discount', 'created')
    list_filter = ('name',)
    search_fields = ('name',)

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('installment', 'transaction_id', 'transaction_uuid', 'order_id', 'amount', 'currency', 'status', 'created')
    list_filter = ('installment', 'status')
    search_fields = ('installment', 'status')

@admin.register(HDFCPaymentConfig)
class HDFCPaymentConfigAdmin(admin.ModelAdmin):
    list_display = ('merchant_id', 'is_production', 'webhook_url', 'is_active', 'created')
    list_filter = ('is_active', 'is_production', 'created')
    search_fields = ('merchant_id', 'access_code', 'webhook_url')
    
    fieldsets = (
        ('Gateway Configuration', {
            'fields': ('merchant_id', 'access_code', 'working_key', 'api_key', 'payment_page_client_id', 'is_production')
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_url', 'webhook_username', 'webhook_password', 'webhook_secret', 'webhook_custom_headers')
        }),
        ('Status', {
            'fields': ('is_active', 'is_deleted', 'created', 'updated')
        }),
    )
    readonly_fields = ('created', 'updated')


