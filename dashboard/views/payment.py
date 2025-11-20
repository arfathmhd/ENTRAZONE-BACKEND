import razorpay
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from dashboard.models import RazorpayConfig, FeeInstallment, PaymentTransaction, Subscription, WebhookLog
import uuid

logger = logging.getLogger(__name__)

def get_razorpay_client():
    """Get Razorpay client with current configuration"""
    config = RazorpayConfig.objects.filter(is_active=True, is_deleted=False).first()
    if not config:
        # Fallback to direct keys if no config in database
        from django.conf import settings
        key_id = getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_RhsUx4BhQf5fID')
        key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '1y3J16vpLc27Pt4xSP9KeQLU')
        return razorpay.Client(auth=(key_id, key_secret))
    
    return razorpay.Client(auth=(config.key_id, config.get_key_secret()))

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_razorpay_order(request):
    """Create Razorpay order for installment payment or premium unlock"""
    try:
        installment_id = request.data.get('installment_id')
        amount = request.data.get('amount')
        
        if installment_id:
            # Payment for specific installment
            installment = get_object_or_404(FeeInstallment, id=installment_id, is_deleted=False)
            amount = int(installment.amount_due * 100)  # Convert to paise
            notes = {
                'user_id': str(request.user.id),
                'installment_id': str(installment.id),
                'subscription_id': str(installment.subscription.id),
                'purpose': 'installment_payment'
            }
            receipt = f'installment_{installment.id}_{uuid.uuid4().hex[:8]}'
        else:
            # Custom payment (like premium unlock)
            amount = int(float(amount) * 100)  # Convert to paise
            notes = {
                'user_id': str(request.user.id),
                'purpose': 'premium_subscription'
            }
            receipt = f'premium_{request.user.id}_{uuid.uuid4().hex[:8]}'
        
        client = get_razorpay_client()
        
        order_data = {
            'amount': amount,
            'currency': 'INR',
            'receipt': receipt,
            'notes': notes
        }
        
        order = client.order.create(data=order_data)
        
        # Create payment transaction record
        transaction = PaymentTransaction.objects.create(
            installment_id=installment_id if installment_id else None,
            order_id=order['id'],
            amount=amount / 100,  # Convert back to rupees
            currency='INR',
            status='PENDING'
        )
        
        config = RazorpayConfig.objects.filter(is_active=True).first()
        key_id = config.key_id if config else getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_RhsUx4BhQf5fID')
        
        return Response({
            'id': order['id'],
            'amount': order['amount'],
            'currency': order['currency'],
            'key': key_id,
            'transaction_id': str(transaction.transaction_uuid)
        })
        
    except Exception as e:
        logger.error(f"Error creating Razorpay order: {str(e)}")
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    """Verify Razorpay payment signature"""
    try:
        data = request.data
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')
        
        client = get_razorpay_client()
        
        # Verify the payment signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        client.utility.verify_payment_signature(params_dict)
        
        # Get transaction and update status
        transaction = PaymentTransaction.objects.get(order_id=razorpay_order_id)
        transaction.status = 'SUCCESS'
        transaction.razorpay_payment_id = razorpay_payment_id
        transaction.razorpay_order_id = razorpay_order_id
        transaction.razorpay_signature = razorpay_signature
        transaction.transaction_id = razorpay_payment_id
        transaction.save()
        
        # Update installment status if exists
        if transaction.installment:
            transaction.update_installment_status()
        
        return Response({
            'status': 'Payment successful', 
            'transaction_id': transaction.transaction_id,
            'transaction_uuid': str(transaction.transaction_uuid)
        })
        
    except razorpay.errors.SignatureVerificationError:
        return Response({'error': 'Invalid payment signature'}, status=400)
    except PaymentTransaction.DoesNotExist:
        return Response({'error': 'Transaction not found'}, status=404)
    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        return Response({'error': str(e)}, status=400)

