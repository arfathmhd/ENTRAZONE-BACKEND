import uuid
import json
import hmac
import hashlib
import logging
import requests
import base64
import time
import urllib.parse
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from dashboard.models import PaymentTransaction, WebhookLog, HDFCPaymentConfig

logger = logging.getLogger(__name__)

def generate_smartgateway_payment_link(installment, config):
    """
    Generate a payment link using HDFC SmartGateway API
    
    Args:
        installment: FeeInstallment object
        config: HDFCPaymentConfig object
    
    Returns:
        dict: API response with payment link details
    """
    
    # Generate a unique order ID - must be less than 21 chars, no special chars, alphanumeric, non-sequential
    # Format: SAH-{installment_id}-{random_hex}
    order_id = f"SAH{installment.id}{uuid.uuid4().hex[:8]}"
    # Ensure it's less than 21 chars
    if len(order_id) > 20:
        order_id = order_id[:20]
    # Get student details
    student = installment.subscription.user
    
    # Format amount with exactly 2 decimal places
    amount = "{:.2f}".format(float(installment.amount_due))
    
    # Prepare API request payload according to documentation
    payload = {
        "order_id": order_id,
        "amount": amount,
        "currency": "INR",
        "customer_id": str(student.id),
        "customer_email": student.email,
        "customer_phone": student.phone_number,
        "payment_page_client_id": config.payment_page_client_id or "hdfcmaster",  # Use hdfcmaster for sandbox
        "action": "paymentPage",
        "return_url": f"{settings.DOMAIN_URL}/payment/callback/",
        "description": f"Fee payment for {student.name}",
        "first_name": student.name,
        "last_name": "",
        "metadata.expiryInMins": "1440"  # 24 hours
    }
    
    # Add payment filter to allow all payment methods
    payment_filter = {
        "allowDefaultOptions": True,
        "options": [
            {"paymentMethodType": "NB", "enable": True},
            {"paymentMethodType": "UPI", "enable": True},
            {"paymentMethodType": "CARD", "enable": True},
            {"paymentMethodType": "WALLET", "enable": True}
        ]
    }
    payload["payment_filter"] = payment_filter
    
    # Add UDFs for tracking
    payload["udf1"] = f"installment_{installment.id}"
    payload["udf2"] = f"student_{student.id}"
    payload["udf3"] = f"subscription_{installment.subscription.id}"
    
    # Set up headers according to documentation
    # Basic Auth requires username:password format
    # For HDFC SmartGateway, it's api_key: (with colon and empty password)
    api_key_bytes = f"{config.api_key}:".encode('ascii')
    encoded_auth = base64.b64encode(api_key_bytes).decode('ascii')
    
    headers = {
        'Authorization': f'Basic {encoded_auth}',
        'x-merchantid': config.merchant_id,
        'x-customerid': str(student.id),
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Make API request
    try:
        response = requests.post(
            f"{config.api_url}/session",
            json=payload,
            headers=headers
        )
        
        # Raise exception for error status codes
        response.raise_for_status()
        response_data = response.json()
        
        # Extract payment link details
        payment_link = response_data['payment_links']['web']
        payment_link_expiry = response_data['payment_links']['expiry']
        transaction_id = response_data.get('id')
        
        # Parse expiry date
        try:
            expiry_datetime = datetime.strptime(payment_link_expiry, "%Y-%m-%dT%H:%M:%SZ")
            expiry_datetime = timezone.make_aware(expiry_datetime)
        except ValueError:
            expiry_datetime = timezone.now() + timezone.timedelta(days=1)
        
        # Create transaction record
        transaction = PaymentTransaction.objects.create(
            installment=installment,
            transaction_id=transaction_id,
            order_id=order_id,
            amount=installment.amount_due,
            status='INITIATED',
            payment_link=payment_link,
            payment_link_expiry=expiry_datetime,
            gateway_response=response_data
        )

        return {
            'success': True,
            'transaction': transaction,
            'payment_link': payment_link,
            'expiry': payment_link_expiry
        }
        
    except requests.exceptions.RequestException as e:
        
        error_transaction = PaymentTransaction.objects.create(
            installment=installment,
            order_id=order_id,
            amount=installment.amount_due,
            status='FAILURE',
            gateway_response={
                'error': str(e),
                'response_text': e.response.text if hasattr(e, 'response') and e.response else None
            }
        )
        
        return {
            'success': False,
            'error': str(e)
        }

def verify_signature(params, signature, signature_algorithm, secret_key):
    """
    Verify HMAC signature from HDFC SmartGateway
    
    Args:
        params: Dictionary of parameters from the return URL
        signature: The signature to verify (base64 encoded)
        signature_algorithm: The algorithm used for signature (e.g., 'HMAC-SHA256')
        secret_key: The secret key used for HMAC calculation
    
    Returns:
        bool: True if signature is valid, False otherwise
    """
    try:
        # 1. Filter out signature and signature_algorithm parameters
        filtered_params = {k: v for k, v in params.items() 
                         if k not in ['signature', 'signature_algorithm']}
        
        # 2. Percentage encode each key and value
        encoded_params = {}
        for k, v in filtered_params.items():
            encoded_key = urllib.parse.quote_plus(k)
            encoded_value = urllib.parse.quote_plus(str(v))
            encoded_params[encoded_key] = encoded_value
        
        # 3. Sort parameters alphabetically by encoded key (ASCII based sort)
        encoded_sorted = []
        for k in sorted(encoded_params.keys()):
            encoded_sorted.append(f"{k}={encoded_params[k]}")
        
        # 4. Join with '&' character
        joined_string = '&'.join(encoded_sorted)
        
        # 5. Percentage encode the generated string
        encoded_string = urllib.parse.quote_plus(joined_string)
        
        # 6. Calculate HMAC using the secret key
        if signature_algorithm == 'HMAC-SHA256':
            # Create HMAC with SHA256
            digest = hmac.new(
                key=secret_key.encode(),
                msg=encoded_string.encode(),
                digestmod=hashlib.sha256
            ).digest()
            
            # Base64 encode the digest
            calculated_signature = base64.b64encode(digest).decode()
            
            # Percentage encode the calculated signature for comparison
            encoded_calculated_signature = urllib.parse.quote_plus(calculated_signature)
            
            # The signature in the response should be percentage decoded once before comparing
            decoded_signature = urllib.parse.unquote(signature)
            
            # Compare signatures (raw calculated with decoded received)
            return calculated_signature == decoded_signature
        else:
            # Unsupported algorithm
            print("Unsupported signature algorithm")
            return False
    except Exception as e:
        print(f"Error verifying signature: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def handle_smartgateway_callback(request, config):
    """Handle callback from HDFC SmartGateway with enhanced security"""
    webhook_log = WebhookLog(
        headers={k: v for k, v in request.headers.items()},
        ip_address=request.META.get('REMOTE_ADDR'),
        event_type='PAYMENT_CALLBACK'  # Distinguish callback from webhook
    )
    
    try:
        # Parse data from request
        data = {}
        try:
            if request.body:
                data = json.loads(request.body)
        except json.JSONDecodeError:
            if request.POST:
                data = request.POST.dict()
            elif request.GET:
                data = request.GET.dict()
        
        webhook_log.request_data = data
  
        # Check if this is a standard webhook format with id, date_created, etc.
        if 'id' in data and data.get('id', '').startswith('evt_'):
            webhook_id = data.get('id', '')
            date_created = data.get('date_created', '')
            event_name = data.get('event_name', '')
            
            # For backward compatibility, also check event_type
            event_name = event_name or data.get('event_type', '')
            
            # Log the webhook metadata
            if event_name:
                webhook_log.event_type = event_name
            webhook_log.webhook_id = webhook_id
            webhook_log.webhook_date = date_created if date_created else None
        else:
            # For callback URL format, use status as event_type if no event_type is already set
            if data.get('status') and webhook_log.event_type == 'PAYMENT_CALLBACK':
                webhook_log.event_type = f"PAYMENT_CALLBACK_{data.get('status')}"
            
            # Generate a pseudo webhook ID for tracking
            if data.get('order_id'):
                webhook_log.webhook_id = f"callback_{data.get('order_id')}_{int(time.time())}"
        
        # Extract order_id from data
        order_id = ''
        if 'content' in data and 'order' in data.get('content', {}):
            order_data = data['content']['order']
            order_id = order_data.get('order_id', '')
            if 'status' in order_data:
                data = order_data
        else:
            order_id = data.get('order_id', '')
        
        webhook_log.order_id = order_id
        
        if not order_id:
            webhook_log.status = 'FAILED'
            webhook_log.error_message = "Missing order_id in callback"
            webhook_log.save()
            return redirect("payment-failure", transaction_id=trans.transaction_uuid)
        
        
        try:
            trans = PaymentTransaction.objects.get(order_id=order_id)
            webhook_log.transaction = trans
        except PaymentTransaction.DoesNotExist:
            webhook_log.status = 'FAILED'
            webhook_log.error_message = f"Transaction not found for order_id: {order_id}"
            webhook_log.save()
            return redirect("payment-failure", transaction_id=trans.transaction_uuid)
        
        # Verify signature if present and response_key is configured
        if 'signature' in data and 'signature_algorithm' in data and config.working_key:
            signature = data.get('signature', '')
            signature_algorithm = data.get('signature_algorithm', '')
            
            # Verify the signature
            is_valid_signature = verify_signature(
                params=data,
                signature=signature,
                signature_algorithm=signature_algorithm,
                secret_key=config.working_key
            )
            
            webhook_log.signature_valid = is_valid_signature
            
            if not is_valid_signature:
                logger.error(f"Invalid signature for order_id: {data.get('order_id', 'unknown')}")
                webhook_log.status = 'FAILED'
                webhook_log.error_message = "Invalid signature"
                webhook_log.save()
                return redirect("payment-failure", transaction_id=trans.transaction_uuid)
        
        # Find the transaction in our database
        
        # CRITICAL: Server-side verification of transaction status
        # Make direct API call to payment gateway to verify transaction status
        api_url = f"{config.api_url}/orders/{order_id}"
        auth_header = base64.b64encode(f"{config.api_key}:".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/json',
            'x-merchantid': config.merchant_id,
            'x-customerid': str(trans.installment.subscription.user.id)
        }
        
        # Make server-to-server API request to verify transaction
        try:
            response = requests.get(api_url, headers=headers)
            if response.status_code != 200:
                webhook_log.status = 'FAILED'
                webhook_log.error_message = f"Failed to verify transaction status: {response.text}"
                webhook_log.save()
                return redirect("payment-failure", transaction_id=trans.transaction_uuid)
            
            # Parse verified response from payment gateway
            verified_data = response.json()
            
            # CRITICAL: Verify transaction amount matches expected amount
            verified_amount = float(verified_data.get('amount', 0))
            expected_amount = float(trans.amount)
            
            if abs(verified_amount - expected_amount) > 0.01:  # Allow small rounding differences
                webhook_log.status = 'INVALID'
                webhook_log.error_message = f"Amount mismatch: expected {expected_amount}, got {verified_amount}"
                webhook_log.save()
                logger.error(f"Payment amount mismatch for order {order_id}: expected {expected_amount}, got {verified_amount}")
                return redirect("payment-failure", transaction_id=trans.transaction_uuid)
            
            # Get verified transaction status
            verified_status = verified_data.get('status', '').upper()
            transaction_status = 'PENDING'
            
            # Map verified status to our transaction status
            if verified_status == 'NEW':
                transaction_status = 'INITIATED'
            elif verified_status == 'CHARGED':
                transaction_status = 'SUCCESS'
            elif verified_status in ['AUTHENTICATION_FAILED', 'AUTHORIZATION_FAILED', 'CAPTURE_FAILED', 'FAILED']:
                transaction_status = 'FAILURE'
            elif verified_status == 'CANCELLED':
                transaction_status = 'CANCELLED'
            
            # Update transaction with verified data
            with transaction.atomic():
                trans.status = transaction_status
                trans.payment_mode = verified_data.get('payment_method', {}).get('type', 'UNKNOWN') if isinstance(verified_data.get('payment_method'), dict) else 'UNKNOWN'
                trans.bank_ref_number = verified_data.get('payment_method', {}).get('reference', '') if isinstance(verified_data.get('payment_method'), dict) else ''
                trans.gateway_response = verified_data  # Store verified data, not client-provided data
                trans.save()
                
                logger.info(f"Updated transaction {trans.id} status to {transaction_status} (verified)")
                
                # Update installment status if payment is successful
                if transaction_status == 'SUCCESS':
                    trans.update_installment_status()
                    logger.info(f"Updated installment {trans.installment.id} status to PAID")
                elif transaction_status == 'FAILURE':
                    installment = trans.installment
                    installment.payment_attempts += 1
                    installment.status = 'FAILED'
                    installment.save()
                
                webhook_log.status = verified_status
                webhook_log.save()
            
            # Redirect based on verified status
            if transaction_status == 'SUCCESS':
                return redirect('payment-success', transaction_id=trans.transaction_uuid)
            else:
                return redirect('payment-failure', transaction_id=trans.transaction_uuid)
                
        except requests.RequestException as e:
            webhook_log.status = 'FAILED'
            webhook_log.error_message = f"Failed to verify transaction: {str(e)}"
            webhook_log.save()
            return redirect("payment-failure", transaction_id=trans.transaction_uuid)
            
    except Exception as e:
        webhook_log.status = 'FAILED'
        webhook_log.error_message = str(e)
        webhook_log.save()
        return redirect("payment-failure", transaction_id=trans.transaction_uuid)


@login_required
@require_http_methods(["GET"])
def check_order_status(request, order_id):
    """
    Check the status of an order with HDFC Smart Gateway
    
    Args:
        request: HTTP request
        order_id: Order ID to check status for
    
    Returns:
        JsonResponse with order status details or error
    """
    try:
        # Get the transaction
        transaction = PaymentTransaction.objects.filter(order_id=order_id).first()
        student = transaction.installment.subscription.user
        # transaction_order = transaction.transaction_id
        if not transaction:
            return JsonResponse({
                'success': False,
                'message': f'Transaction with order ID {order_id} not found'
            }, status=404)
            
        # Get payment gateway configuration
        payment_config = HDFCPaymentConfig.objects.filter(is_active=True).first()
        if not payment_config:
            return JsonResponse({
                'success': False, 
                'message': 'Payment gateway configuration not found'
            }, status=500)
        
        # Prepare API request
        api_url = f"{payment_config.api_url}/orders/{order_id}"
        # Create Basic Auth header with API key
        auth_header = base64.b64encode(f"{payment_config.api_key}:".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/json',
            'x-merchantid': payment_config.merchant_id,
            'x-customerid': str(student.id)
        }
        
        # Make API request to HDFC Smart Gateway
        response = requests.get(api_url, headers=headers)
        # Log the response
        WebhookLog.objects.create(
            transaction=transaction,
            request_data=response.text,
            status='PROCESSED' if response.status_code == 200 else 'FAILED',
            ip_address=request.META.get('REMOTE_ADDR', ''),
            error_message=None if response.status_code == 200 else f"Status code: {response.status_code}"
        )
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Update transaction status if needed
            gateway_status = "SUCCESS" if response_data.get('status') == "CHARGED" else response_data.get('status')
            if gateway_status and transaction.status != gateway_status:
                transaction.status = gateway_status
                transaction.gateway_response = response.text
                transaction.save()
                transaction.update_installment_status()
            
            return JsonResponse({
                'success': True,
                'data': response_data
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'Failed to fetch order status: {response.text}',
                'status_code': response.status_code
            }, status=500)
            
    except Exception as e:
        print(e)
        return JsonResponse({
            'success': False,
            'message': f'Error checking order status: {str(e)}'
        }, status=500)
