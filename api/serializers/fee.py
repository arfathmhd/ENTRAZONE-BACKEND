from rest_framework import serializers
from dashboard.models import (
    FeePaymentPlan, Subscription, FeeInstallment,
    PaymentTransaction, Batch, CustomUser
)


class FeePaymentPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeePaymentPlan
        fields = [
            'id', 'name', 'total_amount', 'discount',
            'number_of_installments', 'frequency', 'created'
        ]


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'transaction_id', 'transaction_uuid', 'order_id',
            'amount', 'currency', 'status', 'payment_mode',
            'bank_ref_number', 'gateway_response', 'payment_link',
            'payment_link_expiry', 'razorpay_payment_id',
            'razorpay_order_id', 'razorpay_signature',
            'created', 'updated'
        ]


class FeeInstallmentSerializer(serializers.ModelSerializer):
    transactions = PaymentTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = FeeInstallment
        fields = [
            'id', 'due_date', 'amount_due', 'is_paid', 'paid_on',
            'payment_reference', 'discount_applied', 'status',
            'payment_link', 'payment_link_uuid', 'payment_link_expires',
            'payment_attempts', 'notes', 'created', 'updated',
            'transactions'
        ]


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ['id', 'batch_name', 'start_date', 'batch_expiry']


class SubscriptionSerializer(serializers.ModelSerializer):
    payment_plan = FeePaymentPlanSerializer(read_only=True)
    installments = FeeInstallmentSerializer(many=True, read_only=True)
    batch = BatchSerializer(many=True, read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'id', 'user', 'batch', 'custom_amount', 'payment_plan',
            'created', 'total_paid', 'total_due', 'last_payment_date',
            'installments'
        ]
        extra_kwargs = {
            'user': {'write_only': True}
        }
