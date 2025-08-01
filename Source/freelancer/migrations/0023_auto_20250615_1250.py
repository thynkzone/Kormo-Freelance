# Generated by Django 5.2 on 2025-06-15 06:50

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('freelancer', '0022_add_created_updated_to_subscriptionplan'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriptionplan',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
