import requests
import json
from django.conf import settings

def onesignal_request(heading, content, url=None, image_url=None, user_ids=None):
    """
    Send a push notification via OneSignal
    
    Args:
        heading: The notification title
        content: The notification message
        url: URL to open when notification is clicked (optional)
        image_url: URL of image to display in notification (optional)
        user_ids: List of user external IDs to target (optional, if None sends to all users)
    """
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Basic {settings.ONESIGNAL_API_KEY}"
    }
    
    payload = {
        "app_id": settings.ONESIGNAL_APP_ID,
        "headings": {"en": heading},
        "contents": {"en": content},
        "data": {"type": "notification"}
    }
    
    # Target specific users if user_ids are provided, otherwise send to all users
    if user_ids and isinstance(user_ids, list) and len(user_ids) > 0:
        payload["include_external_user_ids"] = user_ids
    else:
        payload["included_segments"] = ["All"]
    
    # Add optional parameters if provided
    if url:
        payload["url"] = url
    
    if image_url:
        payload["big_picture"] = image_url  # For Android
        payload["ios_attachments"] = {"id": image_url}  # For iOS
        payload["chrome_web_image"] = image_url  # For Chrome
    
    try:
        response = requests.post(
            "https://onesignal.com/api/v1/notifications",
            headers=headers,
            data=json.dumps(payload)
        )
        return response.json()
    except Exception as e:
        # Log the error but don't crash the application
        print(f"OneSignal API Error: {str(e)}")
        return {"error": str(e)}