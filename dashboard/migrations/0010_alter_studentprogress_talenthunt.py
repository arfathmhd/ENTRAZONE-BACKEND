# Generated by Django 5.1.2 on 2024-11-07 11:27

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0009_alter_studentprogress_exam_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentprogress',
            name='talenthunt',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='student_talentHunt', to='dashboard.talenthunt'),
        ),
    ]
