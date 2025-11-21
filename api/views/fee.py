from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from dashboard.models import Subscription
from api.serializers.fee import SubscriptionSerializer


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_fees_list(request):
    user = request.user
    subscriptions = Subscription.objects.filter(user=user)

    serializer = SubscriptionSerializer(subscriptions, many=True)
    return Response({
        "user": user.username,
        "total_subscriptions": subscriptions.count(),
        "subscriptions": serializer.data
    })