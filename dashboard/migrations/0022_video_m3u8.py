# Generated by Django 5.1.2 on 2024-11-29 12:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0021_rename_m3u8_video_is_m3u8'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='m3u8',
            field=models.URLField(blank=True, null=True),
        ),
    ]