@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """Handle Razorpay webhook events"""
    try:
        webhook_body = request.body.decode('utf-8')
        webhook_data = json.loads(webhook_body)
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        
        # Log webhook request
        webhook_log = WebhookLog.objects.create(
            webhook_id=webhook_data.get('id'),
            event_type=webhook_data.get('event'),
            request_data=webhook_data,
            headers=dict(request.headers),
            ip_address=get_client_ip(request)
        )
        
        # Verify webhook signature
        config = RazorpayConfig.objects.filter(is_active=True).first()
        if config and config.get_webhook_secret():
            try:
                client = get_razorpay_client()
                client.utility.verify_webhook_signature(
                    webhook_body, 
                    webhook_signature, 
                    config.get_webhook_secret()
                )
                webhook_log.signature_valid = True
            except Exception as e:
                webhook_log.signature_valid = False
                webhook_log.status = 'INVALID'
                webhook_log.error_message = f"Invalid signature: {str(e)}"
                webhook_log.save()
                return JsonResponse({'status': 'invalid signature'}, status=400)
        
        # Process webhook event
        event = webhook_data.get('event')
        payload = webhook_data.get('payload', {})
        payment_entity = payload.get('payment', {})
        order_entity = payload.get('order', {})
        
        order_id = order_entity.get('id') or payment_entity.get('order_id')
        
        if order_id:
            try:
                transaction = PaymentTransaction.objects.get(order_id=order_id)
                webhook_log.transaction = transaction
                webhook_log.order_id = order_id
                
                if event == 'payment.captured':
                    transaction.status = 'SUCCESS'
                    transaction.razorpay_payment_id = payment_entity.get('id')
                    transaction.payment_mode = payment_entity.get('method')
                    transaction.bank_ref_number = payment_entity.get('bank_reference_id')
                    transaction.gateway_response = payment_entity
                    transaction.save()
                    
                    if transaction.installment:
                        transaction.update_installment_status()
                    
                    webhook_log.status = 'PROCESSED'
                
                elif event == 'payment.failed':
                    transaction.status = 'FAILURE'
                    transaction.gateway_response = payment_entity
                    transaction.save()
                    
                    if transaction.installment:
                        transaction.installment.status = 'FAILED'
                        transaction.installment.payment_attempts += 1
                        transaction.installment.save()
                    
                    webhook_log.status = 'PROCESSED'
                
            except PaymentTransaction.DoesNotExist:
                webhook_log.status = 'FAILED'
                webhook_log.error_message = 'Transaction not found'
        
        webhook_log.save()
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        if 'webhook_log' in locals():
            webhook_log.status = 'FAILED'
            webhook_log.error_message = str(e)
            webhook_log.save()
        logger.error(f"Razorpay webhook error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_installments(request):
    """Get user's pending installments"""
    subscriptions = Subscription.objects.filter(user=request.user, is_deleted=False)
    installments = FeeInstallment.objects.filter(
        subscription__in=subscriptions,
        is_paid=False,
        is_deleted=False
    ).order_by('due_date')
    
    installment_data = []
    for installment in installments:
        installment_data.append({
            'id': installment.id,
            'amount_due': installment.amount_due,
            'due_date': installment.due_date,
            'status': installment.status,
            'subscription_id': installment.subscription.id,
            'batch_names': [batch.batch_name for batch in installment.subscription.batch.all()]
        })
    
    return Response(installment_data)

def razorpay_payment_redirect(request, uuid):
    """Handle payment redirect with shareable link for Razorpay"""
    try:
        installment = get_object_or_404(FeeInstallment, payment_link_uuid=uuid)
        
        # Check if link is expired
        if installment.payment_link_expires and installment.payment_link_expires < timezone.now():
            return render(request, 'dashboard/payment/link_expired.html', {'installment': installment})
        
        # Check if already paid
        if installment.is_paid:
            return render(request, 'dashboard/payment/already_paid.html', {'installment': installment})
        
        student = installment.subscription.user
        subscription = installment.subscription
        batches = subscription.batch.all()
        
        context = {
            'installment': installment,
            'student': student,
            'subscription': subscription,
            'batches': batches,
            'amount': installment.amount_due,
            'razorpay_key': RazorpayConfig.objects.filter(is_active=True).first().key_id if RazorpayConfig.objects.filter(is_active=True).exists() else 'rzp_test_RhsUx4BhQf5fID'
        }
        
        return render(request, 'dashboard/payment/razorpay_checkout.html', context)
            
    except Exception as e:
        logger.error(f"Razorpay payment redirect error: {str(e)}")
        return render(request, 'dashboard/payment/gateway_error.html', {'error': str(e)})

def payment_success(request, transaction_uuid):
    """Show payment success page"""
    transaction = get_object_or_404(PaymentTransaction, transaction_uuid=transaction_uuid)
    
    context = {
        'transaction': transaction,
        'installment': transaction.installment,
        'student': transaction.installment.subscription.user if transaction.installment else None
    }
    
    return render(request, 'dashboard/payment/success.html', context)

def payment_failure(request, transaction_uuid):
    """Show payment failure page"""
    transaction = get_object_or_404(PaymentTransaction, transaction_uuid=transaction_uuid)
    
    context = {
        'transaction': transaction,
        'installment': transaction.installment,
        'student': transaction.installment.subscription.user if transaction.installment else None,
        'error_message': 'Payment failed. Please try again.'
    }
    
    return render(request, 'dashboard/payment/failure.html', context)