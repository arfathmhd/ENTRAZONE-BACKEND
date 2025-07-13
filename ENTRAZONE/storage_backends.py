from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    """
    Storage class for media files on DigitalOcean Spaces.
    """
    location = 'media'
    default_acl = 'public-read'
    file_overwrite = False
    querystring_auth=False

class PrivateMediaStorage(S3Boto3Storage):
    """
    Storage class for private media files on DigitalOcean Spaces.
    """
    location = settings.AWS_PRIVATE_MEDIA_LOCATION
    default_acl = 'private'
    file_overwrite = False

class StaticStorage(S3Boto3Storage):
    location = 'static'
    default_acl = 'public-read'
    file_overwrite = False
    querystring_auth=False
