# Generated by Django 5.1.2 on 2024-11-06 10:05

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0008_remove_studentprogress_completed_on_level_duration_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentprogress',
            name='exam',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='student_exams', to='dashboard.exam'),
        ),
        migrations.AlterField(
            model_name='studentprogress',
            name='student',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='progress', to=settings.AUTH_USER_MODEL),
        ),
    ]
