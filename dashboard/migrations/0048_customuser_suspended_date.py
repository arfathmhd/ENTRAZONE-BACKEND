# Generated by Django 5.1.2 on 2025-05-20 05:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0047_customuser_is_suspended'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='suspended_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
