# Generated by Django 5.1.2 on 2025-06-24 07:06

import dashboard.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0066_chapter_old_id_course_old_id_currentaffairs_old_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='banner',
            name='image',
            field=models.ImageField(upload_to=dashboard.models.Banner.get_file_path),
        ),
        migrations.AlterField(
            model_name='chapter',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=dashboard.models.Chapter.get_file_path),
        ),
        migrations.AlterField(
            model_name='course',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=dashboard.models.Course.get_file_path),
        ),
        migrations.AlterField(
            model_name='currentaffairs',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=dashboard.models.CurrentAffairs.get_file_path),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=dashboard.models.CustomUser.get_file_path),
        ),
        migrations.AlterField(
            model_name='exam',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=dashboard.models.Exam.get_file_path),
        ),
        migrations.AlterField(
            model_name='lesson',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=dashboard.models.Lesson.get_file_path),
        ),
        migrations.AlterField(
            model_name='notification',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=dashboard.models.Notification.get_file_path),
        ),
        migrations.AlterField(
            model_name='pdfnote',
            name='file',
            field=models.FileField(upload_to=dashboard.models.PDFNote.get_file_path),
        ),
        migrations.AlterField(
            model_name='question',
            name='explanation_image',
            field=models.ImageField(blank=True, null=True, upload_to=dashboard.models.Question.get_file_path),
        ),
        migrations.AlterField(
            model_name='subject',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=dashboard.models.Subject.get_file_path),
        ),
        migrations.AlterField(
            model_name='talenthunt',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=dashboard.models.TalentHunt.get_file_path),
        ),
    ]
