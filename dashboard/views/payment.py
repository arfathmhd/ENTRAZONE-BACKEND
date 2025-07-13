import uuid
import json
import logging
import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q, F
from django.core.paginator import Paginator
from dashboard.forms.customer import PaymentPlanForm
from dashboard.views.customer import create_installments_for_plan

from dashboard.models import (
    CustomUser, 
    Batch, 
    Subscription, 
    FeePaymentPlan, 
    FeeInstallment,
    HDFCPaymentConfig,
    PaymentTransaction,
    WebhookLog
)

# Import SmartGateway functions
from dashboard.views.smartgateway import generate_smartgateway_payment_link, handle_smartgateway_callback

logger = logging.getLogger(__name__)

# Payment Dashboard Views
@login_required
def payment_dashboard(request):
    """Admin dashboard for payment management"""
    # Get payment statistics
    total_due = FeeInstallment.objects.filter(is_paid=False).aggregate(total=Sum('amount_due'))['total'] or 0
    total_paid = FeeInstallment.objects.filter(is_paid=True).aggregate(total=Sum('amount_due'))['total'] or 0
    total_overdue = FeeInstallment.objects.filter(status='OVERDUE').aggregate(total=Sum('amount_due'))['total'] or 0
    
    # Get recent transactions
    recent_transactions = PaymentTransaction.objects.filter(
        is_deleted=False
        ).order_by('-created')
    
    # Get pending installments
    pending_installments = FeeInstallment.objects.filter(
        is_paid=False,
        due_date__lte=timezone.now() + timedelta(days=3)
    ).order_by('due_date')
    
    # Get payment gateway config
    try:
        payment_config = HDFCPaymentConfig.objects.filter(is_active=True).first()
        payment_gateway_configured = payment_config is not None
    except:
        payment_gateway_configured = False
    
    context = {
        'total_due': total_due,
        'total_paid': total_paid,
        'total_overdue': total_overdue,
        'recent_transactions': recent_transactions,
        'pending_installments': pending_installments,
        'payment_gateway_configured': payment_gateway_configured
    }
    
    return render(request, 'dashboard/payment/dashboard.html', context)

@login_required
def payment_config(request):
    """Manage payment gateway configuration"""
    config = HDFCPaymentConfig.objects.filter(is_active=True).first()
    
    if request.method == 'POST':
        merchant_id = request.POST.get('merchant_id')
        gateway_type = request.POST.get('gateway_type', 'HYPERCHECKOUT')
        is_production = request.POST.get('is_production') == 'on'
        webhook_secret = request.POST.get('webhook_secret')
        
        # Get gateway-specific fields
        access_code = request.POST.get('access_code')
        working_key = request.POST.get('working_key')
        api_key = request.POST.get('api_key')
        payment_page_client_id = request.POST.get('payment_page_client_id')
        
        logger.info(f"Updating payment gateway config: type={gateway_type}, production={is_production}")
        
        if config:
            # Update existing config
            config.merchant_id = merchant_id
            config.gateway_type = gateway_type
            config.is_production = is_production
            config.webhook_secret = webhook_secret
            
            # Update gateway-specific fields
            if gateway_type == 'HYPERCHECKOUT':
                config.access_code = access_code
                if working_key:  # Only update if provided
                    config.working_key = working_key
            else:  # SMARTGATEWAY
                config.api_key = api_key
                config.payment_page_client_id = payment_page_client_id
            
            config.save()
            logger.info(f"Updated existing payment gateway config ID: {config.id}")
        else:
            # Create new config with appropriate fields
            config_data = {
                'merchant_id': merchant_id,
                'gateway_type': gateway_type,
                'is_production': is_production,
                'webhook_secret': webhook_secret
            }
            
            # Add gateway-specific fields
            if gateway_type == 'HYPERCHECKOUT':
                config_data.update({
                    'access_code': access_code,
                    'working_key': working_key
                })
            else:  # SMARTGATEWAY
                config_data.update({
                    'api_key': api_key,
                    'payment_page_client_id': payment_page_client_id
                })
            
            # Create new config
            config = HDFCPaymentConfig.objects.create(**config_data)
            logger.info(f"Created new payment gateway config ID: {config.id}")
        
        messages.success(request, 'Payment gateway configuration updated successfully')
        return redirect('dashboard-payment-config')
    
    return render(request, 'dashboard/payment/config.html', {'config': config})

