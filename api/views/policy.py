from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404


@csrf_exempt
def privacy_policy(request):
    return render(request, 'dashboard/policy/privacy_policy.html')
@csrf_exempt
def about_us(request):
    return render(request, 'dashboard/policy/about_us.html')
@csrf_exempt
def terms_conditions(request):
    return render(request, 'dashboard/policy/terms_condition.html')