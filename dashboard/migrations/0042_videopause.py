# Generated by Django 5.1.2 on 2025-05-12 04:46

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0041_exam_number_of_attempt'),
    ]

    operations = [
        migrations.CreateModel(
            name='VideoPause',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minutes_watched', models.TimeField(default='00:00:00')),
                ('total_duration', models.TimeField(default='00:00:00')),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='video_progress', to=settings.AUTH_USER_MODEL)),
                ('video', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress', to='dashboard.video')),
            ],
        ),
    ]
