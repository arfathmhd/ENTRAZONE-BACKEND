
from rest_framework.response import Response
from dashboard.views.imports import *
from django.contrib.auth import authenticate
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status




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

@api_view(["POST"])  
@permission_classes([IsAuthenticated])  
def register(request):
    user = request.user
    district_number = request.data.get("district")
    email = request.data.get("email")
    name = request.data.get("username")  
    image = request.data.get("image")  
    address = request.data.get("address")  


    if not user.is_authenticated:
        return Response({"status": "error", "message": "User not authenticated."}, status=status.HTTP_401_UNAUTHORIZED)

    if not district_number:
        return Response({"status": "error", "message": "Please provide a valid district"}, status=status.HTTP_400_BAD_REQUEST)

    if not email:
        return Response({"status": "error", "message": "Please provide a valid email"}, status=status.HTTP_400_BAD_REQUEST)
    
    if not name:
        return Response({"status": "error", "message": "Please provide your name"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        if CustomUser.objects.filter(email=email, is_deleted=False).exists():
            return Response({"status": "error", "message": "User with this email already exists"}, status=status.HTTP_400_BAD_REQUEST)
       
        valid_districts = [choice[0] for choice in STATE_CHOICES]
        if district_number not in valid_districts:
            return Response({"status": "error", "message": "Invalid district number"}, status=status.HTTP_400_BAD_REQUEST)

        
        phone= request.user.phone_number
        combined_username = f"{phone}_{name}"
        user.email = email
        user.username = combined_username
        user.name = name  
        user.district = district_number  
        if image:  
            user.image = image
        if address:  
            user.address = address
        user.save()  

        district_name = dict(STATE_CHOICES).get(district_number, "")

        user_details = {
            "id": user.id,
            "name": user.name if user.name else "", 
            "image": request.build_absolute_uri(user.image.url) if user.image else "",
            "username": user.username if user.username else "",
            "phone": user.phone_number if user.phone_number else "",
            "email": user.email if user.email else "",
            "state": district_name,
            "address": user.address if user.address else "",
        }

        return Response({
            "status": "success",
            "message": "Registration Successful",
            "user": user_details,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





def sendsms(otp, phone):
    try:
        url = f"https://2factor.in/API/V1/e9d24a95-606f-11f0-a562-0200cd936042/SMS/{phone}/{otp}/EntrazonOTP"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("OTP SMS sent successfully:", response.json())
        else:
            print("Failed to send OTP SMS:", response.status_code, response.text)
    except Exception as e:
        print("Error while sending OTP SMS:", str(e))


@api_view(["POST"])
def otp_auth(request):
    phone = request.data.get("phone")
    request_id = request.data.get("request_id")

    if phone and request_id:
        try:
            user = CustomUser.objects.filter(phone_number=phone, is_deleted=False).first()

            # If user exists and is valid
            if user:
                otp_exists = Otp.objects.filter(
                    request_id=request_id, requested_by=user, verified=False
                ).exists()
                if otp_exists:
                    otp = Otp.objects.filter(
                        request_id=request_id, requested_by=user, verified=False
                    ).first()
                    code = otp.code
                    if phone != "9876543210":
                        sendsms(str(code), phone)
                    context = {
                        "status": "Success",
                        "status_code": status.HTTP_200_OK,
                        "message": "Login OTP Send!",
                        "route": "login",
                    }
                else:
                    code = randint(1000, 9999)
                    if phone == "9876543210":
                        code = 5555
                    otp = Otp(requested_by=user, code=code, request_id=request_id)
                    otp.save()
                    code = otp.code
                    if phone != "9876543210":
                        sendsms(str(code), phone)
                    context = {
                        "status": "success",
                        "status_code": status.HTTP_200_OK,
                        "message": "Login OTP Send!",
                        "route": "login",
                    }
            else:
                # No valid user found; treat as a Signup request
                otp_exists = Otp.objects.filter(
                    temp_user__phone=phone, request_id=request_id, verified=False
                ).exists()
                if otp_exists:
                    otp = Otp.objects.filter(
                        temp_user__phone=phone, request_id=request_id, verified=False
                    ).first()
                    code = otp.code
                    if phone != "9876543210":
                        sendsms(str(code), phone)
                    context = {
                        "status": "Success",
                        "status_code": status.HTTP_200_OK,
                        "message": "Signup OTP Send!",
                        "route": "signup",
                    }
                else:
                    username = str(phone)
                    code = randint(1000, 9999)
                    if phone == "9876543210":
                        code = 5555
                    tempuser = TempUser.objects.create(
                        name="", username=username, phone=phone, email=""
                    )
                    otp = Otp(temp_user=tempuser, request_id=request_id, code=code)
                    otp.save()
                    code = otp.code
                    if phone != "9876543210":
                        sendsms(str(code), phone)
                    context = {
                        "status": "success",
                        "status_code": status.HTTP_200_OK,
                        "message": "Signup OTP Send!",
                        "route": "signup",
                    }

        except Exception as e:
            context = {
                "status": "error",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": str(e),
            }
        return Response(context)
    else:
        response = {
            "status": "error",
            "status_code": status.HTTP_400_BAD_REQUEST,
            "message": "incomplete request",
        }
        return Response(response)

    



@api_view(["POST"])
def otp_login_verify(request):
    phone = request.data.get("phone")
    code = request.data.get("code")
    request_id = request.data.get("request_id")


    if phone and code and request_id:
        if CustomUser.objects.filter(phone_number=phone, is_deleted=False).exists():
            user = CustomUser.objects.filter(phone_number=phone, is_deleted=False).first()

            if Otp.objects.filter(
                requested_by=user, code=code, request_id=request_id, verified=False
            ).exists():
                otp = Otp.objects.get(
                    requested_by=user, code=code, request_id=request_id, verified=False
                )
                otp.verified = True
                date_from = datetime.now() - timedelta(days=1)
                otp.created__gte = date_from
                otp.save()
                district_name = dict(STATE_CHOICES).get(user.district, "")

                user_details = {
                    "id": user.id,
                    "name": user.name if user.name else "",
                    "image":user.image.url if user.image else "",
                    "phone": user.phone_number if user.phone_number else "",
                    "email": user.email if user.email else "",
                    "state": district_name ,  
                }

                refresh = RefreshToken.for_user(user)
                context = {
                    "status": "success",
                    "message": "Login successful",
                    "user": user_details,
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
                return Response(context, status=status.HTTP_200_OK)
            else:
                context = {
                    "status": "error",
                    "message": "OTP verification failed",
                }
                return Response(context, status=status.HTTP_410_GONE)
        else:
            context = {
                "status": "error",
                "message": "User not found",
            }
            return Response(context, status=status.HTTP_404_NOT_FOUND)
    else:
        return Response(
            {
                "status": "error",
                "message": "Incomplete request",
            },
            status=status.HTTP_400_BAD_REQUEST,  # Explicitly return 400 status
        )





@api_view(["POST"])
def otp_signup_verify(request):
    phone = request.data.get("phone")
    code = request.data.get("code")
    request_id = request.data.get("request_id")



    if phone and code and request_id:
        try:
            date_from = datetime.now() - timedelta(days=1)
            otp = Otp.objects.filter(
                request_id=request_id, code=code, verified=False, temp_user__phone=phone
            ).first()

            if otp:
                otp.verified = True
                otp.created__gte = date_from
                otp.save()

                temp_user = otp.temp_user
                new_user = CustomUser.objects.create(
                    name=temp_user.name,
                    username=temp_user.username,
                    phone_number=temp_user.phone,
                    email=temp_user.email,
                    is_active=True,
                )
                temp_user.deleted = True
                temp_user.save()
                otp.requested_by = new_user
                otp.save()

                user_details = {
                    "id": new_user.id,
                    "name": new_user.name if new_user.name else "",
                    
                    # "username": new_user.username,
                    "phone": new_user.phone_number if new_user.phone_number else "",
                    "email": new_user.email if new_user.email else "",
                }

                refresh = RefreshToken.for_user(new_user)
                context = {
                    "status": "success",
                    "message": "OTP verified and logged in!",
                    "user": user_details,
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            elif Otp.objects.filter(
                request_id=request_id,
                code=code,
                verified=True,
                requested_by__phone_number=phone,
            ).exists():
                context = {
                    "status": "error",
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": "User already exists, please login.",
                }
            else:
                context = {
                    "status": "error",
                    "status_code": status.HTTP_410_GONE,
                    "message": "OTP verification failed.",
                }

            return Response(context)
        except (Otp.DoesNotExist, CustomUser.DoesNotExist):
            context = {
                "status": "error",
                "status_code": status.HTTP_404_NOT_FOUND,
                "message": "OTP verification failed.",
            }
            return Response(context)
    else:
        response = {
            "status": "error",
            "status_code": status.HTTP_400_BAD_REQUEST,
            "message": "Incomplete request.",
        }
        return Response(response)











@api_view(["POST"])
def resend_otp(request):
    request_id = request.data.get("request_id")
    phone = request.data.get("phone")

    is_temp_otp = Otp.objects.filter(
        request_id=request_id, verified=False, temp_user__phone=phone
    )
    is_user_otp = Otp.objects.filter(
        request_id=request_id, verified=False, requested_by__phone_number=phone
    )

    if is_temp_otp:
        otp = is_temp_otp[0]
        code = otp.code
        if phone != "9876543210":
            sendsms(str(code), phone)
        response = {
            "status": "success",
            "message": "OTP resend!",
            "route": "sign up",
        }
        return Response(response, status=status.HTTP_200_OK)
    elif is_user_otp:
        otp = is_user_otp[0]
        code = otp.code
        if phone != "9876543210":
            sendsms(str(code), phone)
        response = {
            "status": "success",
            "message": "OTP resend!",
            "route": "login",
        }
        return Response(response, status.HTTP_200_OK)
    else:
        response = {
            "status": "error",
            "message": "OTP does not exist",
        }
        return Response(response, status=status.HTTP_404_NOT_FOUND)
