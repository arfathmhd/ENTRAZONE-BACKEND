# Generated by Django 5.1.2 on 2025-06-26 06:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0069_remove_course_order'),
    ]

    operations = [
        migrations.AlterField(
            model_name='video',
            name='m3u8',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name='video',
            name='tp_stream',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name='video',
            name='url',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
    ]
