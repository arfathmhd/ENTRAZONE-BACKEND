from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
import os


class CKEditorS3Storage(S3Boto3Storage):
    """
    Custom storage for CKEditor that properly handles S3 directory browsing.
    """
    location = settings.AWS_LOCATION + '/uploads' if hasattr(settings, 'AWS_LOCATION') else 'uploads'
    default_acl = 'public-read'
    file_overwrite = False
    querystring_auth = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_uploads_directory()

    def _create_uploads_directory(self):
        """Create the uploads directory structure in S3 if it doesn't exist."""
        try:
            # Create main uploads directory
            self.connection.meta.client.put_object(
                Bucket=self.bucket_name,
                Key=f"{self.location}/",
                Body=''
            )
            # Create images subdirectory
            self.connection.meta.client.put_object(
                Bucket=self.bucket_name,
                Key=f"{self.location}/images/",
                Body=''
            )
        except Exception:
            # Silently pass if directory already exists or other issues
            pass

    def listdir(self, path):
        """
        Override listdir to handle S3 directory structure properly.
        This is the key method that fixes the NoSuchKey error.
        """
        path = self._normalize_name(path)
        # The path needs to end with a slash to prevent incorrect prefix matching
        if path and not path.endswith('/'):
            path += '/'

        directories, files = [], []
        paginator = self.connection.meta.client.get_paginator('list_objects_v2')
        
        try:
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=path, Delimiter='/')
            
            for page in pages:
                # Handle directories (CommonPrefixes)
                for prefix in page.get('CommonPrefixes', []):
                    directories.append(os.path.basename(prefix.get('Prefix').rstrip('/')))
                
                # Handle files
                for obj in page.get('Contents', []):
                    file_key = obj.get('Key')
                    if file_key != path:  # Skip the directory marker itself
                        files.append(os.path.basename(file_key))
        except Exception:
            # If the directory doesn't exist yet, return empty lists
            pass
            
        return directories, files

    def get_available_name(self, name, max_length=None):
        """Generate a unique filename for uploads."""
        import os
        import string
        import random
        from datetime import datetime
        
        def get_random_string():
            chars = string.ascii_lowercase
            strin = "".join(random.choice(chars) for _ in range(6))
            date = datetime.now().strftime("%m%d%H%M%S")
            return "f" + date + strin



        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        ext = file_name.split(".")[-1]
        tmp = get_random_string()
        filename = "%s.%s" % (tmp, ext)
        # name = os.path.join("uploads", filename)
        
        return filename