@login_required
def installment_list(request):
    """List all installments with filters"""
    # Get filter parameters
    status_values = request.GET.getlist('status')
    student_id = request.GET.get('student_id')
    batch_id = request.GET.get('batch_id')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset
    installments = FeeInstallment.objects.filter(
        is_deleted=False,
        subscription__is_deleted=False,
        subscription__user__is_deleted=False,
        subscription__user__is_active=True,
        subscription__user__user_type=0
        ).select_related('subscription__user')
    
    # Apply filters
    if status_values:
        installments = installments.filter(status__in=status_values)
    if student_id:
        installments = installments.filter(subscription__user_id=student_id)
    if batch_id:
        # Since batch is a ManyToManyField in Subscription, we need to filter differently
        # Use a subquery to get subscriptions that have this batch
        subscriptions_with_batch = Subscription.objects.filter(batch__id=batch_id).values_list('id', flat=True)
        installments = installments.filter(subscription_id__in=subscriptions_with_batch)
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            installments = installments.filter(due_date__gte=date_from)
        except ValueError:
            pass
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            installments = installments.filter(due_date__lte=date_to)
        except ValueError:
            pass
    
    # Order by due date
    installments = installments.order_by('due_date')
    
    # Pagination
    paginator = Paginator(installments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all active students for the dropdown
    students = CustomUser.objects.filter(is_active=True,is_deleted=False,user_type=0).order_by('name')
    
    # Get all active batches for the dropdown
    batches = Batch.objects.filter(is_deleted=False).order_by('batch_name')
    
    context = {
        'page_obj': page_obj,
        'students': students,
        'batches': batches,
        'filters': {
            'status': status_values,
            'student_id': student_id,
            'batch_id': batch_id,
            'date_from': date_from,
            'date_to': date_to
        }
    }
    
    return render(request, 'dashboard/payment/installment_list.html', context)


@login_required
def generate_payment_link(request, installment_id):
    """Generate payment link for an installment"""
    installment = get_object_or_404(FeeInstallment, id=installment_id)
    
    if request.method == 'POST':
        # Generate or regenerate payment link
        base_url = request.build_absolute_uri('/')[:-1]  # Get base URL without trailing slash
        payment_link = installment.generate_payment_link(base_url)
        
        # Check if notification should be sent
        send_notification = request.POST.get('send_notification') == 'on'
        
        # TODO: if send_notification and payment_link:
        if False:
            student = installment.subscription.user
            user_ids = [str(student.phone_number)]  # Convert to string as OneSignal expects string IDs
            
            # Format the amount with 2 decimal places
            amount = f'₹{installment.amount_due:.2f}'
            
            # Send notification via OneSignal
            notification_result = onesignal_request(
                heading=f'Payment Reminder: {amount}',
                content=f'Please complete your pending payment of {amount}',
                url=payment_link,
                user_ids=user_ids
            )
            
            if notification_result and 'id' in notification_result:
                notification, created = Notification.objects.create_or_update(
                    title=f'Payment Reminder: {amount}',
                    message=f'Please complete your pending payment of {amount}',
                    notification_type='payment',
                    installments=installment,
                    students=student,
                    url=payment_link
                )
                
                StudentNotification.objects.create(
                    student=student,
                    notification=notification,
                )
                messages.success(request, f'Payment link generated and notification sent successfully!')
            else:
                messages.warning(request, f'Payment link generated but notification could not be sent.')
        else:
            messages.success(request, f'Payment link generated successfully!')
            
        return redirect('dashboard-installment-detail', pk=installment_id)
    
    return render(request, 'dashboard/payment/generate_link.html', {'installment': installment})

@login_required
def installment_detail(request, pk):
    """View installment details including payment history"""
    installment = get_object_or_404(FeeInstallment, id=pk)
    transactions = PaymentTransaction.objects.filter(installment=installment).order_by('-created')
    
    
    context = {
        'installment': installment,
        'transactions': transactions,
        'subscription': installment.subscription,
        'student': installment.subscription.user,
        'batch': installment.subscription.batch.first()
    }
    
    return render(request, 'dashboard/payment/installment_detail.html', context)


@login_required
def send_payment_notification(request):
    """Send payment notification with payment link"""
    if request.method == 'POST':
        installment_id = request.POST.get('installment_id')
        payment_link = request.POST.get('payment_link')
        amount = request.POST.get('amount')
        student_id = request.POST.get('student_id')
        
        if not all([installment_id, payment_link, student_id, amount]):
            return JsonResponse({'success': False, 'message': 'Missing required parameters'}, status=400)
        
        try:
            installment = FeeInstallment.objects.get(id=installment_id)
            
            # Send notification via OneSignal
            from dashboard.utils.onesignal import onesignal_request
            student = get_object_or_404(CustomUser, id=student_id)
            user_ids = [str(student.phone_number)]  # Convert to string as OneSignal expects string IDs
            
            notification_result = onesignal_request(
                heading=f'Payment Reminder: ₹{amount}',
                content=f'Please complete your pending payment of ₹{amount}',
                url=payment_link,
                user_ids=user_ids
            )
            
            if notification_result and 'id' in notification_result:
                notification, created = Notification.objects.create_or_update(
                    title=f'Payment Reminder: ₹{amount}',
                    message=f'Please complete your pending payment of ₹{amount}',
                    notification_type='payment',
                    installments=installment,
                    students=student,
                    url=payment_link
                )
                StudentNotification.objects.create(
                    student=student,
                    notification=notification,
                )
                return JsonResponse({
                    'success': True, 
                    'message': 'Notification sent successfully',
                    'notification_id': notification_result['id']
                })
            else:
                return JsonResponse({
                    'success': False, 
                    'message': 'Failed to send notification',
                    'error': notification_result.get('error', 'Unknown error')
                }, status=500)
                
        except FeeInstallment.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Installment not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

@login_required
def subscription_detail(request, pk):
    """View subscription details with all installments"""
    subscription = get_object_or_404(Subscription, id=pk)
    installments = FeeInstallment.objects.filter(subscription=subscription).order_by('due_date')

    # Update payment totals to ensure they're current
    subscription.update_payment_totals()
    
    # Get available payment plans for the modal form
    payment_plans = FeePaymentPlan.objects.filter(is_deleted=False)
    
    context = {
        'subscription': subscription,
        'installments': installments,
        'student': subscription.user,
        'batches': subscription.batch.all(),
        'payment_plans': payment_plans
    }
    
    return render(request, 'dashboard/payment/subscription_detail.html', context)


@login_required
def add_payment_plan_to_subscription(request, subscription_id):
    """Add a payment plan to an existing subscription"""
    subscription = get_object_or_404(Subscription, id=subscription_id)
    
    if request.method == 'POST':
        # Use the PaymentPlanForm for validation
        form = PaymentPlanForm(request.POST)
        
        if form.is_valid():
            payment_plan_type = form.cleaned_data['payment_plan_type']
            
            if payment_plan_type == 'existing':
                # Use existing payment plan
                payment_plan = form.cleaned_data.get('existing_plan')
                if payment_plan:
                    # Associate the payment plan with the subscription
                    subscription.payment_plan = payment_plan
                    subscription.save()
                    messages.success(request, f"Payment plan '{payment_plan.name}' added to subscription successfully.")
                else:
                    messages.error(request, "Please select an existing payment plan.")
            elif payment_plan_type == 'new':
                try:
                    # Create the payment plan using form data
                    payment_plan = FeePaymentPlan.objects.create(
                        name=form.cleaned_data['plan_name'],
                        total_amount=form.cleaned_data['total_amount'],
                        discount=form.cleaned_data['discount'] or Decimal('0.00'),
                        number_of_installments=form.cleaned_data['number_of_installments'],
                        frequency=form.cleaned_data['installment_frequency']
                    )
                    
                    # Associate the payment plan with the subscription
                    subscription.payment_plan = payment_plan
                    subscription.save()
                    
                    # Create installments
                    create_installments_for_plan(payment_plan, subscription)
                    
                    messages.success(request, f"New payment plan '{payment_plan.name}' created and added to subscription successfully.")
                except Exception as e:
                    messages.error(request, f"Error creating payment plan: {str(e)}")
        else:
            # Form validation failed
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    return redirect('dashboard-subscription-detail', pk=subscription_id)

@login_required
def mark_as_paid(request, installment_id):
    """Manually mark an installment as paid"""
    installment = get_object_or_404(FeeInstallment, id=installment_id)
    
    if request.method == 'POST':
        reference = request.POST.get('reference', str(uuid.uuid4().hex[:8]))
        
        with transaction.atomic():
            # Mark installment as paid
            installment.mark_as_paid(reference=reference)
            
            # Create transaction record
            PaymentTransaction.objects.create(
                installment=installment,
                order_id=f"MANUAL-{uuid.uuid4().hex[:8]}",
                transaction_id=None,
                amount=installment.amount_due,
                status='SUCCESS',
                payment_mode='MANUAL',
                gateway_response={'method': 'manual', 'user': request.user.username}
            )
            
            # Update subscription totals
            installment.subscription.update_payment_totals()
            installment.subscription.last_payment_date = timezone.now()
            installment.subscription.save()
        
        messages.success(request, f'Installment of ₹{installment.amount_due} marked as paid successfully')
        return redirect('dashboard-installment-detail', pk=installment_id)
    
    return render(request, 'dashboard/payment/mark_paid.html', {'installment': installment})

# Payment Processing Views
def payment_redirect(request, uuid):
    """Handle payment redirect with shareable link"""
    try:
        installment = get_object_or_404(FeeInstallment, payment_link_uuid=uuid)
        
        # Check if link is expired
        if installment.payment_link_expires and installment.payment_link_expires < timezone.now():
            return render(request, 'dashboard/payment/link_expired.html', {'installment': installment})
        
        # Check if already paid
        if installment.is_paid:
            return render(request, 'dashboard/payment/already_paid.html', {'installment': installment})
        
        # Get payment gateway config
        config = HDFCPaymentConfig.objects.filter(is_active=True).first()
        if not config:
            return render(request, 'dashboard/payment/gateway_error.html', 
                         {'error': 'Payment gateway not configured'})
        
        # Get student and subscription details
        student = installment.subscription.user
        subscription = installment.subscription
        batches = subscription.batch.all()
        
        logger.info(f"Processing payment for student: {student.id}, installment: {installment.id}, amount: {installment.amount_due}")
        
        # Check if there's an existing transaction for this installment
        transaction = PaymentTransaction.objects.filter(
            installment=installment,
            status='INITIATED',
        ).order_by('-created').first()
        
        # For SmartGateway, check if we have an active payment link
        if config:
            if transaction and transaction.payment_link and not transaction.is_expired():
                # Return the redirect template with auto-redirect
                return render(request, 'dashboard/payment/smartgateway_redirect.html', {
                    'payment_link': transaction.payment_link,
                    'meta_title': f"Pay ₹{installment.amount_due} - Sahakari",
                    'meta_description': f"Fee payment for {student.name}"
                })
            else:
                # Generate new payment link
                result = generate_smartgateway_payment_link(installment, config)
                
                if result['success']:
                    # Return the redirect template with auto-redirect
                    return render(request, 'dashboard/payment/smartgateway_redirect.html', {
                        'payment_link': result['payment_link'],
                        'meta_title': f"Pay ₹{installment.amount_due} - Sahakari",
                        'meta_description': f"Fee payment for {student.name}"
                    })
                else:
                    return render(request, 'dashboard/payment/gateway_error.html', 
                                {'error': f'Failed to generate payment link: {result["error"]}'})        
            
    except Exception as e:
        print(f"Payment redirect error: {str(e)}")
        return render(request, 'dashboard/payment/gateway_error.html', {'error': str(e)})


@csrf_exempt
@require_POST
def payment_callback(request):
    """Handle payment gateway callback"""
    logger.info("Payment callback received")
    
    # Get payment gateway config
    config = HDFCPaymentConfig.objects.filter(is_active=True).first()
    if not config:
        return render(request, 'dashboard/payment/gateway_error.html', {
                    'error': f"Payment gateway not configured"
                })
    
    try:
        # SmartGateway callback
        return handle_smartgateway_callback(request, config)
            
    except Exception as e:
        return render(request, 'dashboard/payment/gateway_error.html', {
                    'error': f"Error processing payment response: {str(e)}"
                })

def payment_success(request, transaction_id):
    """Show payment success page"""
    transaction = get_object_or_404(PaymentTransaction, transaction_uuid=transaction_id)
    
    context = {
        'transaction': transaction,
        'installment': transaction.installment,
        'student': transaction.installment.subscription.user
    }
    
    return render(request, 'dashboard/payment/success.html', context)

def payment_failure(request, transaction_id):
    """Show payment failure page"""
    transaction = get_object_or_404(PaymentTransaction, transaction_uuid=transaction_id)
    
    context = {
        'transaction': transaction,
        'installment': transaction.installment,
        'student': transaction.installment.subscription.user,
        'error_message': transaction.gateway_response.get('status_message', 'Payment failed')
    }
    
    return render(request, 'dashboard/payment/failure.html', context)

def payment_cancel(request, transaction_id):
    """Handle payment cancellation"""
    transaction = get_object_or_404(PaymentTransaction, transaction_uuid=transaction_id)
    
    # Update transaction status
    transaction.status = 'CANCELLED'
    transaction.save()
    
    context = {
        'transaction': transaction,
        'installment': transaction.installment
    }
    
    return render(request, 'dashboard/payment/cancelled.html', context)


# SmartGateway production and sandbox IPs as per documentation
SMARTGATEWAY_PRODUCTION_IPS = [
    '13.126.232.13',
    '35.154.93.248',
    '65.2.117.44',
    '3.110.250.172'
]

SMARTGATEWAY_SANDBOX_IPS = [
    '52.221.151.249',
    '13.228.4.195',
    '13.234.141.165',
    '3.111.27.22',
    '3.109.41.51',
    '13.235.85.36',
    '3.6.2.61'
]

@csrf_exempt
@require_POST
def payment_webhook(request):
    """Handle asynchronous payment gateway webhook from SmartGateway"""
    # Create a webhook log entry to record the request
    webhook_log = WebhookLog(
        request_data=json.loads(request.body) if request.body else {},
        headers={k: v for k, v in request.headers.items()},
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    config = HDFCPaymentConfig.objects.filter(is_active=True).first()
    if not config:
        webhook_log.status = 'FAILED'
        webhook_log.error_message = "Payment gateway not configured"
        webhook_log.save()
        return JsonResponse({"status": "error", "message": "Payment gateway not configured"}, status=500)
    
    # Validate IP address if not in development mode
    if not settings.DEBUG:
        client_ip = request.META.get('REMOTE_ADDR')
        allowed_ips = SMARTGATEWAY_PRODUCTION_IPS if config.is_production else SMARTGATEWAY_SANDBOX_IPS
        
        if client_ip not in allowed_ips:
            webhook_log.status = 'INVALID'
            webhook_log.error_message = f"Invalid IP address: {client_ip}"
            webhook_log.save()
            logger.warning(f"Webhook received from unauthorized IP: {client_ip}")
            # Still return 200 as per SmartGateway requirements
            return JsonResponse({"status": "success", "message": "Webhook received"})
    
    # Verify Basic Authentication as per SmartGateway requirements
    auth_header = request.headers.get('Authorization', '')
    if config.webhook_username and config.webhook_password:
        if not auth_header.startswith('Basic '):
            webhook_log.status = 'INVALID'
            webhook_log.error_message = "Missing Basic Authentication"
            webhook_log.save()
            return JsonResponse({"status": "error", "message": "Authentication required"}, status=401)
        
        # Extract and decode the base64 credentials
        try:
            encoded_credentials = auth_header.split(' ')[1]
            decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            username, password = decoded_credentials.split(':')
            
            if username != config.webhook_username or password != config.webhook_password:
                webhook_log.status = 'INVALID'
                webhook_log.error_message = "Invalid credentials"
                webhook_log.save()
                return JsonResponse({"status": "error", "message": "Invalid credentials"}, status=403)
        except Exception as e:
            webhook_log.status = 'INVALID'
            webhook_log.error_message = f"Authentication error: {str(e)}"
            webhook_log.save()
            return JsonResponse({"status": "error", "message": "Authentication error"}, status=401)
    
    # Verify custom headers if configured
    if config.webhook_custom_headers:
        for header_name, header_value in config.webhook_custom_headers.items():
            if request.headers.get(header_name) != header_value:
                webhook_log.status = 'INVALID'
                webhook_log.error_message = f"Missing or invalid custom header: {header_name}"
                webhook_log.save()
                return JsonResponse({"status": "error", "message": "Invalid headers"}, status=403)
    
    # Note: Based on observed behavior, SmartGateway webhooks don't include signatures
    # But we'll check the payload for a signature just in case
    try:
        data = json.loads(request.body) if request.body else {}
        signature_valid = None
        
        # Only verify signature if it's included in the payload and we have a webhook_secret
        if 'signature' in data and config.webhook_secret:
            received_signature = data.get('signature', '')
            signature_algorithm = data.get('signature_algorithm', 'HMAC-SHA256')
            
            # Create payload for signature validation by removing the signature itself
            validation_data = {k: v for k, v in data.items() if k != 'signature'}
            
            # Sort the keys alphabetically as per HDFC documentation
            sorted_data = {k: validation_data[k] for k in sorted(validation_data.keys())}
            
            # Convert to string format required by HDFC
            payload_string = '&'.join([f"{k}={v}" for k, v in sorted_data.items()])
            
            # Calculate expected signature using HMAC-SHA256
            key = config.webhook_secret.encode('utf-8')
            message = payload_string.encode('utf-8')
            
            if signature_algorithm == 'HMAC-SHA256':
                expected_signature = base64.b64encode(
                    hmac.new(key, message, digestmod=hashlib.sha256).digest()
                ).decode('utf-8')
                
                signature_valid = (received_signature == expected_signature)
                webhook_log.signature_valid = signature_valid
                
                if not signature_valid:
                    webhook_log.status = 'INVALID'
                    webhook_log.error_message = "Invalid signature"
                    webhook_log.save()
                    # Still return 200 as per SmartGateway requirements
                    return JsonResponse({"status": "success", "message": "Webhook received"})
        else:
            # No signature in payload, which is expected for standard webhooks
            webhook_log.signature_valid = None
    except Exception as e:
        logger.error(f"Error checking signature: {str(e)}")
        webhook_log.signature_valid = None
    
    try:
        # Parse webhook payload
        data = json.loads(request.body)
        order_id = ''
        
        # Extract webhook metadata according to SmartGateway standard structure
        webhook_id = data.get('id', '')
        date_created = data.get('date_created', '')
        event_name = data.get('event_name', '')
        
        # For backward compatibility, also check event_type
        event_name = event_name or data.get('event_type', '')
        
        # Log the webhook metadata
        webhook_log.event_type = event_name
        webhook_log.webhook_id = webhook_id
        
        # Handle date_created - convert to datetime object if it's a string
        if date_created:
            try:
                from datetime import datetime
                if isinstance(date_created, str):
                    webhook_log.webhook_date = datetime.fromisoformat(date_created.replace('Z', '+00:00'))
                else:
                    webhook_log.webhook_date = date_created
            except Exception as e:
                logger.warning(f"Error parsing webhook date: {str(e)}")
                webhook_log.webhook_date = None
        else:
            webhook_log.webhook_date = None
        
        # Check if this is a webhook event with standard SmartGateway nested structure
        if 'content' in data and 'order' in data.get('content', {}):
            # Extract from nested structure as per SmartGateway documentation
            order_data = data['content']['order']
            order_id = order_data.get('order_id', '')
            
            # If status is in the nested structure, update data to use the nested order data
            # This ensures the rest of the function works with the order data
            if 'status' in order_data:
                data = order_data
        else:
            # Direct structure (legacy or non-standard format)
            order_id = data.get('order_id', '')
            
        webhook_log.order_id = order_id
        
        if not order_id:
            webhook_log.status = 'FAILED'
            webhook_log.error_message = "Missing order_id"
            webhook_log.save()
            return JsonResponse({"status": "success", "message": "Webhook received but missing order_id"})
        
        # Check if this webhook has already been processed (idempotency check)
        # If webhook_id is available, use it for more precise idempotency check
        if webhook_id:
            existing_webhook = WebhookLog.objects.filter(
                webhook_id=webhook_id,
                status='PROCESSED'
            ).exists()
        else:
            # Fall back to order_id and event_type if webhook_id is not available
            existing_webhook = WebhookLog.objects.filter(
                order_id=order_id,
                event_type=event_name,
                status='PROCESSED'
            ).exists()
        
        if existing_webhook:
            webhook_log.status = 'DUPLICATE'
            webhook_log.error_message = "Webhook already processed"
            webhook_log.save()
            return JsonResponse({"status": "success", "message": "Webhook already processed"})
        
        # Process payment status
        with transaction.atomic():
            payment_transaction = PaymentTransaction.objects.get(order_id=order_id)
            webhook_log.transaction = payment_transaction
            
            # Extract transaction_id from the appropriate location in the data structure
            txn_id = ''
            if 'content' in data and 'order' in data.get('content', {}):
                # Get from nested structure
                txn_id = data['content']['order'].get('txn_id', '')
            
            # Fall back to top-level fields if not found in nested structure
            if not txn_id:
                txn_id = data.get('txn_id', '')
            
            # Only update transaction_id if we have a non-empty value to prevent unique constraint violation
            if txn_id:
                payment_transaction.transaction_id = txn_id
            
            # Extract status from the appropriate location in the data structure
            status = ''
            if 'content' in data and 'order' in data.get('content', {}):
                # Get from nested structure
                status = data['content']['order'].get('status', '')
            
            # Fall back to top-level fields if not found in nested structure
            if not status:
                status = data.get('order_status', data.get('status', ''))
            
            # Map SmartGateway status to our internal status
            if status == 'CHARGED':
                payment_transaction.status = 'SUCCESS'
            elif status == 'PENDING_VBV':
                payment_transaction.status = 'PENDING'
            elif status in ['AUTHENTICATION_FAILED', 'AUTHORIZATION_FAILED', 'JUSPAY_DECLINED', 'AUTHORIZATION_DECLINED']:
                payment_transaction.status = 'FAILURE'
            elif status == 'VOID':
                payment_transaction.status = 'CANCELLED'
            elif status == 'REFUNDED':
                payment_transaction.status = 'REFUNDED'
            
            # Always save the gateway response
            payment_transaction.gateway_response = data
            payment_transaction.save()
            
            # Update installment status only if we have a definitive result
            payment_transaction.update_installment_status()
            
            # Update webhook log status to PROCESSED (our internal status)
            webhook_log.status = 'PROCESSED'
            webhook_log.save()
        
        # Always return 200 status as per SmartGateway requirements
        return JsonResponse({"status": "success", "message": "Webhook processed successfully"})
        
    except PaymentTransaction.DoesNotExist:
        webhook_log.status = 'FAILED'
        webhook_log.error_message = f"Transaction not found for order_id: {order_id}"
        webhook_log.save()
        logger.error(f"Transaction not found for order_id: {order_id}")
        # Return 200 even for errors as per SmartGateway requirements
        return JsonResponse({"status": "success", "message": "Webhook received but transaction not found"})
    except Exception as e:
        webhook_log.status = 'FAILED'
        webhook_log.error_message = str(e)
        webhook_log.save()
        logger.error(f"Payment webhook error: {str(e)}", exc_info=True)
        # Return 200 even for errors as per SmartGateway requirements
        return JsonResponse({"status": "success", "message": "Webhook received"})
