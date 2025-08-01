# Generated by Django 5.2 on 2025-06-21 08:55

from django.db import migrations


def fix_null_ratings(apps, schema_editor):
    Freelancer = apps.get_model('freelancer', 'Freelancer')
    # Update any NULL ratings to 0.00
    Freelancer.objects.filter(rating__isnull=True).update(rating=0.00)


class Migration(migrations.Migration):

    dependencies = [
        ('freelancer', '0026_freelancer_cv_alter_freelancer_bkash_account_and_more'),
    ]

    operations = [
        migrations.RunPython(fix_null_ratings, reverse_code=migrations.RunPython.noop),
    ]
