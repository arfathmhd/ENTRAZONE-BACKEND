# Generated by Django 5.1.2 on 2024-11-06 04:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0006_alter_customuser_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='talenthunt',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='talenthunt_images/'),
        ),
    ]
