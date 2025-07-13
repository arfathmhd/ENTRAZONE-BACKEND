from dashboard.views.imports import *

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_profile(request):
    user = request.user

    valid_districts = dict(CustomUser.STATE_CHOICES)
    district_name = valid_districts.get(user.district, "")  

    image_url = request.build_absolute_uri(user.image.url) if user.image else ""

    user_details = {
        "id": user.id,
        "name": user.name if user.name else "",
        "image": image_url,
        "email": user.email if user.email else "",
        "district": {
            "id": user.district,  
            "name": district_name  
        }
    }

    return Response({
        "status": "success", 
        "message": "Profile details retrieved successfully",
        "user": user_details
    }, status=status.HTTP_200_OK)


@api_view(["PUT"])
@csrf_exempt  
@permission_classes([IsAuthenticated])
def update_profile(request):
    if request.method == 'PUT':
        # user_id = request.data.get("user_id")
        user_id=request.user.id
        
        # if user_id is None:
        #     return Response({"status": "error", "message": "User ID must be provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(id=user_id, is_deleted=False)
        except CustomUser.DoesNotExist:
            return Response({"status": "error", "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get("name", user.name)
        district_number = request.data.get("district", user.district)
        email = request.data.get("email", user.email)

        image = request.FILES.get("image")

        if not name:
            return Response({"status": "error", "message": "Please provide a valid name"}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_districts = dict(CustomUser.STATE_CHOICES)
        if district_number not in valid_districts:
            return Response({"status": "error", "message": "Invalid district number"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not email:
            return Response({"status": "error", "message": "Please provide a valid email"}, status=status.HTTP_400_BAD_REQUEST)

        user.name = name
        user.district = district_number
        user.email = email

        if image:
            user.image = image
        
        try:
            user.save()

            district_name = valid_districts.get(district_number, "")
            
            user_details = {
                "id": user.id,
                # "username": user.username,
                "name": user.name,
                "image": request.build_absolute_uri(user.image.url) if user.image else "",
                "email": user.email,
                "district": district_name,  
            }

            return Response({"status": "success", "message": "Profile updated successfully", "user": user_details}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({"status": "error", "message": "Invalid request method"}, status=status.HTTP_400_BAD_REQUEST)
