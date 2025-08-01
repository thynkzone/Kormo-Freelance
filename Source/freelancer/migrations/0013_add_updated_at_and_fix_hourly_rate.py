# Generated by Django 5.2 on 2025-05-02 10:18

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('freelancer', '0012_add_video_introduction'),
    ]

    operations = [
        migrations.AddField(
            model_name='freelancer',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='freelancer',
            name='hourly_rate',
            field=models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]
